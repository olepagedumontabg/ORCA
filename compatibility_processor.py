import os
import logging
import pandas as pd
import json
import traceback
import time
from datetime import datetime
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('compatibility_processor')

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

def series_compatible(base_series, compare_series):
    """Check if two series are compatible"""
    if not base_series or not compare_series:
        return False
        
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def brand_family_match_doors(base_brand, base_family, other_brand, other_family):
    """Check if brands and families match for doors compatibility"""
    return (
        (base_brand == "Maax" and other_brand == "Maax") or
        (base_brand == "Neptune" and other_brand == "Neptune") or
        (base_brand == "Aker" and other_brand == "Maax")
    )

def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for walls compatibility"""
    return (
        (base_brand == "Swan" and wall_brand == "Swan") or
        (base_brand == "Maax" and wall_brand == "Maax") or
        (base_brand == "Neptune" and wall_brand == "Neptune") or
        (base_brand == "Bootz" and wall_brand == "Bootz") or
        (base_family == "W&B" and wall_family == "W&B") or
        (base_family == "Olio" and wall_family == "Olio") or
        (base_family == "Vellamo" and wall_brand == "Vellamo") or
        (base_family in ["B3", "Finesse", "Distinct", "Zone", "Olympia", "Icon"] and
         wall_family in ["Utile", "Denso", "Nextile", "Versaline"])
    )

def bathtub_brand_family_match(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for bathtub compatibility"""
    return (
        (base_brand == "Swan" and wall_brand == "Swan") or
        (base_brand == "Bootz" and wall_brand == "Bootz") or
        (base_family == "Olio" and wall_family == "Olio") or
        (base_family == "Vellamo" and wall_brand == "Vellamo") or
        (base_family in ["Nomad", "Mackenzie", "Exhibit", "New Town", "Rubix", "Bosca", "Cocoon", "Corinthia"] and
         wall_family in ["Utile", "Nextile", "Versaline"])
    )

def load_product_data():
    """Load all product data from the database"""
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        return None
    
    try:
        # Create database engine
        engine = create_engine(DATABASE_URL)
        
        # Query all products
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM products"))
            products = result.fetchall()
        
        # Organize by category
        categories = {}
        for product in products:
            category = product.category
            if category not in categories:
                categories[category] = []
            
            # Convert to dictionary
            product_dict = {
                'id': product.id,
                'sku': product.sku,
                'brand': product.brand,
                'family': product.family,
                'series': product.series,
                'nominal_dimensions': product.nominal_dimensions,
                'installation': product.installation,
                'max_door_width': product.max_door_width,
                'width': product.width,
                'length': product.length,
                'height': product.height
            }
            
            # Add additional attributes from JSON data
            if product.product_data:
                try:
                    additional_data = json.loads(product.product_data)
                    for key, value in additional_data.items():
                        if key not in product_dict:
                            product_dict[key] = value
                except:
                    pass
            
            categories[category].append(product_dict)
        
        return categories
    
    except Exception as e:
        logger.error(f"Error loading product data: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def match_base_doors_walls():
    """Match shower bases with compatible doors and walls"""
    products = load_product_data()
    if not products:
        logger.error("Could not load product data")
        return
    
    logger.info("Starting base-doors-walls compatibility processing")
    
    # Check if we have the necessary categories
    if 'Shower Bases' not in products:
        logger.warning("No Shower Bases found in product data")
        return
    
    if 'Doors' not in products:
        logger.warning("No Doors found in product data")
        return
    
    if 'Walls' not in products:
        logger.warning("No Walls found in product data")
        return
    
    if 'Return Panels' not in products:
        logger.warning("No Return Panels found in product data")
        
    if 'Enclosures' not in products:
        logger.warning("No Enclosures found in product data")
    
    # Get product categories
    bases = products.get('Shower Bases', [])
    doors = products.get('Doors', [])
    return_panels = products.get('Return Panels', [])
    enclosures = products.get('Enclosures', [])
    walls = products.get('Walls', [])
    
    logger.info(f"Processing {len(bases)} bases, {len(doors)} doors, {len(return_panels)} return panels, {len(enclosures)} enclosures, {len(walls)} walls")
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    # Clear existing compatibility data for these categories
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM compatibilities 
            WHERE source_sku IN (SELECT sku FROM products WHERE category = 'Shower Bases')
            AND target_category IN ('Doors', 'Walls', 'Enclosures')
        """))
        conn.commit()
    
    # Set tolerance values
    tolerance = 2  # inches
    wall_tolerance = 3  # inches for Walls
    
    # Process each base
    compatibility_count = 0
    for base in bases:
        # Get base attributes
        base_sku = base.get('sku')
        base_width = base.get('max_door_width')
        base_install = str(base.get('installation', '')).lower()
        base_series = base.get('series')
        base_fit_return = base.get('Fits Return Panel Size')
        base_length = base.get('length')
        base_width_actual = base.get('width')
        base_nominal = base.get('nominal_dimensions')
        base_brand = base.get('brand')
        base_family = base.get('family')
        
        # Initialize lists for compatibilities
        door_compatibilities = []
        enclosure_compatibilities = []
        wall_compatibilities = []
        
        # ---------- Match Doors ----------
        for door in doors:
            door_sku = door.get('sku')
            door_type = str(door.get('Type', '')).lower()
            door_min_width = door.get('Minimum Width')
            door_max_width = door.get('Maximum Width')
            door_has_return = door.get('Has Return Panel')
            door_family = door.get('Family')
            door_series = door.get('Series')
            door_brand = door.get('Brand')
            
            # Skip if missing critical data
            if not door_sku:
                continue
                
            # Match alcove installation
            if (
                "shower" in door_type and
                "alcove" in base_install and
                base_width is not None and 
                door_min_width is not None and 
                door_max_width is not None and
                door_min_width <= base_width <= door_max_width and
                series_compatible(base_series, door_series) and
                brand_family_match_doors(base_brand, base_family, door_brand, door_family)
            ):
                door_compatibilities.append({
                    'target_sku': door_sku,
                    'target_category': 'Doors',
                    'requires_return_panel': None
                })
            
            # Match corner installation with return panel
            if (
                "shower" in door_type and
                "corner" in base_install and
                door_has_return == "Yes" and
                base_width is not None and 
                door_min_width is not None and 
                door_max_width is not None and
                door_min_width <= base_width <= door_max_width and
                series_compatible(base_series, door_series) and
                brand_family_match_doors(base_brand, base_family, door_brand, door_family)
            ):
                for panel in return_panels:
                    panel_size = panel.get('Return Panel Size')
                    panel_family = panel.get('Family')
                    panel_brand = panel.get('Brand')
                    panel_sku = panel.get('sku')
                    
                    if (
                        panel_sku and
                        base_fit_return == panel_size and
                        brand_family_match_doors(base_brand, base_family, panel_brand, panel_family)
                    ):
                        door_compatibilities.append({
                            'target_sku': door_sku,
                            'target_category': 'Doors',
                            'requires_return_panel': panel_sku
                        })
        
        # ---------- Match Enclosures ----------
        if "corner" in base_install:
            for enclosure in enclosures:
                enc_sku = enclosure.get('sku')
                enc_series = enclosure.get('Series')
                enc_nominal = enclosure.get('Nominal Dimensions')
                enc_door_width = enclosure.get('Door Width')
                enc_return_width = enclosure.get('Return Panel Width')
                enc_brand = enclosure.get('Brand')
                enc_family = enclosure.get('Family')
                
                if not enc_sku:
                    continue
                
                if not (
                    series_compatible(base_series, enc_series) and
                    brand_family_match_doors(base_brand, base_family, enc_brand, enc_family)
                ):
                    continue
                
                nominal_match = base_nominal == enc_nominal
                
                dimension_match = (
                    base_length is not None and enc_door_width is not None and
                    base_width_actual is not None and enc_return_width is not None and
                    base_length >= enc_door_width and
                    (base_length - enc_door_width) <= tolerance and
                    base_width_actual >= enc_return_width and
                    (base_width_actual - enc_return_width) <= tolerance
                )
                
                if nominal_match or dimension_match:
                    enclosure_compatibilities.append({
                        'target_sku': enc_sku,
                        'target_category': 'Enclosures',
                        'requires_return_panel': None
                    })
        
        # ---------- Match Walls ----------
        for wall in walls:
            wall_sku = wall.get('sku')
            wall_type = str(wall.get('Type', '')).lower()
            wall_brand = wall.get('Brand')
            wall_series = wall.get('Series')
            wall_family = wall.get('Family')
            wall_nominal = wall.get('Nominal Dimensions')
            wall_length = wall.get('Length')
            wall_width = wall.get('Width')
            wall_cut = wall.get('Cut to Size')
            
            if not wall_sku:
                continue
            
            alcove_match = (
                "alcove shower" in wall_type and
                (base_install in ["alcove", "alcove or corner"]) and
                series_compatible(base_series, wall_series) and
                brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
                (
                    base_nominal == wall_nominal or
                    (wall_cut == "Yes" and
                     base_length is not None and wall_length is not None and
                     base_width_actual is not None and wall_width is not None and
                     base_length <= wall_length and
                     abs(base_length - wall_length) <= wall_tolerance and
                     base_width_actual <= wall_width and
                     abs(base_width_actual - wall_width) <= wall_tolerance)
                )
            )
            
            corner_match = (
                "corner shower" in wall_type and
                (base_install in ["corner", "alcove or corner"]) and
                series_compatible(base_series, wall_series) and
                brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
                (
                    base_nominal == wall_nominal or
                    (wall_cut == "Yes" and
                     base_length is not None and wall_length is not None and
                     base_width_actual is not None and wall_width is not None and
                     base_length <= wall_length and
                     abs(base_length - wall_length) <= wall_tolerance and
                     base_width_actual <= wall_width and
                     abs(base_width_actual - wall_width) <= wall_tolerance)
                )
            )
            
            if alcove_match or corner_match:
                wall_compatibilities.append({
                    'target_sku': wall_sku,
                    'target_category': 'Walls',
                    'requires_return_panel': None
                })
        
        # Insert all compatibility data for this base
        all_compatibilities = door_compatibilities + enclosure_compatibilities + wall_compatibilities
        
        for compat in all_compatibilities:
            try:
                with engine.connect() as conn:
                    insert_query = text("""
                        INSERT INTO compatibilities 
                        (source_sku, target_sku, target_category, requires_return_panel) 
                        VALUES (:source_sku, :target_sku, :target_category, :requires_return_panel)
                    """)
                    
                    conn.execute(insert_query, {
                        'source_sku': base_sku,
                        'target_sku': compat['target_sku'],
                        'target_category': compat['target_category'],
                        'requires_return_panel': compat['requires_return_panel']
                    })
                    conn.commit()
                compatibility_count += 1
            except Exception as e:
                logger.error(f"Error inserting compatibility {base_sku} -> {compat['target_sku']}: {str(e)}")
                continue
    
    logger.info(f"Processed {compatibility_count} compatibility relationships for shower bases")

def match_showers_and_tub_showers():
    """Match showers and tub showers with compatible doors"""
    products = load_product_data()
    if not products:
        logger.error("Could not load product data")
        return
    
    logger.info("Starting showers and tub-showers compatibility processing")
    
    # Check if we have the necessary categories
    if 'Showers' not in products:
        logger.warning("No Showers found in product data")
        return
    
    if 'Tub Showers' not in products:
        logger.warning("No Tub Showers found in product data")
        return
    
    if 'Doors' not in products:
        logger.warning("No Doors found in product data")
        return
    
    if 'Tub Doors' not in products:
        logger.warning("No Tub Doors found in product data")
    
    # Get product categories
    showers = products.get('Showers', [])
    tub_showers = products.get('Tub Showers', [])
    doors = products.get('Doors', [])
    tub_doors = products.get('Tub Doors', [])
    
    logger.info(f"Processing {len(showers)} showers, {len(tub_showers)} tub showers, {len(doors)} doors, {len(tub_doors)} tub doors")
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    # Clear existing compatibility data for these categories
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM compatibilities 
            WHERE (source_sku IN (SELECT sku FROM products WHERE category = 'Showers') AND target_category = 'Doors')
            OR (source_sku IN (SELECT sku FROM products WHERE category = 'Tub Showers') AND target_category = 'Tub Doors')
        """))
        conn.commit()
    
    # Process showers
    compatibility_count = 0
    for shower in showers:
        shower_sku = shower.get('sku')
        shower_width = shower.get('max_door_width')
        shower_height = shower.get('height')  # Adjust if column name is different
        shower_install = shower.get('installation')
        shower_series = shower.get('series')
        
        door_matches = []
        
        for door in doors:
            door_sku = door.get('sku')
            door_type = str(door.get('Type', '')).lower()
            door_min_width = door.get('Minimum Width')
            door_max_width = door.get('Maximum Width')
            door_max_height = door.get('Maximum Height')
            door_series = door.get('Series')
            
            if not door_sku:
                continue
                
            if (
                "shower" in door_type and
                shower_install == "Alcove" and
                shower_width is not None and 
                shower_height is not None and
                door_min_width is not None and 
                door_max_width is not None and 
                door_max_height is not None and
                door_min_width <= shower_width <= door_max_width and
                shower_height >= door_max_height and
                series_compatible(shower_series, door_series)
            ):
                door_matches.append(door_sku)
        
        # Insert compatibilities
        for door_sku in door_matches:
            try:
                with engine.connect() as conn:
                    insert_query = text("""
                        INSERT INTO compatibilities 
                        (source_sku, target_sku, target_category, requires_return_panel) 
                        VALUES (:source_sku, :target_sku, :target_category, :requires_return_panel)
                    """)
                    
                    conn.execute(insert_query, {
                        'source_sku': shower_sku,
                        'target_sku': door_sku,
                        'target_category': 'Doors',
                        'requires_return_panel': None
                    })
                    conn.commit()
                compatibility_count += 1
            except Exception as e:
                logger.error(f"Error inserting compatibility {shower_sku} -> {door_sku}: {str(e)}")
                continue
    
    # Process tub showers
    tub_compatibility_count = 0
    for tub in tub_showers:
        tub_sku = tub.get('sku')
        tub_width = tub.get('max_door_width')
        tub_height = tub.get('height')  # Adjust if column name is different
        tub_series = tub.get('series')
        
        door_matches = []
        
        for door in tub_doors:
            door_sku = door.get('sku')
            door_min_width = door.get('Minimum Width')
            door_max_width = door.get('Maximum Width')
            door_max_height = door.get('Maximum Height')
            door_series = door.get('Series')
            
            if not door_sku:
                continue
                
            if (
                tub_width is not None and 
                tub_height is not None and
                door_min_width is not None and 
                door_max_width is not None and 
                door_max_height is not None and
                door_min_width <= tub_width <= door_max_width and
                tub_height >= door_max_height and
                series_compatible(tub_series, door_series)
            ):
                door_matches.append(door_sku)
        
        # Insert compatibilities
        for door_sku in door_matches:
            try:
                with engine.connect() as conn:
                    insert_query = text("""
                        INSERT INTO compatibilities 
                        (source_sku, target_sku, target_category, requires_return_panel) 
                        VALUES (:source_sku, :target_sku, :target_category, :requires_return_panel)
                    """)
                    
                    conn.execute(insert_query, {
                        'source_sku': tub_sku,
                        'target_sku': door_sku,
                        'target_category': 'Tub Doors',
                        'requires_return_panel': None
                    })
                    conn.commit()
                tub_compatibility_count += 1
            except Exception as e:
                logger.error(f"Error inserting compatibility {tub_sku} -> {door_sku}: {str(e)}")
                continue
    
    logger.info(f"Processed {compatibility_count} compatibility relationships for showers and {tub_compatibility_count} for tub showers")

def match_bathtubs():
    """Match bathtubs with compatible doors and walls"""
    products = load_product_data()
    if not products:
        logger.error("Could not load product data")
        return
    
    logger.info("Starting bathtubs compatibility processing")
    
    # Check if we have the necessary categories
    if 'Bathtubs' not in products:
        logger.warning("No Bathtubs found in product data")
        return
    
    if 'Tub Doors' not in products:
        logger.warning("No Tub Doors found in product data")
        return
    
    if 'Walls' not in products:
        logger.warning("No Walls found in product data")
        return
    
    # Get product categories
    bathtubs = products.get('Bathtubs', [])
    tub_doors = products.get('Tub Doors', [])
    walls = products.get('Walls', [])
    
    logger.info(f"Processing {len(bathtubs)} bathtubs, {len(tub_doors)} tub doors, {len(walls)} walls")
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    # Clear existing compatibility data for these categories
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM compatibilities 
            WHERE source_sku IN (SELECT sku FROM products WHERE category = 'Bathtubs')
            AND target_category IN ('Tub Doors', 'Walls')
        """))
        conn.commit()
    
    # Set tolerance value
    tolerance = 3  # inches
    
    # Process each bathtub
    compatibility_count = 0
    for tub in bathtubs:
        tub_sku = tub.get('sku')
        tub_width = tub.get('max_door_width')
        tub_install = tub.get('installation')
        tub_series = tub.get('series')
        tub_brand = tub.get('brand')
        tub_family = tub.get('family')
        tub_nominal = tub.get('nominal_dimensions')
        tub_length = tub.get('length')
        tub_width_actual = tub.get('width')
        
        door_matches = []
        wall_matches = []
        
        # Match tub doors
        for door in tub_doors:
            door_sku = door.get('sku')
            door_min_width = door.get('Minimum Width')
            door_max_width = door.get('Maximum Width')
            door_series = door.get('Series')
            
            if not door_sku:
                continue
                
            if (
                tub_install == "Alcove" and
                tub_width is not None and 
                door_min_width is not None and 
                door_max_width is not None and
                door_min_width <= tub_width <= door_max_width and
                series_compatible(tub_series, door_series)
            ):
                door_matches.append(door_sku)
        
        # Match walls
        for wall in walls:
            wall_sku = wall.get('sku')
            wall_type = str(wall.get('Type', '')).lower()
            wall_brand = wall.get('Brand')
            wall_series = wall.get('Series')
            wall_family = wall.get('Family')
            wall_nominal = wall.get('Nominal Dimensions')
            wall_length = wall.get('Length')
            wall_width = wall.get('Width')
            wall_cut = wall.get('Cut to Size')
            
            if not wall_sku:
                continue
                
            if (
                "tub" in wall_type and
                series_compatible(tub_series, wall_series) and
                bathtub_brand_family_match(tub_brand, tub_family, wall_brand, wall_family) and
                (
                    tub_nominal == wall_nominal or
                    (wall_cut == "Yes" and
                     tub_length is not None and wall_length is not None and
                     tub_width_actual is not None and wall_width is not None and
                     tub_length >= wall_length - tolerance and
                     tub_length <= wall_length + tolerance and
                     tub_width_actual >= wall_width - tolerance and
                     tub_width_actual <= wall_width + tolerance)
                )
            ):
                wall_matches.append(wall_sku)
        
        # Insert door compatibilities
        for door_sku in door_matches:
            try:
                with engine.connect() as conn:
                    insert_query = text("""
                        INSERT INTO compatibilities 
                        (source_sku, target_sku, target_category, requires_return_panel) 
                        VALUES (:source_sku, :target_sku, :target_category, :requires_return_panel)
                    """)
                    
                    conn.execute(insert_query, {
                        'source_sku': tub_sku,
                        'target_sku': door_sku,
                        'target_category': 'Tub Doors',
                        'requires_return_panel': None
                    })
                    conn.commit()
                compatibility_count += 1
            except Exception as e:
                logger.error(f"Error inserting door compatibility {tub_sku} -> {door_sku}: {str(e)}")
                continue
        
        # Insert wall compatibilities
        for wall_sku in wall_matches:
            try:
                with engine.connect() as conn:
                    insert_query = text("""
                        INSERT INTO compatibilities 
                        (source_sku, target_sku, target_category, requires_return_panel) 
                        VALUES (:source_sku, :target_sku, :target_category, :requires_return_panel)
                    """)
                    
                    conn.execute(insert_query, {
                        'source_sku': tub_sku,
                        'target_sku': wall_sku,
                        'target_category': 'Walls',
                        'requires_return_panel': None
                    })
                    conn.commit()
                compatibility_count += 1
            except Exception as e:
                logger.error(f"Error inserting wall compatibility {tub_sku} -> {wall_sku}: {str(e)}")
                continue
    
    logger.info(f"Processed {compatibility_count} compatibility relationships for bathtubs")

def run_compatibility_process():
    """Run all compatibility matching processes"""
    logger.info("Starting compatibility processing")
    
    # Run each matching process
    match_base_doors_walls()
    match_showers_and_tub_showers()
    match_bathtubs()
    
    logger.info("Compatibility processing completed")

if __name__ == "__main__":
    # Run once immediately
    run_compatibility_process()
    
    # Then run every day
    while True:
        # Sleep for 24 hours
        time.sleep(86400)
        run_compatibility_process()