import pandas as pd

items = pd.read_csv("data/raw/items.csv")
print(sorted(items["family"].unique()))

KEEP = ["BREAD/BAKERY", "DELI", "PREPARED FOODS", "POULTRY"]
keep_ids = set(items.loc[items["family"].isin(KEEP), "item_nbr"])
print("Items kept:", len(keep_ids))

parts = []
for chunk in pd.read_csv("data/raw/train.csv", chunksize=5_000_000,
                         parse_dates=["date"]):
    parts.append(chunk[chunk["item_nbr"].isin(keep_ids)])
    print("rows kept so far:", sum(len(p) for p in parts))

df = pd.concat(parts).merge(items, on="item_nbr")
df.to_csv("data/processed/favorita_food.csv", index=False)
print(df.shape)
print(df.head())