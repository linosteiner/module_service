# Build stage: resolves the locked dependencies into a virtualenv with uv. Nothing of uv
# itself ends up in the runtime image.
FROM ghcr.io/astral-sh/uv:0.9.30-python3.13-bookworm-slim AS build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
COPY pyproject.toml uv.lock ./
# --frozen: install exactly uv.lock, fail if it is out of date with pyproject.toml.
# --no-install-project: the app is run from /app as source, it is not installed as a package.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev


FROM python:3.13-slim-bookworm
LABEL authors="Lennard Bernet, Lino Steiner"

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Fixed numeric uid, so Kubernetes' runAsNonRoot can verify it without a passwd lookup.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY schema.sql ./
COPY app/ app/

USER 10001
EXPOSE 8080

# One worker per container: scaling happens through replicas and the container's cpu/memory
# limits, not through processes inside the pod. The sync endpoints run on uvicorn's
# threadpool, so a single worker still serves requests concurrently.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
