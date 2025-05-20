"""
Test script to debug product description generation
"""
import logging
import os
import sys
from product_descriptions import fetch_description_from_url
from product_manager import ProductManager

# Configure console logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_description.log')
    ]
)
logger = logging.getLogger('test_description')

def main():
    """Main test function"""
    try:
        # Get product ID from command line
        if len(sys.argv) < 2:
            print("Usage: python test_description.py <product_id>")
            return
            
        product_id = sys.argv[1]
        logger.info(f"Testing product description fetch for product ID: {product_id}")
        
        # Check if XML file exists
        xml_path = os.path.join('data', 'products_latest.xml')
        if not os.path.exists(xml_path):
            logger.error(f"XML file does not exist: {xml_path}")
            return
            
        # Initialize product manager
        logger.info("Initializing ProductManager")
        product_manager = ProductManager()
        
        # Get product from XML for test
        logger.info(f"Getting product {product_id} from XML")
        xml_product = product_manager.get_product_from_xml(product_id)
        if not xml_product:
            logger.error(f"Product ID: {product_id} not found in XML")
            return
            
        logger.info(f"Product found in XML: {xml_product.get('name')}")
        logger.info(f"Product URL: {xml_product.get('url')}")
        
        # Fetch description
        logger.info("Starting description fetch")
        result = fetch_description_from_url(product_manager, product_id)
        
        # Show result
        if result['success']:
            logger.info("Successfully fetched description")
            logger.info(f"Description length: {len(result['description'])} characters")
            
            # Try to update the product
            logger.info("Attempting to update product description")
            success = product_manager.update_product_description(product_id, result['description'])
            if success:
                logger.info("Product description updated successfully")
            else:
                logger.error("Failed to update product description")
        else:
            logger.error(f"Failed to fetch description: {result.get('message', 'Unknown error')}")
        
    except Exception as e:
        logger.exception(f"Error in test script: {str(e)}")

if __name__ == "__main__":
    main()
