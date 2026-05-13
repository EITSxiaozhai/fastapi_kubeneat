# fastapi-kubeneat

FastAPI + Celery backend for uploading Kubernetes YAML manifests and cleaning them with `kubectl-neat`.

## Run

Install backend dependencies:

```bash
pip install -e .
```

Start Redis, then run:

```bash
uvicorn app.main:app --reload
celery -A app.celery_app.celery_app worker --loglevel=info --pool=solo
```

`kubectl-neat` must be available in `PATH`, or set `KUBECTL_NEAT_BIN`.
