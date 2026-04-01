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
- **NuGet Packages**: Npgsql.EntityFrameworkCore.PostgreSQL, ClosedXML, Microsoft.EntityFrameworkCore.Design
