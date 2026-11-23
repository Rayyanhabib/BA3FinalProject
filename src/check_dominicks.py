import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

df = pd.read_parquet("data/processed/dominicks_dept.parquet")
out = []

out.append(f"rows: {len(df)}  stores: {df['store'].nunique()}")
out.append(f"date range: {df['date'].min()} to {df['date'].max()}")

out.append("\nrows per year:")
out.append(df["date"].dt.year.value_counts().sort_index().to_string())

out.append("\nrows per store (smallest 10 and largest 5):")
c = df["store"].value_counts()
out.append(c.tail(10).to_string())
out.append(c.head(5).to_string())

out.append("\nsummary:")
out.append(df[["bakery", "deli", "custcoun"]].describe().to_string())

out.append(f"\nnegative bakery: {(df['bakery'] < 0).sum()}")
out.append(f"zero bakery: {(df['bakery'] == 0).sum()}")
out.append(f"custcoun < 100: {(df['custcoun'] < 100).sum()}")

out.append("\nstore 0 sample:")
out.append(df[df["store"] == 0].sort_values("date").head(5).to_string())

text = "\n".join(out)
print(text)
open("results/dominicks_check.txt", "w").write(text)