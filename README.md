# Module Service

Der Service verwaltet Module über eine REST-API und speichert sie in MySQL.

## API

| Methode | Pfad | Beschreibung | Status |
| --- | --- | --- | --- |
| `POST` | `/api/v1/modules` | Modul anlegen | `201` |
| `GET` | `/api/v1/modules` | Alle Module lesen | `200` |
| `GET` | `/api/v1/modules/{module_id}` | Modul lesen | `200` |
| `PATCH` | `/api/v1/modules/{module_id}` | Modul teilweise aktualisieren | `200` |
| `DELETE` | `/api/v1/modules/{module_id}` | Modul löschen | `204` |
| `GET` | `/api/v1/users/{user_id}/modules` | Module eines Users lesen | `200` |
| `PUT` | `/api/v1/users/{user_id}/modules/{module_id}` | Modul einem User zuweisen | `204` |

Ein Modul enthält folgende Felder:

```json
{
  "id": "c02f58f2-3aca-4f1e-8076-bacf6f1999e6",
  "code": "CLOUD-ARCH",
  "name": "Cloud Architecture",
  "description": "Designing reliable and scalable cloud systems",
  "created_at": "2026-09-16T09:02:09",
  "updated_at": "2026-09-16T09:02:09"
}
```

Die OpenAPI-Dokumentation ist unter `/docs` erreichbar.

Die Zuweisung ist idempotent: Wiederholte `PUT`-Requests für denselben User und dasselbe
Modul erzeugen nur einen Eintrag in `users_modules`. Die User-ID stammt aus dem
`user_mgmt_service`; der Module Service prüft nur, ob das angegebene Modul existiert.

Fehler haben immer die Form `{"code": "...", "message": "..."}`:

| Status | Code | Wann |
| --- | --- | --- |
| `404` | `MODULE_NOT_FOUND` | Modul existiert nicht |
| `409` | `MODULE_CODE_EXISTS` | Modul-Code ist bereits vergeben |
| `422` | – | Ungültiger Request (z. B. keine UUID) |
| `503` | `DATABASE_UNAVAILABLE` | MySQL ist nicht erreichbar; ein späterer Versuch kann gelingen |

## Betrieb

| Pfad | Zweck |
| --- | --- |
| `GET /health/live` | Liveness-Probe. Prüft nur den Prozess, nicht die Datenbank: ein MySQL-Ausfall soll keine Neustart-Schleife auslösen. |
| `GET /health/ready` | Readiness-Probe. `503`, solange MySQL nicht erreichbar ist; der Pod fällt dann aus dem Service. |
| `GET /metrics` | Prometheus-Metriken (siehe unten). |

Metriken für Request Rate, Response Time und Error Rate:

```text
http_requests_total{method, path, status}             Counter
http_request_duration_seconds_bucket{method, path, le} Histogram
http_requests_in_progress{method}                      Gauge
```

`path` ist das Routen-Template (`/api/v1/modules/{module_id}`), nie die konkrete URL. Probes
und Scrapes (`/health/*`, `/metrics`) werden nicht gezählt. Dazu kommen die Standard-Metriken
von `prometheus_client` (`process_cpu_seconds_total`, `process_resident_memory_bytes`, ...).

### Konfiguration

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `DATABASE_URL` | – | Komplette SQLAlchemy-URL (lokale Entwicklung) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Port `3306` | Alternative zu `DATABASE_URL` (Kubernetes); das Passwort kommt aus einem Secret und wird korrekt escaped |
| `MYSQL_SSL_DISABLED` | `false` | TLS zu MySQL abschalten (nur lokal) |
| `MYSQL_SSL_CA` | – | CA-Datei, gegen die das Server-Zertifikat geprüft wird |
| `MYSQL_SSL_VERIFY_HOSTNAME` | `true` | Zusätzlich den Hostnamen im Zertifikat prüfen |
| `LOG_LEVEL` | `INFO` | |

### Schema

`schema.sql` ist die einzige Quelle für das Schema. `python -m app.migrate` spielt es ein; alle
Statements sind idempotent (`CREATE TABLE IF NOT EXISTS`, `INSERT IGNORE`). In Kubernetes
läuft das als Init-Container vor jedem Pod-Start, es braucht also keinen manuellen Schritt.

## Anwendung starten

```bash
uv sync --frozen --extra dev
cp .env.example .env
uv run python -m app.migrate
uv run uvicorn app.main:app --reload --port 8080
```

Tests und Linting:

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Container:

```bash
docker build -t module_service .
docker run --rm -p 8080:8080 --env-file .env module_service
```

## Pipeline

`.github/workflows/build-and-promote.yml` läuft bei jedem Push auf `main`: Tests und Lint,
dann Build und Push von `xxpirl2knc5/module_service:<commit-sha>` nach Docker Hub, dann ein
Commit ins Ops-Repository (`bernetlennard/user_mgmt_ops`), der `moduleService.image.tag`
setzt. ArgoCD rollt das Image von dort aus. Benötigte Repository-Secrets: `DOCKERHUB_USERNAME`,
`DOCKERHUB_TOKEN`, `OPS_REPO_TOKEN` (dieselben wie in `user_mgmt_service`).
