from datasets import load_dataset

ds = load_dataset("Dingdong-Inc/FreshRetailNet-50K")
print(ds)

train = ds["train"].to_pandas()
print(train.shape)
print(train.columns.tolist())
train.to_csv("data/processed/fresh_train.csv", index=False)
ds["eval"].to_pandas().to_csv("data/processed/fresh_eval.csv", index=False)