# Deploy — free Hugging Face ZeroGPU Space

One ASGI app serves everything on port 7860, so there is no CORS setup and no
mixed-content problem:

| Path | Serves |
|---|---|
| `/` | the exported Expo web bundle (the recipe pie chart app) |
| `/api/*` | `food_server/server.py`, mounted as WSGI, unmodified |
| `/gradio/` | a Gradio demo of the gram estimator |

| | |
|---|---|
| Host | Hugging Face Space, Gradio SDK, **ZeroGPU** hardware |
| Cost | Free. No credit card. |
| Model weights | [`KL946/deberta-v3-base-grams`](https://huggingface.co/KL946/deberta-v3-base-grams), pulled from the Hub at startup |
| Gram backends | `deberta` only — Ollama (`phi3`, `llama3:8b`) needs a local daemon |

> **Why ZeroGPU and not plain CPU?** HF moved Gradio and Docker Spaces on free
> `cpu-basic` behind a PRO subscription in mid-2026; Static Spaces are the only
> free option left, and they cannot run Flask. The exception is ZeroGPU: free
> personal accounts in good standing can host **2 ZeroGPU Spaces at no cost**.
> Inference genuinely runs on the GPU here, so this is the intended use, not a
> workaround — and DeBERTa on GPU is far faster than on `cpu-basic` anyway.

## Prerequisites

ZeroGPU's free tier requires a Hugging Face account **in good standing**:
verified email and **older than 30 days**. Maximum 2 ZeroGPU Spaces.

## 1. Create the Space

At <https://huggingface.co/new-space>:

- **Owner** `KL946`, **Space name** `food_chart`
- **SDK** → **Gradio** (not Docker — Docker requires PRO)
- **Hardware** → **ZeroGPU**
- **Visibility** → Public

Let HF create it through the web UI rather than pushing to an empty repo. HF
writes a `README.md` with the correct `sdk` and `sdk_version` front matter, and
the deploy script keeps that file.

## 2. Deploy

```bash
scripts/deploy_space.sh KL946/food_chart
```

The script builds the Expo bundle with `EXPO_BASE_URL=/app` and
`EXPO_PUBLIC_API_URL=/api`, clones the Space, copies in `app.py`,
`requirements.txt`, `server.py` and the bundle, then pushes.

`EXPO_BASE_URL` is required. Without it the bundle is built for the root path,
so serving it at `/app` still returns HTTP 200 with the right HTML, but
expo-router boots, matches no route and renders "This screen does not exist".
`curl` cannot see that failure — only a browser can. `food_app/app.config.js`
turns the variable into `experiments.baseUrl`; unset, the app stays at the root
as before for Docker, Cloud Run and local dev. Pushing needs an HF access token with **write** scope as the git
password, or `hf auth login` plus the git credential helper.

The first build takes several minutes: torch, transformers and Gradio.

## 3. Verify

```bash
curl -s https://kl946-food-chart.hf.space/api/health
```

Expect `"deberta_loaded": true`. The app is at the root URL; the Gradio demo is
at `/gradio/`.

---

## How the GPU is used

ZeroGPU allocates a GPU only inside a `@spaces.GPU` function and bills the
**daily quota by GPU seconds** — 5 minutes/day on a free account.

Allocating per ingredient would be wasteful: each allocation costs seconds of
process and CUDA setup, dwarfing the ~50ms of actual inference. So `server.py`
exposes a hook:

```python
deberta_batch_runner = None   # (list[item]) -> {index: {"predicted_grams", "trace"}}
```

`app.py` installs a `@spaces.GPU`-decorated batch function into it, so **one
allocation covers a whole request** no matter how many ingredients it carries.

The hook degrades safely, which is verified behaviour:

| Situation | Result |
|---|---|
| No runner installed (local, Docker, Cloud Run) | per-item path, unchanged |
| Runner installed | one batch call per request |
| Runner raises | falls back to per-item, HTTP 200, not a 500 |
| Runner returns only some indices | the missing ones fall back individually |

Outside a `@spaces.GPU` function ZeroGPU runs a CUDA emulation layer, so
`server.py` placing the model on `cuda` at import time works as ZeroGPU
requires. `spaces` is preinstalled on ZeroGPU hardware; `app.py` guards the
import so it still runs locally, where it simply uses the CPU path.

## Version constraints

Neither of these is optional:

- **torch 2.8.0 – 2.11.0.** ZeroGPU supports only that range, and it needs the
  CUDA build from PyPI — not the CPU wheel index the Docker image uses.
  Pinned to `2.9.1`.
- **transformers 5.6.0.** The checkpoint was saved by it: `config.json` uses the
  v5 `dtype` key, `tokenizer_config.json` declares `"backend": "tokenizers"`,
  and the folder has no `spm.model` for a v4 slow tokenizer to fall back on.

## Notes and limits

- **Sleep**: free Spaces pause after a period of inactivity and wake on the next
  request.
- **Quota**: 5 GPU-minutes/day on a free account. At ~50ms per prediction that
  is roughly 6,000 ingredients per day; the quota resets 24h after first use.
- **Scraping**: `recipe-scrapers` fetches recipe URLs from HF's IP range. Some
  sites block datacenter IPs, which surfaces as an error in the UI.
- **Fallback chain** is unchanged: DeBERTa → Ollama (unavailable) → T5 (not
  shipped) → heuristic. A DeBERTa failure still returns numbers, from the
  heuristic, so check `model_used` in the response when a result looks wrong.

## Re-uploading the model

The weights are 738MB, over GitHub's 100MB file limit, so they live on the Hub.
After retraining:

```bash
pip install -U "huggingface_hub[cli]"
hf auth login

hf upload KL946/deberta-v3-base-grams \
  food_model/gptgram_model/artifacts/deberta_v3_base_grams_text_input_final \
  --repo-type model
```

The folder must contain `config.json`, `model.safetensors`, `tokenizer.json`,
`tokenizer_config.json`, and the repo must stay public.

## What changed for deployment

- `food_server/server.py` — optional `STATIC_DIR` web serving, a `/health`
  endpoint, `PORT` from the environment, and the `deberta_batch_runner` hook.
  With none of them set it behaves exactly as before, API only.
- `food_app/app/index.jsx` — `BASE_URL` reads `EXPO_PUBLIC_API_URL` and defaults
  to same-origin; the model list reads `EXPO_PUBLIC_MODEL_OPTIONS`.
- `deploy/space/` — the Space entrypoint and its requirements.
- `scripts/deploy_space.sh` — build and push.
- `Dockerfile` — all-in-one image, used by the Cloud Run route below.
- `.gcloudignore` — upload filter for Cloud Run.
- `docker/frontend.Dockerfile` — takes an `EXPO_PUBLIC_API_URL` build arg so the
  existing `docker compose` setup (separate nginx + Flask origins) still works.

## Other deployment routes

- [`deploy/cloudrun.md`](deploy/cloudrun.md) — Google Cloud Run with the
  all-in-one Docker image. Always on, no GPU quota, but needs a credit card and
  costs a few cents a month for image storage.

## Local development

```bash
cp food_app/.env.example food_app/.env    # points at http://localhost:5050
cd food_app && npx expo start --web
```

Backend separately, or via the existing `docker compose up --build`.
