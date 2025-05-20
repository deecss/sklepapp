#!/usr/bin/env python3
"""
Script for bulk importing product descriptions from janshop.pl
"""
import sys
import logging
import argparse
from product_manager import ProductManager
from product_descriptions import update_product_descriptions_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mass_import_descriptions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mass_import')

def import_descriptions(product_ids=None, max_products=None, category=None, max_workers=4):
    """
    Import descriptions for multiple products
    
    Args:
        product_ids: List of specific product IDs to import (optional)
        max_products: Maximum number of products to process (optional)
        category: Filter products by category (optional)
        max_workers: Maximum number of parallel workers
    
    Returns:
        dict: Results with counts of updated and failed products
    """
    logger.info("Starting mass import of product descriptions")
    try:
        # Initialize product manager
        product_manager = ProductManager()
        logger.info("ProductManager initialized")

        # If no specific product_ids provided, get all published products
        ids_to_process = product_ids or []
        
        if not ids_to_process:
            # Get all published products
            all_products = product_manager.get_published_products()
            logger.info(f"Found {len(all_products)} published products")
            
            # Filter by category if specified
            if category:
                filtered_products = [p for p in all_products if category.lower() in p.get('category', '').lower()]
                logger.info(f"Filtered to {len(filtered_products)} products in category '{category}'")
                all_products = filtered_products
            
            # Get IDs
            ids_to_process = [str(p['id']) for p in all_products]
            
            # Apply max limit if specified
            if max_products and max_products < len(ids_to_process):
                logger.info(f"Limiting to {max_products} products")
                ids_to_process = ids_to_process[:max_products]
        
        # Process products
        logger.info(f"Processing {len(ids_to_process)} products with {max_workers} workers")
        results = update_product_descriptions_batch(product_manager, ids_to_process, max_workers)
        
        logger.info(f"Import complete. Updated: {results['updated']}, Errors: {results['errors']}")
        return results
    
    except Exception as e:
        logger.error(f"Error during mass import: {str(e)}", exc_info=True)
        return {
            'success': False,
            'updated': 0,
            'errors': 1,
            'error_details': [{'message': str(e)}]
        }

def main():
    """Command-line entry point"""
    parser = argparse.ArgumentParser(description='Mass import product descriptions from janshop.pl')
    parser.add_argument('--ids', nargs='+', help='Specific product IDs to process')
    parser.add_argument('--max', type=int, help='Maximum number of products to process')
    parser.add_argument('--category', type=str, help='Filter products by category')
    parser.add_argument('--workers', type=int, default=4, help='Maximum number of parallel workers')
    
    args = parser.parse_args()
    
    results = import_descriptions(
        product_ids=args.ids,
        max_products=args.max,
        category=args.category,
        max_workers=args.workers
    )
    
    print(f"Import complete.")
    print(f"Updated: {results['updated']} products")
    print(f"Errors: {results['errors']} products")
    if results.get('error_details') and len(results['error_details']) > 0:
        print("\nError details:")
        for error in results['error_details'][:5]:  # Show first 5 errors only
            print(f"  - Product ID {error.get('product_id', 'Unknown')}: {error.get('message', 'Unknown error')}")
        if len(results['error_details']) > 5:
            print(f"  ... and {len(results['error_details']) - 5} more errors.")

if __name__ == "__main__":
    main()
