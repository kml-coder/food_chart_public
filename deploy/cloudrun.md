# Alternative deploy — all-in-one image on Google Cloud Run

> The primary target is a free Hugging Face ZeroGPU Space; see
> [`../DEPLOY.md`](../DEPLOY.md). Use this route if you want an always-on
> service with no GPU quota and no Space sleep, and you are willing to attach a
> credit card. Compute stays inside the always-free tier; image storage costs a
> few cents a month.

One Docker image serves the exported Expo web bundle **and** the Flask API on a
single port. Same origin, so there is no CORS setup and no mixed-content problem.

| | |
|---|---|
| Host | Google Cloud Run, scale-to-zero, HTTPS included |
| Model weights | [`KL946/deberta-v3-base-grams`](https://huggingface.co/KL946/deberta-v3-base-grams), baked into the image at build time |
| Gram backends | `deberta` only — Ollama (`phi3`, `llama3:8b`) needs a local daemon |
| Cost | Compute fits the always-free tier; image storage runs a few cents a month (see below) |

> **Why not Hugging Face Spaces?** HF moved Docker Spaces behind a paywall in
> mid-2026: creating one now requires billing credits or a PRO subscription.
> Static Spaces stay free but cannot host the Flask backend.

---

## 1. Upload the DeBERTa weights to the Hub — done

The weights are 738MB, over GitHub's 100MB file limit, so they live on the Hub
(public, non-gated). To re-upload after retraining:

```bash
pip install -U "huggingface_hub[cli]"
hf auth login

hf upload KL946/deberta-v3-base-grams \
  food_model/gptgram_model/artifacts/deberta_v3_base_grams_text_input_final \
  --repo-type model
```

The folder must contain `config.json`, `model.safetensors`, `tokenizer.json`,
`tokenizer_config.json`.

## 2. Point the Dockerfile at that repo — done

```dockerfile
ARG DEBERTA_REPO_ID=KL946/deberta-v3-base-grams
```

## 3. Set up gcloud

```bash
brew install --cask google-cloud-sdk
```

Then, interactively (these open a browser):

```bash
gcloud auth login
gcloud projects create food-chart-app --name="Food Chart"   # or reuse a project
gcloud config set project food-chart-app
```

Enable billing on the project at
<https://console.cloud.google.com/billing> — a card is required even though the
usage below stays inside the free tier. Then enable the APIs:

```bash
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

## 4. Deploy

```bash
gcloud run deploy food-chart \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 4 \
  --min-instances 0 \
  --max-instances 3
```

Cloud Build builds the Dockerfile in the cloud, pushes to Artifact Registry, and
Cloud Run starts it. First deploy takes ~15 minutes: `npm ci` plus the Expo
export, the CPU torch wheel, and the 738MB model download.

The flags matter:

- `--memory 2Gi` — torch plus DeBERTa-v3-base is ~1.5GB resident. 1Gi OOMs.
- `--min-instances 0` — no idle cost, at the price of cold starts.
- `--concurrency 4` — gunicorn runs a single sync worker, so requests are
  handled one at a time anyway; a high concurrency just builds a queue.
- `--timeout 300` — matches the gunicorn timeout, covers slow scraping.

`--source .` uploads the working directory, filtered by `.gcloudignore`. That
filter is **not optional**: it cuts the upload from 22GB to about 4MB by
excluding `food_model/` (training artifacts and the 6.7GB fastText binary),
`node_modules/`, and `.venv/`.

## 5. Verify

```bash
SERVICE_URL=$(gcloud run services describe food-chart \
  --region us-central1 --format='value(status.url)')

curl -s "$SERVICE_URL/health"
```

Expect `"deberta_loaded": true` and `"serving_web": true`. The UI is at the same
URL; the pie chart page is the root route `/`.

---

## Cost

Always-free monthly tier, and what this app uses:

| Resource | Free per month | Notes |
|---|---|---|
| Cloud Run requests | 2,000,000 | Request-based billing only |
| Cloud Run memory | 360,000 GiB-seconds | 2GiB × ~180,000s of request time |
| Cloud Run vCPU | 180,000 vCPU-seconds | 2 vCPU × ~90,000s of request time |
| Cloud Build | 2,500 build-minutes | A deploy costs ~15 |
| Artifact Registry | **0.5 GB storage** | The image is ~1GB compressed |

Only the last line goes over: image storage costs roughly **$0.10/month**, and
grows if old revisions pile up. Clean them out periodically:

```bash
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/food-chart-app/cloud-run-source-deploy/food-chart
```

Compute stays free at hobby traffic because CPU is billed only while a request
is in flight.

## Notes and limits

- **Cold start**: the model is baked into the image, so a wake-up is container
  start plus loading 738MB into RAM — roughly 20-40s on the first request after
  idle. Set `--min-instances 1` to remove it, but that bills continuously and
  leaves the free tier.
- **Inference**: DeBERTa-v3-base on 2 vCPU is a few hundred ms per ingredient.
  `Predict Grams` over a long except-list is sequential.
- **Scraping**: `recipe-scrapers` fetches the recipe URL from Google's IP range.
  Some sites block datacenter IPs, which surfaces as an error in the UI.
- **Fallback chain** is unchanged: DeBERTa → Ollama (unavailable) → T5 (not
  shipped) → heuristic. A DeBERTa failure still returns numbers, from the
  heuristic, so check `model_used` in the response when a result looks wrong.

## What changed for deployment

- `food_server/server.py` — serves `STATIC_DIR` (the web bundle) plus a `/health`
  endpoint; the port comes from `PORT`. With `STATIC_DIR` unset it behaves
  exactly as before, API only.
- `food_app/app/index.jsx` — the pie chart screen, now the only route.
  `BASE_URL` reads `EXPO_PUBLIC_API_URL`
  and defaults to same-origin; the model list reads `EXPO_PUBLIC_MODEL_OPTIONS`.
- `Dockerfile` — new, the all-in-one image.
- `.gcloudignore` — new, the upload filter described above.
- `docker/frontend.Dockerfile` — takes an `EXPO_PUBLIC_API_URL` build arg so the
  existing `docker compose` setup (separate nginx + Flask origins) still works.

## Runtime environment variables

| Variable | Default in image | Purpose |
|---|---|---|
| `STATIC_DIR` | `/home/user/app/web` | Web bundle directory; empty = API only |
| `PORT` | `7860`, overridden by Cloud Run | Port gunicorn binds |
| `DEBERTA_MODEL_PATH` | the `ARG` value | Hub repo id or local model directory |
| `USE_OLLAMA_GRAMS` | `false` | No Ollama daemon in the container |

## Testing the image locally

The image targets **linux/amd64**, matching Cloud Run. The PyTorch CPU wheel
index has no aarch64 build past 2.5.1, so on Apple Silicon pass the platform
flag and let emulation handle it:

```bash
docker build --platform linux/amd64 -t food-chart-space .
docker run --rm -p 7860:7860 food-chart-space
curl -s localhost:7860/health
```

## Local development

```bash
cp food_app/.env.example food_app/.env    # points at http://localhost:5050
cd food_app && npx expo start --web
```

Backend separately, or via the existing `docker compose up --build`.
