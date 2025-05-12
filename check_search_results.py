#!/usr/bin/env python
"""
Script to analyze a search result and find door types.
"""

import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_search_results(sku):
    """
    Send a search request and analyze the door types in the results
    """
    try:
        logger.info(f"Searching for SKU: {sku}")
        
        # Send the search request
        response = requests.post(
            "http://localhost:5000/search",
            json={"sku": sku},
            headers={"Content-Type": "application/json"}
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                logger.info(f"Found product: {data['product']['name']}")
                
                # Analyze the compatible products
                door_types = set()
                
                for category in data.get("compatibles", []):
                    if category.get("category") == "Shower Doors":
                        logger.info(f"Found {len(category.get('products', []))} compatible doors")
                        
                        for product in category.get("products", []):
                            door_type = product.get("door_type")
                            if door_type:
                                door_types.add(door_type)
                
                # Print the door types
                logger.info(f"Found {len(door_types)} unique door types:")
                for door_type in sorted(door_types):
                    logger.info(f"  - {door_type}")
                
                # Count occurrences of each door type
                door_type_counts = {}
                for category in data.get("compatibles", []):
                    if category.get("category") == "Shower Doors":
                        for product in category.get("products", []):
                            door_type = product.get("door_type", "Unknown")
                            door_type_counts[door_type] = door_type_counts.get(door_type, 0) + 1
                
                logger.info("\nDoor type counts in search results:")
                for door_type, count in sorted(door_type_counts.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"  - {door_type}: {count}")
                
                # Save the JSON response to a file for analysis
                with open("search_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("Saved response to search_response.json")
                
            else:
                logger.info(f"No product found: {data.get('message')}")
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            logger.error(response.text)
    
    except Exception as e:
        logger.error(f"Error analyzing search results: {str(e)}")

if __name__ == "__main__":
    # Use the SKU: 420043-541-001
    analyze_search_results("420043-541-001")