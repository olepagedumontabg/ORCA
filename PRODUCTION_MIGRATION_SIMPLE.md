# Simple Production Database Migration Guide

The easiest way to populate your production database is to run your existing migration scripts directly against the production database.

## Quick Overview

You already have two powerful scripts:
1. **`db_migrate.py`** - Imports products from Excel to database
2. **`complete_all_compatibilities.py`** - Computes all compatibility relationships

These scripts can work with ANY database by changing the `DATABASE_URL` environment variable.

---

## Step 1: Publish Your App First

**This is critical** - Publishing creates the production database with the correct schema.

```bash
# In Replit workspace:
# 1. Click "Publish" button at top
# 2. Wait for deployment to complete
# 3. Verify it's running at your URL
```

✅ **Result:** Production database exists with tables (products, product_compatibility, compatibility_overrides)

---

## Step 2: Get Your Production DATABASE_URL

### Method A: From Database Pane
1. Click **"Database"** in sidebar
2. Select **"Production Database"** dropdown
3. Click **"Commands"** tab
4. Copy the `DATABASE_URL` value

### Method B: From Shell
```bash
# This will show you the development URL (for reference)
echo $DATABASE_URL
```

Your production URL will look similar but with different credentials.

---

## Step 3: Run Migration Against Production

### Option A: Direct Method (Recommended)

Run the migration script with the production DATABASE_URL:

```bash
# Replace 'YOUR_PRODUCTION_URL' with actual production DATABASE_URL
DATABASE_URL='postgresql://user:pass@host.neon.tech/main' python db_migrate.py
```

This will:
- Import all 2,193 products from `data/Product Data.xlsx`
- Takes about 5-10 seconds

### Option B: Using a Helper Script

Create a temporary script to make it easier:

```bash
# Create migrate_prod.sh
cat > migrate_prod.sh <<'EOF'
#!/bin/bash
# Save original development DATABASE_URL
DEV_DATABASE_URL=$DATABASE_URL

# Set your production DATABASE_URL here
export DATABASE_URL='postgresql://user:pass@host.neon.tech/main'

echo "Migrating products to production..."
python db_migrate.py

# Restore development DATABASE_URL
export DATABASE_URL=$DEV_DATABASE_URL
echo "Restored development DATABASE_URL"
echo "Done! Check the output above for any errors."
EOF

chmod +x migrate_prod.sh
./migrate_prod.sh
```

---

## Step 4: Compute Compatibilities in Production

After products are imported, compute the compatibility relationships:

```bash
# Same approach - use production DATABASE_URL
DATABASE_URL='postgresql://user:pass@host.neon.tech/main' python complete_all_compatibilities.py
```

**⚠️ This takes time:**
- Processes 1,657 products (those that need compatibilities)
- ~0.1-1.8 products/second
- Could take 15-60+ minutes depending on your setup

**Progress tracking:**
The script will show progress every 10 products and save after every 100.

---

## Step 5: Verify Production Database

Check that the data was migrated successfully:

```bash
# Count products in production
DATABASE_URL='postgresql://your-prod-url' psql -c "SELECT COUNT(*) FROM products;"

# Count compatibilities in production  
DATABASE_URL='postgresql://your-prod-url' psql -c "SELECT COUNT(*) FROM product_compatibility;"

# Check coverage statistics
DATABASE_URL='postgresql://your-prod-url' psql -c "
SELECT 
  COUNT(DISTINCT base_product_id) as products_with_compat,
  (SELECT COUNT(*) FROM products) as total_products,
  ROUND(100.0 * COUNT(DISTINCT base_product_id) / (SELECT COUNT(*) FROM products), 1) as coverage_pct
FROM product_compatibility;
"
```

**Expected results:**
- Products: 2,193
- Compatibilities: 54,796+
- Coverage: 75.6%

**⚠️ Important:** After working with production, restore your development DATABASE_URL:

```bash
# If you temporarily changed DATABASE_URL in your shell
export DATABASE_URL=$DEV_DATABASE_URL

# Or simply close the terminal and open a new one to get the default dev URL
```

---

## Step 6: Test Your Live API

```bash
# Test product endpoint
curl https://orca-ABG-Web-ops.replit.app/api/product/410001-502-001 | jq

# Test compatibility endpoint
curl https://orca-ABG-Web-ops.replit.app/api/compatible/410001-502-001 | jq
```

Both should return `"data_source": "database"` and actual product data.

---

## Faster Alternative: Batch Processing

If you want to process compatibilities faster, you can use `batch_process_all.py` which processes multiple products in parallel:

```bash
DATABASE_URL='postgresql://your-prod-url' python batch_process_all.py
```

This processes products in batches and is significantly faster than the sequential approach.

---

## Future Updates

When you update products in the future:

### Full Refresh (Recommended for major updates):
```bash
# 1. Export from development
DATABASE_URL=$DEV_DATABASE_URL python db_migrate.py

# 2. Import to production
DATABASE_URL=$PROD_DATABASE_URL python db_migrate.py

# 3. Recompute compatibilities
DATABASE_URL=$PROD_DATABASE_URL python complete_all_compatibilities.py
```

### Incremental Update (For small changes):
```bash
# Just re-run the migration - it's smart enough to update existing products
DATABASE_URL=$PROD_DATABASE_URL python db_migrate.py
```

---

## Safety Tips

✅ **Safe:**
- Running `db_migrate.py` multiple times (it updates existing products)
- Re-computing compatibilities (replaces old ones)
- Testing with development DATABASE_URL first

⚠️ **Be Careful:**
- Always double-check the DATABASE_URL before running
- Production URLs should contain your deployment hostname
- Never share or commit DATABASE_URL values

🔒 **Protected:**
- Development and production databases are completely separate
- The Replit Agent cannot modify production directly
- You have full control over what goes to production

---

## Troubleshooting

### "relation 'products' does not exist"
- **Fix:** You haven't published your app yet. Publish first to create production database.

### "No such file: data/Product Data.xlsx"
- **Fix:** Make sure you're running from your workspace root directory, or update FTP to download latest data first.

### Script hangs on compatibility computation
- **Normal:** This takes a long time (15-60 minutes for 1,657 products). Be patient.
- **Alternative:** Use `batch_process_all.py` for faster parallel processing.

### Products imported but compatibilities are 0
- **Fix:** Run `complete_all_compatibilities.py` or `batch_process_all.py` separately.

---

## Quick Commands Reference

```bash
# Import products to production
DATABASE_URL='prod-url-here' python db_migrate.py

# Compute compatibilities in production
DATABASE_URL='prod-url-here' python complete_all_compatibilities.py

# Faster compatibility computation (parallel)
DATABASE_URL='prod-url-here' python batch_process_all.py

# Check production stats
DATABASE_URL='prod-url-here' psql -c "SELECT COUNT(*) FROM products;"
DATABASE_URL='prod-url-here' psql -c "SELECT COUNT(*) FROM product_compatibility;"

# Test live API
curl https://orca-ABG-Web-ops.replit.app/api/health
curl https://orca-ABG-Web-ops.replit.app/api/product/SKU-HERE
```

---

## Why This Approach is Better

✅ **Uses your existing, tested scripts**
✅ **No new code to debug**
✅ **Same process you used for development**
✅ **Direct control over what goes to production**
✅ **Easy to re-run for updates**

Instead of exporting/importing files, you just point your existing scripts at the production database. Simple!
