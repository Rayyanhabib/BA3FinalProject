# Model benchmark results

Profile: `quick`. Every model is scored on identical rows. MAE and RMSE are in each dataset's own units, so compare models within a dataset, not across datasets. 'Waste cut' and 'missed-sales cut' compare a model-based production plan with a simulated habit (same day last week x 1.15); they are stylized because public data has sales but no production figures.

## FreshRetailNet-50K (China, perishables, daily, 2024)
Test window: 2024-06-26 to 2024-07-02 (the dataset's eval week) - 6,129 rows - unit: normalized units

| Rank | Model | Type | MAE | WAPE | vs same day last week | Waste cut (equal missed sales) |
|---|---|---|---|---|---|---|
| 1 | Ensemble (LightGBM + HGB + RF) | Ensemble | 0.322 | 0.293 | -21.7% | -41.4% |
| 2 | LightGBM (median) | Boosting | 0.3224 | 0.293 | -21.6% | -41.4% |
| 3 | LightGBM (mean) | Boosting | 0.3262 | 0.297 | -20.6% | -39.9% |
| 4 | HistGradientBoosting | Boosting | 0.3267 | 0.297 | -20.5% | -40.1% |
| 5 | XGBoost | Boosting | 0.3274 | 0.298 | -20.4% | -39.5% |
| 6 | Random forest | Tree ensemble | 0.328 | 0.298 | -20.2% | -39.1% |
| 7 | Lasso | Linear | 0.3287 | 0.299 | -20.0% | -38.6% |
| 8 | Ridge | Linear | 0.3287 | 0.299 | -20.0% | -38.6% |
| 9 | ElasticNet | Linear | 0.3287 | 0.299 | -20.0% | -38.6% |
| 10 | Linear regression | Linear | 0.3287 | 0.299 | -20.0% | -38.7% |
| 11 | Extra trees | Tree ensemble | 0.3324 | 0.302 | -19.1% | -37.1% |
| 12 | Decision tree | Tree | 0.3434 | 0.312 | -16.5% | -33.4% |
| 13 | MLP neural network | Neural | 0.3483 | 0.317 | -15.3% | -32.0% |
| 14 | 7-day moving average | No-ML benchmark | 0.3653 | 0.332 | -11.1% | -23.4% |
| 15 | Same day last week | No-ML benchmark | 0.411 | 0.374 | +0.0% | +0.0% |
| 16 | Average of last 4 same weekdays | No-ML benchmark | 0.426 | 0.388 | +3.6% | +9.9% |

## Favorita (Ecuador grocery: bakery, deli, poultry, prepared foods, 2014-2017)
Test window: 2017-07-19 to 2017-08-15 (last 28 days) - 17,286 rows - unit: units (some by weight)

| Rank | Model | Type | MAE | WAPE | vs same day last week | Waste cut (equal missed sales) |
|---|---|---|---|---|---|---|
| 1 | LightGBM (median) | Boosting | 3.063 | 0.413 | -25.9% | -52.6% |
| 2 | Ensemble (LightGBM + HGB + RF) | Ensemble | 3.1 | 0.418 | -25.0% | -46.9% |
| 3 | LightGBM (mean) | Boosting | 3.123 | 0.421 | -24.4% | -44.0% |
| 4 | HistGradientBoosting | Boosting | 3.138 | 0.423 | -24.0% | -42.9% |
| 5 | XGBoost | Boosting | 3.158 | 0.426 | -23.5% | -42.5% |
| 6 | MLP neural network | Neural | 3.189 | 0.430 | -22.8% | -44.1% |
| 7 | Random forest | Tree ensemble | 3.206 | 0.432 | -22.4% | -40.9% |
| 8 | Linear regression | Linear | 3.225 | 0.435 | -21.9% | -42.3% |
| 9 | Ridge | Linear | 3.225 | 0.435 | -21.9% | -42.3% |
| 10 | ElasticNet | Linear | 3.225 | 0.435 | -21.9% | -42.3% |
| 11 | Lasso | Linear | 3.225 | 0.435 | -21.9% | -42.2% |
| 12 | Extra trees | Tree ensemble | 3.254 | 0.439 | -21.2% | -39.4% |
| 13 | Decision tree | Tree | 3.263 | 0.440 | -21.0% | -40.2% |
| 14 | 7-day moving average | No-ML benchmark | 3.419 | 0.461 | -17.2% | -40.6% |
| 15 | Average of last 4 same weekdays | No-ML benchmark | 3.549 | 0.478 | -14.1% | -34.6% |
| 16 | Same day last week | No-ML benchmark | 4.131 | 0.557 | +0.0% | +0.0% |

## Dominick's Finer Foods (Chicago, daily bakery + deli dollar sales, 1988-1997)
Test window: 1997-02-06 to 1997-04-30 (last 84 days) - 13,960 rows - unit: US dollars per day

| Rank | Model | Type | MAE | WAPE | vs same day last week | Waste cut (equal missed sales) |
|---|---|---|---|---|---|---|
| 1 | LightGBM (mean) | Boosting | 213 | 0.101 | -38.8% | -57.8% |
| 2 | XGBoost | Boosting | 214.8 | 0.102 | -38.3% | -57.9% |
| 3 | MLP neural network | Neural | 215.4 | 0.103 | -38.1% | -54.7% |
| 4 | LightGBM (median) | Boosting | 217.1 | 0.103 | -37.6% | -57.0% |
| 5 | Ensemble (LightGBM + HGB + RF) | Ensemble | 217.4 | 0.104 | -37.5% | -55.6% |
| 6 | HistGradientBoosting | Boosting | 218.2 | 0.104 | -37.3% | -55.0% |
| 7 | Random forest | Tree ensemble | 229.6 | 0.109 | -34.0% | -49.4% |
| 8 | Extra trees | Tree ensemble | 237 | 0.113 | -31.9% | -48.1% |
| 9 | Decision tree | Tree | 246.3 | 0.117 | -29.2% | -44.2% |
| 10 | Average of last 4 same weekdays | No-ML benchmark | 264.4 | 0.126 | -24.0% | -32.1% |
| 11 | Lasso | Linear | 274.1 | 0.131 | -21.2% | -32.3% |
| 12 | ElasticNet | Linear | 274.2 | 0.131 | -21.2% | -32.3% |
| 13 | Ridge | Linear | 274.3 | 0.131 | -21.2% | -32.2% |
| 14 | Linear regression | Linear | 274.3 | 0.131 | -21.2% | -32.2% |
| 15 | Same day last week | No-ML benchmark | 348 | 0.166 | +0.0% | +0.0% |
| 16 | 7-day moving average | No-ML benchmark | 538.8 | 0.257 | +54.8% | +106.0% |
