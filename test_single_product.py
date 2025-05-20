#!/usr/bin/env python3
import sys
import logging
import json
from product_manager import ProductManager
from product_descriptions import fetch_description_from_url

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('single_product_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('single_product_test')

def main():
    # Specific product ID to test
    product_id = "529200"
    
    logger.info(f"Starting test for product ID: {product_id}")
    
    try:
        # Initialize product manager
        product_manager = ProductManager()
        logger.info("ProductManager initialized")
        
        # Verify if the product exists in the XML
        xml_product = product_manager.get_product_from_xml(product_id)
        if xml_product:
            logger.info(f"Product found in XML: {json.dumps(xml_product, indent=2)}")
        else:
            logger.error(f"Product ID {product_id} not found in XML")
            return
        
        # Try to fetch the description
        logger.info("Fetching description from URL...")
        result = fetch_description_from_url(product_manager, product_id)
        
        if result['success']:
            logger.info("Description fetched successfully")
            logger.info(f"Description length: {len(result['description'])} characters")
            
            # Write description to file for inspection
            with open(f"description_{product_id}.html", "w", encoding="utf-8") as f:
                f.write(result['description'])
            logger.info(f"Description saved to description_{product_id}.html")
            
            # Update the product description
            update_success = product_manager.update_product_description(product_id, result['description'])
            logger.info(f"Update success: {update_success}")
            
            if not update_success:
                logger.error("Failed to update product description")
        else:
            logger.error(f"Failed to fetch description: {result.get('message', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
