# Data Pipeline

## Why I Built a Hybrid Dataset

I first tried to build unit-training data mainly from USDA.
However, USDA is largely focused on processed foods and standard portion descriptions, and it does not fully cover the wide variety of unit expressions seen in real recipe text.

So I adopted a hybrid strategy:

- Use USDA for stable portion-to-gram supervision
- Use large-scale recipe data for real-world unit diversity

---

## Recipe Data Pipeline (Allrecipes)

### 1) Collect

- Extract all recipes from Allrecipes XML
- Total recipes: `48,688`
- Expanded to ingredient-level rows: `393,471`

### 2) Keep non-direct-conversion units

To focus on the model-needed area, I excluded units that can be converted to grams directly (`kg`, `ounce`, `pound`, `ml`, etc.).

### 3) Deduplicate

Deduplication rule: exact match on `unit + size + name`

- Result: `18,352` rows (`output_filled.json`)

### 4) Messy-data cleanup (merged pipeline)

Reference notebook: `food_model/gptgram_model/scrape/unit_size_cleanup.ipynb`

**STEP 1**
- Remove size words (`small|medium|large`) from `unit`
- Move removed size words to the `size` field

**STEP 2**
- Simplify adjective-style unit expressions (`thin slice`, `thick slice` -> `slice`)
- Remove multi-word or noisy units (`fluid_ounce bottle`, `good handful`, `petainch * picoinch`, etc.)

**STEP 3-4**
- Detect rows where the ingredient `name` redundantly contains its own unit token, then remove that token from `name`

Merged cleanup pipeline logs:

- Source rows: `18,352`
- STEP1: `removed_size_words=155`, `moved_to_size=155`
- STEP2: `normalized_to_slice=102`, `removed_multiword=130`
- STEP3 match rows: `34`
- STEP4 final rows: `18,222`, `names_changed=34`

Output JSON files:

- `output_filled_unit_size_fixed.json`
- `output_filled_unit_singleword_only.json`
- `name_contains_its_own_unit_rows.json`
- `output_filled_name_unit_removed.json`

CSV outputs:

- `unit_counts_singleword_only.csv`
- `removed_multiword_units.csv`
- `multiword_unit_cleanup_summary.csv`
- `name_contains_its_own_unit_rows.csv`
- `name_unit_removed_rows.csv`
- `name_unit_removed_summary.csv`

---

## USDA Data Pipeline

### 1) Convert and inspect

- Source data: USDA `food.xlsx` (`22,046` rows)
- Keep relevant columns and convert to JSON
  - `Main food description`
  - `Portion description`
  - `Portion weight (g)`
- Audit unit types and frequencies

### 2) Unit-based filtering

- Exclude low-value unit patterns (for example, `package school meal`)
- Keep rows where selected unit names appear in `Portion description`
- Result: about `9,220` rows

### 3) Rule-based deletion

Deletion targets:

- Brand-dependent expressions
- Dimension-based expressions
- Guideline/serving-rule expressions
- Overly ambiguous units
- Portion descriptions that hurt training quality

After deletion: about `7,919` rows

### 4) Normalize and map fields

- Split size and unit in portion text (`1 large cup` -> size=`large`, unit=`cup`)
- Normalize unit expressions (`unit_normalized`)
- Use text before the first comma in `Main food description` as the core ingredient name (`main_ingredient`)

Final field mapping:

- `unit` <- `unit_normalized`
- `size` <- `size_normalized`
- `name` <- `main_ingredient`
- `long_name` <- `Main food description`
- `gram` <- `Portion weight (g)`

Result: about `7,919` rows (`food_portion_description_converted.json`)

---

## Final Merge

- I merged recipe-cleaned data with USDA-converted data
- Final merged dataset: about `26,140` rows (`scrape/final.json`)

I used this merged dataset as the core unit/gram training data for my gram prediction model.

---

## Dataset Versions

Model experiments ran across three versions of this data. `usable` counts rows with `gram > 0`.

| Version | File | Rows | Usable | What changed |
| --- | --- | ---: | ---: | --- |
| v1 raw | `scrape/output_filled.json` | 18,352 | 18,262 | Recipe rows, deduplicated |
| v2 cleaned | `scrape/output_filled_name_unit_removed.json` | 18,222 | 18,136 | STEP1–4 cleanup |
| v3 merged | `final_unit_removed.json` | 26,069 | **25,983** | USDA merged in (`long_name` added) |

The shipped model is trained on **v3**, and every metric reported in this repo refers to v3.

---

## Known Limits

- **The published dataset carries no recipe id.** Rows are ingredient-level and were
  deduplicated on `unit + size + name`, which collapses rows across recipes. As a
  result, counts here are ingredient rows rather than recipes, and any per-recipe
  metric (for example the pie-chart slice error in the model doc) has to be
  approximated with synthetic groupings instead of measured directly.
- USDA coverage skews toward processed foods and standard portion descriptions, so
  unusual recipe-side units (`bunch`, `sprig`, `handful`) rely mostly on the recipe
  pipeline and carry higher error.

---

## Data Lineage (Audit View)

| Input file | Transform | Output file | Row count |
| --- | --- | --- | ---: |
| Allrecipes ingredient rows | Keep non-direct-conversion units + deduplicate (`unit+size+name`) | `output_filled.json` | 18,352 |
| `output_filled.json` | STEP1-4 merged cleanup (size move, unit cleanup, name-unit cleanup) | `output_filled_name_unit_removed.json` | 18,222 |
| `food.xlsx` | Column select + JSON conversion | `food.json` | 22,046 |
| `food.json` | Selected-unit filtering in `Portion description` | `food_portion_description_contains_selected_units.json` | 9,220 |
| Selected USDA subset | Rule-based deletion + unit/size normalization + name extraction | `food_portion_description_unit_rules_applied_with_main_ingredient_before_first_comma.json` | 7,919 |
| Previous USDA output | Field mapping to training schema | `food_portion_description_converted.json` | 7,919 |
| Recipe-cleaned + USDA-converted | Merge | `final.json` | 26,140 |
