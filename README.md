# BA3FinalProject
Food Waste Model

## Data

Large datasets are not stored in this repository because GitHub rejects files over 100 MB. They are shared on Google Drive.

| Folder | Contents | Link |
|---|---|---|
| Raw data | Original downloads: Favorita, Dominick's, ReFED, Census County Business Patterns | [Google Drive](https://drive.google.com/drive/folders/1DiKUPiMNTmhG4iaJDRadzsm55AXw5rir) |
| Processed data | Cleaned CSV files produced by the scripts in `src/02_clean/` | [Google Drive](https://drive.google.com/drive/folders/1alVkq2fGT_oae52FV9JdRddRhYan_Hh-) |

### Processed files (`data/processed/`)

| File | Size | Location |
|---|---|---|
| `dominicks_clean.csv` | 19.9 MB | GitHub and Drive |
| `dominicks_dept.csv` | 20.3 MB | GitHub and Drive |
| `fresh_eval.csv` | 77.8 MB | GitHub and Drive |
| `fresh_clean.csv` | 419 MB | Drive only |
| `fresh_train.csv` | 999 MB | Drive only |
| `favorita_clean.csv` | 529 MB | Drive only |
| `favorita_food.csv` | 645 MB | Drive only |

Download the Drive-only files into `data/processed/`. They are listed in `.gitignore`, so Git will not try to commit them.

Column definitions for every file are in [`data/data_dictionary.md`](data/data_dictionary.md). Reports on the data are in `output/`: `data_inventory.md`, `cleaning_report.md` and `dominicks_quality_report.md`.

## Repository layout

```
data/
  raw/                 original downloads, never edited
  processed/           cleaned CSV files
src/
  01_download/         download and extract raw data
    reports/           data checks and the manifest
  02_clean/            filter and clean into data/processed/
  03_features/         feature building (to come)
  04_model/            modeling (to come)
  05_evaluations/      evaluation (to come)
output/
  *.md                  cleaning report, data inventory, Dominick's quality report
```

Run every script from the repository root, for example `python src/02_clean/clean_data.py`.
