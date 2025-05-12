"""
Compatibility Processor
Processes product data to calculate compatibility between products.
"""
import os
import sys
import pandas as pd
import json
import logging
import time
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

class CompatibilityProcessor:
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
            'Enclosure': 'Enclosures'
        }
        
        # Check if any sheet name needs to be adjusted
        self.alternative_sheets = {
            'Shower Doors': 'Doors',
            'Shower Doors': 'Tub Doors'
        }
        
        # Initialize dataframes dictionary
        self.dataframes = {}
        
    def load_product_data(self):
        """Load all product data from the database"""
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
            
        # Add your bathtub compatibility logic here
        return (
            (base_brand == "Maax" and wall_brand == "Maax") or 
            (base_brand == "Neptune" and wall_brand == "Neptune") or
            (base_brand == "Aker" and wall_brand == "Maax")
        )
            
    def match_base_doors_walls(self):
        """Match shower bases with compatible doors and walls"""
        if 'Shower Base' not in self.dataframes or self.dataframes['Shower Base'].empty:
            logger.warning("No shower base data available for matching")
            return
            
        if 'Door' not in self.dataframes or self.dataframes['Door'].empty:
            logger.warning("No door data available for matching")
            return
            
        logger.info("Starting shower base compatibility matching...")
        
        # Create database engine
        engine = create_engine(self.db_url)
        
        # Process each base
        match_count = 0
        bases_df = self.dataframes['Shower Base']
        doors_df = self.dataframes['Door']
        return_panels_df = self.dataframes.get('Return Panel', pd.DataFrame())
        walls_df = self.dataframes.get('Wall', pd.DataFrame())
        
        # Initialize empty columns if they don't exist
        if 'Compatible Doors' not in bases_df.columns:
            bases_df['Compatible Doors'] = ""
        else:
            bases_df['Compatible Doors'] = bases_df['Compatible Doors'].astype(str)
            
        if 'Compatible Walls' not in bases_df.columns:
            bases_df['Compatible Walls'] = ""
        else:
            bases_df['Compatible Walls'] = bases_df['Compatible Walls'].astype(str)
        
        tolerance = 2  # inches
        wall_tolerance = 3  # inches
        
        for i, base in bases_df.iterrows():
            base_sku = base.get('Unique ID')
            if pd.isna(base_sku) or not base_sku:
                continue
                
            # Clear existing compatibility data for this base
            try:
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM compatibilities WHERE source_sku = :sku"), {'sku': base_sku})
                    conn.commit()
            except Exception as e:
                logger.error(f"Error clearing compatibilities for {base_sku}: {e}")
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
            matching_doors = []
            
            for _, door in doors_df.iterrows():
                door_sku = door.get('Unique ID')
                if pd.isna(door_sku) or not door_sku:
                    continue
                    
                door_type = str(door.get("Type", "")).lower()
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_has_return = door.get("Has Return Panel")
                door_family = door.get("Family")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                
                # Match alcove installation doors
                if (
                    "shower" in door_type and
                    "alcove" in base_install and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    self.series_compatible(base_series, door_series) and
                    self.brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                ):
                    # Add to database
                    try:
                        with engine.connect() as conn:
                            conn.execute(text('''
                                INSERT INTO compatibilities 
                                (source_sku, target_sku, target_category, requires_return_panel) 
                                VALUES (:source, :target, :category, :return_panel)
                            '''), {
                                'source': base_sku,
                                'target': door_sku,
                                'category': 'Doors',
                                'return_panel': None
                            })
                            conn.commit()
                            match_count += 1
                    except Exception as e:
                        logger.error(f"Error inserting compatibility: {e}")
                
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
                            # Add to database with return panel
                            try:
                                with engine.connect() as conn:
                                    conn.execute(text('''
                                        INSERT INTO compatibilities 
                                        (source_sku, target_sku, target_category, requires_return_panel) 
                                        VALUES (:source, :target, :category, :return_panel)
                                    '''), {
                                        'source': base_sku,
                                        'target': door_sku,
                                        'category': 'Doors',
                                        'return_panel': panel_sku
                                    })
                                    conn.commit()
                                    match_count += 1
                            except Exception as e:
                                logger.error(f"Error inserting compatibility with return panel: {e}")
            
            # Match walls
            for _, wall in walls_df.iterrows():
                wall_sku = wall.get('Unique ID')
                if pd.isna(wall_sku) or not wall_sku:
                    continue
                    
                wall_type = str(wall.get("Type", "")).lower()
                wall_brand = wall.get("Brand")
                wall_series = wall.get("Series")
                wall_family = wall.get("Family")
                wall_nominal = wall.get("Nominal Dimensions")
                wall_length = wall.get("Length")
                wall_width = wall.get("Width")
                wall_cut = wall.get("Cut to Size")
                
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
                         abs(base_length - wall_length) <= wall_tolerance and
                         base_width_actual <= wall_width and
                         abs(base_width_actual - wall_width) <= wall_tolerance)
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
                         abs(base_length - wall_length) <= wall_tolerance and
                         base_width_actual <= wall_width and
                         abs(base_width_actual - wall_width) <= wall_tolerance)
                    )
                )
                
                if alcove_match or corner_match:
                    # Add to database
                    try:
                        with engine.connect() as conn:
                            conn.execute(text('''
                                INSERT INTO compatibilities 
                                (source_sku, target_sku, target_category, requires_return_panel) 
                                VALUES (:source, :target, :category, :return_panel)
                            '''), {
                                'source': base_sku,
                                'target': wall_sku,
                                'category': 'Walls',
                                'return_panel': None
                            })
                            conn.commit()
                            match_count += 1
                    except Exception as e:
                        logger.error(f"Error inserting wall compatibility: {e}")
            
            # Log progress for every 10 bases
            if i % 10 == 0:
                logger.info(f"Processed {i+1}/{len(bases_df)} shower bases")
                
        logger.info(f"Shower base compatibility matching complete. Created {match_count} compatibility relationships")
        
    def match_showers_and_tub_showers(self):
        """Match showers and tub showers with compatible doors"""
        # Add your implementation here for showers and tub-showers
        logger.info("Showers and tub-showers matching not implemented yet")
        
    def match_bathtubs(self):
        """Match bathtubs with compatible doors and walls"""
        # Add your implementation here for bathtubs
        logger.info("Bathtubs matching not implemented yet")
        
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
        

# Function to run as a service
def run_compatibility_processor():
    """Main function to run the compatibility processor"""
    processor = CompatibilityProcessor()
    processor.run_compatibility_process()
    
if __name__ == "__main__":
    run_compatibility_processor()