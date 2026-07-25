# ============================================================
# All-in-one image: one process serves both the exported Expo web bundle and
# the Flask API on a single port, so there is no CORS or mixed-content problem.
#
# Target is Google Cloud Run, which injects $PORT. Also runs unchanged on any
# host that does the same (Fly, Render) or that expects 7860 (HF Spaces).
# Build for linux/amd64.
# ============================================================

# ---------- stage 1: build the Expo web bundle ----------
FROM node:20-alpine AS web-builder

WORKDIR /build

COPY food_app/package*.json /build/
RUN npm ci

COPY food_app /build

# Empty API URL => same-origin requests, handled by the Flask server below.
# Ollama backends are unavailable in the hosted image, so only DeBERTa is offered.
ENV EXPO_PUBLIC_MODEL_OPTIONS=deberta

# --output-dir must stay inside the project directory.
RUN npx expo export --platform web --output-dir web-dist

# ---------- stage 2: runtime ----------
FROM python:3.10-slim

# Hugging Face Spaces expects the container to run as uid 1000.
RUN useradd -m -u 1000 user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

USER user
WORKDIR /home/user/app

COPY --chown=user docker/space.requirements.txt /tmp/requirements.txt

# CPU-only torch wheel: the default PyPI build drags in ~2GB of CUDA libraries
# that this image never uses.
#
# This pin is linux/amd64 only, which is what Hugging Face Spaces runs. The CPU
# index carries no aarch64 wheel past 2.5.1, so a native arm64 build fails here;
# build with --platform linux/amd64 to test on Apple Silicon.
#
# The pip bundled with python:3.10-slim (23.0.1) rejects the PyTorch index's
# typing_extensions wheel over a name-normalization mismatch, so upgrade first.
RUN pip install --no-cache-dir --user --upgrade pip \
 && pip install --no-cache-dir --user torch==2.9.1 \
        --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --user -r /tmp/requirements.txt

# ---- EDIT THIS LINE: your Hugging Face model repo id ----
ARG DEBERTA_REPO_ID=KL946/deberta-v3-base-grams

# Bake the weights into the image so a cold start does not re-download 700MB.
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('${DEBERTA_REPO_ID}')"

COPY --chown=user food_server/server.py /home/user/app/server.py
COPY --chown=user --from=web-builder /build/web-dist /home/user/app/web

ENV DEBERTA_MODEL_PATH=${DEBERTA_REPO_ID} \
    STATIC_DIR=/home/user/app/web \
    USE_OLLAMA_GRAMS=false \
    PORT=7860

EXPOSE 7860

# 1 worker: the model is ~1.5GB resident and requests are CPU bound anyway.
# 300s timeout covers slow recipe scraping and CPU inference.
# Shell form so $PORT is expanded: Cloud Run and Fly inject their own port,
# HF Spaces wants 7860. `exec` replaces the shell so gunicorn becomes PID 1 and
# actually receives SIGTERM on shutdown.
CMD exec gunicorn -b 0.0.0.0:${PORT:-7860} -w 1 -t 300 server:app
