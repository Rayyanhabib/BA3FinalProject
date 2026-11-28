"""
STAGE 2 - Censoring-aware quantile forecasting + production decision backtest.

What it builds
  1. Features from RECOVERED demand (stage 1), so stocked-out days stop biasing the history.
  2. LightGBM quantile models (tau = 0.5 ... 0.9) on a scale-free target (demand / recent level).
  3. Conformal calibration of the quantiles on a held-out week.
  4. A newsvendor decision layer: "make q_tau" -> waste vs missed-sales trade-off curve,
     compared with a simulated store habit (last week's sales + 15%).
  5. An ablation: the same model WITHOUT demand recovery, to show what recovery is worth.

Run from the repo root with the venv active:
    python src/train_advanced_final.py --sample-series 5000      # quick check (a few minutes)
    python src/train_advanced_final.py                           # all 50,000 series (long)
    python src/train_advanced_final.py --threads 8               # set CPU threads

Needs: data/processed/fresh_clean.parquet (clean_data.py) and
       data/processed/fresh_recovered_final.parquet (demand_recovery_final.py)

Time layout (day 0 = 2024-03-28; 97 days):
    train   days 14-75   |  early stopping  days 76-82  |  calibration + W3 test  days 83-89
    final model trained on days 14-89  ->  FINAL TEST = the 7-day eval split, days 90-96
Every feature for day t uses only days < t (plus covariates that are known in advance:
planned discount, holiday/activity flags, weather forecast).
"""
import argparse
import pathlib
import time
import warnings

import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
ap = argparse.ArgumentParser()
ap.add_argument("--clean", default="data/processed/fresh_clean.parquet")
ap.add_argument("--tag", default="_final", help="suffix added to every output file name")
ap.add_argument("--recovered", default=None, help="default: data/processed/fresh_recovered<tag>.parquet")
ap.add_argument("--out", default="results")
ap.add_argument("--sample-series", type=int, default=0, help="0 = all series")
ap.add_argument("--quantiles", type=float, nargs="+", default=[0.5, 0.6, 0.7, 0.8, 0.9])
ap.add_argument("--service-alpha", type=float, default=0.8, help="quantile used for recommendations")
ap.add_argument("--rec-weight", type=float, default=0.5, help="training weight of recovered (stocked-out) days")
ap.add_argument("--habit-buffer", type=float, default=0.15)
ap.add_argument("--threads", type=int, default=0, help="0 = all cores")
ap.add_argument("--rounds", type=int, default=600)
ap.add_argument("--skip-ablation", action="store_true")
ap.add_argument("--use-calibration", action="store_true",
                help="apply conformal shifts to the quantiles used for decisions (off by default)")
args = ap.parse_args()
TAG = args.tag
if args.recovered is None:
    args.recovered = f"data/processed/fresh_recovered{TAG}.parquet"

SEED = 42
OUT = pathlib.Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


# =============================================================== 1. load, align
clean = pd.read_parquet(args.clean)
clean["date"] = pd.to_datetime(clean["date"])
rec = pd.read_parquet(args.recovered)
rec["date"] = pd.to_datetime(rec["date"])
keys = ["store_id", "product_id", "date"]
if args.sample_series:
    pick = clean[["store_id", "product_id"]].drop_duplicates().sample(
        args.sample_series, random_state=SEED)
    clean = clean.merge(pick, on=["store_id", "product_id"])
    rec = rec.merge(pick, on=["store_id", "product_id"])
df = clean.merge(rec[keys + ["demand_rec", "coverage"]], on=keys, how="left")
df = df.sort_values(keys).reset_index(drop=True)
del clean, rec
S = df[["store_id", "product_id"]].drop_duplicates().shape[0]
T = df["date"].nunique()
assert len(df) == S * T and T == 97, f"expected complete series of 97 days, got {len(df)} rows / {S} series"
log(f"series: {S:,}   days: {T}   rows: {len(df):,}")

M = lambda c: df[c].to_numpy("float64").reshape(S, T)          # series x day matrices
obs, stock, disc = M("sale_amount"), M("stock_hour6_22_cnt"), M("discount")
act, hol = M("activity_flag"), M("holiday_flag")
rain, temp, hum, wind = M("precpt"), M("avg_temperature"), M("avg_humidity"), M("avg_wind_level")
drec, cover = M("demand_rec"), M("coverage")
usable = df["usable"].to_numpy().reshape(S, T)                  # in stock all day AND discount ok
valid = disc > 0
dates = df["date"].to_numpy().reshape(S, T)[0]
dow = pd.DatetimeIndex(dates).dayofweek.to_numpy()
meta = df.iloc[::T]
grp = {"store": meta["store_id"].to_numpy(), "product": meta["product_id"].to_numpy(),
       "cat": meta["first_category_id"].to_numpy(), "city": meta["city_id"].to_numpy()}
didx = np.tile(np.arange(T), (S, 1))


# =============================================================== 2. features
def shift(A, k):
    out = np.full_like(A, np.nan)
    out[:, k:] = A[:, :-k]
    return out


def sroll(A, w, minp, stat="mean"):                              # uses days t-w .. t-1 only
    r = pd.DataFrame(A.T).shift(1).rolling(w, min_periods=minp)
    return getattr(r, stat)().to_numpy().T


def group_index(R, g, name):
    gm = pd.DataFrame(R).groupby(g).mean()
    return gm.reindex(g).to_numpy()


def make_features(H):
    """H = demand signal used for history (S x T, NaN where unknown)."""
    f = {}
    for k in (1, 2, 3, 7, 14):
        f[f"lag{k}"] = shift(H, k)
    for w, mp in ((3, 2), (7, 3), (14, 5), (28, 7)):
        f[f"ma{w}"] = sroll(H, w, mp)
    f["std7"], f["std14"] = sroll(H, 7, 3, "std"), sroll(H, 14, 5, "std")
    f["same_dow_mean"] = np.nanmean(np.stack([shift(H, 7), shift(H, 14), shift(H, 21)]), axis=0)
    base = np.maximum(f["ma28"], 0.05)
    f["trend7_28"] = f["ma7"] / base
    # demand shocks shared by a store / product / category / city (relative to each series' own level)
    R = H / base
    for name, g in grp.items():
        idx = group_index(R, g, name)
        f[f"{name}_idx_lag1"] = shift(idx, 1)
        f[f"{name}_idx_ma7"] = sroll(idx, 7, 3)
    # hidden-demand signals from stockouts
    f["stock_lag1"], f["stock_ma7"] = shift(stock, 1), sroll(stock, 7, 3)
    f["cover_lag1"] = shift(cover, 1)
    # covariates known in advance for day t
    f["discount"], f["discount_lag1"], f["discount_ma7"] = disc, shift(disc, 1), sroll(disc, 7, 3)
    f["activity"], f["holiday"], f["holiday_lag1"] = act, hol, shift(hol, 1)
    f["precpt"], f["precpt_lag1"] = rain, shift(rain, 1)
    f["temp"], f["temp_diff"] = temp, temp - shift(temp, 1)
    f["humidity"], f["wind"] = hum, wind
    flat = {k: v.reshape(-1).astype("float32") for k, v in f.items()}
    X = pd.DataFrame(flat)
    X["dow"] = np.tile(dow, S).astype("int8")
    X["cat"] = np.repeat(pd.factorize(grp["cat"])[0], T).astype("int16")
    X["city"] = np.repeat(pd.factorize(grp["city"])[0], T).astype("int16")
    return X, base.reshape(-1), H.reshape(-1)


H_rec = np.where(valid & np.isfinite(drec), drec, np.nan)       # recovered demand history
H_obs = np.where(valid & usable, obs, np.nan)                   # uncensored sales only (ablation)
variants = {"recovered": H_rec}
if not args.skip_ablation:
    variants["observed_only"] = H_obs
FEATS = {}
for name, H in variants.items():
    FEATS[name] = make_features(H)
    log(f"features built: {name}  ({FEATS[name][0].shape[1]} columns)")
CATS = ["dow", "cat", "city"]

# =============================================================== 3. masks and targets
day = didx.reshape(-1)
y_obs = obs.reshape(-1)
true_ok = usable.reshape(-1)                                     # observed sales == true demand
w_rec = np.where(true_ok, 1.0, args.rec_weight)


def rows_in(lo, hi):
    return (day >= lo) & (day <= hi)


W3 = rows_in(83, 89) & true_ok            # out-of-sample week for calibration and a first test
W4 = rows_in(90, 96) & true_ok            # FINAL TEST: the eval split, uncensored rows
log(f"test rows  W3 (days 83-89): {int(W3.sum()):,}   FINAL W4 (days 90-96): {int(W4.sum()):,}")


def train_rows(H_flat, base, lo, hi):
    return rows_in(lo, hi) & np.isfinite(H_flat) & np.isfinite(base)


# =============================================================== 4. model fitting
nthreads = args.threads if args.threads else -1


def params(alpha):
    return dict(objective="quantile", alpha=alpha, learning_rate=0.06, num_leaves=63,
                min_data_in_leaf=100, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
                lambda_l2=1.0, max_bin=127, verbose=-1, seed=SEED, num_threads=nthreads)


def make_ds(X, idx, H_flat, base, weights):
    y = H_flat[idx] / base[idx]
    return lgb.Dataset(X.iloc[idx], y, weight=(base[idx] * weights[idx]),
                       categorical_feature=CATS, free_raw_data=False)


def fit(variant, alpha):
    X, base, Hf = FEATS[variant]
    tr = np.flatnonzero(train_rows(Hf, base, 14, 75))
    va = np.flatnonzero(train_rows(Hf, base, 76, 82))
    dtr, dva = make_ds(X, tr, Hf, base, w_rec), make_ds(X, va, Hf, base, w_rec)
    m_cal = lgb.train(params(alpha), dtr, args.rounds, valid_sets=[dva],
                      callbacks=[lgb.early_stopping(40, verbose=False)])
    best = max(m_cal.best_iteration, 20)
    fin = np.flatnonzero(train_rows(Hf, base, 14, 89))
    m_fin = lgb.train(params(alpha), make_ds(X, fin, Hf, base, w_rec), int(best * 1.15) + 1)
    return m_cal, m_fin, best


def predict(model, variant, mask):
    X, base, _ = FEATS[variant]
    ok = mask & np.isfinite(base)
    p = np.full(len(X), np.nan)
    p[ok] = np.clip(model.predict(X[ok]), 0, None) * base[ok]
    return p


def wquantile(e, w, q):
    o = np.argsort(e)
    e, w = e[o], w[o]
    c = np.cumsum(w) / w.sum()
    return e[min(np.searchsorted(c, q), len(e) - 1)]


models, preds_w3, preds_w4 = {}, {}, {}
fit_plan = {"recovered": args.quantiles, "observed_only": [0.5]}
for variant, qs in fit_plan.items():
    if variant not in FEATS:
        continue
    for a in qs:
        m_cal, m_fin, best = fit(variant, a)
        models[(variant, a)] = m_fin
        preds_w3[(variant, a)] = predict(m_cal, variant, W3)
        preds_w4[(variant, a)] = predict(m_fin, variant, W4)
        log(f"fitted {variant} tau={a}  (best rounds {best})")

# =============================================================== 5. conformal calibration
base_rec = FEATS["recovered"][1]
shifts = {}
for a in args.quantiles:
    p = preds_w3[("recovered", a)]
    ok = W3 & np.isfinite(p) & np.isfinite(base_rec)
    e = (y_obs[ok] - p[ok]) / base_rec[ok]                       # miss in "relative demand" units
    shifts[a] = wquantile(e, base_rec[ok], a)                    # >0 means quantile was too low
cal_w4 = {}
stack = np.stack([preds_w4[("recovered", a)] + shifts[a] * base_rec for a in args.quantiles])
stack = np.sort(np.clip(stack, 0, None), axis=0)                 # no crossing quantiles
for i, a in enumerate(args.quantiles):
    cal_w4[a] = stack[i]
log("calibration shifts (relative units): " + ", ".join(f"{a}: {shifts[a]:+.3f}" for a in args.quantiles))

# =============================================================== 6. accuracy table (same rows for every model)
def metrics(y, p, label, alpha=None):
    r = {"model": label, "rows": len(y), "MAE": np.abs(y - p).mean(),
         "WAPE": np.abs(y - p).sum() / y.sum(), "bias": p.sum() / y.sum() - 1}
    if alpha is not None:
        d = y - p
        r["pinball"] = np.mean(np.maximum(alpha * d, (alpha - 1) * d))
        r["coverage"] = np.mean(y <= p)
    return r


Xo, base_o, _ = FEATS["observed_only"] if "observed_only" in FEATS else make_features(H_obs)
fin = lambda a: np.isfinite(a)
lag7_base = np.where(fin(Xo["lag7"]), Xo["lag7"], np.where(fin(Xo["ma7"]), Xo["ma7"], Xo["ma28"])).astype(float)
ma7_base = np.where(fin(Xo["ma7"]), Xo["ma7"], Xo["ma28"]).astype(float)


def lasso_preds():
    Xl = Xo.copy()
    for c in CATS:
        Xl = pd.concat([Xl.drop(columns=c), pd.get_dummies(Xl[c], prefix=c).astype("float32")], axis=1)
    Hf = H_obs.reshape(-1)
    idx = np.flatnonzero(train_rows(Hf, base_o, 14, 89))
    mdl = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Lasso(alpha=1e-4, max_iter=3000))
    mdl.fit(Xl.iloc[idx], Hf[idx] / base_o[idx], lasso__sample_weight=base_o[idx])
    ok = W4 & fin(base_o)
    p = np.full(len(Xl), np.nan)
    p[ok] = np.clip(mdl.predict(Xl[ok]), 0, None) * base_o[ok]
    return p


lasso_p = lasso_preds()
qraw = {a: preds_w4[("recovered", a)] for a in args.quantiles}
obs_p = preds_w4.get(("observed_only", 0.5))
cm = W4 & fin(lag7_base) & fin(ma7_base) & fin(lasso_p)
for a in args.quantiles:
    cm &= fin(qraw[a]) & fin(cal_w4[a])
if obs_p is not None:
    cm &= fin(obs_p)
log(f"final-test rows scored (identical for every model): {int(cm.sum()):,} of {int(W4.sum()):,}")

y4 = y_obs[cm]
rows = [metrics(y4, lag7_base[cm], "Baseline: same day last week"),
        metrics(y4, ma7_base[cm], "7-day moving average"),
        metrics(y4, lasso_p[cm], "Lasso (observed history)")]
if obs_p is not None:
    rows.append(metrics(y4, obs_p[cm], "LightGBM median, NO demand recovery", 0.5))
rows.append(metrics(y4, qraw[0.5][cm], "LightGBM median + demand recovery", 0.5) if 0.5 in qraw else {})
for a in args.quantiles:
    rows.append(metrics(y4, qraw[a][cm], f"LightGBM q{int(a * 100)} raw", a))
    rows.append(metrics(y4, cal_w4[a][cm], f"LightGBM q{int(a * 100)} conformal-calibrated", a))
res = pd.DataFrame([r for r in rows if r])
res["MAE_vs_baseline"] = res["MAE"] / res.loc[0, "MAE"] - 1
res.to_csv(OUT / f"fresh_advanced_metrics{TAG}.csv", index=False)
pd.set_option("display.width", 220)
print("\nACCURACY on the final test week, uncensored days only (observed sales = true demand)")
print(res.round(4).to_string(index=False))

imp = pd.Series(models[("recovered", 0.5)].feature_importance("gain"),
                index=FEATS["recovered"][0].columns).sort_values(ascending=False)
(imp / imp.sum()).rename("gain_share").to_csv(OUT / f"fresh_advanced_importance{TAG}.csv")
print("\nTop features (share of gain):\n", (imp / imp.sum()).head(10).round(3).to_string())

# =============================================================== 7. decision backtests
bs = np.round(np.arange(0, 1.001, 0.025), 3)


def outcomes(sold, made):
    tot = sold.sum()
    return np.clip(made - sold, 0, None).sum() / tot, np.clip(sold - made, 0, None).sum() / tot


def run_backtest(name, mask, truth, habit, ma7, preds, with_cal):
    """waste% and missed% of demand for the store habit and for the model-based plans."""
    sold = truth[mask]
    curves = {"Store habit: last week x (1+b)": [(b, *outcomes(sold, habit[mask] * (1 + b))) for b in bs],
              "7-day average x (1+b)  [smart non-ML]": [(b, *outcomes(sold, ma7[mask] * (1 + b))) for b in bs]}
    if preds.get(("observed_only", 0.5)) is not None:
        p = preds[("observed_only", 0.5)][mask]
        curves["Median x (1+b), no recovery"] = [(b, *outcomes(sold, p * (1 + b))) for b in bs]
    p = preds[("recovered", 0.5)][mask]
    curves["Median x (1+b), with recovery"] = [(b, *outcomes(sold, p * (1 + b))) for b in bs]
    curves["Quantile q_tau, with recovery"] = [(a, *outcomes(sold, preds[("recovered", a)][mask]))
                                                for a in args.quantiles]
    if with_cal:
        curves["Quantile q_tau, conformal-calibrated"] = [(a, *outcomes(sold, cal_w4[a][mask]))
                                                          for a in args.quantiles]
    hw, hm = outcomes(sold, habit[mask] * (1 + args.habit_buffer))
    print(f"\nBACKTEST {name}: {int(mask.sum()):,} rows. Simulated habit = last week x "
          f"{1 + args.habit_buffer:.2f}  ->  waste {hw:.1%}, missed {hm:.1%} of demand")
    for k, v in curves.items():
        if k.startswith("Store"):
            continue
        same_m = [x for x in v if x[2] <= hm]
        same_w = [x for x in v if x[1] <= hw]
        line = f"  {k}:"
        if same_m:
            _, w, m = min(same_m, key=lambda x: x[1])
            line += f" same missed sales -> waste {w:.1%} ({w / hw - 1:+.0%});"
        if same_w:
            _, w, m = min(same_w, key=lambda x: x[2])
            line += f" same waste -> missed {m:.1%} ({m / hm - 1:+.0%})"
        print(line)
    df_out = pd.DataFrame([{"test": name, "strategy": k, "parameter": p_, "waste_pct": w, "missed_pct": m}
                           for k, v in curves.items() for (p_, w, m) in v])
    return curves, (hw, hm), df_out


# A) uncensored days only: observed sales are true demand, but these are the easier, lower-demand days
curves_A, ref_A, bt_A = run_backtest("A (uncensored days)", cm, y_obs, lag7_base, ma7_base, {**preds_w4, **{("recovered", a): qraw[a] for a in args.quantiles}}, True)

# B) ALL days: truth = observed sales if the product stayed in stock, else recovered demand
#    (recovery validated to ~0% bias by the masking test). The store habit sees only its own
#    recorded (censored) sales, as a real store would.
drec_f, valid_f = drec.reshape(-1), valid.reshape(-1)
truth_B = np.where(true_ok, y_obs, drec_f)
ALL4 = rows_in(90, 96) & valid_f & fin(truth_B)
Hraw = np.where(valid, obs, np.nan)
raw7 = shift(Hraw, 7).reshape(-1)
raw_ma7 = sroll(Hraw, 7, 3).reshape(-1)
habit_B = np.where(fin(raw7), raw7, raw_ma7)
ma7_B = raw_ma7
predsB = {}
for (variant, a), mdl in models.items():
    predsB[(variant, a)] = predict(mdl, variant, ALL4)
cmB = ALL4 & fin(habit_B) & fin(ma7_B)
for k, v in predsB.items():
    cmB &= fin(v)
curves_B, ref_B, bt_B = run_backtest("B (all days, recovered truth)", cmB, truth_B, habit_B, ma7_B, predsB, False)
pd.concat([bt_A, bt_B]).to_csv(OUT / f"fresh_advanced_backtest{TAG}.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
sty = {"Store habit: last week x (1+b)": ("#999999", "o-"),
       "7-day average x (1+b)  [smart non-ML]": ("#27ae60", "P-"),
       "Median x (1+b), no recovery": ("#d98c1f", "s-"),
       "Median x (1+b), with recovery": ("#2a7de1", "^-"),
       "Quantile q_tau, with recovery": ("#c0392b", "D-"),
       "Quantile q_tau, conformal-calibrated": ("#7d3c98", "v--")}
for ax, curves, ref, ttl in [(axes[0], curves_A, ref_A, "A) Uncensored days only"),
                             (axes[1], curves_B, ref_B, "B) All days (stockouts recovered)")]:
    for k, v in curves.items():
        ax.plot([m * 100 for _, _, m in v], [w * 100 for _, w, _ in v], sty[k][1], color=sty[k][0],
                label=k, ms=4, lw=1.4)
    ax.plot(ref[1] * 100, ref[0] * 100, "k*", ms=14, label=f"Habit at +{args.habit_buffer:.0%}")
    ax.set_title(ttl); ax.set_xlabel("Missed sales (% of demand)"); ax.grid(alpha=0.3)
    ax.set_xlim(0, 45); ax.set_ylim(0, 70)
axes[0].set_ylabel("Waste (% of demand)")
axes[0].legend(fontsize=7.5)
fig.suptitle("Waste vs missed sales, final test week (lower-left is better)")
fig.tight_layout(); fig.savefig(OUT / f"fresh_advanced_frontier{TAG}.png", dpi=160)

# =============================================================== 8. recommendation mock-up (last day)
last = rows_in(96, 96)
sh = shifts if args.use_calibration else {a: 0.0 for a in args.quantiles}
rs = np.stack([predict(models[("recovered", a)], "recovered", last) + sh[a] * base_rec for a in args.quantiles])
rs = np.sort(np.clip(rs, 0, None), axis=0)
ia = int(np.argmin([abs(a - args.service_alpha) for a in args.quantiles]))
make = rs[ia]
leftover = np.clip(make[None, :] - rs, 0, None).mean(0)          # approx E[(make - demand)+] from the quantile grid
sel = np.flatnonzero(last & fin(make))
mock = pd.DataFrame({"store_id": df["store_id"].to_numpy()[sel], "product_id": df["product_id"].to_numpy()[sel],
                     "date": df["date"].to_numpy()[sel],
                     "forecast_median": rs[args.quantiles.index(0.5)][sel] if 0.5 in args.quantiles else np.nan,
                     "recommended_make": make[sel], "expected_leftover_approx": leftover[sel]})
num = mock.select_dtypes("number").columns
mock[num] = mock[num].round(3)
mock.head(300).to_csv(OUT / f"fresh_recommendations_sample{TAG}.csv", index=False)
log(f"saved results to {OUT}/  (metrics, backtest, importance, frontier chart, recommendations sample)")
