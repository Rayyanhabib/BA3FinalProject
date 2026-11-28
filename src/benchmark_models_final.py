"""
Benchmark many ML models on all three datasets with ONE identical protocol.

Datasets : fresh (FreshRetailNet), favorita (bakery/deli/poultry/prepared foods), dominicks (bakery + deli $)
Models   : 3 no-ML benchmarks + Linear, Ridge, Lasso, ElasticNet, Decision tree, Random forest,
           Extra trees, HistGradientBoosting, LightGBM (mean and median), XGBoost, MLP, Ensemble
Protocol : features for day t use only days before t (plus covariates known in advance);
           train on the past, test on the LAST window of each dataset (never shuffled in time);
           every model is scored on exactly the same test rows.

Run from the repo root with the venv active:
    pip install lightgbm xgboost
    python src/benchmark_models_final.py --profile quick     # a few minutes per dataset, subsampled
    python src/benchmark_models_final.py --profile full      # much larger samples (long run)
    python src/benchmark_models_final.py --datasets fresh dominicks --threads 8

Needs data/processed/{fresh_clean,favorita_clean,dominicks_clean}.parquet (src/clean_data.py).

Outputs (results/):
    benchmark_all_models_final.csv      one row per dataset x model (use this for tables)
    benchmark_summary_final.json        same data plus dataset metadata (use this for a website)
    benchmark_report_final.md           ready-to-paste markdown tables
    benchmark_mae_improvement_final.png chart: each model vs the "same day last week" benchmark
    benchmark_importance_<dataset>_final.csv  top LightGBM features
"""
import argparse
import json
import pathlib
import time
import warnings

import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

try:
    import xgboost as xgb
except Exception:                                   # xgboost is optional
    xgb = None

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser()
ap.add_argument("--in-dir", default="data/processed")
ap.add_argument("--out", default="results")
ap.add_argument("--datasets", nargs="+", default=["fresh", "favorita", "dominicks"],
                choices=["fresh", "favorita", "dominicks"])
ap.add_argument("--profile", default="quick", choices=["quick", "full"])
ap.add_argument("--max-series", type=int, default=0, help="override series cap for every dataset")
ap.add_argument("--max-train-rows", type=int, default=0, help="override training-row cap")
ap.add_argument("--rf-trees", type=int, default=0, help="override trees for random forest / extra trees")
ap.add_argument("--gbm-rounds", type=int, default=0, help="override boosting rounds")
ap.add_argument("--ens-rows", type=int, default=0, help="override training rows for random forest / extra trees")
ap.add_argument("--tag", default="_final", help="suffix added to every output file name")
ap.add_argument("--habit-buffer", type=float, default=0.15)
ap.add_argument("--threads", type=int, default=0, help="0 = all cores")
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

TAG = args.tag
IN, OUT = pathlib.Path(args.in_dir), pathlib.Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)
NT = args.threads if args.threads else -1
SEED = args.seed
T0 = time.time()
PROFILE = {
    "quick": dict(series={"fresh": 1500, "favorita": 700, "dominicks": 0}, train_rows=150_000,
                  ens_rows=40_000, rf_trees=60, rf_depth=14, gbm_rounds=200, mlp_iter=40),
    "full": dict(series={"fresh": 20_000, "favorita": 3_000, "dominicks": 0}, train_rows=1_000_000,
                 ens_rows=250_000, rf_trees=100, rf_depth=18, gbm_rounds=500, mlp_iter=60),
}[args.profile]


if args.rf_trees:
    PROFILE["rf_trees"] = args.rf_trees
if args.gbm_rounds:
    PROFILE["gbm_rounds"] = args.gbm_rounds
if args.ens_rows:
    PROFILE["ens_rows"] = args.ens_rows


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


# ============================================================================ helpers
def shift(A, k):
    out = np.full_like(A, np.nan)
    if k < A.shape[1]:
        out[:, k:] = A[:, :-k]
    return out


def sroll(A, w, minp, stat="mean"):                     # uses days t-w .. t-1 only
    r = pd.DataFrame(A.T).shift(1).rolling(w, min_periods=minp)
    return getattr(r, stat)().to_numpy().T


def group_index(R, g):
    return pd.DataFrame(R).groupby(g).mean().reindex(g).to_numpy()


def calendar(dates, us_holidays, cols):
    d = pd.DatetimeIndex(dates)
    cal = {"dow": d.dayofweek.to_numpy(), "dom": d.day.to_numpy(), "month": d.month.to_numpy(),
           "month_end": d.is_month_end.astype(int), "payday": ((d.day == 15) | d.is_month_end).astype(int)}
    if us_holidays:
        hol = USFederalHolidayCalendar().holidays(d.min(), d.max())
        cal["us_holiday"] = d.isin(hol).astype(int)
        cal["day_before_holiday"] = (d + pd.Timedelta(days=1)).isin(hol).astype(int)
    return {k: v for k, v in cal.items() if k in cols or cols == "all"}


# ============================================================================ dataset loaders
def pick_series(df, keys, cap):
    if cap:
        pick = df[keys].drop_duplicates()
        pick = pick.sample(min(cap, len(pick)), random_state=SEED)
        df = df.merge(pick, on=keys)
    return df


def load_fresh(cap):
    df = pd.read_parquet(IN / "fresh_clean.parquet")
    df["date"] = pd.to_datetime(df["date"])
    df = pick_series(df, ["store_id", "product_id"], cap)
    df = df.sort_values(["store_id", "product_id", "date"]).reset_index(drop=True)
    S, T = df[["store_id", "product_id"]].drop_duplicates().shape[0], df["date"].nunique()
    assert len(df) == S * T
    M = lambda c: df[c].to_numpy("float64").reshape(S, T)
    H = np.where(df["usable"].to_numpy().reshape(S, T), M("sale_amount"), np.nan)
    meta = df.iloc[::T]
    dates = df["date"].to_numpy().reshape(S, T)[0]
    return dict(
        name="fresh", label="FreshRetailNet-50K (China, perishables, daily, 2024)", unit="normalized units",
        H=H, dates=dates, test_lo=90, test_hi=96, min_hist=14,
        known={"discount": M("discount"), "activity": M("activity_flag"), "holiday": M("holiday_flag"),
               "precpt": M("precpt"), "temp": M("avg_temperature"), "humidity": M("avg_humidity"),
               "wind": M("avg_wind_level")},
        past={"stock": M("stock_hour6_22_cnt")},
        groups={"store": meta["store_id"].to_numpy(), "product": meta["product_id"].to_numpy(),
                "cat": meta["first_category_id"].to_numpy(), "city": meta["city_id"].to_numpy()},
        statics={"cat": pd.factorize(meta["first_category_id"])[0], "city": pd.factorize(meta["city_id"])[0]},
        cal_cols=["dow"], us_holidays=False, cat_features=["dow", "cat", "city"], onehot=["dow", "cat", "city"],
        drop_linear=[], test_desc="2024-06-26 to 2024-07-02 (the dataset's eval week)")


def load_favorita(cap):
    df = pd.read_parquet(IN / "favorita_clean.parquet",
                         columns=["date", "store_nbr", "item_nbr", "unit_sales", "onpromotion", "family"])
    df["date"] = pd.to_datetime(df["date"])
    df = pick_series(df, ["store_nbr", "item_nbr"], cap)
    df["sid"] = df.groupby(["store_nbr", "item_nbr"]).ngroup()
    d0 = df["date"].min()
    t = (df["date"] - d0).dt.days.to_numpy()
    S, T = df["sid"].nunique(), int(t.max()) + 1
    sid = df["sid"].to_numpy()
    H = np.full((S, T), np.nan)
    H[sid, t] = df["unit_sales"].to_numpy()
    promo = np.zeros((S, T))
    promo[sid, t] = df["onpromotion"].to_numpy()
    meta = df.drop_duplicates("sid").sort_values("sid")
    dates = (d0 + pd.to_timedelta(np.arange(T), unit="D")).to_numpy()
    return dict(
        name="favorita", label="Favorita (Ecuador grocery: bakery, deli, poultry, prepared foods, 2014-2017)",
        unit="units (some by weight)", H=H, dates=dates, test_lo=T - 28, test_hi=T - 1, min_hist=28,
        known={"promo": promo}, past={},
        groups={"store": meta["store_nbr"].to_numpy(), "item": meta["item_nbr"].to_numpy(),
                "family": meta["family"].astype(str).to_numpy()},
        statics={"family": pd.factorize(meta["family"].astype(str))[0],
                 "store": pd.factorize(meta["store_nbr"])[0]},
        cal_cols=["dow", "dom", "month", "month_end", "payday"], us_holidays=False,
        cat_features=["dow", "family", "store"], onehot=["dow", "month", "family"], drop_linear=["store"],
        test_desc=f"{pd.Timestamp(dates[T - 28]).date()} to {pd.Timestamp(dates[T - 1]).date()} (last 28 days)")


def load_dominicks(cap):
    df = pd.read_parquet(IN / "dominicks_clean.parquet",
                         columns=["store", "date", "bakery", "deli", "custcoun", "usable"])
    df["date"] = pd.to_datetime(df["date"])
    d0, d1 = df["date"].min(), df["date"].max()
    T = (d1 - d0).days + 1
    stores = np.sort(df["store"].unique())
    si = np.searchsorted(stores, df["store"].to_numpy())
    t = (df["date"] - d0).dt.days.to_numpy()
    ok = df["usable"].to_numpy()
    Hs = []
    for dept in ("bakery", "deli"):
        A = np.full((len(stores), T), np.nan)
        A[si[ok], t[ok]] = df.loc[ok, dept].to_numpy()
        Hs.append(A)
    C = np.full((len(stores), T), np.nan)
    C[si[ok], t[ok]] = df.loc[ok, "custcoun"].to_numpy()
    H = np.vstack(Hs)
    ns = len(stores)
    dates = (d0 + pd.to_timedelta(np.arange(T), unit="D")).to_numpy()
    return dict(
        name="dominicks", label="Dominick's Finer Foods (Chicago, daily bakery + deli dollar sales, 1988-1997)",
        unit="US dollars per day", H=H, dates=dates, test_lo=T - 84, test_hi=T - 1, min_hist=28,
        known={}, past={"cust": np.vstack([C, C])},
        groups={"store": np.tile(stores, 2), "dept": np.repeat([0, 1], ns)},
        statics={"dept": np.repeat([0, 1], ns), "store": np.tile(pd.factorize(stores)[0], 2)},
        cal_cols="all", us_holidays=True, cat_features=["dow", "dept", "store"], onehot=["dow", "month", "dept"],
        drop_linear=["store"],
        test_desc=f"{pd.Timestamp(dates[T - 84]).date()} to {pd.Timestamp(dates[T - 1]).date()} (last 84 days)")


LOADERS = {"fresh": load_fresh, "favorita": load_favorita, "dominicks": load_dominicks}


# ============================================================================ features
def make_features(ds):
    H = ds["H"]
    S, T = H.shape
    f = {}
    for k in (1, 2, 3, 7, 14):
        f[f"lag{k}"] = shift(H, k)
    if T > 200:
        f["lag21"], f["lag28"] = shift(H, 21), shift(H, 28)
    for w, mp in ((3, 2), (7, 3), (14, 5), (28, 7)):
        f[f"ma{w}"] = sroll(H, w, mp)
    f["std7"], f["std14"] = sroll(H, 7, 3, "std"), sroll(H, 14, 5, "std")
    f["same_dow_mean"] = np.nanmean(np.stack([shift(H, k) for k in (7, 14, 21, 28) if k < T]), axis=0)
    floor = 0.02 * np.nanmedian(f["ma28"])
    base = np.maximum(f["ma28"], floor)
    f["trend7_28"] = f["ma7"] / base
    R = H / base
    for name, g in ds["groups"].items():
        idx = group_index(R, g)
        f[f"{name}_idx_lag1"], f[f"{name}_idx_ma7"] = shift(idx, 1), sroll(idx, 7, 3)
    for k, v in ds["past"].items():
        f[f"{k}_lag1"], f[f"{k}_ma7"] = shift(v, 1), sroll(v, 7, 3)
    for k, v in ds["known"].items():
        f[k], f[f"{k}_lag1"] = v, shift(v, 1)
    return {k: v.astype("float32") for k, v in f.items()}, base


def build_x(ds, f, rows, T):
    X = pd.DataFrame({k: v.reshape(-1)[rows] for k, v in f.items()})
    day, sid = rows % T, rows // T
    for k, v in calendar(ds["dates"], ds["us_holidays"], ds["cal_cols"]).items():
        X[k] = v[day].astype("int16")
    for k, v in ds["statics"].items():
        X[k] = v[sid].astype("int16")
    return X


def linear_view(ds, Xtr, Xte):
    both = pd.concat([Xtr, Xte], ignore_index=True).drop(columns=ds["drop_linear"], errors="ignore")
    both = pd.get_dummies(both, columns=[c for c in ds["onehot"] if c in both.columns], dtype="float32")
    return both.iloc[:len(Xtr)], both.iloc[len(Xtr):]


# ============================================================================ models
def model_zoo():
    P = PROFILE
    imp = lambda *steps: make_pipeline(SimpleImputer(strategy="median"), *steps)
    z = [
        ("Linear regression", "Linear", "lin", lambda: imp(StandardScaler(), LinearRegression())),
        ("Ridge", "Linear", "lin", lambda: imp(StandardScaler(), Ridge(alpha=10.0))),
        ("Lasso", "Linear", "lin", lambda: imp(StandardScaler(), Lasso(alpha=1e-4, max_iter=3000))),
        ("ElasticNet", "Linear", "lin", lambda: imp(StandardScaler(), ElasticNet(alpha=1e-4, l1_ratio=0.5, max_iter=3000))),
        ("Decision tree", "Tree", "tree", lambda: imp(DecisionTreeRegressor(max_depth=10, min_samples_leaf=100, random_state=SEED))),
        ("Random forest", "Tree ensemble", "tree", lambda: imp(RandomForestRegressor(
            n_estimators=P["rf_trees"], max_depth=P["rf_depth"], min_samples_leaf=30, max_samples=0.5,
            max_features=0.6, n_jobs=NT, random_state=SEED))),
        ("Extra trees", "Tree ensemble", "tree", lambda: imp(ExtraTreesRegressor(
            n_estimators=P["rf_trees"], max_depth=P["rf_depth"], min_samples_leaf=30, max_samples=0.5,
            bootstrap=True, max_features=0.6, n_jobs=NT, random_state=SEED))),
        ("HistGradientBoosting", "Boosting", "tree", lambda: HistGradientBoostingRegressor(
            max_iter=P["gbm_rounds"], learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=100,
            l2_regularization=1.0, random_state=SEED)),
        ("LightGBM (mean)", "Boosting", "lgb", "regression"),
        ("LightGBM (median)", "Boosting", "lgb", "regression_l1"),
        ("MLP neural network", "Neural", "lin", lambda: imp(StandardScaler(), MLPRegressor(
            hidden_layer_sizes=(64, 32), max_iter=P["mlp_iter"], early_stopping=True, random_state=SEED))),
    ]
    if xgb is not None:
        z.insert(9, ("XGBoost", "Boosting", "tree", lambda: xgb.XGBRegressor(
            n_estimators=P["gbm_rounds"], learning_rate=0.06, max_depth=8, subsample=0.8, colsample_bytree=0.8,
            min_child_weight=50, tree_method="hist", n_jobs=NT if NT > 0 else -1, random_state=SEED)))
    return z


def fit_one(spec, ds, Xt_tree, Xt_lin, ytr, wtr, Xe_tree, Xe_lin, sub):
    name, fam, kind, make = spec
    if kind == "lgb":
        prm = dict(objective=make, learning_rate=0.06, num_leaves=63, min_data_in_leaf=100, feature_fraction=0.8,
                   bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, max_bin=127, verbose=-1, seed=SEED,
                   num_threads=NT)
        cats = [c for c in ds["cat_features"] if c in Xt_tree.columns]
        m = lgb.train(prm, lgb.Dataset(Xt_tree, ytr, weight=wtr, categorical_feature=cats), PROFILE["gbm_rounds"])
        imp = pd.Series(m.feature_importance("gain"), index=Xt_tree.columns)
        return m.predict(Xe_tree), imp
    est = make()
    Xtr, Xte = (Xt_lin, Xe_lin) if kind == "lin" else (Xt_tree, Xe_tree)
    if name in ("Random forest", "Extra trees"):          # these two are slow: fit on a row subsample
        Xtr, ytr, wtr = Xtr.iloc[sub], ytr[sub], wtr[sub]
    if hasattr(est, "steps"):
        kw = {f"{est.steps[-1][0]}__sample_weight": wtr}
        try:
            est.fit(Xtr, ytr, **kw)
        except TypeError:                                   # e.g. older sklearn MLP without weights
            est.fit(Xtr, ytr)
    else:
        est.fit(Xtr, ytr, sample_weight=wtr)
    return est.predict(Xte), None


# ============================================================================ evaluation
def metrics(y, p):
    e = p - y
    return dict(MAE=np.abs(e).mean(), RMSE=np.sqrt((e ** 2).mean()), WAPE=np.abs(e).sum() / y.sum(),
                bias=p.sum() / y.sum() - 1)


def decision_cut(sold, made, habit, buf):
    """Waste cut at equal missed sales, and missed-sales cut at equal waste, vs 'last week x (1+buf)'."""
    tot = sold.sum()
    hw = np.clip(habit * (1 + buf) - sold, 0, None).sum() / tot
    hm = np.clip(sold - habit * (1 + buf), 0, None).sum() / tot
    best_w, best_m = np.nan, np.nan
    for b in np.arange(0, 2.0001, 0.01):
        q = made * (1 + b)
        w, m = np.clip(q - sold, 0, None).sum() / tot, np.clip(sold - q, 0, None).sum() / tot
        if m <= hm and (np.isnan(best_w) or w < best_w):
            best_w = w
        if w <= hw and (np.isnan(best_m) or m < best_m):
            best_m = m
    return (best_w / hw - 1 if hw > 0 else np.nan), (best_m / hm - 1 if hm > 0 else np.nan)


def run_dataset(name):
    cap = args.max_series or PROFILE["series"][name]
    log(f"=== {name}: loading (series cap {cap or 'none'})")
    ds = LOADERS[name](cap)
    H = ds["H"]
    S, T = H.shape
    log(f"{S:,} series x {T} days; test window {ds['test_desc']}")
    f, base = make_features(ds)
    rng = np.random.RandomState(SEED)
    day = np.tile(np.arange(T), S)
    fin = np.isfinite(H).reshape(-1) & np.isfinite(base).reshape(-1)
    cand = np.flatnonzero(fin & (day >= ds["min_hist"]) & (day < ds["test_lo"]))
    te = np.flatnonzero(fin & (day >= ds["test_lo"]) & (day <= ds["test_hi"]))
    cap_rows = args.max_train_rows or PROFILE["train_rows"]
    tr = np.sort(rng.choice(cand, size=min(cap_rows, len(cand)), replace=False))
    log(f"training rows {len(tr):,} (of {len(cand):,} available)   test rows {len(te):,}")

    Xtr, Xte = build_x(ds, f, tr, T), build_x(ds, f, te, T)
    Xtr_l, Xte_l = linear_view(ds, Xtr, Xte)
    b_tr, b_te = base.reshape(-1)[tr], base.reshape(-1)[te]
    ytr = H.reshape(-1)[tr] / b_tr
    y = H.reshape(-1)[te]

    # no-ML benchmarks (what a manager could do in a spreadsheet)
    g = lambda k: f[k].reshape(-1)[te].astype(float)
    fill = lambda *arrs: np.select([np.isfinite(a) for a in arrs], arrs, default=np.nan)
    lag7 = fill(g("lag7"), g("ma7"), g("ma28"))
    preds = {"Same day last week": lag7,
             "7-day moving average": fill(g("ma7"), g("ma28")),
             "Average of last 4 same weekdays": fill(g("same_dow_mean"), g("ma7"), g("ma28"))}
    fam = {k: "No-ML benchmark" for k in preds}
    secs = {k: 0.0 for k in preds}
    importance = None
    sub = np.sort(rng.choice(len(tr), size=min(PROFILE["ens_rows"], len(tr)), replace=False))
    for spec in model_zoo():
        t = time.time()
        try:
            p, imp = fit_one(spec, ds, Xtr, Xtr_l, ytr, b_tr, Xte, Xte_l, sub)
        except Exception as e:                              # one failing model must not stop the run
            log(f"  {spec[0]}: FAILED ({type(e).__name__}: {str(e)[:80]})")
            continue
        preds[spec[0]] = np.clip(p, 0, None) * b_te
        fam[spec[0]], secs[spec[0]] = spec[1], time.time() - t
        if imp is not None and spec[0] == "LightGBM (median)":
            importance = imp
        log(f"  {spec[0]:<24} done in {secs[spec[0]]:5.0f}s")
    boost = [k for k in ("LightGBM (median)", "HistGradientBoosting", "Random forest") if k in preds]
    if len(boost) >= 2:
        preds["Ensemble (LightGBM + HGB + RF)"] = np.mean([preds[k] for k in boost], axis=0)
        fam["Ensemble (LightGBM + HGB + RF)"], secs["Ensemble (LightGBM + HGB + RF)"] = "Ensemble", 0.0

    ok = np.ones(len(te), bool)
    for p in preds.values():
        ok &= np.isfinite(p)
    log(f"rows scored identically for every model: {int(ok.sum()):,} of {len(te):,}")
    y_ok, habit = y[ok], lag7[ok]
    rows = []
    for k, p in preds.items():
        m = metrics(y_ok, p[ok])
        wc, mc = decision_cut(y_ok, p[ok], habit, args.habit_buffer)
        rows.append(dict(dataset=name, model=k, family=fam[k], rows=int(ok.sum()), **m,
                         waste_cut_equal_missed=wc, missed_cut_equal_waste=mc, fit_seconds=secs[k]))
    res = pd.DataFrame(rows)
    b = res.loc[res["model"] == "Same day last week", "MAE"].iloc[0]
    res["MAE_vs_same_day_last_week"] = res["MAE"] / b - 1
    res["rank_by_MAE"] = res["MAE"].rank().astype(int)
    if importance is not None:
        (importance / importance.sum()).sort_values(ascending=False).head(15).rename("gain_share").to_csv(
            OUT / f"benchmark_importance_{name}{TAG}.csv")
    meta = dict(dataset=name, label=ds["label"], unit=ds["unit"], series=int(S), days=int(T),
                train_rows=int(len(tr)), test_rows=int(ok.sum()), test_window=ds["test_desc"],
                habit=f"same day last week x {1 + args.habit_buffer:.2f}")
    return res.sort_values("MAE"), meta


# ============================================================================ run + reports
for name in args.datasets:
    r, m = run_dataset(name)
    json.dump({"meta": m, "res": r.to_dict("records")}, open(OUT / f"_benchmark_{name}{TAG}.json", "w"), default=float)
all_res, all_meta = [], []
for name in ("fresh", "favorita", "dominicks"):             # combine every dataset run so far
    p = OUT / f"_benchmark_{name}{TAG}.json"
    if p.exists():
        d = json.load(open(p))
        all_meta.append(d["meta"])
        all_res.append(pd.DataFrame(d["res"]))
pd.concat(all_res, ignore_index=True).to_csv(OUT / f"benchmark_all_models{TAG}.csv", index=False)

pd.set_option("display.width", 230)
for m, r in zip(all_meta, all_res):
    print(f"\n{m['label']}\n  test window: {m['test_window']}   rows scored: {m['test_rows']:,}")
    show = r[["model", "family", "MAE", "RMSE", "WAPE", "bias", "MAE_vs_same_day_last_week",
              "waste_cut_equal_missed", "missed_cut_equal_waste", "fit_seconds"]]
    print(show.round(4).to_string(index=False))

json.dump({"generated": pd.Timestamp.now().isoformat(timespec="seconds"), "profile": args.profile,
           "habit_buffer": args.habit_buffer,
           "datasets": [dict(**m, models=r.round(5).to_dict("records")) for m, r in zip(all_meta, all_res)]},
          open(OUT / f"benchmark_summary{TAG}.json", "w"), indent=2, default=float)

pct = lambda x: "n/a" if pd.isna(x) else f"{x:+.1%}"
md = ["# Model benchmark results", "",
      f"Profile: `{args.profile}`. Every model is scored on identical rows. MAE and RMSE are in each dataset's own "
      "units, so compare models within a dataset, not across datasets. 'Waste cut' and 'missed-sales cut' compare a "
      f"model-based production plan with a simulated habit (same day last week x {1 + args.habit_buffer:.2f}); "
      "they are stylized because public data has sales but no production figures.", ""]
for m, r in zip(all_meta, all_res):
    md += [f"## {m['label']}", f"Test window: {m['test_window']} - {m['test_rows']:,} rows - unit: {m['unit']}", "",
           "| Rank | Model | Type | MAE | WAPE | vs same day last week | Waste cut (equal missed sales) |",
           "|---|---|---|---|---|---|---|"]
    for _, x in r.iterrows():
        md.append(f"| {x['rank_by_MAE']} | {x['model']} | {x['family']} | {x['MAE']:.4g} | {x['WAPE']:.3f} | "
                  f"{pct(x['MAE_vs_same_day_last_week'])} | {pct(x['waste_cut_equal_missed'])} |")
    md.append("")
(OUT / f"benchmark_report{TAG}.md").write_text("\n".join(md), encoding="utf-8")

fig, axes = plt.subplots(1, len(all_res), figsize=(5.6 * len(all_res), 6.2), squeeze=False)
colors = {"No-ML benchmark": "#999999", "Linear": "#2a7de1", "Tree": "#d98c1f", "Tree ensemble": "#27ae60",
          "Boosting": "#c0392b", "Neural": "#7d3c98", "Ensemble": "#111111"}
for ax, m, r in zip(axes[0], all_meta, all_res):
    r = r.sort_values("MAE_vs_same_day_last_week", ascending=False)
    ax.barh(r["model"], r["MAE_vs_same_day_last_week"] * 100, color=[colors.get(f, "#555") for f in r["family"]])
    ax.axvline(0, color="k", lw=0.8)
    ax.set_title(m["dataset"], fontsize=11)
    ax.set_xlabel("MAE vs 'same day last week' (%, lower is better)")
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="x", alpha=0.3)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
fig.legend(handles, colors.keys(), loc="lower center", ncol=len(colors), fontsize=8)
fig.suptitle("Forecast error relative to the 'same day last week' benchmark", y=0.995)
fig.tight_layout(rect=(0, 0.04, 1, 0.97))
fig.savefig(OUT / f"benchmark_mae_improvement{TAG}.png", dpi=160)
log(f"saved to {OUT}/ with suffix {TAG}: all_models csv, summary json, report md, chart, importance files")
