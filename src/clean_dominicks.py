import pandas as pd, pathlib

folder = pathlib.Path("data/raw/dominicks")
cc = pd.read_stata(next(folder.rglob("ccount*.dta")))

print("date dtype:", cc["date"].dtype)
print(cc["date"].astype(str).str.strip().replace("", pd.NA).dropna().head(10).tolist())

# Dates are stored as 6-character strings (YYMMDD)
cc["date_parsed"] = pd.to_datetime(
    cc["date"].astype(str).str.strip(), format="%y%m%d", errors="coerce"
)
print("rows with a valid date:", cc["date_parsed"].notna().sum(), "of", len(cc))
print("date range:", cc["date_parsed"].min(), "to", cc["date_parsed"].max())
print("stores:", cc["store"].nunique())
print("store 0 rows:", (cc["store"] == 0).sum())

cols = ["store", "date_parsed", "bakery", "deli", "deliself",
        "deliexpr", "convfood", "saladbar", "custcoun"]
df = cc[cols].rename(columns={"date_parsed": "date"}).dropna(subset=["date"])

print(df.describe().T[["count", "mean", "min", "max"]])
print("negative bakery rows:", (df["bakery"] < 0).sum())
print("zero bakery rows:", (df["bakery"] == 0).sum())

df.to_parquet("data/processed/dominicks_dept.parquet")
print(df.shape)
print(df.head())