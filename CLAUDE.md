# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

CRM-ERP for VF Digital Solutions, a computer repair workshop. API-first Django backend + React/Vite frontend. Integrates with `vf-hometracker` (sister React app whose stack informs this one) and includes `vf-lookout` (hardware diagnostics CLI tool) as a submodule at `lookout/`.

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

# Tests (Django's built-in runner, no pytest)
docker compose run --rm api python manage.py test
docker compose run --rm api python manage.py test inventario.tests  # single app
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
| `inventario` | `Product`, `ProductCategory`, `Supplier`, `Brand`, `ProductSupplier`, `InventoryMovement` (stock derived from movements) |
| `cotizaciones` | `Quote` with polymorphic `QuoteLine` (service XOR product, snapshot prices) |
| `trabajos` | `WorkOrder` + `WorkOrderLine` — spine of the system; triggers inventory SALIDA and financial INGRESO |
| `finanzas` | `FinancialTransaction` (neutral ledger) → `Allocation` → `AllocationDetail` per fund → `FundMovement` (fund balances); also `GastoRecurrente`, `GastoPendiente`, `AlertaFinanciera`, `ExpenseCategory` |
| `calculadora` | Pricing calculator — `ParametrosCalculadora` (singleton), calculates service prices from cost-per-hour + overheads, saves results to `catalogo.Service` |
| `usuarios` | `UsuarioVF(AbstractUser)` with `rol` (ADMIN/TECNICO/VENDEDOR) |

### Key patterns

**Polymorphic lines** (`QuoteLine`, `WorkOrderLine`): two nullable FKs (`service` / `product`) with a `validate()` check enforcing exactly one. Snapshot fields (`description`, `unit_price`, `unit_cost`, `quantity`) are copied at creation and never updated from catalog changes.

**Identity keys**: `Client.save()` calls `vf_core.normalize.normalize()` to compute `identity_key` before every save. Same logic used by vf-lookout for cross-system deduplication.

**Neutral ledger**: `FinancialTransaction` is the source of truth. `Allocation` + `AllocationDetail` are derived layers (fund percentages snapshot at allocation time). Never compute balances from `AllocationDetail` directly — use `FundMovement` aggregates.

**Diagnosis dedup**: `Diagnosis.save()` computes `content_hash = sha256(json.dumps(raw_json, sort_keys=True))`. Import flows should catch `IntegrityError` on this unique field.

**Number generation**: `WorkOrder` and `Quote` auto-generate correlative numbers (`OT-YYYY-NNNN`, `COT-YYYY-NNNN`) in `save()` when blank.

**List vs detail serializers**: Several apps define `*ListSerializer` (flat fields, read-only) and `*Serializer` (full with nested writes). Views switch via `get_serializer_class()` checking `self.action == "list"`.

**Cross-app signals**: Automation between apps is done via `post_save` signals, never by importing across apps directly in model/view code. Each app that fires signals registers them in `apps.py → ready()`. Current signals:
- `trabajos/signals.py` — `WorkOrder` PAID → `FinancialTransaction(INCOME)` + fund allocation
- `inventario/signals.py` — `InventoryMovement` ENTRY → `FinancialTransaction(EXPENSE)`

Always import the target app's models inside the signal function body (lazy import) to avoid circular imports.

**Stock**: `Product.stock` is a computed `@property` — a `Sum` over `InventoryMovement` with `ENTRY` adding, `EXIT` subtracting, `ADJUSTMENT` adding signed quantity. There is no stored stock counter.

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

```bash
cd frontend
npm install
npm run dev          # dev server on :5173
npx tsc --noEmit     # type check (no lint script configured)
npm run build        # tsc + vite build
```

`@/` resolves to `frontend/src/` (configured in `vite.config.ts`). The Vite dev server proxies `/api/*` to `http://localhost:8000` (or `VITE_API_PROXY_TARGET`).

### Frontend architecture

**Routing**: All routes except `/login` are wrapped in `ProtectedRoute` → `AppLayout` (sidebar + `<Outlet>`). Routes are defined in `src/App.tsx`. Adding a new page requires: create `src/pages/<module>/<Page>.tsx`, add a `<Route>` in `App.tsx`, add a `NavLink` entry in `src/components/layout/Sidebar.tsx`.

**API layer**: One `apiClient` (axios instance) at `src/lib/axios.ts`. It auto-attaches the JWT bearer token and handles silent refresh on 401 (queue-based). All modules expose a `*Service` object in `src/services/` that wraps `apiClient` calls. Never call `apiClient` directly from components.

**State**: Auth state (tokens + user) lives in `useAuthStore` (Zustand + `persist` to localStorage) at `src/store/auth.ts`. Server state is managed by React Query (`@tanstack/react-query`) — use `useQuery` / `useMutation` with descriptive `queryKey` arrays. After a mutation that changes list data, call `qc.invalidateQueries({ queryKey: [...] })`.

**Forms**: React Hook Form + Zod (`zodResolver`). Use `z.coerce.number()` for numeric inputs (they arrive as strings from `<input>`). For optional nullable FK selects, use `z.preprocess((v) => (v === '' || v == null ? null : Number(v)), z.number().nullable())`.

**Styling**: Tailwind CSS. Conditional classes via `cn()` from `src/lib/utils.ts` (clsx + tailwind-merge). Brand colors: `bg-brand-navy` for sidebar. Active nav links use `bg-amber-600`.

**Types**: All shared TypeScript interfaces live in `src/types/index.ts`. Paginated list responses use `PaginatedResponse<T>` from that file.

## Dockerfile note

The backend Dockerfile has `context: .` (repo root) but `COPY requirements.txt .` expects the file without a path prefix — it resolves because `backend/requirements.txt` is the only one and the volume mount overlays it at runtime. Don't restructure the COPY paths without also updating the compose `context`.

## Data model reference

`modelo-datos-vf-admin.md` at repo root is the authoritative design document. All closed decisions (polymorphic lines, identity keys, fund allocation, snapshot prices, neutral ledger) are documented there. Read it before modifying any of the financial or client identity logic.
