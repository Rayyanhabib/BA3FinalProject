import zipfile, py7zr, pathlib

raw = pathlib.Path("data/raw")

for z in raw.glob("*.zip"):
    print("Unzipping", z.name)
    with zipfile.ZipFile(z) as f:
        f.extractall(raw)

for f in raw.glob("*.7z"):
    print("Extracting", f.name)
    with py7zr.SevenZipFile(f) as s:
        s.extractall(raw)

print("Done. Files:", [p.name for p in raw.iterdir()])