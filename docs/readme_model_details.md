# Model Details

## Model Strategy

- Large open LLMs are possible, but they are oversized for this task in terms of cost and model footprint.
- I trained a domain-focused lightweight model directly for practical deployment efficiency.
- My objective is to predict grams from `unit`, `size`, and `name`, so I used an encoder-based regression model (`DeBERTa`).
- My goal was to keep the model practical for deployment while improving gram prediction quality on noisy ingredient-unit text.

## How I Built Inputs and Labels

I loaded the cleaned dataset from `final_unit_removed.json` and kept only rows where `gram > 0`.

- Input text (`text_input`) was created from normalized ingredient fields:
  - if `unit` exists: `"{quantity/article} {size} {unit} of {name}"`
  - if `unit` is empty: `"{quantity/article} {size} {name}"`
- Label was the numeric gram value from `gram`.
- For training stability, I transformed labels with `log1p`:
  - `label = log1p(gram)`
- I split the dataset into train/validation with an 80/20 split (`random_state=42`) and tokenized `text_input` with max length 96.
- Total usable rows (gram > 0): **25,983** — validation set: **5,197**

## Reproducibility

- Dataset file: `food_model/gptgram_model/final_unit_removed.json`
- Training split: 80/20 via `train_test_split(test_size=0.2, random_state=42)`
- Model: `microsoft/deberta-v3-base` with `num_labels=1`, `problem_type='regression'`
- Tokenization: max input length `96`
- Label transform: `log1p(gram)` for training, `expm1` for metric-space evaluation
- Training setup: epoch-level eval/save with early stopping (`patience=5`)
- Runtime note: training logs indicate a long single run to epoch `31.0` before best-checkpoint selection

---

## Training Result (DeBERTa)

```text
TrainOutput(
  global_step=20150,
  training_loss=0.3624865152433552,
  metrics={
    'train_runtime': 4931.4811,
    'train_samples_per_second': 210.748,
    'train_steps_per_second': 6.59,
    'total_flos': 4311873811009200.0,
    'train_loss': 0.3624865152433552,
    'epoch': 31.0
  }
)
```

- Best checkpoint: `artifacts/deberta_v3_base_grams_text_input/checkpoint-16900`
- Best eval loss: `0.16793961822986603`

---

## Evaluation Metrics

| metric | value |
| --- | ---: |
| parse_success_rate | 1.000000 |
| MAE_g | 38.87 |
| MAPE_pct | 40.46 |
| within_20pct | 0.544 |

## Range Metrics

| range_bin | count | mae_g | mape_pct | within20 |
| --- | ---: | ---: | ---: | ---: |
| 0–50 g | 2320 | 4.97 | 55.25 | 0.629 |
| 50–200 g | 1762 | 37.01 | 30.35 | 0.484 |
| 200 g+ | 1115 | 112.36 | 25.65 | 0.463 |

> Note: MAPE is heavily influenced by the 0–50 g range, where small absolute errors translate to large relative errors due to tiny true values (e.g. 1 saffron strand = 0.01 g). The model performs most stably in the 200 g+ range (MAPE 25.6%).

---

## Result Figures

### Overview

![DeBERTa Evaluation Overview](images/deberta_eval_improved.png)

*Predicted vs True zoomed to ≤ 2000 g, Absolute Error clipped to ≤ 500 g, Relative Error clipped to ≤ 3.*

---

### Error Analysis

#### Fig 1 — Top 20 Ingredients by MAPE

![Worst Ingredients](images/fig1_worst_ingredients.png)

Ingredients highlighted in red (MAPE > 80%) are structurally ambiguous: a single leaf of kale or spinach can range from <1 g to >100 g depending on serving context, and the model has no signal beyond the name. These are known hard cases, not random failures.

---

#### Fig 2 — Performance by Input Completeness

![Input Completeness](images/fig2_input_completeness.png)

When a `unit` is present (e.g. `"a cup of sugar"`), MAPE drops from **106%** to **27.8%** and within-20% accuracy rises from **37.8%** to **57.6%**. This confirms that the unit field is the strongest predictor — inputs without units rely entirely on the model's learned density priors.

---

#### Fig 3 — Prediction Bias Analysis

![Bias Analysis](images/fig3_bias_analysis.png)

The model over-predicts in **63.4%** of cases (median signed error: +3.3 g). This bias increases with weight range — in the 200 g+ bin, 84% of predictions are over-predictions. This is consistent with a log-space regression model that regresses to the mean: rare large-gram items are underrepresented in training, so the model hedges upward for ambiguous inputs.

---

#### Fig 4 — Case Study: Where the Model Succeeds and Fails

![Case Study](images/fig4_case_study.png)

**Worst cases** share a common pattern: inputs where the unit implies a count (leaf, strand, raisin, stick) but the true gram is context-dependent and near zero. `"a serving nonstick cooking spray"` (true: 0.3 g, pred: 101.6 g) is an extreme example — the model has no spray-specific density prior.

**Best cases** are predominantly standard volumetric units (`teaspoon`, `tablespoon`, `cup`, `fluid_ounce`) applied to ingredients with stable densities (mustard, vinegar, oil, cheese). These are the inputs the model was effectively trained for.

---

## Model Artifacts

- My DeBERTa model path in server runtime: `DEBERTA_MODEL_PATH`
- Optional model release link (to be added soon):

---

## Known Limits

- Parsing quality still varies across recipe websites.
- Lines without explicit units or with highly irregular expressions (leaf, strand, bunch) rely entirely on model inference and show significantly higher error.
- Some ingredients have large context-dependent weight variation even with the same name (e.g. `kale`, `spinach`).
- The model has a systematic over-prediction bias, especially in the 200 g+ range — likely due to underrepresentation of large-gram items in training data.
- Count-based units without a standard density prior (spray, raisin, strand) are the primary failure mode.
