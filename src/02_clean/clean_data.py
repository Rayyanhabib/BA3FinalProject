"""
Clean the processed datasets for the SurplusIQ models.

Run from the repo root (the "Final Project" folder), with the venv active:
    python src/02_clean/clean_data.py

Inputs  (data/processed/): fresh_train, fresh_eval, favorita_food, dominicks_dept (.csv)
Outputs (data/processed/): fresh_clean, favorita_clean, dominicks_clean (.csv)
Note: CSV has no dtypes. Read the outputs with parse_dates=["date"].
Log     (output/cleaning_report.md)

Design rule: bad or censored rows are FLAGGED or MASKED here, and are removed only
AFTER lag features (same day last week, 7-day average) are built. Dropping them first
would leave holes in each daily series, and lag_7 would then point at the wrong day.
Every output has a boolean `usable` column. Model code keeps only usable == True
after the features are built.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--in-dir", default="data/processed")
ap.add_argument("--out-dir", default="data/processed")
ap.add_argument("--log", default="output/cleaning_report.md")
ap.add_argument("--only", choices=["fresh", "favorita", "dominicks"], default=None)
args = ap.parse_args()

IN = pathlib.Path(args.in_dir)
OUT = pathlib.Path(args.out_dir)
OUT.mkdir(parents=True, exist_ok=True)
LOG = []


def say(msg=""):
    print(msg)
    LOG.append(str(msg))


# ----------------------------------------------------------------------------
# 1. FreshRetailNet-50K
# ----------------------------------------------------------------------------
def clean_fresh():
    say("=" * 64)
    say("FreshRetailNet-50K")
    # Read only the scalar columns. The hourly array columns use far too much memory.
    cols = ["city_id", "store_id", "product_id", "first_category_id", "dt",
            "sale_amount", "stock_hour6_22_cnt", "discount", "holiday_flag",
            "activity_flag", "precpt", "avg_temperature", "avg_humidity",
            "avg_wind_level"]
    parts = []
    for split in ["train", "eval"]:
        df = pd.read_csv(IN / f"fresh_{split}.csv", usecols=cols)
        df["split"] = split
        say(f"{split}: {len(df):,} rows read")
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    del parts

    df["dt"] = pd.to_datetime(df["dt"])
    df = df.rename(columns={"dt": "date"})

    # Rule 1: stocked out for at least one hour (6:00-22:00) -> sales are censored
    df["censored"] = df["stock_hour6_22_cnt"] > 0
    # Rule 2: discount == 0 looks like a missing value (avg sales 14.5 vs about 1.0)
    df["bad_discount"] = df["discount"] <= 0
    df["usable"] = ~(df["censored"] | df["bad_discount"])

    say(f"rows total:                 {len(df):,}")
    say(f"censored (stockout hours>0): {df['censored'].sum():,} "
        f"({df['censored'].mean():.1%})")
    say(f"bad discount (<= 0):         {df['bad_discount'].sum():,}")
    say(f"usable rows:                 {df['usable'].sum():,} "
        f"({df['usable'].mean():.1%})")
    for s in ["train", "eval"]:
        m = df["split"] == s
        say(f"  usable in {s}: {df.loc[m, 'usable'].sum():,} of {m.sum():,}")

    # Checks: no duplicates, and every series is a complete daily run
    key = ["store_id", "product_id", "date"]
    assert not df.duplicated(key).any(), "duplicate store-product-days"
    df = df.sort_values(key).reset_index(drop=True)
    span = df.groupby(["store_id", "product_id"])["date"].agg(["count", "min", "max"])
    full = ((span["max"] - span["min"]).dt.days + 1) == span["count"]
    assert full.all(), "some series have gaps"
    say(f"series: {len(span):,}, all complete daily runs")

    for c in ["city_id", "store_id", "product_id", "first_category_id"]:
        df[c] = df[c].astype("int32")
    for c in ["stock_hour6_22_cnt", "holiday_flag", "activity_flag"]:
        df[c] = df[c].astype("int8")
    for c in ["sale_amount", "discount", "precpt", "avg_temperature",
              "avg_humidity", "avg_wind_level"]:
        df[c] = df[c].astype("float32")

    df.to_csv(OUT / "fresh_clean.csv", index=False)
    say(f"saved fresh_clean.csv  shape={df.shape}")


# ----------------------------------------------------------------------------
# 2. Favorita (food only)
# ----------------------------------------------------------------------------
def clean_favorita():
    say("=" * 64)
    say("Favorita (bakery, deli, poultry, prepared foods)")
    START = pd.Timestamp("2014-04-01")   # onpromotion is missing before this date

    cols = ["date", "store_nbr", "item_nbr", "unit_sales", "onpromotion",
            "family", "class"]
    df = pd.read_csv(IN / "favorita_food.csv", usecols=cols, parse_dates=["date"],
                     low_memory=False)
    say(f"rows read: {len(df):,}")

    # Rule 1: promo flag is missing for all of 2013 and Jan-Mar 2014
    n0 = len(df)
    df = df[df["date"] >= START].copy()
    say(f"dropped before {START.date()} (promo not recorded): {n0 - len(df):,}")
    assert df["onpromotion"].notna().all()
    df["onpromotion"] = df["onpromotion"].astype("int8")

    # Rule 2: negative unit_sales are returns, not sales
    n0 = len(df)
    df = df[df["unit_sales"] >= 0].copy()
    say(f"dropped negative unit_sales (returns): {n0 - len(df):,}")

    df["store_nbr"] = df["store_nbr"].astype("int16")
    df["item_nbr"] = df["item_nbr"].astype("int32")
    df["unit_sales"] = df["unit_sales"].astype("float32")
    meta_items = (df[["item_nbr", "family", "class"]]
                  .drop_duplicates("item_nbr").set_index("item_nbr"))
    df = df[["date", "store_nbr", "item_nbr", "unit_sales", "onpromotion"]]

    # Rule 3: keep only series with enough history (>= 365 sale days, >= 50% filled)
    g = df.groupby(["store_nbr", "item_nbr"])["date"].agg(["count", "min", "max"])
    g["span"] = (g["max"] - g["min"]).dt.days + 1
    g["fill"] = g["count"] / g["span"]
    keep = g[(g["count"] >= 365) & (g["fill"] >= 0.5)]
    say(f"series total: {len(g):,}   kept (>=365 obs, fill>=0.5): {len(keep):,}")

    # Rule 4: fill missing days with 0 sales, but only on days the store was open
    # (any food sale that day) and only between a series' first and last sale.
    frames = []
    for store, sdf in df.groupby("store_nbr"):
        if store not in keep.index.get_level_values(0):
            continue
        open_days = np.sort(sdf["date"].unique())
        meta = keep.loc[store]
        dates, items = [], []
        for item, first, last in zip(meta.index, meta["min"], meta["max"]):
            d = open_days[(open_days >= first.to_datetime64())
                          & (open_days <= last.to_datetime64())]
            dates.append(d)
            items.append(np.full(len(d), item, dtype="int32"))
        grid = pd.DataFrame({"date": np.concatenate(dates),
                             "item_nbr": np.concatenate(items)})
        grid = grid.merge(sdf[["date", "item_nbr", "unit_sales", "onpromotion"]],
                          on=["date", "item_nbr"], how="left")
        grid["zero_filled"] = grid["unit_sales"].isna()
        grid["unit_sales"] = grid["unit_sales"].fillna(0).astype("float32")
        grid["onpromotion"] = grid["onpromotion"].fillna(0).astype("int8")
        grid["store_nbr"] = np.int16(store)
        frames.append(grid)
    out = pd.concat(frames, ignore_index=True)
    del frames, df

    out = out.merge(meta_items.reset_index(), on="item_nbr", how="left")
    out["family"] = out["family"].astype("category")
    out["usable"] = True
    out = out.sort_values(["store_nbr", "item_nbr", "date"]).reset_index(drop=True)
    assert not out.duplicated(["store_nbr", "item_nbr", "date"]).any()

    say(f"rows after zero-fill: {len(out):,}   "
        f"zero-filled days: {out['zero_filled'].sum():,} "
        f"({out['zero_filled'].mean():.1%})")
    say(f"date range: {out['date'].min().date()} to {out['date'].max().date()}")
    out.to_csv(OUT / "favorita_clean.csv", index=False)
    say(f"saved favorita_clean.csv  shape={out.shape}")


# ----------------------------------------------------------------------------
# 3. Dominick's (daily department dollars)
# ----------------------------------------------------------------------------
def clean_dominicks():
    say("=" * 64)
    say("Dominick's ccount (daily store-department dollar sales)")
    df = pd.read_csv(IN / "dominicks_dept.csv", parse_dates=["date"])
    df = df.drop(columns=[c for c in df.columns if c.startswith("__index")])
    say(f"rows read: {len(df):,}")

    # Rule 1: dates outside 1988-1997 are parse errors
    n0 = len(df)
    df = df[(df["date"] >= "1988-01-01") & (df["date"] <= "1997-12-31")].copy()
    say(f"dropped impossible dates: {n0 - len(df):,}")

    # Rule 2: keep only stores with a long, nearly complete history
    g = df.groupby("store")["date"].agg(["count", "min", "max"])
    g["span"] = (g["max"] - g["min"]).dt.days + 1
    g["fill"] = g["count"] / g["span"]
    keep = g[(g["span"] >= 1000) & (g["fill"] >= 0.95)]
    say(f"stores total: {len(g)}   kept (span>=1000 days, fill>=0.95): {len(keep)}")
    df = df[df["store"].isin(keep.index)]

    # Rule 3: reindex each store to a full daily calendar so lag_7 is correct.
    # Added days become unusable rows.
    frames = []
    for store, sdf in df.groupby("store"):
        idx = pd.date_range(sdf["date"].min(), sdf["date"].max(), freq="D")
        s2 = sdf.set_index("date").reindex(idx)
        s2["store"] = store
        s2.index.name = "date"
        frames.append(s2.reset_index())
    df = pd.concat(frames, ignore_index=True)
    del frames

    # Rule 4: flag implausible rows (store closed, bad data, or chain-wide totals)
    ok = (
        df["custcoun"].between(100, 20000)
        & df["bakery"].gt(0) & df["bakery"].le(10000)
        & df["deli"].gt(0) & df["deli"].le(50000)
    )
    df["usable"] = ok.fillna(False)
    say(f"rows after calendar fill: {len(df):,}")
    say(f"usable rows: {df['usable'].sum():,} ({df['usable'].mean():.1%})")
    say(f"  customer count outside 100-20,000: "
        f"{(~df['custcoun'].between(100, 20000)).sum():,}")
    say(f"  bakery <=0 or >10,000: {(~(df['bakery'].gt(0) & df['bakery'].le(10000))).sum():,}")
    say(f"  deli <=0 or >50,000:   {(~(df['deli'].gt(0) & df['deli'].le(50000))).sum():,}")

    df["store"] = df["store"].astype("int16")
    df = df.sort_values(["store", "date"]).reset_index(drop=True)
    assert not df.duplicated(["store", "date"]).any()
    df.to_csv(OUT / "dominicks_clean.csv", index=False)
    say(f"saved dominicks_clean.csv  shape={df.shape}")
    say("NOTE: values are dollars (not units) from 1988-1997. 1988 kept; confirm "
        "its start date in the Kilts data manual.")


if __name__ == "__main__":
    steps = {"fresh": clean_fresh, "favorita": clean_favorita,
             "dominicks": clean_dominicks}
    for name, fn in steps.items():
        if args.only in (None, name):
            fn()
    log_path = pathlib.Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.only else "w"
    head = ""
    if mode == "w":
        head = (
            "# Cleaning report\n\n"
            "Shows what each cleaning rule removed or flagged in the three datasets, with row "
            "counts before and after. It is the evidence behind the rule that a row is only "
            "modeled when `usable` is true.\n\n"
            "*Generated by `src/02_clean/clean_data.py`.*\n\n"
        )
    with log_path.open(mode, encoding="utf-8") as f:
        f.write(head + "```text\n" + "\n".join(LOG) + "\n```\n\n")
    print(f"\nLog written to {log_path}")
