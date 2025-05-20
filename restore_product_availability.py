#!/usr/bin/env python3
"""
Script to restore product availability for products with descriptions.
This script can be used when products with descriptions are not showing up on the website.
"""
import logging
import json
import os
from product_manager import ProductManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('restore_availability.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('restore_availability')

def restore_availability():
    """Restore availability for all products that have descriptions."""
    try:
        # Initialize product manager
        product_manager = ProductManager()
        logger.info("ProductManager initialized")
        
        # Get all products
        products = product_manager.get_all_products(include_unavailable=True)
        logger.info(f"Found {len(products)} total products")
        
        # Count products with descriptions but not available
        unavailable_with_desc_count = 0
        for product in products:
            if not product.get('available_for_sale', False) and product.get('description'):
                unavailable_with_desc_count += 1
                
        logger.info(f"Found {unavailable_with_desc_count} products with descriptions but unavailable")
        
        # Prompt for confirmation
        if unavailable_with_desc_count > 0:
            proceed = input(f"Found {unavailable_with_desc_count} products with descriptions but unavailable. Restore availability? (y/n): ")
            
            if proceed.lower() != 'y':
                logger.info("Operation cancelled by user.")
                return
                
            # Restore availability for products with descriptions
            restored_count = 0
            for product in products:
                if not product.get('available_for_sale', False) and product.get('description'):
                    # Set product as available
                    product['available_for_sale'] = True
                    restored_count += 1
            
            # Save changes
            if restored_count > 0:
                logger.info(f"Setting {restored_count} products as available...")
                product_manager._save_to_db()
                logger.info(f"Successfully restored availability for {restored_count} products!")
            else:
                logger.info("No products needed availability restoration.")
        else:
            logger.info("No products need availability restoration.")
            
    except Exception as e:
        logger.error(f"Error during availability restoration: {str(e)}")

if __name__ == "__main__":
    restore_availability()
