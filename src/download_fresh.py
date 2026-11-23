from datasets import load_dataset

ds = load_dataset("Dingdong-Inc/FreshRetailNet-50K")
print(ds)

train = ds["train"].to_pandas()
print(train.shape)
print(train.columns.tolist())
train.to_parquet("data/processed/fresh_train.parquet")
ds["eval"].to_pandas().to_parquet("data/processed/fresh_eval.parquet")