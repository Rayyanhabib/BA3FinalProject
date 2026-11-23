import pandas as pd, pathlib

names = ["fresh_train", "fresh_eval", "favorita_food", "dominicks_dept"]
out = []

for name in names:
    p = pathlib.Path(f"data/processed/{name}.parquet")
    out.append("=" * 60)
    out.append(name)
    if not p.exists():
        out.append("MISSING")
        continue

    df = pd.read_parquet(p)
    out.append(f"size on disk: {p.stat().st_size / 1e6:.1f} MB")
    out.append(f"rows: {len(df):,}   columns: {df.shape[1]}")

    for c in df.columns:
        if c.lower() in ("date", "dt"):
            d = pd.to_datetime(df[c], errors="coerce")
            out.append(f"{c} range: {d.min()} to {d.max()}")

    out.append("\ncolumns (dtype, % missing):")
    for c in df.columns:
        out.append(f"  {c}: {df[c].dtype}, {df[c].isna().mean() * 100:.1f}%")
    out.append("")

text = "\n".join(out)
print(text)
open("results/data_manifest.txt", "w").write(text)
