"""
Full Compatibility Processor
Integrates all three compatibility checking scripts into a single processor that
handles Shower Bases, Showers, Tub Showers, and Bathtubs and their compatible products.
"""
import os
import sys
import pandas as pd
import json
import logging
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('compatibility_processor')

class FullCompatibilityProcessor:
    def __init__(self):
        # Database connection
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            logger.error("DATABASE_URL environment variable not set")
            sys.exit(1)
            
        # Define product categories and their corresponding sheet names
        self.product_categories = {
            'Shower Base': 'Shower Bases',
            'Door': 'Shower Doors',
            'Return Panel': 'Return Panels',
            'Wall': 'Walls',
            'Enclosure': 'Enclosures',
            'Shower': 'Showers',
            'Tub Shower': 'Tub Showers',
            'Tub Door': 'Tub Doors',
            'Bathtub': 'Bathtubs'
        }
        
        # Check if any sheet name needs to be adjusted
        self.alternative_sheets = {
            'Shower Doors': 'Doors',
            'Tub Doors': 'Doors'
        }
        
        # Initialize dataframes dictionary
        self.dataframes = {}
        
        # Tolerances for dimensional matching
        self.tolerance = 2  # inches for general matching
        self.wall_tolerance = 3  # inches for Walls matching
        
    def load_product_data(self):
        """Load all product data from the Excel file"""
        # Find the Excel file
        excel_path = os.path.join('data', 'Product Data.xlsx')
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return False
            
        logger.info(f"Loading product data from {excel_path}")
        
        try:
            # Load the Excel file
            excel_file = pd.ExcelFile(excel_path)
            available_sheets = excel_file.sheet_names
            logger.info(f"Available sheets: {available_sheets}")
            
            # Load each category sheet
            for category, sheet_name in self.product_categories.items():
                if sheet_name in available_sheets:
                    self.dataframes[category] = excel_file.parse(sheet_name)
                    logger.info(f"Loaded {len(self.dataframes[category])} {category} products from {sheet_name}")
                else:
                    # Try alternative sheet names
                    if sheet_name in self.alternative_sheets and self.alternative_sheets[sheet_name] in available_sheets:
                        alt_sheet = self.alternative_sheets[sheet_name]
                        self.dataframes[category] = excel_file.parse(alt_sheet)
                        logger.info(f"Loaded {len(self.dataframes[category])} {category} products from {alt_sheet} (alternative)")
                    else:
                        logger.warning(f"Sheet {sheet_name} not found, category {category} will not be processed")
                        self.dataframes[category] = pd.DataFrame()  # Empty dataframe
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading product data: {e}")
            return False
            
    def series_compatible(self, base_series, compare_series):
        """Check if two series are compatible"""
        if pd.isna(base_series) or pd.isna(compare_series):
            return False
            
        if base_series == "Retail":
            return compare_series in ["Retail", "MAAX"]
        if base_series == "MAAX":
            return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
        if base_series in ["Collection", "Professional"]:
            return compare_series in ["MAAX", "Collection", "Professional"]
        return False
        
    def brand_family_match_doors(self, base_brand, base_family, other_brand, other_family):
        """Check if brands and families match for doors compatibility"""
        if pd.isna(base_brand) or pd.isna(other_brand):
            return False
            
        return (
            (base_brand == "Maax" and other_brand == "Maax") or
            (base_brand == "Neptune" and other_brand == "Neptune") or
            (base_brand == "Aker" and other_brand == "Maax")
        )
        
    def brand_family_match_walls(self, base_brand, base_family, wall_brand, wall_family):
        """Check if brands and families match for walls compatibility"""
        if pd.isna(base_brand) or pd.isna(wall_brand):
            return False
        if pd.isna(base_family) or pd.isna(wall_family):
            return False
            
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
        
    def bathtub_brand_family_match(self, base_brand, base_family, wall_brand, wall_family):
        """Check if brands and families match for bathtub compatibility"""
        if pd.isna(base_brand) or pd.isna(wall_brand):
            return False
        if pd.isna(base_family) or pd.isna(wall_family):
            return False
            
        return (
            (base_brand == "Swan" and wall_brand == "Swan") or
            (base_brand == "Bootz" and wall_brand == "Bootz") or
            (base_family == "Olio" and wall_family == "Olio") or
            (base_family == "Vellamo" and wall_brand == "Vellamo") or
            (base_family in ["Nomad", "Mackenzie", "Exhibit", "New Town", "Rubix", "Bosca", "Cocoon", "Corinthia"] and
             wall_family in ["Utile", "Nextile", "Versaline"])
        )
            
    def store_compatibility(self, source_sku, target_sku, target_category, return_panel=None):
        """Store compatibility relationship in the database"""
        engine = create_engine(self.db_url)
        
        try:
            with engine.connect() as conn:
                conn.execute(text('''
                    INSERT INTO compatibilities 
                    (source_sku, target_sku, target_category, requires_return_panel) 
                    VALUES (:source, :target, :category, :return_panel)
                '''), {
                    'source': source_sku,
                    'target': target_sku,
                    'category': target_category,
                    'return_panel': return_panel
                })
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing compatibility: {e}")
            return False
    
    def clear_product_compatibilities(self, sku):
        """Clear all existing compatibilities for a product"""
        engine = create_engine(self.db_url)
        
        try:
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM compatibilities WHERE source_sku = :sku"), {'sku': sku})
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing compatibilities for {sku}: {e}")
            return False
            
    def match_base_doors_walls(self):
        """Match shower bases with compatible doors and walls"""
        # Check if required data is available
        if 'Shower Base' not in self.dataframes or self.dataframes['Shower Base'].empty:
            logger.warning("No shower base data available for matching")
            return
            
        if 'Door' not in self.dataframes or self.dataframes['Door'].empty:
            logger.warning("No door data available for matching")
            return
            
        logger.info("Starting shower base compatibility matching...")
        
        # Process each base
        match_count = 0
        bases_df = self.dataframes['Shower Base']
        doors_df = self.dataframes['Door']
        return_panels_df = self.dataframes.get('Return Panel', pd.DataFrame())
        walls_df = self.dataframes.get('Wall', pd.DataFrame())
        enclosures_df = self.dataframes.get('Enclosure', pd.DataFrame())
        
        for i, base in bases_df.iterrows():
            base_sku = base.get('Unique ID')
            if pd.isna(base_sku) or not base_sku:
                continue
                
            # Clear existing compatibility data for this base
            if not self.clear_product_compatibilities(base_sku):
                continue
            
            # Get base properties
            base_width = base.get("Max Door Width")
            base_install = str(base.get("Installation", "")).lower()
            base_series = base.get("Series")
            base_fit_return = base.get("Fits Return Panel Size")
            base_length = base.get("Length")
            base_width_actual = base.get("Width")
            base_nominal = base.get("Nominal Dimensions")
            base_brand = base.get("Brand")
            base_family = base.get("Family")
            
            # Match doors
            door_match_count = 0
            
            for _, door in doors_df.iterrows():
                door_sku = door.get('Unique ID')
                if pd.isna(door_sku) or not door_sku:
                    continue
                    
                door_type = str(door.get("Type", "")).lower() if not pd.isna(door.get("Type")) else ""
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_has_return = door.get("Has Return Panel")
                door_family = door.get("Family")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                
                # Match alcove installation doors
                try:
                    if (
                        "shower" in door_type and
                        "alcove" in base_install and
                        pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= base_width <= door_max_width and
                        self.series_compatible(base_series, door_series) and
                        self.brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                    ):
                        # Store compatibility in database
                        if self.store_compatibility(base_sku, door_sku, 'Doors'):
                            door_match_count += 1
                except Exception as e:
                    logger.warning(f"Error matching alcove door {door_sku} with base {base_sku}: {e}")
                
                # Match corner installation doors with return panels
                try:
                    if (
                        "shower" in door_type and
                        "corner" in base_install and
                        door_has_return == "Yes" and
                        pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= base_width <= door_max_width and
                        self.series_compatible(base_series, door_series) and
                        self.brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                    ):
                        # Check for return panels
                        for _, panel in return_panels_df.iterrows():
                            panel_sku = panel.get('Unique ID')
                            if pd.isna(panel_sku) or not panel_sku:
                                continue
                                
                            panel_size = panel.get("Return Panel Size")
                            panel_family = panel.get("Family")
                            panel_brand = panel.get("Brand")
                            
                            if (
                                base_fit_return == panel_size and
                                self.brand_family_match_doors(base_brand, base_family, panel_brand, panel_family)
                            ):
                                # Store compatibility with return panel
                                if self.store_compatibility(base_sku, door_sku, 'Doors', panel_sku):
                                    door_match_count += 1
                except Exception as e:
                    logger.warning(f"Error matching corner door {door_sku} with base {base_sku}: {e}")
            
            # Match enclosures
            enclosure_match_count = 0
            if "corner" in base_install:
                for _, enclosure in enclosures_df.iterrows():
                    enclosure_sku = enclosure.get('Unique ID')
                    if pd.isna(enclosure_sku) or not enclosure_sku:
                        continue
                        
                    enc_series = enclosure.get("Series")
                    enc_nominal = enclosure.get("Nominal Dimensions")
                    enc_door_width = enclosure.get("Door Width")
                    enc_return_width = enclosure.get("Return Panel Width")
                    enc_brand = enclosure.get("Brand")
                    enc_family = enclosure.get("Family")
                    
                    try:
                        # Check for a match
                        if not (
                            self.series_compatible(base_series, enc_series) and
                            self.brand_family_match_doors(base_brand, base_family, enc_brand, enc_family)
                        ):
                            continue
                            
                        nominal_match = base_nominal == enc_nominal
                        
                        dimension_match = (
                            pd.notna(base_length) and pd.notna(enc_door_width) and
                            pd.notna(base_width_actual) and pd.notna(enc_return_width) and
                            base_length >= enc_door_width and
                            (base_length - enc_door_width) <= self.tolerance and
                            base_width_actual >= enc_return_width and
                            (base_width_actual - enc_return_width) <= self.tolerance
                        )
                        
                        if nominal_match or dimension_match:
                            # Store compatibility
                            if self.store_compatibility(base_sku, enclosure_sku, 'Enclosures'):
                                enclosure_match_count += 1
                    except Exception as e:
                        logger.warning(f"Error matching enclosure {enclosure_sku} with base {base_sku}: {e}")
            
            # Match walls
            wall_match_count = 0
            for _, wall in walls_df.iterrows():
                wall_sku = wall.get('Unique ID')
                if pd.isna(wall_sku) or not wall_sku:
                    continue
                    
                wall_type = str(wall.get("Type", "")).lower() if not pd.isna(wall.get("Type")) else ""
                wall_brand = wall.get("Brand")
                wall_series = wall.get("Series")
                wall_family = wall.get("Family")
                wall_nominal = wall.get("Nominal Dimensions")
                wall_length = wall.get("Length")
                wall_width = wall.get("Width")
                wall_cut = wall.get("Cut to Size")
                
                try:
                    # Check for alcove match
                    alcove_match = (
                        "alcove shower" in wall_type and
                        (base_install in ["alcove", "alcove or corner"]) and
                        self.series_compatible(base_series, wall_series) and
                        self.brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
                        (
                            base_nominal == wall_nominal or
                            (wall_cut == "Yes" and
                             pd.notna(base_length) and pd.notna(wall_length) and
                             pd.notna(base_width_actual) and pd.notna(wall_width) and
                             base_length <= wall_length and
                             abs(base_length - wall_length) <= self.wall_tolerance and
                             base_width_actual <= wall_width and
                             abs(base_width_actual - wall_width) <= self.wall_tolerance)
                        )
                    )
                    
                    # Check for corner match
                    corner_match = (
                        "corner shower" in wall_type and
                        (base_install in ["corner", "alcove or corner"]) and
                        self.series_compatible(base_series, wall_series) and
                        self.brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
                        (
                            base_nominal == wall_nominal or
                            (wall_cut == "Yes" and
                             pd.notna(base_length) and pd.notna(wall_length) and
                             pd.notna(base_width_actual) and pd.notna(wall_width) and
                             base_length <= wall_length and
                             abs(base_length - wall_length) <= self.wall_tolerance and
                             base_width_actual <= wall_width and
                             abs(base_width_actual - wall_width) <= self.wall_tolerance)
                        )
                    )
                    
                    if alcove_match or corner_match:
                        # Store compatibility
                        if self.store_compatibility(base_sku, wall_sku, 'Walls'):
                            wall_match_count += 1
                except Exception as e:
                    logger.warning(f"Error matching wall {wall_sku} with base {base_sku}: {e}")
                    
            # Log progress for every 10 bases
            if i % 10 == 0:
                logger.info(f"Processed {i+1}/{len(bases_df)} shower bases")
                
            # Update total count
            match_count += door_match_count + enclosure_match_count + wall_match_count
            
            # Report matches for this base
            if door_match_count > 0 or enclosure_match_count > 0 or wall_match_count > 0:
                logger.info(f"Base {base_sku}: Found {door_match_count} doors, {enclosure_match_count} enclosures, {wall_match_count} walls")
                
        logger.info(f"Shower base compatibility matching complete. Created {match_count} compatibility relationships")
        
    def match_showers_and_tub_showers(self):
        """Match showers and tub showers with compatible doors"""
        # Check if required data is available
        if 'Shower' not in self.dataframes or self.dataframes['Shower'].empty:
            logger.warning("No shower data available for matching")
        else:
            logger.info("Starting shower compatibility matching...")
            
            # Process showers
            match_count = 0
            showers_df = self.dataframes['Shower']
            doors_df = self.dataframes['Door']
            
            for i, shower in showers_df.iterrows():
                shower_sku = shower.get('Unique ID')
                if pd.isna(shower_sku) or not shower_sku:
                    continue
                    
                # Clear existing compatibility data for this shower
                if not self.clear_product_compatibilities(shower_sku):
                    continue
                
                # Get shower properties
                shower_width = shower.get("Max Door Width")
                shower_height = shower.get("Max Door Height")
                shower_install = shower.get("Installation")
                shower_series = shower.get("Series")
                
                # Process doors
                shower_match_count = 0
                for _, door in doors_df.iterrows():
                    door_sku = door.get('Unique ID')
                    if pd.isna(door_sku) or not door_sku:
                        continue
                        
                    door_type = str(door.get("Type", "")).lower() if not pd.isna(door.get("Type")) else ""
                    door_min_width = door.get("Minimum Width")
                    door_max_width = door.get("Maximum Width")
                    door_max_height = door.get("Maximum Height")
                    door_series = door.get("Series")
                    
                    try:
                        # Match based on shower criteria
                        if (
                            "shower" in door_type and
                            shower_install == "Alcove" and
                            pd.notna(shower_width) and pd.notna(shower_height) and
                            pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_max_height) and
                            door_min_width <= shower_width <= door_max_width and
                            shower_height >= door_max_height and
                            self.series_compatible(shower_series, door_series)
                        ):
                            # Store compatibility
                            if self.store_compatibility(shower_sku, door_sku, 'Doors'):
                                shower_match_count += 1
                    except Exception as e:
                        logger.warning(f"Error matching door {door_sku} with shower {shower_sku}: {e}")
                        
                # Log progress for every 10 showers
                if i % 10 == 0:
                    logger.info(f"Processed {i+1}/{len(showers_df)} showers")
                    
                # Update total count
                match_count += shower_match_count
                
                # Report matches for this shower
                if shower_match_count > 0:
                    logger.info(f"Shower {shower_sku}: Found {shower_match_count} compatible doors")
                    
            logger.info(f"Shower compatibility matching complete. Created {match_count} compatibility relationships")
        
        # Process tub showers
        if 'Tub Shower' not in self.dataframes or self.dataframes['Tub Shower'].empty:
            logger.warning("No tub shower data available for matching")
        else:
            logger.info("Starting tub shower compatibility matching...")
            
            # Process tub showers
            match_count = 0
            tub_showers_df = self.dataframes['Tub Shower']
            tub_doors_df = self.dataframes.get('Tub Door', pd.DataFrame())
            
            # Fall back to regular doors if tub doors sheet is missing
            if tub_doors_df.empty and 'Door' in self.dataframes:
                logger.warning("No tub door data available, using regular doors instead")
                tub_doors_df = self.dataframes['Door']
            
            for i, tub in tub_showers_df.iterrows():
                tub_sku = tub.get('Unique ID')
                if pd.isna(tub_sku) or not tub_sku:
                    continue
                    
                # Clear existing compatibility data for this tub shower
                if not self.clear_product_compatibilities(tub_sku):
                    continue
                    
                # Get tub shower properties
                tub_width = tub.get("Max Door Width")
                tub_height = tub.get("Max Door Height")
                tub_series = tub.get("Series")
                
                # Process doors
                tub_match_count = 0
                for _, door in tub_doors_df.iterrows():
                    door_sku = door.get('Unique ID')
                    if pd.isna(door_sku) or not door_sku:
                        continue
                        
                    door_min_width = door.get("Minimum Width")
                    door_max_width = door.get("Maximum Width")
                    door_max_height = door.get("Maximum Height")
                    door_series = door.get("Series")
                    
                    try:
                        # Match based on tub shower criteria
                        if (
                            pd.notna(tub_width) and pd.notna(tub_height) and
                            pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_max_height) and
                            door_min_width <= tub_width <= door_max_width and
                            tub_height >= door_max_height and
                            self.series_compatible(tub_series, door_series)
                        ):
                            # Store compatibility
                            if self.store_compatibility(tub_sku, door_sku, 'Doors'):
                                tub_match_count += 1
                    except Exception as e:
                        logger.warning(f"Error matching door {door_sku} with tub shower {tub_sku}: {e}")
                        
                # Log progress for every 10 tub showers
                if i % 10 == 0:
                    logger.info(f"Processed {i+1}/{len(tub_showers_df)} tub showers")
                    
                # Update total count
                match_count += tub_match_count
                
                # Report matches for this tub shower
                if tub_match_count > 0:
                    logger.info(f"Tub shower {tub_sku}: Found {tub_match_count} compatible doors")
                    
            logger.info(f"Tub shower compatibility matching complete. Created {match_count} compatibility relationships")
        
    def match_bathtubs(self):
        """Match bathtubs with compatible doors and walls"""
        # Check if required data is available
        if 'Bathtub' not in self.dataframes or self.dataframes['Bathtub'].empty:
            logger.warning("No bathtub data available for matching")
            return
            
        logger.info("Starting bathtub compatibility matching...")
        
        # Process bathtubs
        match_count = 0
        bathtubs_df = self.dataframes['Bathtub']
        tub_doors_df = self.dataframes.get('Tub Door', pd.DataFrame())
        walls_df = self.dataframes.get('Wall', pd.DataFrame())
        
        # Fall back to regular doors if tub doors sheet is missing
        if tub_doors_df.empty and 'Door' in self.dataframes:
            logger.warning("No tub door data available, using regular doors instead")
            tub_doors_df = self.dataframes['Door']
            
        for i, tub in bathtubs_df.iterrows():
            tub_sku = tub.get('Unique ID')
            if pd.isna(tub_sku) or not tub_sku:
                continue
                
            # Clear existing compatibility data for this bathtub
            if not self.clear_product_compatibilities(tub_sku):
                continue
                
            # Get bathtub properties
            tub_width = tub.get("Max Door Width")
            tub_install = tub.get("Installation")
            tub_series = tub.get("Series")
            tub_brand = tub.get("Brand")
            tub_family = tub.get("Family")
            tub_nominal = tub.get("Nominal Dimensions")
            tub_length = tub.get("Length")
            tub_width_actual = tub.get("Width")
            
            # Match doors
            door_match_count = 0
            for _, door in tub_doors_df.iterrows():
                door_sku = door.get('Unique ID')
                if pd.isna(door_sku) or not door_sku:
                    continue
                    
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_series = door.get("Series")
                
                try:
                    # Match based on bathtub criteria
                    if (
                        tub_install == "Alcove" and
                        pd.notna(tub_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= tub_width <= door_max_width and
                        self.series_compatible(tub_series, door_series)
                    ):
                        # Store compatibility
                        if self.store_compatibility(tub_sku, door_sku, 'Doors'):
                            door_match_count += 1
                except Exception as e:
                    logger.warning(f"Error matching door {door_sku} with bathtub {tub_sku}: {e}")
                    
            # Match walls
            wall_match_count = 0
            for _, wall in walls_df.iterrows():
                wall_sku = wall.get('Unique ID')
                if pd.isna(wall_sku) or not wall_sku:
                    continue
                    
                wall_type = str(wall.get("Type", "")).lower() if not pd.isna(wall.get("Type")) else ""
                wall_brand = wall.get("Brand")
                wall_series = wall.get("Series")
                wall_family = wall.get("Family")
                wall_nominal = wall.get("Nominal Dimensions")
                wall_length = wall.get("Length")
                wall_width = wall.get("Width")
                wall_cut = wall.get("Cut to Size")
                
                try:
                    # Match based on bathtub wall criteria
                    if (
                        "tub" in wall_type and
                        self.series_compatible(tub_series, wall_series) and
                        self.bathtub_brand_family_match(tub_brand, tub_family, wall_brand, wall_family) and
                        (
                            tub_nominal == wall_nominal or
                            (wall_cut == "Yes" and
                             pd.notna(tub_length) and pd.notna(wall_length) and
                             pd.notna(tub_width_actual) and pd.notna(wall_width) and
                             tub_length >= wall_length - self.wall_tolerance and
                             tub_length <= wall_length + self.wall_tolerance and
                             tub_width_actual >= wall_width - self.wall_tolerance and
                             tub_width_actual <= wall_width + self.wall_tolerance)
                        )
                    ):
                        # Store compatibility
                        if self.store_compatibility(tub_sku, wall_sku, 'Walls'):
                            wall_match_count += 1
                except Exception as e:
                    logger.warning(f"Error matching wall {wall_sku} with bathtub {tub_sku}: {e}")
                    
            # Log progress for every 10 bathtubs
            if i % 10 == 0:
                logger.info(f"Processed {i+1}/{len(bathtubs_df)} bathtubs")
                
            # Update total count
            match_count += door_match_count + wall_match_count
            
            # Report matches for this bathtub
            if door_match_count > 0 or wall_match_count > 0:
                logger.info(f"Bathtub {tub_sku}: Found {door_match_count} doors, {wall_match_count} walls")
                
        logger.info(f"Bathtub compatibility matching complete. Created {match_count} compatibility relationships")
            
    def process_single_sku(self, sku):
        """Process a single SKU for compatibility matching"""
        # First identify product type
        product_type = None
        product_data = None
        
        for category, df in self.dataframes.items():
            if df.empty:
                continue
                
            matches = df[df['Unique ID'] == sku]
            if not matches.empty:
                product_type = category
                product_data = matches.iloc[0]
                break
                
        if not product_type or product_data is None:
            logger.error(f"SKU {sku} not found in any product category")
            return False
            
        logger.info(f"Processing single SKU {sku} - Type: {product_type}")
        
        # Clear existing compatibility data
        if not self.clear_product_compatibilities(sku):
            return False
            
        # Process based on product type
        if product_type == 'Shower Base':
            self._process_single_base(sku, product_data)
        elif product_type == 'Shower':
            self._process_single_shower(sku, product_data)
        elif product_type == 'Tub Shower':
            self._process_single_tub_shower(sku, product_data)
        elif product_type == 'Bathtub':
            self._process_single_bathtub(sku, product_data)
        else:
            logger.warning(f"Product type {product_type} not supported for compatibility processing")
            return False
            
        return True
        
    def _process_single_base(self, sku, base_data):
        """Process a single shower base"""
        doors_df = self.dataframes.get('Door', pd.DataFrame())
        return_panels_df = self.dataframes.get('Return Panel', pd.DataFrame())
        walls_df = self.dataframes.get('Wall', pd.DataFrame())
        enclosures_df = self.dataframes.get('Enclosure', pd.DataFrame())
        
        # Get base properties
        base_width = base_data.get("Max Door Width")
        base_install = str(base_data.get("Installation", "")).lower()
        base_series = base_data.get("Series")
        base_fit_return = base_data.get("Fits Return Panel Size")
        base_length = base_data.get("Length")
        base_width_actual = base_data.get("Width")
        base_nominal = base_data.get("Nominal Dimensions")
        base_brand = base_data.get("Brand")
        base_family = base_data.get("Family")
        
        match_count = 0
        
        # Process with the same logic as in match_base_doors_walls
        # This is a simplified version for a single product
        
        # Match doors
        for _, door in doors_df.iterrows():
            door_sku = door.get('Unique ID')
            if pd.isna(door_sku) or not door_sku:
                continue
                
            door_type = str(door.get("Type", "")).lower() if not pd.isna(door.get("Type")) else ""
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_has_return = door.get("Has Return Panel")
            door_family = door.get("Family")
            door_series = door.get("Series")
            door_brand = door.get("Brand")
            
            try:
                # Match alcove installation doors
                if (
                    "shower" in door_type and
                    "alcove" in base_install and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    self.series_compatible(base_series, door_series) and
                    self.brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                ):
                    # Store compatibility
                    if self.store_compatibility(sku, door_sku, 'Doors'):
                        match_count += 1
                        logger.info(f"Match: Base {sku} -> Door {door_sku}")
                
                # Match corner installation doors with return panels
                if (
                    "shower" in door_type and
                    "corner" in base_install and
                    door_has_return == "Yes" and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    self.series_compatible(base_series, door_series) and
                    self.brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                ):
                    # Find matching return panels
                    for _, panel in return_panels_df.iterrows():
                        panel_sku = panel.get('Unique ID')
                        if pd.isna(panel_sku) or not panel_sku:
                            continue
                            
                        panel_size = panel.get("Return Panel Size")
                        panel_family = panel.get("Family")
                        panel_brand = panel.get("Brand")
                        
                        if (
                            base_fit_return == panel_size and
                            self.brand_family_match_doors(base_brand, base_family, panel_brand, panel_family)
                        ):
                            # Store compatibility with return panel
                            if self.store_compatibility(sku, door_sku, 'Doors', panel_sku):
                                match_count += 1
                                logger.info(f"Match: Base {sku} -> Door {door_sku} with Return Panel {panel_sku}")
            except Exception as e:
                logger.warning(f"Error matching door {door_sku} with base {sku}: {e}")
        
        # Match walls
        for _, wall in walls_df.iterrows():
            wall_sku = wall.get('Unique ID')
            if pd.isna(wall_sku) or not wall_sku:
                continue
                
            wall_type = str(wall.get("Type", "")).lower() if not pd.isna(wall.get("Type")) else ""
            wall_brand = wall.get("Brand")
            wall_series = wall.get("Series")
            wall_family = wall.get("Family")
            wall_nominal = wall.get("Nominal Dimensions")
            wall_length = wall.get("Length")
            wall_width = wall.get("Width")
            wall_cut = wall.get("Cut to Size")
            
            try:
                # Check for alcove and corner match using the same logic as in the script
                alcove_match = (
                    "alcove shower" in wall_type and
                    (base_install in ["alcove", "alcove or corner"]) and
                    self.series_compatible(base_series, wall_series) and
                    self.brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
                    (
                        base_nominal == wall_nominal or
                        (wall_cut == "Yes" and
                         pd.notna(base_length) and pd.notna(wall_length) and
                         pd.notna(base_width_actual) and pd.notna(wall_width) and
                         base_length <= wall_length and
                         abs(base_length - wall_length) <= self.wall_tolerance and
                         base_width_actual <= wall_width and
                         abs(base_width_actual - wall_width) <= self.wall_tolerance)
                    )
                )
                
                corner_match = (
                    "corner shower" in wall_type and
                    (base_install in ["corner", "alcove or corner"]) and
                    self.series_compatible(base_series, wall_series) and
                    self.brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
                    (
                        base_nominal == wall_nominal or
                        (wall_cut == "Yes" and
                         pd.notna(base_length) and pd.notna(wall_length) and
                         pd.notna(base_width_actual) and pd.notna(wall_width) and
                         base_length <= wall_length and
                         abs(base_length - wall_length) <= self.wall_tolerance and
                         base_width_actual <= wall_width and
                         abs(base_width_actual - wall_width) <= self.wall_tolerance)
                    )
                )
                
                if alcove_match or corner_match:
                    # Store compatibility
                    if self.store_compatibility(sku, wall_sku, 'Walls'):
                        match_count += 1
                        match_type = "alcove" if alcove_match else "corner"
                        logger.info(f"Match: Base {sku} -> Wall {wall_sku} ({match_type})")
            except Exception as e:
                logger.warning(f"Error matching wall {wall_sku} with base {sku}: {e}")
                
        logger.info(f"Processed base {sku}: Found {match_count} compatibilities")
            
    def _process_single_shower(self, sku, shower_data):
        """Process a single shower"""
        doors_df = self.dataframes.get('Door', pd.DataFrame())
        
        # Get shower properties
        shower_width = shower_data.get("Max Door Width")
        shower_height = shower_data.get("Max Door Height")
        shower_install = shower_data.get("Installation")
        shower_series = shower_data.get("Series")
        
        match_count = 0
        
        # Match doors
        for _, door in doors_df.iterrows():
            door_sku = door.get('Unique ID')
            if pd.isna(door_sku) or not door_sku:
                continue
                
            door_type = str(door.get("Type", "")).lower() if not pd.isna(door.get("Type")) else ""
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_max_height = door.get("Maximum Height")
            door_series = door.get("Series")
            
            try:
                # Match based on shower criteria
                if (
                    "shower" in door_type and
                    shower_install == "Alcove" and
                    pd.notna(shower_width) and pd.notna(shower_height) and
                    pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_max_height) and
                    door_min_width <= shower_width <= door_max_width and
                    shower_height >= door_max_height and
                    self.series_compatible(shower_series, door_series)
                ):
                    # Store compatibility
                    if self.store_compatibility(sku, door_sku, 'Doors'):
                        match_count += 1
                        logger.info(f"Match: Shower {sku} -> Door {door_sku}")
            except Exception as e:
                logger.warning(f"Error matching door {door_sku} with shower {sku}: {e}")
                
        logger.info(f"Processed shower {sku}: Found {match_count} compatibilities")
            
    def _process_single_tub_shower(self, sku, tub_data):
        """Process a single tub shower"""
        tub_doors_df = self.dataframes.get('Tub Door', pd.DataFrame())
        
        # If no tub doors, try regular doors
        if tub_doors_df.empty:
            tub_doors_df = self.dataframes.get('Door', pd.DataFrame())
            
        # Get tub shower properties
        tub_width = tub_data.get("Max Door Width")
        tub_height = tub_data.get("Max Door Height")
        tub_series = tub_data.get("Series")
        
        match_count = 0
        
        # Match doors
        for _, door in tub_doors_df.iterrows():
            door_sku = door.get('Unique ID')
            if pd.isna(door_sku) or not door_sku:
                continue
                
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_max_height = door.get("Maximum Height")
            door_series = door.get("Series")
            
            try:
                # Match based on tub shower criteria
                if (
                    pd.notna(tub_width) and pd.notna(tub_height) and
                    pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_max_height) and
                    door_min_width <= tub_width <= door_max_width and
                    tub_height >= door_max_height and
                    self.series_compatible(tub_series, door_series)
                ):
                    # Store compatibility
                    if self.store_compatibility(sku, door_sku, 'Doors'):
                        match_count += 1
                        logger.info(f"Match: Tub Shower {sku} -> Door {door_sku}")
            except Exception as e:
                logger.warning(f"Error matching door {door_sku} with tub shower {sku}: {e}")
                
        logger.info(f"Processed tub shower {sku}: Found {match_count} compatibilities")
            
    def _process_single_bathtub(self, sku, tub_data):
        """Process a single bathtub"""
        tub_doors_df = self.dataframes.get('Tub Door', pd.DataFrame())
        walls_df = self.dataframes.get('Wall', pd.DataFrame())
        
        # If no tub doors, try regular doors
        if tub_doors_df.empty:
            tub_doors_df = self.dataframes.get('Door', pd.DataFrame())
            
        # Get bathtub properties
        tub_width = tub_data.get("Max Door Width")
        tub_install = tub_data.get("Installation")
        tub_series = tub_data.get("Series")
        tub_brand = tub_data.get("Brand")
        tub_family = tub_data.get("Family")
        tub_nominal = tub_data.get("Nominal Dimensions")
        tub_length = tub_data.get("Length")
        tub_width_actual = tub_data.get("Width")
        
        match_count = 0
        
        # Match doors
        for _, door in tub_doors_df.iterrows():
            door_sku = door.get('Unique ID')
            if pd.isna(door_sku) or not door_sku:
                continue
                
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_series = door.get("Series")
            
            try:
                # Match based on bathtub criteria
                if (
                    tub_install == "Alcove" and
                    pd.notna(tub_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= tub_width <= door_max_width and
                    self.series_compatible(tub_series, door_series)
                ):
                    # Store compatibility
                    if self.store_compatibility(sku, door_sku, 'Doors'):
                        match_count += 1
                        logger.info(f"Match: Bathtub {sku} -> Door {door_sku}")
            except Exception as e:
                logger.warning(f"Error matching door {door_sku} with bathtub {sku}: {e}")
                
        # Match walls
        for _, wall in walls_df.iterrows():
            wall_sku = wall.get('Unique ID')
            if pd.isna(wall_sku) or not wall_sku:
                continue
                
            wall_type = str(wall.get("Type", "")).lower() if not pd.isna(wall.get("Type")) else ""
            wall_brand = wall.get("Brand")
            wall_series = wall.get("Series")
            wall_family = wall.get("Family")
            wall_nominal = wall.get("Nominal Dimensions")
            wall_length = wall.get("Length")
            wall_width = wall.get("Width")
            wall_cut = wall.get("Cut to Size")
            
            try:
                # Match based on bathtub wall criteria
                if (
                    "tub" in wall_type and
                    self.series_compatible(tub_series, wall_series) and
                    self.bathtub_brand_family_match(tub_brand, tub_family, wall_brand, wall_family) and
                    (
                        tub_nominal == wall_nominal or
                        (wall_cut == "Yes" and
                         pd.notna(tub_length) and pd.notna(wall_length) and
                         pd.notna(tub_width_actual) and pd.notna(wall_width) and
                         tub_length >= wall_length - self.wall_tolerance and
                         tub_length <= wall_length + self.wall_tolerance and
                         tub_width_actual >= wall_width - self.wall_tolerance and
                         tub_width_actual <= wall_width + self.wall_tolerance)
                    )
                ):
                    # Store compatibility
                    if self.store_compatibility(sku, wall_sku, 'Walls'):
                        match_count += 1
                        logger.info(f"Match: Bathtub {sku} -> Wall {wall_sku}")
            except Exception as e:
                logger.warning(f"Error matching wall {wall_sku} with bathtub {sku}: {e}")
                
        logger.info(f"Processed bathtub {sku}: Found {match_count} compatibilities")
    
    def run_compatibility_process(self):
        """Run all compatibility matching processes"""
        logger.info("Starting compatibility processing...")
        
        # Load product data
        if not self.load_product_data():
            return
            
        # Match compatibility for each product type
        self.match_base_doors_walls()
        self.match_showers_and_tub_showers()
        self.match_bathtubs()
        
        logger.info("Compatibility processing completed")


def run_compatibility_for_sku(sku):
    """Run compatibility processing for a specific SKU"""
    processor = FullCompatibilityProcessor()
    
    # Load product data
    if not processor.load_product_data():
        logger.error("Failed to load product data")
        return False
        
    # Process the specific SKU
    return processor.process_single_sku(sku)

def run_full_compatibility_process():
    """Run the complete compatibility processor for all products"""
    processor = FullCompatibilityProcessor()
    processor.run_compatibility_process()
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run for a specific SKU
        sku = sys.argv[1]
        logger.info(f"Running compatibility processing for SKU: {sku}")
        run_compatibility_for_sku(sku)
    else:
        # Run for all products
        logger.info("Running full compatibility processing")
        run_full_compatibility_process()