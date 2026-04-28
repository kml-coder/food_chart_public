# Data Pipeline

## 1) Collect

- Collect ingredient lines from recipe websites
- Support both URL-based input and raw text input

## 2) Clean

Based on `food_model/gptgram_model/scrape/unit_size_cleanup.ipynb`:

- Separate `small|medium|large` from `unit`
- Normalize `thin slice` / `thick slice` to `slice`
- Remove multi-word units
- Remove duplicated unit tokens inside `name`

Output summary:

- Source rows: `18,352` (`output_filled.json`)
- Clean rows: `18,221` (`output_filled_name_unit_removed.json`)
- size cleanup/move count: `155`
- `slice` normalization count: `102`
- multi-word unit removals: `130`
- name-level unit cleanup count: `34`

## 3) Enrich

- Enrich missing unit/ingredient expressions with external data
- Normalize USDA entries using text before the first comma (short name)
- Fill selected data gaps with `ChatGPT API` for better accuracy

> The public JSON does not include recipe IDs, so metrics are tracked by ingredient rows rather than recipe count.
