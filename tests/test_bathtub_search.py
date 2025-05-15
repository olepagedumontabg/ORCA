#!/usr/bin/env python
import pandas as pd
import requests
import json

def check_bathtub_sku(sku):
    """
    Check if a bathtub SKU exists in the data file and if it can be searched via the API
    """
    print(f"Checking bathtub SKU: {sku}")
    
    # Step 1: Check in the Excel file
    try:
        bathtubs_df = pd.read_excel('data/Product Data.xlsx', sheet_name='Bathtubs')
        sku_found = str(sku) in bathtubs_df['Unique ID'].astype(str).values
        
        if sku_found:
            # Get the row data for this SKU
            row = bathtubs_df[bathtubs_df['Unique ID'].astype(str) == str(sku)].iloc[0]
            print(f"✅ Found SKU in Excel file: {sku}")
            print(f"    Product Name: {row.get('Product Name')}")
            print(f"    Max Door Width: {row.get('Max Door Width')}")
            print(f"    Category: Bathtubs")
        else:
            print(f"❌ SKU not found in Excel file: {sku}")
            return False
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return False
    
    # Step 2: Try to search via API
    try:
        # The search endpoint expects a POST request
        response = requests.post('http://localhost:5000/search', data={'sku': sku})
        
        if response.status_code == 200:
            print(f"✅ Successfully searched via API: {sku}")
            
            # Check if the response looks like valid HTML
            if '<html' in response.text.lower():
                print("✅ API returned HTML response (expected)")
            else:
                print("❌ API did not return HTML response")
                print(f"Response: {response.text[:100]}...")
        else:
            print(f"❌ API search failed: Status {response.status_code}")
            print(f"Response: {response.text[:100]}...")
        
    except Exception as e:
        print(f"Error searching via API: {str(e)}")
        return False
    
    return True

def check_suggest_endpoint(query):
    """
    Test the suggest endpoint to see if it returns results for the query
    """
    print(f"\nTesting suggest endpoint with query: {query}")
    
    try:
        response = requests.get(f'http://localhost:5000/suggest?q={query}')
        
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get('suggestions', [])
            display_suggestions = data.get('displaySuggestions', [])
            
            print(f"✅ Suggest endpoint returned {len(suggestions)} results")
            
            if suggestions:
                print("Sample suggestions:")
                for i, (suggestion, display) in enumerate(zip(suggestions, display_suggestions)):
                    if i >= 5:  # Limit to 5 samples
                        break
                    print(f"  {display}")
                
                return True
        else:
            print(f"❌ Suggest endpoint failed: Status {response.status_code}")
            print(f"Response: {response.text[:100]}...")
            
    except Exception as e:
        print(f"Error with suggest endpoint: {str(e)}")
        
    return False

if __name__ == "__main__":
    # Test a known bathtub SKU
    sku_to_check = "105821"  # Brome 6030
    
    # First check the bathtub SKU
    check_bathtub_sku(sku_to_check)
    
    # Then test the suggest endpoint with partial queries
    check_suggest_endpoint("105")  # Should match by SKU prefix
    check_suggest_endpoint("bro")  # Should match by name