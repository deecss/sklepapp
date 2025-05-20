#!/usr/bin/env python3
"""
Skrypt do resetowania dostępności wszystkich produktów.
Ustawia flagę available_for_sale na False dla wszystkich produktów lub dla wybranej kategorii.
"""

import os
import json
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('reset_availability')

def reset_product_availability(category=None):
    """
    Resetuje dostępność wszystkich produktów lub produktów z określonej kategorii
    
    Args:
        category (str, optional): Nazwa kategorii, której produkty mają być zresetowane
        
    Returns:
        int: Liczba zresetowanych produktów
    """
    try:
        # Ścieżka do pliku bazy danych produktów
        db_path = os.path.join('data', 'products.json')
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(db_path):
            logger.error(f"Plik bazy danych produktów nie istnieje: {db_path}")
            return 0
        
        # Wczytaj produkty z bazy danych
        with open(db_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        count = 0
        # Resetuj dostępność produktów
        for product in products:
            if category is None or product.get('category') == category:
                if product.get('available_for_sale', False):
                    product['available_for_sale'] = False
                    count += 1
        
        # Zapisz zmiany
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Zresetowano dostępność dla {count} produktów")
        return count
    
    except Exception as e:
        logger.error(f"Błąd podczas resetowania dostępności produktów: {str(e)}")
        return 0

if __name__ == "__main__":
    # Pobierz kategorię z argumentów wiersza poleceń
    category = None
    if len(sys.argv) > 1:
        category = sys.argv[1]
        print(f"Resetowanie dostępności produktów z kategorii: {category}")
    else:
        print("Resetowanie dostępności wszystkich produktów")
    
    # Resetuj dostępność
    count = reset_product_availability(category)
    print(f"Zresetowano dostępność dla {count} produktów")
