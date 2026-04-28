# Model Details

## Model Strategy

- Large open LLMs are possible, but they are oversized for this task in terms of cost and model footprint
- Train domain-focused lightweight models directly for practical deployment efficiency
- After baseline comparisons, center experiments on `t5-small`, with a `DeBERTa` path also wired in the server

Experiment logs (representative values):

- usable rows: `18,262` / `18,136` / `25,983`
- Parse success rate: `1.0000`
- MAE: `55.1919 g`
- MAPE: `175.99%`
- Within 20%: `0.5809`
- Robust MAE: `29.8048 g`

> Metrics vary depending on dataset version and experiment settings.

---

## Model Artifacts

- Local T5 model download: [Google Drive](https://drive.google.com/file/d/1_l-JuXDqZ-0Qd15OYCNO-n60bmftbety/view?usp=drive_link)
- Server model loading path: `food_server/model`
- DeBERTa path via environment variable: `DEBERTA_MODEL_PATH`
- Hugging Face link (to be added after release):
  - `https://huggingface.co/<your-org-or-id>/<model-repo>`

---

## Documentation

Detailed model-building and experiment notes are available in:

- `food_model/gptgram_model/scrape/unit_size_cleanup.ipynb`
- `food_model/gptgram_model/t5_small_regression.ipynb`

---

## Known Limits

- Parsing quality varies across recipe websites
- Lines without units or with highly irregular formats depend more heavily on model inference
- Some ingredients have large context-dependent weight variation even with the same name
