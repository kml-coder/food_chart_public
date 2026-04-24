# Docker Run Guide

This project supports both local Docker build and GHCR-based deployment.
Docker scope is intentionally limited to:

- `food_app` (frontend)
- `food_server` (backend API)

`food_model` training/data scripts are not part of Docker runtime.

## 1) Required model directory

The backend loads a local model from `./food_server/model`.

- Download your model files
- Place them under:

```bash
food_server/model
```

## 2) Local build mode (current machine)

From repository root:

```bash
docker compose up --build
```

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:5050`

Stop:

```bash
docker compose down
```

Ollama model can be changed with backend environment variable:

```bash
OLLAMA_MODEL=phi3
```

For example, use `llama3:8b` if needed.

## 3) GHCR image publish (GitHub Actions)

Workflow file:

```bash
.github/workflows/docker-publish.yml
```

When code is pushed to `main`, GitHub Actions publishes two images:

- `ghcr.io/<OWNER>/<REPO>-backend:latest`
- `ghcr.io/<OWNER>/<REPO>-frontend:latest`

`<OWNER>` = GitHub owner, `<REPO>` = repository name.

## 4) Server deployment with pulled images

Use `docker-compose.deploy.yml` on your server.

Set environment variables:

```bash
export GHCR_OWNER=<your-github-owner>
export IMAGE_PREFIX=<your-repository-name>
```

Then deploy:

```bash
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

Stop:

```bash
docker compose -f docker-compose.deploy.yml down
```
