# Bathroom Compatibility Finder — API

## Overview

A lean ASP.NET Core 8 REST API (C#) that identifies compatible bathroom products (shower bases, bathtubs, doors, walls, screens) by analyzing dimensional and specification data. Consumed by an external ASP.NET front-end via the ORCA.API endpoints.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Technical Stack
- **Backend**: ASP.NET Core 8 Web API (C#) — `ORCA.Api/`
- **ORM**: Entity Framework Core 8 with Npgsql provider
- **Excel Parsing**: ClosedXML (for Salsify sync)
- **Deployment**: Kestrel on port 5000, configured for Replit autoscale

### Core Services
- **`CompatibilityEngine`** — Routes compatibility computation to category-specific rule classes
- **`CompatibilityService`** — Orchestrates pre-computed lookup + on-demand computation + override support
- **`ProductService`** — Database CRUD for products
- **`SalsifyService`** — Downloads Excel from S3, upserts products to DB, triggers background recompute

### Compatibility Rules (in `ORCA.Api/Services/Rules/`)
- `ShowerBaseRules.cs` — Alcove/corner door matching, return panels, enclosures, screens, walls
- `BathtubRules.cs` — Tub door/screen matching, walls
- `ShowerRules.cs` — Shower unit door matching
- `TubShowerRules.cs` — Tub-shower door matching
- `SharedRules.cs` — Shared dimension helpers (door width, screen gap, enclosure fit, brand family)
- Reverse lookups built into `CompatibilityEngine.cs` (door/screen/enclosure → compatible bases)

### Database (Neon PostgreSQL via `DATABASE_URL`)
| Table | Purpose |
|-------|---------|
| `products` | All product data with JSON `attributes` column |
| `product_compatibility` | Pre-computed compatible pairs |
| `compatibility_overrides` | Manual whitelist/blacklist overrides |
| `sync_statuses` | Salsify webhook sync history |

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + DB stats |
| GET | `/api/categories` | All product categories with counts |
| GET | `/api/products` | All products (optional `?category=&page=&pageSize=`) |
| GET | `/api/product/{sku}` | Single product by SKU |
| GET | `/api/products/{id}` | Single product by ID |
| GET | `/api/compatible/{sku}` | Compatible products for a SKU |
| GET | `/api/products/sku/{sku}/compatible` | Compatible products (alt route) |
| POST | `/api/compatibility/search` | Search with filters (body: `{sku, category, brand, limit}`) |
| POST | `/api/compatibility/compute/{sku}` | Force recompute for one SKU |
| POST | `/api/compute-compatibilities` | Recompute all products |
| POST | `/api/salsify/webhook?key=SECRET` | Salsify publication webhook |
| GET | `/api/salsify/status` | Sync status history |
| POST | `/api/salsify/cleanup` | Remove old sync records |
| GET | `/api/overrides` | List all overrides (optional `?sku=` filter) |
| POST | `/api/overrides` | Create a whitelist or blacklist override |
| DELETE | `/api/overrides/{id}` | Delete an override by ID |

### Project Structure
```
ORCA.Api/
├── Controllers/          — HTTP endpoint handlers
├── Data/                 — EF Core DbContext + entity configurations
├── Domain/
│   ├── Constants/        — Category names, family rules, tolerances
│   └── Entities/         — Product, ProductCompatibility, etc.
├── DTOs/                 — Request/response shapes
├── Migrations/           — EF Core database migrations
└── Services/
    ├── Rules/            — Category-specific compatibility logic
    ├── CompatibilityEngine.cs
    ├── CompatibilityService.cs
    ├── ProductService.cs
    └── SalsifyService.cs
```

## External Dependencies

- **Salsify PIM**: Webhook at `POST /api/salsify/webhook?key=SALSIFY_WEBHOOK_SECRET`; publishes Excel to S3; C# downloads and syncs automatically in background
- **PostgreSQL**: Neon-hosted, accessed via `DATABASE_URL` environment variable
- **NuGet Packages**: Npgsql.EntityFrameworkCore.PostgreSQL, ClosedXML, Swashbuckle.AspNetCore, Microsoft.EntityFrameworkCore.Design, Auth0.AspNetCore.Authentication

### Frontend
Static HTML/CSS/JS files are served directly by the C# app:
- `templates/` — HTML pages (index, sync-history, overrides, documentation) served by `HomeController`
- `static/` — CSS, JS, images served at `/static/` via `PhysicalFileProvider`
- Swagger UI available at `/swagger` (interactive API explorer)
- Human-readable API docs at `/documentation`
- Override management UI at `/overrides` — add/remove whitelist and blacklist overrides (protected by Auth0 login + `override-admin` role)
- `templates/403.html` — role-denied page shown to authenticated users without the `override-admin` role

### Auth0 Authentication

**All routes are protected** — unauthenticated users are redirected to Auth0 login.

**Role hierarchy** (must be created in Auth0 dashboard):
| Role | Access |
|------|--------|
| `ORCA - Viewer` | Home (`/`) only |
| `ORCA - Editor` | Home + Overrides |
| `ORCA - Admin` | All pages (Home, Overrides, Sync History, API Docs) |

**Protected routes**:
- `GET /` — requires `ORCA - Viewer` (or higher)
- `GET /overrides` — requires `ORCA - Editor` (or Admin); API endpoints same
- `GET /sync-history` — requires `ORCA - Admin`
- `GET /documentation` — requires `ORCA - Admin`

**Auth endpoints** (public):
- `GET /account/login` — initiates Auth0 login
- `GET /account/logout` — signs out locally + from Auth0
- `GET /api/me` — returns authenticated user's email, roles, is_editor, is_admin (JSON)

**Required secrets** (app will not start without all three):
- `AUTH0_DOMAIN` — e.g. `your-tenant.us.auth0.com`
- `AUTH0_CLIENT_ID` — from your Auth0 Regular Web Application settings
- `AUTH0_CLIENT_SECRET` — from your Auth0 Regular Web Application settings

#### Auth0 Dashboard Setup (one-time)

**Step 1 — Create a Regular Web Application**
1. Auth0 Dashboard → Applications → Create Application
2. Name: `ORCA Overrides` (or similar), Type: **Regular Web Applications** → Create
3. Go to the **Settings** tab; copy the Client ID and Client Secret into Replit Secrets

**Step 2 — Configure Application URIs**
In the Settings tab → Application URIs, add (for both dev and prod):
- **Allowed Callback URLs**: `https://<your-dev-url>/callback, https://<your-prod-url>/callback`
- **Allowed Logout URLs**: `https://<your-dev-url>, https://<your-prod-url>`
- **Allowed Web Origins**: `https://<your-dev-url>, https://<your-prod-url>`
- Click **Save Changes**

**Step 3 — Create the `override-admin` role**
1. Auth0 Dashboard → User Management → Roles → Create Role
2. Name: `override-admin`, Description: `Can manage compatibility overrides`
3. Click **Create**

**Step 4 — Create a Post Login Action to inject roles into the ID token**
1. Actions → Library → Build Custom
2. Name: `Add Roles to Token`, Trigger: **Login / Post Login**, Runtime: Node 18
3. Replace the default code with:
```javascript
exports.onExecutePostLogin = async (event, api) => {
  const roles = event.authorization?.roles || [];
  // Must match the namespace used in Program.cs: https://{AUTH0_DOMAIN}/roles
  api.idToken.setCustomClaim('https://' + event.secrets.AUTH0_DOMAIN + '/roles', roles);
};
```
4. Click the **Secrets** icon (🔒) → Add Secret:
   - Key: `AUTH0_DOMAIN` — Value: your Auth0 domain (e.g. `abg-prod.us.auth0.com`)
5. Click **Deploy**

**Step 5 — Add Action to Login flow**
1. Actions → Flows → Login
2. Drag your `Add Roles to Token` action between Start and Complete
3. Click **Apply**

**Step 6 — Assign the role to users**
1. User Management → Users → click a user → **Roles** tab
2. Assign Roles → select `override-admin` → Assign

**Role claim mapping**: The `Program.cs` `OnTicketReceived` handler reads the namespaced claim `https://{AUTH0_DOMAIN}/roles` (a JSON array) and maps each value to `ClaimTypes.Role`, enabling `User.IsInRole("override-admin")` checks.

### Notes
- All Python source files (`app.py`, `main.py`, `models.py`, `services/`, `logic/`) have been removed. The project is 100% C#.
- `data/` folder retains legacy Excel files for reference but is not used by the running API.
