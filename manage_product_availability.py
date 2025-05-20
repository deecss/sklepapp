#!/usr/bin/env python3
"""
Skrypt do bezpośredniego zarządzania dostępnością produktów w bazie danych.
"""

import os
import json
import sys
import time
import shutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('manage_availability')

def reset_all_products():
    """Ustawia wszystkie produkty jako niedostępne do sprzedaży"""
    try:
        # Ścieżka do pliku bazy danych produktów
        db_path = os.path.join('data', 'products.json')
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(db_path):
            logger.error(f"Plik bazy danych produktów nie istnieje: {db_path}")
            return False
        
        # Utwórz kopię zapasową pliku
        backup_path = f"{db_path}.bak.{int(time.time())}"
        shutil.copy2(db_path, backup_path)
        logger.info(f"Utworzono kopię zapasową: {backup_path}")
        
        # Wczytaj produkty z bazy danych
        with open(db_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # Resetuj dostępność wszystkich produktów
        for product in products:
            product['available_for_sale'] = False
        
        # Zapisz zmiany
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Zresetowano dostępność dla {len(products)} produktów")
        return True
    
    except Exception as e:
        logger.error(f"Błąd podczas resetowania dostępności produktów: {str(e)}")
        return False

def set_products_available_by_category(category, available=True):
    """Ustawia produkty z danej kategorii jako dostępne/niedostępne do sprzedaży"""
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
        
        # Licznik zmienionych produktów
        count = 0
        
        # Ustaw dostępność dla produktów z danej kategorii
        for product in products:
            if product.get('category') == category:
                product['available_for_sale'] = available
                count += 1
        
        # Zapisz zmiany
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        status = "dostępne" if available else "niedostępne"
        logger.info(f"Ustawiono {count} produktów z kategorii '{category}' jako {status}")
        return count
    
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania dostępności produktów: {str(e)}")
        return 0

def set_product_available_by_id(product_id, available=True):
    """Ustawia konkretny produkt jako dostępny/niedostępny do sprzedaży"""
    try:
        # Ścieżka do pliku bazy danych produktów
        db_path = os.path.join('data', 'products.json')
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(db_path):
            logger.error(f"Plik bazy danych produktów nie istnieje: {db_path}")
            return False
        
        # Wczytaj produkty z bazy danych
        with open(db_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # Znajdź i zaktualizuj produkt
        for product in products:
            if str(product.get('id')) == str(product_id):
                product['available_for_sale'] = available
                
                # Zapisz zmiany
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                
                status = "dostępny" if available else "niedostępny"
                logger.info(f"Produkt '{product.get('name')}' (ID: {product_id}) jest teraz {status}")
                return True
        
        logger.error(f"Nie znaleziono produktu o ID: {product_id}")
        return False
    
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania dostępności produktu: {str(e)}")
        return False

def count_available_products():
    """Zlicza liczbę produktów dostępnych do sprzedaży"""
    try:
        # Ścieżka do pliku bazy danych produktów
        db_path = os.path.join('data', 'products.json')
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(db_path):
            logger.error(f"Plik bazy danych produktów nie istnieje: {db_path}")
            return (0, 0)
        
        # Wczytaj produkty z bazy danych
        with open(db_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # Zlicz produkty dostępne do sprzedaży
        available_count = sum(1 for p in products if p.get('available_for_sale', False))
        
        logger.info(f"Liczba produktów dostępnych do sprzedaży: {available_count}/{len(products)}")
        return (available_count, len(products))
    
    except Exception as e:
        logger.error(f"Błąd podczas zliczania produktów: {str(e)}")
        return (0, 0)

if __name__ == "__main__":
    # Prosty interfejs wiersza poleceń
    if len(sys.argv) < 2:
        print("Użycie: python manage_product_availability.py [komenda] [parametry]")
        print("Dostępne komendy:")
        print("  reset_all - resetuje dostępność wszystkich produktów")
        print("  set_category [kategoria] [dostępność] - ustawia dostępność produktów z danej kategorii")
        print("  set_product [id] [dostępność] - ustawia dostępność konkretnego produktu")
        print("  count - zlicza liczbę produktów dostępnych do sprzedaży")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "reset_all":
        if reset_all_products():
            print("Wszystkie produkty zostały ustawione jako niedostępne do sprzedaży")
        else:
            print("Błąd podczas resetowania dostępności produktów")
    
    elif command == "set_category" and len(sys.argv) >= 3:
        category = sys.argv[2]
        available = True
        if len(sys.argv) >= 4:
            available = sys.argv[3].lower() in ('true', 't', 'yes', 'y', '1')
        
        count = set_products_available_by_category(category, available)
        status = "dostępne" if available else "niedostępne"
        print(f"Ustawiono {count} produktów z kategorii '{category}' jako {status}")
    
    elif command == "set_product" and len(sys.argv) >= 3:
        product_id = sys.argv[2]
        available = True
        if len(sys.argv) >= 4:
            available = sys.argv[3].lower() in ('true', 't', 'yes', 'y', '1')
        
        if set_product_available_by_id(product_id, available):
            status = "dostępny" if available else "niedostępny"
            print(f"Produkt o ID {product_id} jest teraz {status}")
        else:
            print(f"Błąd podczas ustawiania dostępności produktu o ID {product_id}")
    
    elif command == "count":
        available, total = count_available_products()
        print(f"Liczba produktów dostępnych do sprzedaży: {available}/{total} ({available/total*100:.2f}%)")
    
    else:
        print("Nieznana komenda lub brak wymaganych parametrów")
        sys.exit(1)
