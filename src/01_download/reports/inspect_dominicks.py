import pandas as pd, pathlib

folder = pathlib.Path("data/raw/dominicks")
print([p.name for p in folder.rglob("*.dta")])

cc = pd.read_stata(next(folder.rglob("ccount*.dta")))
print(cc.shape)
print(cc.columns.tolist())
print(cc.head())

demo = pd.read_stata(next(folder.rglob("demo*.dta")))
print(demo.shape)
print(demo.columns.tolist())