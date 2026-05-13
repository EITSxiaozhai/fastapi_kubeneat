FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV KUBECTL_NEAT_BIN=/usr/local/bin/kubectl-neat
ENV KUBENEAT_RUNTIME_DIR=/data/runtime

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY kubectl-neat /usr/local/bin/kubectl-neat

RUN pip install --no-cache-dir . \
    && chmod +x /usr/local/bin/kubectl-neat \
    && mkdir -p /data/runtime/uploads /data/runtime/results

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
