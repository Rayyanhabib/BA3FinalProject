import pandas as pd
df = pd.read_parquet("data/processed/fresh_clean.parquet")
print(df["split"].value_counts())