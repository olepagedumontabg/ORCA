# Production Database Migration Guide

This application uses a **single production database** for all operations - development, testing, and production deployment all share the same database.

## Overview

Your database is automatically populated and kept up-to-date via:
- **Salsify Webhook Integration** - Automatic real-time updates when you publish in Salsify
- **Incremental Computation** - Smart compatibility calculations that only process new/changed products

## Database Architecture

**Single Database Approach:**
- One PostgreSQL database (Neon-hosted via Replit)
- All environments use the same database via `DATABASE_URL`
- Salsify webhooks update the database directly
- No sync scripts needed - everything stays in sync automatically

## Initial Setup (One-Time)

If you need to manually populate or re-sync the database:

### Step 1: Import Products from Excel

```bash
python db_migrate.py
```

This imports all products from `data/Product Data.xlsx` into the database (~2,193 products, takes 5-10 seconds).

### Step 2: Compute Compatibilities

```bash
python complete_all_compatibilities.py
```

This computes all compatibility relationships between products (~64,000+ compatibility records, takes 2-3 minutes).

## Ongoing Operations

### Automated Updates via Salsify Webhook

When you publish in Salsify:
1. Webhook receives notification
2. Downloads latest Excel file from S3
3. Syncs changes to database (adds/updates/deletes products)
4. Recomputes compatibilities for changed products only
5. Reloads in-memory cache
6. Updates are live immediately

**No manual intervention required!**

### Adding Individual Products

Use the incremental system for fast updates:

```bash
python add_products.py
```

This:
- Syncs any new products from Excel to database
- Computes compatibilities only for new products (fast!)
- Skips existing products

## Database Schema

Main tables:
- `products` - All bathroom products (2,193 records)
- `product_compatibility` - Pre-computed compatibility matches (64,596 records)
- `sync_status` - Webhook sync history
- `compatibility_overrides` - Manual override rules (whitelist/blacklist)

## Verification

Check database status:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from models import get_session, Product, ProductCompatibility

session = get_session()
print(f'Products: {session.query(Product).count()}')
print(f'Compatibilities: {session.query(ProductCompatibility).count()}')
session.close()
"
```

Expected output:
```
Products: 2193
Compatibilities: 64596
```

## Troubleshooting

### "Database connection error"

Check that `DATABASE_URL` is set:
```bash
echo $DATABASE_URL
```

If empty, check Replit Secrets and ensure `DATABASE_URL` points to your production database.

### "No products found"

Run the import:
```bash
python db_migrate.py
```

### "No compatibilities found"

Run the computation:
```bash
python complete_all_compatibilities.py
```

### Webhook not updating database

Check sync history at `/sync-history` endpoint to see webhook status and any errors.

## Best Practices

1. **Trust the webhook** - Salsify publishes update everything automatically
2. **Use incremental updates** - `add_products.py` for manual additions
3. **Check sync history** - Monitor webhook operations at `/sync-history`
4. **Don't manually edit** - Let Salsify be your source of truth

## Safety Notes

- **Automatic backups** - Replit automatically backs up your database
- **Idempotent operations** - Scripts can be re-run safely
- **Incremental updates** - Only changed products are processed
- **Transaction safety** - All database operations use transactions

Your database is production-ready and automatically maintained!
