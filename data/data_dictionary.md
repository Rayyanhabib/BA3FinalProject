# Data dictionary

Describes every file in `data/processed/` and the raw fields behind it.

**Sources**
- Dominick's: [Kilts Center, Dominick's Manual and Codebook](https://www.chicagobooth.edu/research/kilts/research-data/-/media/enterprise/centers/kilts/datasets/dominicks-dataset/dominicks-manual-and-codebook_kiltscenter), read in full.
- Favorita: [Kaggle, Corporación Favorita Grocery Sales Forecasting, Data tab](https://www.kaggle.com/c/favorita-grocery-sales-forecasting/data), read in full.
- FreshRetailNet-50K: no source document was provided. Only what the project code establishes is described; the rest is marked `[confirm]`.

Where a description is the team's own processing choice rather than the source's, the "Source" column says **Derived** and points to the script.

## Files at a glance

| File | Dataset | Grain (one row per) | Built by |
|---|---|---|---|
| `dominicks_dept.csv` | Dominick's | store, day | `src/01_download/extract_dominicks.py` and `src/02_clean/clean_dominicks.py` |
| `dominicks_clean.csv` | Dominick's | store, day (complete calendar) | `src/02_clean/clean_data.py` |
| `favorita_food.csv` | Favorita | store, item, day (days with sales) | `src/02_clean/filter_favorita.py` |
| `favorita_clean.csv` | Favorita | store, item, day (zero-filled) | `src/02_clean/clean_data.py` |
| `fresh_train.csv`, `fresh_eval.csv` | FreshRetailNet-50K | store, product, day | `src/01_download/download_fresh.py` |
| `fresh_clean.csv` | FreshRetailNet-50K | store, product, day | `src/02_clean/clean_data.py` |

---

## 1. Dominick's (U.S. grocery chain, Chicago area)

The manual describes the customer count file (`ccount`) as store-specific, daily, and compiled from register and scanner receipts. Customer count is the number of customers visiting the store and purchasing something. Sales are totals by Dominick's-defined department.

### `dominicks_dept.csv`

Eight department and traffic fields kept from `ccount`, after parsing the date. No cleaning rules applied.

| Column | Type | Description | Source |
|---|---|---|---|
| `store` | integer | Store code | Manual: "Store Code" |
| `date` | date | Date of the observation | Manual: character, length 6. Parsed as `YYMMDD` by `src/02_clean/clean_dominicks.py` (**format is our reading; the manual gives only the type and length**) |
| `bakery` | decimal | Bakery sales in dollars | Manual |
| `deli` | decimal | Deli sales in dollars | Manual |
| `deliself` | decimal | Deli self-service sales in dollars | Manual |
| `deliexpr` | decimal | Deli express sales in dollars | Manual |
| `convfood` | decimal | Conventional foods sales in dollars | Manual |
| `saladbar` | decimal | Salad bar sales in dollars | Manual |
| `custcoun` | decimal | Customer count | Manual |

Not kept from `ccount`: `week`, all coupon-redeemed fields, and the other department sales fields (beer, dairy, produce and so on). The demographics file (`demo.dta`, 1990 U.S. census profiles per store) is not used.

### `dominicks_clean.csv`

Same columns as `dominicks_dept.csv`, plus one flag. Stores are filtered and each store is reindexed to a complete daily calendar.

| Column | Type | Description | Source |
|---|---|---|---|
| `date`, `store`, `bakery`, `deli`, `deliself`, `deliexpr`, `convfood`, `saladbar`, `custcoun` | | As above | |
| `usable` | boolean | `True` if `custcoun` is between 100 and 20,000, `bakery` is above 0 and at most 10,000, and `deli` is above 0 and at most 50,000. Calendar-filled days are `False`. | Derived (`clean_data.py`) |

Cleaning rules: drop dates outside 1988-1997; keep stores with a span of at least 1,000 days and at least 95% of days present (101 of 128 stores). Result: 297,533 rows, 291,011 usable. Values are **dollars, not units**.

---

## 2. Favorita (Ecuador grocery chain)

Kaggle states the task as predicting unit sales for thousands of items at Favorita stores in Ecuador. Raw files from the competition:

| Raw file | Content (Kaggle) |
|---|---|
| `train.csv` | Target `unit_sales` by `date`, `store_nbr`, `item_nbr`, with a unique `id` |
| `items.csv` | Item metadata: `family`, `class`, `perishable` |
| `stores.csv` | Store metadata: city, state, type, cluster (not used) |
| `transactions.csv` | Count of sales transactions per date and store (not used) |
| `oil.csv`, `holidays_events.csv` | Daily oil price; holidays and events (downloaded, not yet used) |
| `test.csv`, `sample_submission.csv` | Competition test set and submission format (not used) |

### `favorita_food.csv`

`train.csv` joined to `items.csv`, keeping only items in four families: BREAD/BAKERY, DELI, PREPARED FOODS and POULTRY. 11,284,633 rows, 2013-01-01 to 2017-08-15.

| Column | Type | Description | Source |
|---|---|---|---|
| `id` | integer | Unique row identifier | Kaggle: "unique id to label rows" |
| `date` | date | Sale date | Kaggle |
| `store_nbr` | integer | Store number | Kaggle |
| `item_nbr` | integer | Item number | Kaggle |
| `unit_sales` | decimal | Units sold. Can be an integer (a bag of chips) or a decimal (1.5 kg of cheese). **Negative values are returns.** | Kaggle |
| `onpromotion` | boolean | Whether the item was on promotion at that store on that date. Empty when unknown. | Kaggle. Kaggle reports about 16% empty in the full file; this food subset is 20.0% empty, and all empty values fall before 2014-04-01 |
| `family` | text | Item family | Kaggle (`items.csv`) |
| `class` | integer | Item class | Kaggle (`items.csv`) |
| `perishable` | 0 or 1 | 1 if the item is perishable. Perishable items carry a score weight of 1.25 in the competition, otherwise 1.0. | Kaggle (`items.csv`) |

Kaggle also notes that `train.csv` has **no rows for item, store and day combinations with zero sales**, and that there is no information on whether the item was in stock. The cleaning step handles this by zero-filling (below).

### `favorita_clean.csv`

| Column | Type | Description | Source |
|---|---|---|---|
| `date` | date | Sale date, from 2014-04-01 to 2017-08-15 | Kaggle, filtered |
| `store_nbr` | integer | Store number | Kaggle |
| `item_nbr` | integer | Item number | Kaggle |
| `unit_sales` | decimal | Units sold; 0 on zero-filled days | Kaggle / Derived |
| `onpromotion` | 0 or 1 | Promotion flag | Kaggle, converted from true/false |
| `family` | text | Item family | Kaggle (`items.csv`) |
| `class` | integer | Item class | Kaggle (`items.csv`) |
| `zero_filled` | boolean | `True` if the row was added by the zero-fill because the source had no row that day | Derived (`clean_data.py`) |
| `usable` | boolean | Always `True` in this file | Derived |

Cleaning rules: drop rows before 2014-04-01 (promotion flag not recorded); drop negative `unit_sales` (returns); keep series with at least 365 sale days and at least 50% of days present (8,993 of 12,562); fill missing days with 0 only on days the store sold any food item, and only between a series' first and last sale. Result: 9,805,048 rows, of which 1,419,430 (14.5%) are zero-filled. `id` and `perishable` are not carried over.

---

## 3. FreshRetailNet-50K

Files `fresh_train.csv` (2024-03-28 to 2024-06-25) and `fresh_eval.csv` (2024-06-26 to 2024-07-02) hold the raw columns. `fresh_clean.csv` keeps 14 of them plus four derived fields. Descriptions below come only from the project code. `[confirm]` marks items to check against the dataset's own documentation.

### Raw columns (`fresh_train.csv`, `fresh_eval.csv`)

| Column | Type | Description |
|---|---|---|
| `city_id`, `store_id`, `product_id` | integer | Identifiers `[confirm]` |
| `management_group_id`, `first_category_id`, `second_category_id`, `third_category_id` | integer | Store group and three product category levels `[confirm]` |
| `dt` | date | Observation date |
| `sale_amount` | decimal | Sales for the day `[confirm unit]` |
| `hours_sale` | text | 24 hourly sales values stored as one text cell |
| `stock_hour6_22_cnt` | integer | Number of hours stocked out between 06:00 and 22:00 (per `clean_data.py`) |
| `hours_stock_status` | text | 24 hourly stock flags stored as one text cell `[confirm]` |
| `discount` | decimal | Discount level. A value of 0 or below looks like a missing value (per `clean_data.py`) |
| `holiday_flag`, `activity_flag` | 0 or 1 | Holiday and promotional-activity flags `[confirm]` |
| `precpt`, `avg_temperature`, `avg_humidity`, `avg_wind_level` | decimal | Daily weather: precipitation, temperature, humidity, wind `[confirm units]` |

### `fresh_clean.csv`

| Column | Type | Description | Source |
|---|---|---|---|
| `city_id`, `store_id`, `product_id`, `first_category_id` | integer | As above | Raw |
| `date` | date | Renamed from `dt` | Raw |
| `sale_amount`, `stock_hour6_22_cnt`, `discount`, `holiday_flag`, `activity_flag`, `precpt`, `avg_temperature`, `avg_humidity`, `avg_wind_level` | | As above | Raw |
| `split` | text | `train` or `eval`, from the source file | Derived |
| `censored` | boolean | `True` if `stock_hour6_22_cnt` is above 0. Sales on that day are censored (understate demand). | Derived |
| `bad_discount` | boolean | `True` if `discount` is 0 or below | Derived |
| `usable` | boolean | `True` if neither `censored` nor `bad_discount`. 2,710,168 of 4,850,000 rows (55.9%). | Derived |

The hourly array columns and the second and third category levels are dropped. Each of the 50,000 store-product series is a complete daily run.

---

## Notes for readers

- **Dominick's is in dollars, 1988-1997.** Favorita and FreshRetailNet are in units. Do not mix them in one metric without converting.
- **`usable` rows are the only rows to train and score on**, after lag features are built. Bad and censored rows are flagged rather than removed so each daily series keeps its gaps in the right place.
- **None of this is Vietnamese data.** It supports the method, not Vietnamese accuracy.
