# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

CRM-ERP for VF Digital Solutions, a computer repair workshop. API-first Django backend + React/Vite frontend. Integrates with two sister projects: `vf-lookout` (hardware diagnostics tool) and `vf-hometracker` (separate React app whose stack informs this one).

## Services

```
docker compose up          # all services: db (MySQL 3306), api (8000), frontend (5173)
docker compose up api      # backend only (requires db)
```

**Swagger UI:** http://localhost:8000/api/docs/

## Backend (Django)

Working directory for all `manage.py` commands: `backend/`

```bash
# Local dev (requires .venv at repo root)
cd backend
DJANGO_SETTINGS_MODULE=config.settings.dev ../.venv/bin/python manage.py runserver
DJANGO_SETTINGS_MODULE=config.settings.dev ../.venv/bin/python manage.py makemigrations
DJANGO_SETTINGS_MODULE=config.settings.dev ../.venv/bin/python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.dev ../.venv/bin/python manage.py check

# Inside Docker
docker compose run --rm api python manage.py <command>
```

`manage.py` defaults to `config.settings.dev`; prod uses `config.settings.prod`.

### Settings layout

```
backend/config/settings/
  base.py    # all shared config (DRF, JWT, CORS, DB, AllocationFund)
  dev.py     # adds django_extensions, console email backend
  prod.py    # DEBUG=False, security headers
```

Key base settings:
- `AUTH_USER_MODEL = "usuarios.UsuarioVF"`
- `DEFAULT_PERMISSION_CLASS = IsAuthenticated` (global)
- JWT: `TOKEN_OBTAIN_SERIALIZER = "usuarios.serializers.CustomTokenObtainPairSerializer"` — token response includes `rol`, `nombre_completo`, `username`
- Pagination: 25 items per page
- CORS: `http://localhost:5173` (Vite)

### App structure

Every Django app follows the same layout: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`.

| App | Responsibility |
|---|---|
| `core` | `AllocationFund` (los "sobres"), `DiskInterpretation`, `EquipmentLevel` |
| `clientes` | `Client` — PERSON/COMPANY with `identity_key` normalization and `merged_into` self-FK |
| `equipos` | `Equipment` — owned by Client, `identity_key` via serial or hash(brand+model) |
| `diagnosticos` | `Diagnosis` (raw_json + content_hash dedup) + `DetectedSpecification` + `StorageDevice` + `ManualCorrection` |
| `catalogo` | `Service` catalog with snapshot pricing |
| `inventario` | `Product`, `ProductCategory`, `Supplier`, `MovimientoInventario` (stock derived from movements) |
| `cotizaciones` | `Quote` with polymorphic `QuoteLine` (service XOR product, snapshot prices) |
| `trabajos` | `WorkOrder` + `WorkOrderLine` — spine of the system; triggers inventory SALIDA and financial INGRESO |
| `finanzas` | `FinancialTransaction` (neutral ledger) → `Allocation` → `AllocationDetail` per fund → `FundMovement` (fund balances) |
| `usuarios` | `UsuarioVF(AbstractUser)` with `rol` (ADMIN/TECNICO/VENDEDOR) |

### Key patterns

**Polymorphic lines** (`QuoteLine`, `WorkOrderLine`): two nullable FKs (`service` / `product`) with a `validate()` check enforcing exactly one. Snapshot fields (`description`, `unit_price`, `unit_cost`, `quantity`) are copied at creation and never updated from catalog changes.

**Identity keys**: `Client.save()` calls `vf_core.normalize.normalize()` to compute `identity_key` before every save. Same logic used by vf-lookout for cross-system deduplication.

**Neutral ledger**: `FinancialTransaction` is the source of truth. `Allocation` + `AllocationDetail` are derived layers (fund percentages snapshot at allocation time). Never compute balances from `AllocationDetail` directly — use `FundMovement` aggregates.

**Diagnosis dedup**: `Diagnosis.save()` computes `content_hash = sha256(json.dumps(raw_json, sort_keys=True))`. Import flows should catch `IntegrityError` on this unique field.

**Number generation**: `WorkOrder` and `Quote` auto-generate correlative numbers (`OT-YYYY-NNNN`, `COT-YYYY-NNNN`) in `save()` when blank.

**List vs detail serializers**: Several apps define `*ListSerializer` (flat fields, read-only) and `*Serializer` (full with nested writes). Views switch via `get_serializer_class()` checking `self.action == "list"`.

### Auth endpoints

```
POST /api/auth/token/          # login → {access, refresh, rol, nombre_completo, username}
POST /api/auth/token/refresh/  # refresh access token
GET|PATCH /api/admin/me/       # own profile
POST /api/admin/me/cambiar-password/
GET|POST|… /api/admin/users/   # CRUD, requires is_staff=True
```

### vf_core package

Shared Python package at `vf_core/` (repo root), installed as editable in both Docker and the local venv. Provides:
- `vf_core.normalize.normalize(text)` — strips accents, uppercases, removes non-alphanumeric
- `vf_core.schemas.diagnostico` — Pydantic schemas matching vf-lookout's JSON output

## Frontend (React + Vite)

`frontend/` — currently bootstrapping. Stack: React + TypeScript + Vite, port 5173.

```bash
cd frontend
npm install
npm run dev
```

`VITE_API_URL` env var points at the backend (default `http://localhost:8000`).

## Dockerfile note

The backend Dockerfile has `context: .` (repo root) but `COPY requirements.txt .` expects the file without a path prefix — it resolves because `backend/requirements.txt` is the only one and the volume mount overlays it at runtime. Don't restructure the COPY paths without also updating the compose `context`.

## Data model reference

`modelo-datos-vf-admin.md` at repo root is the authoritative design document. All closed decisions (polymorphic lines, identity keys, fund allocation, snapshot prices, neutral ledger) are documented there. Read it before modifying any of the financial or client identity logic.
