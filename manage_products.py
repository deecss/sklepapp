#!/usr/bin/env python3
"""
Product management utility for the shop.
This script helps maintain product availability and troubleshoot issues.
"""
import argparse
import logging
import json
import os
import sys
from product_manager import ProductManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('product_management.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('product_management')

def restore_products_with_descriptions():
    """Make all products with descriptions available for sale."""
    product_manager = ProductManager()
    products = product_manager.get_all_products(include_unavailable=True)
    
    restored_count = 0
    for product in products:
        if not product.get('available_for_sale', False) and product.get('description'):
            product['available_for_sale'] = True
            restored_count += 1
    
    if restored_count > 0:
        logger.info(f"Making {restored_count} products with descriptions available...")
        product_manager._save_to_db()
        print(f"✅ Successfully made {restored_count} products with descriptions available!")
    else:
        print("ℹ️ No products with descriptions needed to be made available.")

def count_products():
    """Count different types of products."""
    product_manager = ProductManager()
    products = product_manager.get_all_products(include_unavailable=True)
    
    total = len(products)
    available = sum(1 for p in products if p.get('available_for_sale', False))
    with_descriptions = sum(1 for p in products if p.get('description'))
    available_with_descriptions = sum(1 for p in products if p.get('available_for_sale', False) and p.get('description'))
    unavailable_with_descriptions = sum(1 for p in products if not p.get('available_for_sale', False) and p.get('description'))
    
    print("\n📊 Product Statistics:")
    print(f"  Total products: {total}")
    print(f"  Available products: {available}")
    print(f"  Products with descriptions: {with_descriptions}")
    print(f"  Available products with descriptions: {available_with_descriptions}")
    print(f"  Unavailable products with descriptions: {unavailable_with_descriptions}")
    print()

def set_all_availability(available=True):
    """Set all products to available or unavailable."""
    product_manager = ProductManager()
    products = product_manager.get_all_products(include_unavailable=True)
    
    changed_count = 0
    for product in products:
        if product.get('available_for_sale', False) != available:
            product['available_for_sale'] = available
            changed_count += 1
    
    if changed_count > 0:
        status = "available" if available else "unavailable"
        logger.info(f"Making {changed_count} products {status}...")
        product_manager._save_to_db()
        print(f"✅ Successfully made {changed_count} products {status}!")
    else:
        print(f"ℹ️ All products were already {'available' if available else 'unavailable'}.")

def set_category_availability(category, available=True):
    """Set all products in a category to available or unavailable."""
    product_manager = ProductManager()
    products = product_manager.get_all_products(include_unavailable=True)
    
    changed_count = 0
    for product in products:
        if product.get('category') == category and product.get('available_for_sale', False) != available:
            product['available_for_sale'] = available
            changed_count += 1
    
    if changed_count > 0:
        status = "available" if available else "unavailable"
        logger.info(f"Making {changed_count} products in category '{category}' {status}...")
        product_manager._save_to_db()
        print(f"✅ Successfully made {changed_count} products in category '{category}' {status}!")
    else:
        print(f"ℹ️ No products in category '{category}' needed to be made {status}.")

def show_categories():
    """Show all product categories with product counts."""
    product_manager = ProductManager()
    products = product_manager.get_all_products(include_unavailable=True)
    
    categories = {}
    for product in products:
        category = product.get('category', 'Unknown')
        if category not in categories:
            categories[category] = {
                'total': 0,
                'available': 0,
                'with_description': 0
            }
        
        categories[category]['total'] += 1
        
        if product.get('available_for_sale', False):
            categories[category]['available'] += 1
            
        if product.get('description'):
            categories[category]['with_description'] += 1
    
    print("\n📁 Categories:")
    for category, stats in sorted(categories.items()):
        print(f"  {category}:")
        print(f"    Total: {stats['total']}")
        print(f"    Available: {stats['available']}")
        print(f"    With descriptions: {stats['with_description']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Product management utility for the shop")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Count products command
    count_parser = subparsers.add_parser("count", help="Count products")
    
    # Restore products with descriptions command
    restore_parser = subparsers.add_parser("restore", help="Make all products with descriptions available")
    
    # Set all products available/unavailable command
    set_all_parser = subparsers.add_parser("set_all", help="Set all products as available or unavailable")
    set_all_parser.add_argument("status", choices=["available", "unavailable"], 
                               help="Status to set for all products")
    
    # Set category available/unavailable command
    set_category_parser = subparsers.add_parser("set_category", help="Set products in a category as available or unavailable")
    set_category_parser.add_argument("category", help="Category name")
    set_category_parser.add_argument("status", choices=["available", "unavailable"], 
                                    help="Status to set for products in the category")
    
    # Show categories command
    categories_parser = subparsers.add_parser("categories", help="Show all product categories")
    
    args = parser.parse_args()
    
    if args.command == "count":
        count_products()
    elif args.command == "restore":
        restore_products_with_descriptions()
    elif args.command == "set_all":
        set_all_availability(args.status == "available")
    elif args.command == "set_category":
        set_category_availability(args.category, args.status == "available")
    elif args.command == "categories":
        show_categories()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
