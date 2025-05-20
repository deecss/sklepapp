#!/usr/bin/env python3
"""
Quick test script to verify product availability persistence after app restart
"""
import json
import os
import sys
from product_manager import ProductManager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def test_availability_persistence():
    print("Testing product availability persistence...")
    
    # Make sure we're in the right directory
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print(f"Module search path: {sys.path}\n")
    
    # Create product manager instance
    pm = ProductManager()
    
    # Get all products
    products = pm.get_all_products(include_unavailable=True)
    total_count = len(products)
    available_count = sum(1 for p in products if p.get('available_for_sale', False))
    with_desc_count = sum(1 for p in products if p.get('description'))
    available_with_desc = sum(1 for p in products if p.get('available_for_sale', False) and p.get('description'))
    
    print(f"Total products: {total_count}")
    print(f"Available products: {available_count}")
    print(f"Products with descriptions: {with_desc_count}")
    print(f"Available products with descriptions: {available_with_desc}")
    
    # Simulate XML parsing
    print("\nSimulating XML parsing (which happens on app restart)...")
    pm.parse_xml()
    
    # Check products after "restart"
    products_after = pm.get_all_products(include_unavailable=True)
    total_after = len(products_after)
    available_after = sum(1 for p in products_after if p.get('available_for_sale', False))
    with_desc_after = sum(1 for p in products_after if p.get('description'))
    available_with_desc_after = sum(1 for p in products_after if p.get('available_for_sale', False) and p.get('description'))
    
    print(f"\nAfter 'restart':")
    print(f"Total products: {total_after}")
    print(f"Available products: {available_after}")
    print(f"Products with descriptions: {with_desc_after}")
    print(f"Available products with descriptions: {available_with_desc_after}")
    
    # Check if availability was preserved
    if available_after == available_count:
        print("\n✅ SUCCESS: Product availability was preserved!")
    else:
        print(f"\n❌ FAILURE: Product availability changed! Before: {available_count}, After: {available_after}")
    
    # Check if descriptions were preserved
    if with_desc_after == with_desc_count:
        print("✅ SUCCESS: Product descriptions were preserved!")
    else:
        print(f"❌ FAILURE: Product description count changed! Before: {with_desc_count}, After: {with_desc_after}")
    
    # Check if available products with descriptions were preserved
    if available_with_desc_after == available_with_desc:
        print("✅ SUCCESS: Available products with descriptions were preserved!")
    else:
        print(f"❌ FAILURE: Available products with descriptions changed! Before: {available_with_desc}, After: {available_with_desc_after}")

if __name__ == "__main__":
    test_availability_persistence()
