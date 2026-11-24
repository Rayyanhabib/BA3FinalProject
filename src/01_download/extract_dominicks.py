import zipfile, pathlib

folder = pathlib.Path("data/raw/dominicks")

for z in list(folder.glob("*.zip")):
    out = folder / z.stem
    out.mkdir(exist_ok=True)
    print("Unzipping", z.name)
    with zipfile.ZipFile(z) as f:
        f.extractall(out)

for p in sorted(folder.rglob("*")):
    if p.is_file() and p.suffix != ".zip":
        print(p.relative_to(folder), round(p.stat().st_size / 1e6, 1), "MB")