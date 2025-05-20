import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime
import logging
import threading  # Dodajemy obsługę wątków
import requests
from bs4 import BeautifulSoup
import re
import uuid
from urllib.parse import urlparse, urljoin

class ProductManager:
    """Klasa zarządzająca produktami - parsowanie XML i zapisywanie do bazy danych"""
    
    def __init__(self):
        """Inicjalizacja menedżera produktów"""
        # Konfiguracja logowania
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='product_manager.log',
            filemode='a'
        )
        self.logger = logging.getLogger('product_manager')
        
        # Konfiguracja ścieżek
        self.data_dir = os.path.join(os.getcwd(), 'data')
        self.uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads')
        self.product_images_dir = os.path.join(self.uploads_dir, 'products')
        self.xml_path = os.path.join(self.data_dir, 'products_latest.xml')
        self.db_path = os.path.join(self.data_dir, 'products.json')
        self.lists_path = os.path.join(self.data_dir, 'product_lists.json')
        self.featured_categories_path = os.path.join(self.data_dir, 'featured_categories.json')
        
        # Utwórz katalogi, jeśli nie istnieją
        for directory in [self.data_dir, self.uploads_dir, self.product_images_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
        # Wczytaj obecne dane
        self.xml_products = []
        self.products = self.load_products()
        self.product_lists = self.load_product_lists()
        self.last_update = time.time()
        
        # Blokada wątku dla operacji na plikach
        self.file_lock = threading.RLock()
        
    # Funkcja do pobierania opisu produktu z janshop.pl
    def fetch_product_description(self, url):
        """Pobiera opis produktu z janshop.pl na podstawie adresu URL"""
        try:
            # Pobierz stronę produktu
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"Nie udało się pobrać strony {url}, kod statusu: {response.status_code}")
                return None

            # Parsuj HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Znajdź div z opisem
            description_div = soup.find('div', id='opis-import')
            if not description_div:
                self.logger.error(f"Nie znaleziono div z id='opis-import' na stronie {url}")
                return None
                
            # Pobranie zawartości diva w formie HTML
            description_html = str(description_div)
            
            # Pobierz wszystkie obrazy z opisu
            images = description_div.find_all('img')
            
            # Przygotuj katalog dla obrazów produktu
            image_dir = os.path.join(self.product_images_dir, str(uuid.uuid4()))
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)
                
            # Pobierz i zapisz obrazy, zaktualizuj ścieżki w opisie
            for img in images:
                if 'src' in img.attrs:
                    # Pobierz pełny URL obrazu
                    img_url = img['src']
                    if not img_url.startswith(('http://', 'https://')):
                        # Jeśli URL jest względny, stwórz pełny URL
                        img_url = urljoin(url, img_url)
                        
                    try:
                        # Pobierz obraz
                        img_response = requests.get(img_url, timeout=10)
                        if img_response.status_code == 200:
                            # Generuj unikalną nazwę dla obrazu
                            img_name = f"{uuid.uuid4()}{os.path.splitext(img_url)[1]}"
                            img_path = os.path.join(image_dir, img_name)
                            
                            # Zapisz obraz
                            with open(img_path, 'wb') as f:
                                f.write(img_response.content)
                                
                            # Zmień ścieżkę w opisie HTML
                            relative_path = os.path.join('/static/uploads/products', os.path.basename(image_dir), img_name)
                            description_html = description_html.replace(img['src'], relative_path)
                    except Exception as e:
                        self.logger.error(f"Błąd podczas pobierania obrazu {img_url}: {str(e)}")
                        
            return description_html
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania opisu produktu z {url}: {str(e)}")
            return None
            
    def update_product_descriptions(self, product_ids=None):
        """
        Aktualizuje opisy produktów na podstawie URL w XML
        
        Args:
            product_ids: Lista ID produktów do zaktualizowania. Jeśli None, aktualizuje wszystkie produkty.
        
        Returns:
            dict: Słownik z informacjami o wynikach operacji
        """
        if not os.path.exists(self.xml_path):
            return {
                'success': False,
                'message': 'Plik XML z produktami nie istnieje',
                'updated': 0,
                'failed': 0,
                'total': 0
            }
            
        try:
            # Parsuj XML
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            
            # Wczytaj aktualne produkty
            products = self.load_products()
            
            # Liczniki
            updated_count = 0
            failed_count = 0
            total_count = 0
            updated_products = []
            failed_products = []
            
            # Przetwarzaj produkty
            for xml_product in root.findall('.//product'):
                product_id = xml_product.find('id').text if xml_product.find('id') is not None else None
                
                # Jeśli podano konkretne ID, sprawdź czy ten produkt ma być zaktualizowany
                if product_ids and product_id not in product_ids:
                    continue
                    
                total_count += 1
                
                # Znajdź URL produktu
                url_element = xml_product.find('url')
                if url_element is None or not url_element.text:
                    failed_count += 1
                    failed_products.append({
                        'id': product_id,
                        'reason': 'Brak URL w XML'
                    })
                    continue
                    
                url = url_element.text
                
                # Pobierz opis produktu
                description_html = self.fetch_product_description(url)
                if not description_html:
                    failed_count += 1
                    failed_products.append({
                        'id': product_id,
                        'reason': 'Nie udało się pobrać opisu ze strony'
                    })
                    continue
                    
                # Znajdź odpowiadający produkt w naszej bazie
                found = False
                for i, product in enumerate(products):
                    if product.get('xml_id') == product_id:
                        # Zaktualizuj opis
                        products[i]['description'] = description_html
                        updated_count += 1
                        updated_products.append({
                            'id': product_id,
                            'name': product.get('name', 'Nieznany produkt')
                        })
                        found = True
                        break
                        
                if not found:
                    failed_count += 1
                    failed_products.append({
                        'id': product_id,
                        'reason': 'Produkt nie został znaleziony w bazie danych'
                    })
                    
            # Zapisz zaktualizowane produkty
            self.save_products(products)
            
            return {
                'success': True,
                'message': f'Zaktualizowano opisy {updated_count} produktów, nie udało się zaktualizować {failed_count} produktów',
                'updated': updated_count,
                'failed': failed_count,
                'total': total_count,
                'updated_products': updated_products,
                'failed_products': failed_products
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji opisów produktów: {str(e)}")
            return {
                'success': False,
                'message': f'Wystąpił błąd: {str(e)}',
                'updated': 0,
                'failed': 0,
                'total': 0
            }
    
    # Pozostałe metody klasy ProductManager...
    
    def parse_xml(self, xml_file=None):
        """Parsuje plik XML z opisami produktów i zapisuje dane do pamięci"""
        # Jeśli nie podano ścieżki do pliku, użyj domyślnej
        if not xml_file:
            if not os.path.exists(self.xml_path):
                self.logger.error(f"Plik XML nie istnieje: {self.xml_path}")
                return False
            xml_file = self.xml_path
            
        try:
            # Parsuj XML
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Wyczyść listę produktów z XML
            self.xml_products = []
            
            # Przetwarzaj produkty
            for product in root.findall('.//product'):
                # Podstawowe pola
                product_data = {
                    'id': product.find('id').text if product.find('id') is not None else None,
                    'name': product.find('name').text if product.find('name') is not None else 'Nieznany produkt',
                    'ean': product.find('ean').text if product.find('ean') is not None else None,
                    'price': float(product.find('price').text) if product.find('price') is not None else 0,
                    'stock': int(product.find('stock').text) if product.find('stock') is not None else 0,
                    'category': product.find('category').text if product.find('category') is not None else 'Bez kategorii',
                    'image': product.find('image').text if product.find('image') is not None else None,
                    'url': product.find('url').text if product.find('url') is not None else None,
                }
                
                # Dodatkowe pola, jeśli istnieją
                vat_element = product.find('vat')
                if vat_element is not None:
                    product_data['vat'] = int(vat_element.text)
                else:
                    product_data['vat'] = 23  # Domyślny VAT w Polsce
                
                # Obsługa podkategorii
                subcategories = []
                category_path = product.find('category_path')
                if category_path is not None:
                    for subcategory in category_path.findall('category'):
                        subcategories.append(subcategory.text)
                product_data['subcategories'] = subcategories
                
                # Dodaj produkt do listy
                self.xml_products.append(product_data)
            
            self.logger.info(f"Sparsowano {len(self.xml_products)} produktów z pliku XML")
            self.last_update = time.time()
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas parsowania XML: {str(e)}")
            return False
            
    def load_products(self):
        """Ładuje produkty z bazy danych JSON"""
        if not os.path.exists(self.db_path):
            return []
            
        try:
            with self.file_lock:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania produktów: {str(e)}")
            return []
    
    def save_products(self, products):
        """Zapisuje produkty do bazy danych JSON"""
        try:
            with self.file_lock:
                with open(self.db_path, 'w', encoding='utf-8') as f:
                    json.dump(products, f, indent=4, ensure_ascii=False)
            self.products = products
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania produktów: {str(e)}")
            return False
            
    def load_product_lists(self):
        """Ładuje listy produktów z pliku JSON"""
        if not os.path.exists(self.lists_path):
            return []
            
        try:
            with self.file_lock:
                with open(self.lists_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania list produktów: {str(e)}")
            return []
            
    def get_published_products(self):
        """Zwraca wszystkie produkty dostępne do sprzedaży"""
        return [p for p in self.products if p.get('available_for_sale', False)]
