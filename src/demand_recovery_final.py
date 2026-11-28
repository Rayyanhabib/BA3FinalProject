"""
STAGE 1 - Demand recovery for FreshRetailNet-50K.

When a product is stocked out for part of a day, recorded sales understate true demand.
We have the 24 hourly sales and 24 hourly stock flags, so we can estimate the demand the
missing hours would have produced:

    profile[product, weekday/weekend, hour]  = share of a day's sales that falls in each hour,
                                               learned from days with NO stockout (6:00-22:00)
    coverage = sum of profile over the hours the product WAS in stock
    recovered demand = sales made during in-stock hours / coverage

Run from the repo root with the venv active (needs the ORIGINAL files that contain the
hourly arrays: data/processed/fresh_train.parquet and fresh_eval.parquet):
    python src/demand_recovery_final.py

Outputs:
    data/processed/fresh_recovered_final.parquet   store_id, product_id, date, demand_rec, coverage, split
    results/fresh_recovery_validation_final.csv    how accurate the recovery is (masking test)

Memory: streams the files in batches of 200k rows, so it fits on a normal laptop.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ap = argparse.ArgumentParser()
ap.add_argument("--in-dir", default="data/processed")
ap.add_argument("--tag", default="_final", help="suffix added to every output file name")
ap.add_argument("--out", default=None, help="default: data/processed/fresh_recovered<tag>.parquet")
ap.add_argument("--results", default="results")
ap.add_argument("--min-cover", type=float, default=0.4,
                help="below this in-stock share of a typical day, recovery is unreliable (NaN)")
ap.add_argument("--min-days", type=int, default=30,
                help="clean days needed before a product gets its own hourly profile")
args = ap.parse_args()
TAG = args.tag
if args.out is None:
    args.out = f"data/processed/fresh_recovered{TAG}.parquet"
IN = pathlib.Path(args.in_dir)
RES = pathlib.Path(args.results)
RES.mkdir(parents=True, exist_ok=True)
rng = np.random.RandomState(42)

COLS = ["store_id", "product_id", "first_category_id", "dt", "sale_amount",
        "hours_sale", "hours_stock_status", "stock_hour6_22_cnt"]


def batches():
    for split in ("train", "eval"):
        pf = pq.ParquetFile(IN / f"fresh_{split}.parquet")
        for b in pf.iter_batches(batch_size=200_000, columns=COLS):
            yield split, b


def unpack(b):
    n = b.num_rows
    hs = b.column("hours_sale").flatten().to_numpy(zero_copy_only=False)
    st = b.column("hours_stock_status").flatten().to_numpy(zero_copy_only=False)
    assert len(hs) == n * 24 and len(st) == n * 24, "hourly arrays are not length 24"
    d = {
        "hs": hs.reshape(n, 24).astype("float32"),
        "st": st.reshape(n, 24).astype("int8"),
        "store": b.column("store_id").to_numpy(zero_copy_only=False),
        "prod": b.column("product_id").to_numpy(zero_copy_only=False),
        "cat": b.column("first_category_id").to_numpy(zero_copy_only=False),
        "sale": b.column("sale_amount").to_numpy(zero_copy_only=False),
        "cnt": b.column("stock_hour6_22_cnt").to_numpy(zero_copy_only=False),
    }
    dt = pd.to_datetime(b.column("dt").to_pandas())
    d["date"] = dt.to_numpy()
    d["wk"] = (dt.dt.dayofweek >= 5).to_numpy().astype(int)
    return d


# ---------------------------------------------------------------- pass 0: id maps
ids = pd.concat([pq.read_table(IN / f"fresh_{s}.parquet",
                               columns=["product_id", "first_category_id"]).to_pandas()
                 for s in ("train", "eval")]).drop_duplicates("product_id")
prods = np.sort(ids["product_id"].to_numpy())
cats = np.sort(ids["first_category_id"].unique())
prod_cat = ids.set_index("product_id").loc[prods, "first_category_id"].to_numpy()
P, C = len(prods), len(cats)
print(f"products: {P}   categories: {C}")

# ---------------------------------------------------------------- pass 1: hourly profiles
psum = np.zeros((P, 2, 24)); pcnt = np.zeros((P, 2))
csum = np.zeros((C, 2, 24)); ccnt = np.zeros((C, 2))
gsum = np.zeros((2, 24))
for split, b in batches():
    d = unpack(b)
    clean = (d["cnt"] == 0) & (d["sale"] > 0)
    if not clean.any():
        continue
    hs, wk = d["hs"][clean], d["wk"][clean]
    pi = np.searchsorted(prods, d["prod"][clean])
    ci = np.searchsorted(cats, d["cat"][clean])
    for w in (0, 1):
        m = wk == w
        np.add.at(psum[:, w, :], pi[m], hs[m])
        np.add.at(pcnt[:, w], pi[m], 1)
        np.add.at(csum[:, w, :], ci[m], hs[m])
        np.add.at(ccnt[:, w], ci[m], 1)
        gsum[w] += hs[m].sum(0)
norm = lambda a: a / np.maximum(a.sum(-1, keepdims=True), 1e-12)
prof_c, prof_g = norm(csum), norm(gsum)
prof_p = norm(psum)
ci_of_p = np.searchsorted(cats, prod_cat)
for w in (0, 1):
    for p in range(P):
        if pcnt[p, w] < args.min_days:                       # fall back: category, then global
            c = ci_of_p[p]
            prof_p[p, w] = prof_c[c, w] if ccnt[c, w] >= args.min_days else prof_g[w]
print("hourly profile (weekday, whole platform):", np.round(prof_g[0], 3))

# ---------------------------------------------------------------- pass 2: recover demand
out, val_rows, mask_pool = [], [], []
for split, b in batches():
    d = unpack(b)
    pi = np.searchsorted(prods, d["prod"])
    prof = prof_p[pi, d["wk"]]
    instock = d["st"] == 0
    cover = (prof * instock).sum(1)
    obs_in = (d["hs"] * instock).sum(1)
    rec = np.where(cover >= args.min_cover, obs_in / np.maximum(cover, 1e-9), np.nan)
    out.append(pd.DataFrame({"store_id": d["store"].astype("int32"),
                             "product_id": d["prod"].astype("int32"),
                             "date": d["date"], "demand_rec": rec.astype("float32"),
                             "coverage": cover.astype("float32"), "split": split,
                             "stock_hours": d["cnt"].astype("int8"),
                             "sale_obs": d["sale"].astype("float32")}))
    # material for the masking validation
    full = (d["st"].sum(1) == 0) & (d["sale"] > 0)           # in stock all 24 hours
    k = np.flatnonzero(full)
    k = rng.choice(k, size=min(600, len(k)), replace=False) if len(k) else k
    val_rows.append((d["hs"][k], prof[k]))
    j = np.flatnonzero(d["cnt"] >= 2)
    j = rng.choice(j, size=min(600, len(j)), replace=False) if len(j) else j
    mask_pool.append(d["st"][j])

res = pd.concat(out, ignore_index=True)
res.drop(columns=["stock_hours", "sale_obs"]).to_parquet(args.out, index=False)
cens = res["stock_hours"] > 0
ok = res["demand_rec"].notna()
print(f"\nrows: {len(res):,}   recovered (coverage >= {args.min_cover}): {ok.mean():.1%}")
print(f"stocked-out rows with a usable recovery: {(cens & ok).sum():,} of {cens.sum():,}")
both = cens & ok
print(f"on those rows, recovered demand is {res.loc[both, 'demand_rec'].sum() / res.loc[both, 'sale_obs'].sum() - 1:+.1%} "
      f"vs recorded sales")

# ---------------------------------------------------------------- validation by masking
H = np.concatenate([v[0] for v in val_rows]); PR = np.concatenate([v[1] for v in val_rows])
M = np.concatenate(mask_pool)
mk = M[rng.randint(0, len(M), size=len(H))] == 0              # a REAL stockout pattern, in-stock hours
obs = (H * mk).sum(1)
cov = (PR * mk).sum(1)
truth = H.sum(1)
keep = cov >= args.min_cover
rec_v = obs[keep] / cov[keep]
t, o = truth[keep], obs[keep]
rows = []
for lo, hi in [(0.4, 0.6), (0.6, 0.8), (0.8, 0.95), (0.95, 1.01), (0.4, 1.01)]:
    s = (cov[keep] >= lo) & (cov[keep] < hi)
    if s.sum() < 50:
        continue
    rows.append({"coverage": f"{lo:.2f}-{min(hi, 1):.2f}" if hi < 1.01 or lo > 0.4 else "all",
                 "rows": int(s.sum()),
                 "recorded_bias": o[s].sum() / t[s].sum() - 1,
                 "recovered_bias": rec_v[s].sum() / t[s].sum() - 1,
                 "recorded_WAPE": np.abs(o[s] - t[s]).sum() / t[s].sum(),
                 "recovered_WAPE": np.abs(rec_v[s] - t[s]).sum() / t[s].sum()})
vdf = pd.DataFrame(rows)
vdf.to_csv(RES / f"fresh_recovery_validation{TAG}.csv", index=False)
print("\nMasking validation (hide real stockout hours on fully in-stock days, then recover):")
print(vdf.round(3).to_string(index=False))
print(f"\nSaved {args.out}")
