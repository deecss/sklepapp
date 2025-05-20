#!/usr/bin/env python3
import logging
import json
import os
from product_manager import ProductManager
from product_descriptions import fetch_description_from_url

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_product.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('debug_product')

# Specify product ID
product_id = "529200"

logger.info(f"Testing product ID: {product_id}")

# Initialize ProductManager
try:
    product_manager = ProductManager()
    logger.info("ProductManager initialized")
    
    # Check if XML is loaded
    if not hasattr(product_manager, 'xml_products') or not product_manager.xml_products:
        logger.error("XML products not loaded")
        exit(1)
    
    logger.info(f"XML products loaded: {len(product_manager.xml_products)} items")
    
    # Search for product in XML data
    xml_product = None
    for product in product_manager.xml_products:
        if str(product.get('id')) == str(product_id):
            xml_product = product
            break
    
    if xml_product:
        logger.info(f"Found product in XML: {json.dumps(xml_product, indent=2)}")
        
        # Get product URL
        url = xml_product.get('url')
        logger.info(f"Product URL: {url}")
        
        # Check if upload folder exists
        upload_folder = os.path.join('static', 'uploads', 'products', str(product_id))
        if not os.path.exists(upload_folder):
            logger.info(f"Creating folder: {upload_folder}")
            os.makedirs(upload_folder, exist_ok=True)
        
        # Try to fetch description
        result = fetch_description_from_url(product_manager, product_id)
        
        if result['success']:
            logger.info("Description fetched successfully")
            logger.info(f"Description length: {len(result['description'])} characters")
            
            # Save description to file
            with open(f"description_{product_id}.html", "w", encoding="utf-8") as f:
                f.write(result['description'])
            logger.info(f"Description saved to description_{product_id}.html")
            
            # Update product description
            update_success = product_manager.update_product_description(product_id, result['description'])
            logger.info(f"Update product description result: {update_success}")
        else:
            logger.error(f"Failed to fetch description: {result.get('message', 'Unknown error')}")
    else:
        logger.error(f"Product ID {product_id} not found in XML data")

except Exception as e:
    logger.exception(f"Error in debug script: {str(e)}")
