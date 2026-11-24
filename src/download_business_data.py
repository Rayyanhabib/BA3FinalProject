"""
Download the two business-plan datasets that have a free API.

Run from the repo root with the venv active:
    $env:CENSUS_KEY="your_key"          # PowerShell, same key as before
    python src/download_business_data.py

Outputs:
    data/raw/acs_indiana_zcta_2024.csv    ACS 2020-2024 5-year, Indiana ZIP areas
    data/raw/acs_indiana_county_2024.csv  ACS 2020-2024 5-year, Indiana counties
    data/raw/midwest_prices.csv           BLS/FRED Midwest food prices + food CPI
"""
import io
import os

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# 1. ACS 2020-2024 5-year estimates (Census API, needs CENSUS_KEY)
# ----------------------------------------------------------------------------
ACS_URL = "https://api.census.gov/data/2024/acs/acs5"
ACS_VARS = {
    "B01003_001E": "population",
    "B19013_001E": "median_household_income",
    "B17001_001E": "poverty_universe",
    "B17001_002E": "below_poverty",
    "B25010_001E": "avg_household_size",
    "B22010_001E": "households_total",
    "B22010_002E": "households_with_snap",
}


def acs(geo_for, geo_in=None):
    key = os.environ["CENSUS_KEY"]
    params = {"get": "NAME," + ",".join(ACS_VARS), "for": geo_for, "key": key}
    if geo_in:
        params["in"] = geo_in
    r = requests.get(ACS_URL, params=params, timeout=120)
    if r.status_code != 200:
        # print the server's explanation, never the URL (it contains the key)
        print("ACS request failed:", r.status_code)
        print(r.text[:500])
        raise SystemExit(1)
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0]).rename(columns=ACS_VARS)
    for c in ACS_VARS.values():
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] < 0, c] = pd.NA          # Census uses -666666666 for "no data"
    df["poverty_rate"] = df["below_poverty"] / df["poverty_universe"]
    df["snap_share"] = df["households_with_snap"] / df["households_total"]
    return df


def download_acs():
    print("ACS: Indiana counties ...")
    county = acs("county:*", "state:18")
    county.to_csv("data/raw/acs_indiana_county_2024.csv", index=False)
    print("  counties:", len(county))

    print("ACS: ZIP areas (all U.S., then keep Indiana) ...")
    z = acs("zip code tabulation area:*")
    zcol = "zip code tabulation area"
    z = z[z[zcol].str.startswith(("46", "47"))]       # Indiana ZIPs are 460-479
    z.to_csv("data/raw/acs_indiana_zcta_2024.csv", index=False)
    print("  Indiana ZIP areas:", len(z))


# ----------------------------------------------------------------------------
# 2. Midwest food prices (BLS series, served by FRED as CSV, no key needed)
# ----------------------------------------------------------------------------
SERIES = {
    "APU0200702111": "white_bread_per_lb",       # BLS average price, Midwest urban
    "APU0200706111": "whole_chicken_per_lb",     # BLS average price, Midwest urban
    "CUUR0200SAF1": "food_cpi_midwest",          # CPI-U, food, Midwest
}


def download_prices():
    frames = []
    for sid, name in SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            print(f"Could not fetch {sid} ({r.status_code}). Download it by hand from "
                  f"https://fred.stlouisfed.org/series/{sid} (Download button, CSV).")
            continue
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", name]
        df[name] = pd.to_numeric(df[name], errors="coerce")
        frames.append(df.set_index("date"))
        print(f"  {sid}: {len(df)} rows, last date {df['date'].iloc[-1]}")
    if frames:
        out = pd.concat(frames, axis=1).reset_index()
        out.to_csv("data/raw/midwest_prices.csv", index=False)
        print("saved data/raw/midwest_prices.csv", out.shape)


if __name__ == "__main__":
    download_acs()
    download_prices()
