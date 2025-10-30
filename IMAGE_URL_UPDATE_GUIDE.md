# Image URL Update Guide

## Overview

This guide shows you how to update product image URLs in the database using a simple CSV file.

## Files

1. **current_image_urls.csv** - Your current product data (auto-generated)
2. **update_image_urls.py** - Script to update the database
3. **image_url_template.csv** - Example template showing the format

## Step-by-Step Instructions

### Step 1: Get Current Product Data

The file `current_image_urls.csv` has been created for you with all products. It contains:
- **SKU** - Product SKU (don't change this)
- **Product Name** - Product name (for reference only)
- **Image URL** - Current image URL (update this column)

### Step 2: Update Image URLs

1. Open `current_image_urls.csv` in Excel or any text editor
2. Update the **Image URL** column with your new URLs
3. You can delete the "Product Name" column if you want (it's just for reference)
4. Save the file

**Example:**
```csv
SKU,Product Name,Image URL
410001-541-001,Utile 60",https://mynewcdn.com/images/410001-541-001.jpg
105821,Brome 6030,https://mynewcdn.com/images/105821.jpg
```

### Step 3: Update the Database

Run the update script:

```bash
python update_image_urls.py current_image_urls.csv
```

The script will:
- ✓ Read your CSV file
- ✓ Update matching products in the database
- ✓ Show progress and results
- ✓ List any SKUs that weren't found

### Step 4: Sync to Production (if needed)

After updating the development database, sync to production:

```bash
python sync_to_production.py
```

## CSV Format Requirements

Your CSV file must have these columns:
- **SKU** - Required, must match existing products
- **Image URL** - Required, the new URL for the product

Optional columns are ignored, so you can keep "Product Name" for reference.

## Tips

1. **Backup First**: The current URLs are saved in `current_image_urls.csv`
2. **Test Small**: Try updating a few products first to test
3. **Valid URLs**: Make sure URLs are complete and accessible
4. **No Quotes Needed**: URLs don't need quotes in the CSV
5. **UTF-8 Encoding**: Save your CSV as UTF-8 if you have special characters

## Example Workflow

```bash
# 1. Export current URLs (already done for you)
python update_image_urls.py --export

# 2. Edit current_image_urls.csv with your new URLs

# 3. Update the database
python update_image_urls.py current_image_urls.csv

# 4. (Optional) Sync to production
python sync_to_production.py
```

## Troubleshooting

**"SKU not found in database"**
- The SKU in your CSV doesn't exist in the database
- Check for typos or extra spaces

**"CSV must have 'SKU' and 'Image URL' columns"**
- Make sure your CSV has the correct column headers
- Column names are case-sensitive

**"No valid updates found"**
- All rows in your CSV are empty or invalid
- Check that you have SKU and Image URL values

## Need Help?

If you have any issues:
1. Check that your CSV format matches the template
2. Verify SKUs exist in the database
3. Make sure image URLs are complete (starting with http:// or https://)
