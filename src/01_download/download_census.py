import os, requests, pandas as pd

key = os.environ["CENSUS_KEY"]
base = "https://api.census.gov/data/2023/cbp"

# Ask the API which variable names exist for 2023
vars_ = requests.get(base + "/variables.json").json()["variables"]
naics = [v for v in vars_ if v.startswith("NAICS") and not v.endswith(("_LABEL", "_F"))]
print("NAICS variable(s):", naics)
has_size = "EMPSZES" in vars_
print("EMPSZES present:", has_size)
naics_var = naics[0]

codes = ["311811", "722515", "722513", "445110"]
rows = []
for code in codes:
    params = {
        "get": f"NAME,{naics_var}_LABEL,ESTAB,EMP",
        "for": "county:*",
        "in": "state:18",
        naics_var: code,
        "key": key,
    }
    if has_size:
        params["EMPSZES"] = "001"          # 001 = all sizes combined
    r = requests.get(base, params=params)
    if r.status_code != 200:
        print("FAILED for", code, "status", r.status_code)
        print(r.text[:500])                # the server explains the problem here
        raise SystemExit
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["naics"] = code
    rows.append(df)
    print(code, "rows:", len(df))

out = pd.concat(rows)
out.to_csv("data/raw/cbp_indiana_2023.csv", index=False)
print(out.shape)
print(out.head())