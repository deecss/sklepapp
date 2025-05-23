import xml.etree.ElementTree as ET
import logging
import time # Dodane dla time.time()
import os
import json
from datetime import datetime, timedelta # Dodano timedelta
import threading # Dodano threading

class ProductManager:
    """Klasa zarządzająca produktami - parsowanie XML i zapisywanie do bazy danych"""
    
    DB_FILE = os.path.join('data', 'products.json')
    XML_CONFIG_FILE = os.path.join('data', 'xml_config.json')
    PRODUCT_LISTS_FILE = os.path.join('data', 'product_lists.json')
    FEATURED_CATEGORIES_FILE = os.path.join('data', 'featured_categories.json')
    DEFAULT_XML_PATH = os.path.join('data', 'products_latest.xml')
    VAT_RATE = 23  # Domyślna stawka VAT w procentach

    def __init__(self, db_file=None, xml_path=None):
        """Inicjalizacja menedżera produktów"""
        # Konfiguracja logowania
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='product_manager.log',
            filemode='a'
        )
        self.logger = logging.getLogger('product_manager')
        
        # Ścieżki do plików
        self.xml_path = os.path.join('data', 'products_latest.xml')
        self.db_path = os.path.join('data', 'products.json')
        
        # Lista produktów
        self.products = []
        self.save_lock = threading.Lock() # Dodajemy blokadę
        
        # Próba załadowania istniejących produktów
        self._load_from_db()
    
    def _load_from_db(self):
        """Ładuje produkty z lokalnej bazy danych JSON"""
        try:
            # Sprawdź główny plik bazy danych
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
                try:
                    with open(self.db_path, 'r', encoding='utf-8') as f:
                        self.products = json.load(f)
                    self.logger.info(f"Załadowano {len(self.products)} produktów z bazy danych")
                    # Konwersja ID na stringi dla pewności, jeśli gdzieś były int
                    for product in self.products:
                        if 'id' in product and product['id'] is not None:
                            product['id'] = str(product['id'])
                    return
                except json.JSONDecodeError:
                    self.logger.error(f"Plik bazy danych jest uszkodzony: {self.db_path}")
                    # Spróbuj użyć kopii zapasowej
            
            # Sprawdź kopię zapasową
            backup_path = f"{self.db_path}.bak"
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        self.products = json.load(f)
                    self.logger.warning(f"Załadowano {len(self.products)} produktów z kopii zapasowej")
                    
                    # Przywróć główny plik z kopii zapasowej
                    import shutil
                    shutil.copy2(backup_path, self.db_path)
                    self.logger.info(f"Przywrócono główny plik bazy danych z kopii zapasowej")
                    return
                except json.JSONDecodeError:
                    self.logger.error(f"Kopia zapasowa bazy danych jest uszkodzona: {backup_path}")
            
            # Jeśli nie udało się załadować z głównego pliku ani kopii zapasowej
            self.products = []
            self.logger.warning("Nie znaleziono pliku bazy danych lub pliki są uszkodzone. Utworzono pustą listę produktów.")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania produktów z bazy danych: {str(e)}")
            self.products = []
    
    def _save_to_db(self):
        """Zapisuje produkty do lokalnej bazy danych JSON"""
        with self.save_lock:  # Używamy blokady dla bezpiecznego zapisu
            try:
                self.logger.info(f"Rozpoczynam zapis {len(self.products)} produktów do bazy danych")
                # Najpierw zapisujemy do pliku tymczasowego
                temp_db_path = f"{self.db_path}.tmp"
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                
                # Sprawdź uprawnienia do katalogu
                data_dir = os.path.dirname(self.db_path)
                try:
                    perm_test_file = os.path.join(data_dir, 'perm_test.txt')
                    with open(perm_test_file, 'w') as f:
                        f.write('test')
                    os.remove(perm_test_file)
                    self.logger.info(f"Uprawnienia do zapisu w katalogu {data_dir} są poprawne")
                except Exception as e:
                    self.logger.error(f"Brak uprawnień do zapisu w katalogu {data_dir}: {str(e)}")
                    return False
                
                self.logger.info(f"Zapisuję do pliku tymczasowego: {temp_db_path}")
                with open(temp_db_path, 'w', encoding='utf-8') as f:
                    json.dump(self.products, f, ensure_ascii=False, indent=2)
                
                # Sprawdzamy czy plik tymczasowy został prawidłowo utworzony
                if not os.path.exists(temp_db_path) or os.path.getsize(temp_db_path) == 0:
                    self.logger.error(f"Nie udało się utworzyć pliku tymczasowego: {temp_db_path}")
                    return False
                
                # Tworzymy kopię zapasową aktualnego pliku, jeśli istnieje
                if os.path.exists(self.db_path):
                    backup_path = f"{self.db_path}.bak"
                    try:
                        self.logger.info(f"Tworzę kopię zapasową: {backup_path}")
                        os.replace(self.db_path, backup_path)
                    except Exception as e:
                        self.logger.warning(f"Nie udało się utworzyć kopii zapasowej: {str(e)}")
                
                # Przemianowujemy plik tymczasowy na właściwy
                self.logger.info(f"Zastępuję plik bazy danych: {self.db_path}")
                os.replace(temp_db_path, self.db_path)
                
                self.logger.info(f"Zapisano {len(self.products)} produktów do bazy danych")
                
                # Dodatkowa weryfikacja zapisu
                if not os.path.exists(self.db_path):
                    self.logger.error(f"Plik bazy danych nie został utworzony: {self.db_path}")
                    return False
                    
                file_size = os.path.getsize(self.db_path)
                if file_size == 0:
                    self.logger.error(f"Plik bazy danych jest pusty: {self.db_path}")
                    return False
                
                self.logger.info(f"Zapis zakończony sukcesem, rozmiar pliku: {file_size} bajtów")
                return True
            except Exception as e:
                self.logger.error(f"Błąd podczas zapisywania produktów do bazy danych: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                return False
    
    def parse_xml(self, xml_path=None):
        """Parsuje plik XML i aktualizuje listę produktów"""
        if xml_path is None:
            xml_path = self.xml_path
            
        if not os.path.exists(xml_path):
            self.logger.error(f"Plik XML nie istnieje: {xml_path}")
            return False
            
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            new_products = []
            parsed_xml_ids = set()

            for product_elem in root.findall('.//offer'):
                product = {}
                
                # Bezpośrednie mapowanie pól
                xml_id = self._safe_get_xml_value(product_elem, 'id')
                if not xml_id:
                    self.logger.warning("Pominięto produkt w XML bez ID.")
                    continue
                
                if xml_id in parsed_xml_ids:
                    self.logger.warning(f"Zduplikowany XML ID {xml_id} w pliku. Pomijam kolejne wystąpienie.")
                    continue
                parsed_xml_ids.add(xml_id)

                product['xml_id'] = xml_id # Zapisujemy ID z XML
                product['id'] = xml_id # Używamy XML ID jako głównego ID produktu dla uproszczenia
                                       # Jeśli potrzebne są osobne ID, trzeba będzie to dostosować

                product['uuid'] = self._safe_get_xml_value(product_elem, 'uuid')
                product['name'] = self._safe_get_xml_value(product_elem, 'name')
                product['EAN'] = self._safe_get_xml_value(product_elem, 'EAN')
                product['producer'] = self._safe_get_xml_value(product_elem, 'producer')
                product['url'] = self._safe_get_xml_value(product_elem, 'url')
                
                # Obsługa obrazów produktu
                product['images'] = []
                pictures_elem = product_elem.find('pictures')
                if pictures_elem is not None:
                    for pic_elem in pictures_elem.findall('picture'):
                        if pic_elem.text and pic_elem.text.strip():
                            product['images'].append(pic_elem.text.strip())
                
                # Ustaw pierwszy obraz jako główny
                if product['images']:
                    product['image'] = product['images'][0]
                else:
                    product['image'] = None
                
                # Domyślnie produkty NIE są dostępne do sprzedaży po zaimportowaniu z XML
                # (dostępność musi być włączona ręcznie lub przez skrypt)
                product['available_for_sale'] = False
                
                # Obsługa kategorii - podział na hierarchię
                category_text = self._safe_get_xml_value(product_elem, 'category')
                if category_text:
                    # Zamień encje HTML na znaki
                    category_text = category_text.replace('&amp;gt;', '>').replace('&gt;', '>')
                    # Podziel na poszczególne poziomy kategorii
                    categories = [cat.strip() for cat in category_text.split('>') if cat.strip()]
                    product['category'] = categories[-1] if categories else "Bez kategorii"
                    product['category_path'] = categories if categories else ["Bez kategorii"]
                else:
                    product['category'] = "Bez kategorii"
                    product['category_path'] = ["Bez kategorii"]
                
                # Obsługa cen - ceny z XML są NETTO, doliczamy VAT
                try:
                    price_net_xml = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                    discounted_price_net_xml = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                    
                    if discounted_price_net_xml == 0:
                        discounted_price_net_xml = price_net_xml

                    product['price_net_xml'] = price_net_xml # Cena netto z XML
                    
                    # Obliczamy ceny brutto
                    price_gross_xml = self._calculate_gross_price(price_net_xml)
                    discounted_price_gross_xml = self._calculate_gross_price(discounted_price_net_xml)

                    # Używamy discounted_price jako głównej ceny brutto, price jest teraz ceną "przed rabatem"
                    product['price'] = discounted_price_gross_xml # Cena brutto po rabacie
                    product['original_price'] = discounted_price_gross_xml # Cena bazowa do narzutów
                    product['regular_price'] = price_gross_xml # Regularna cena (przed rabatem)
                    
                    # Domyślny narzut sklepu to 0% przy pierwszym parsowaniu
                    product['markup_percent'] = 0.0

                except ValueError as e:
                    self.logger.error(f"Błąd konwersji ceny dla produktu XML ID {xml_id}: {e}")
                    product['price_net_xml'] = 0.0
                    product['price'] = 0.0
                    product['discounted_price'] = 0.0
                    product['original_price'] = 0.0
                    product['markup_percent'] = 0.0

                # VAT - pobieramy z XML jeśli jest, inaczej domyślny
                vat_xml = self._safe_get_xml_value(product_elem, 'tax')
                try:
                    product['vat'] = int(vat_xml) if vat_xml else self.VAT_RATE
                except ValueError:
                    product['vat'] = self.VAT_RATE
                
                # Stan magazynowy
                try:
                    product['stock'] = int(self._safe_get_xml_value(product_elem, 'stock', '0'))
                except ValueError:
                    product['stock'] = 0
                
                # Tylko produkty dostępne na magazynie (lub z ujemnym stanem, jeśli tak ma być)
                # Na razie dodajemy wszystkie, filtrowanie może być później
                new_products.append(product)
            
            # Zachowaj dostępność produktów, opisy i narzuty z poprzedniej wersji
            restored_count = 0
            preserved_descriptions = 0
            preserved_markups = 0
            
            if hasattr(self, 'products') and self.products:
                existing_products_map = {str(p.get('xml_id')): p for p in self.products if p.get('xml_id')}
                
                for new_product in new_products:
                    xml_id = str(new_product.get('xml_id'))
                    existing_product = existing_products_map.get(xml_id)
                    
                    if existing_product:
                        # Zachowaj status dostępności
                        if existing_product.get('available_for_sale', False):
                            new_product['available_for_sale'] = True
                            restored_count += 1
                        
                        # Zachowaj opis produktu
                        if 'description' in existing_product and existing_product['description']:
                            new_product['description'] = existing_product['description']
                            preserved_descriptions += 1
                            
                        # Zachowaj narzut sklepu i zaktualizuj cenę, jeśli narzut istnieje
                        if 'markup_percent' in existing_product and existing_product['markup_percent'] is not None:
                            markup_percent = float(existing_product['markup_percent'])
                            new_product['markup_percent'] = markup_percent
                            
                            # Cena bazowa do narzutu to cena brutto z XML (czyli new_product['original_price'])
                            base_gross_price_for_markup = new_product['original_price'] 
                            
                            final_price_with_markup = round(base_gross_price_for_markup * (1 + markup_percent / 100), 2)
                            new_product['price'] = final_price_with_markup
                            # discounted_price również powinno być przeliczone jeśli jest równe cenie bazowej
                            if new_product['discounted_price'] == base_gross_price_for_markup : # Porównujemy z ceną brutto z XML
                                new_product['discounted_price'] = final_price_with_markup
                            preserved_markups +=1
                        
                        # Zachowaj inne istotne pola, które mogły być ręcznie edytowane
                        for field in ['delivery_time', 'delivery_cost', 'custom_name', 'custom_category', 'images', 'image']: # Dodaj inne pola wg potrzeb
                            if field in existing_product and existing_product[field] is not None:
                                new_product[field] = existing_product[field]
            
            self.products = new_products
            self._assign_internal_ids() # Przypisz unikalne ID wewnętrzne jeśli XML ID nie wystarczą
            self._save_to_db()
            
            self.logger.info(f"Pomyślnie sparsowano plik XML {xml_path}, znaleziono {len(new_products)} produktów.")
            self.logger.info(f"Przywrócono dostępność dla {restored_count} produktów.")
            self.logger.info(f"Zachowano opisy dla {preserved_descriptions} produktów.")
            self.logger.info(f"Zachowano i zastosowano narzuty dla {preserved_markups} produktów.")
            return True
            
        except ET.ParseError as e:
            self.logger.error(f"Błąd parsowania XML ({xml_path}): {e}")
            return False
        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd podczas parsowania pliku XML {xml_path}: {str(e)}")
            return False

    def _assign_internal_ids(self):
        """Przypisuje unikalne ID wewnętrzne, jeśli 'id' nie jest jeszcze unikalne lub nie istnieje."""
        # Jeśli używamy xml_id jako 'id', ta funkcja może nie być potrzebna
        # lub może służyć do generowania ID dla produktów dodanych ręcznie
        next_id = 1
        if self.products:
            # Znajdź maksymalne istniejące ID numeryczno
            max_id = max([int(p['id']) for p in self.products if p['id'].isdigit()], default=0)
            next_id = max_id + 1

        for product in self.products:
            if 'id' not in product or product['id'] is None or product['id'] == '':
                product['id'] = str(next_id)
                next_id += 1

    def _safe_get_xml_value(self, element, tag, default_value=None):
        """Bezpieczne pobieranie wartości z elementu XML z obsługą brakujących tagów i encji."""
        try:
            value = element.find(tag).text
            if value is not None:
                return value.strip()
        except Exception as e:
            self.logger.warning(f"Błąd podczas pobierania wartości XML dla tagu '{tag}': {e}")
        return default_value

    def _calculate_gross_price(self, net_price):
        """Oblicza cenę brutto na podstawie ceny netto i stawki VAT."""
        try:
            vat_multiplier = 1 + (self.VAT_RATE / 100)
            gross_price = round(float(net_price) * vat_multiplier, 2)
            return gross_price
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania ceny brutto: {e}")
            return 0.0
    
    def update_product(self, product_id, price=None, markup_percent=None, vat=None, delivery_time=None, delivery_cost=None, available_for_sale=None):
        """
        Aktualizuje produkt w bazie danych.
        
        Args:
            product_id (str): ID produktu
            price (float, optional): Nowa cena produktu
            markup_percent (float, optional): Nowy narzut procentowy
            vat (float, optional): Nowa stawka VAT
            delivery_time (str, optional): Nowy czas dostawy
            delivery_cost (float, optional): Nowy koszt dostawy
            available_for_sale (bool, optional): Nowa dostępność produktu
            
        Returns:
            bool: True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        try:
            self.logger.info(f"Rozpoczynam aktualizację produktu o ID {product_id}")
            self.logger.info(f"Parametry aktualizacji: price={price}, markup_percent={markup_percent}, vat={vat}, delivery_time={delivery_time}, delivery_cost={delivery_cost}, available_for_sale={available_for_sale}")
            
            # Znajdź produkt
            product = None
            for p in self.products:
                if str(p.get('id')) == str(product_id):
                    product = p
                    break
            
            if not product:
                self.logger.error(f"Nie znaleziono produktu o ID {product_id}")
                return False
            
            # Aktualizuj pola
            if available_for_sale is not None:
                product['available_for_sale'] = available_for_sale
            
            if vat is not None:
                product['vat'] = float(vat)
            
            if delivery_time is not None:
                product['delivery_time'] = delivery_time
            
            if delivery_cost is not None:
                product['delivery_cost'] = float(delivery_cost)
            
            # Logika aktualizacji ceny
            if markup_percent is not None:
                product['markup_percent'] = float(markup_percent)
                original_price = product.get('original_price', 0)
                product['price'] = round(original_price * (1 + float(markup_percent) / 100), 2)
            elif price is not None:
                product['price'] = float(price)
                # Oblicz nowy narzut na podstawie podanej ceny
                original_price = product.get('original_price')
                if original_price and original_price > 0:
                    product['markup_percent'] = round(((float(price) / original_price) - 1) * 100, 2)
                else:
                    product['markup_percent'] = 0.0
            
            # Aktualizuj datę modyfikacji
            product['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Zapisz zmiany
            self.logger.info(f"Próba zapisu produktu {product.get('name')} (ID: {product_id}) do bazy danych")
            save_result = self._save_to_db()
            if save_result:
                self.logger.info(f"Produkt {product.get('name')} (ID: {product_id}) został zaktualizowany")
                return True
            else:
                self.logger.error(f"Nie udało się zapisać produktu {product.get('name')} (ID: {product_id}) do bazy danych")
                return False
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji produktu (ID: {product_id}): {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        
    def update_product_description(self, product_id, description):
        """
        Aktualizuje opis produktu w bazie danych.
        
        Args:
            product_id (str): ID produktu
            description (str): Nowy opis produktu w HTML
            
        Returns:
            bool: True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        try:
            # Znajdź produkt
            product = None
            for p in self.products:
                if str(p.get('id')) == str(product_id):
                    product = p
                    break
            
            if not product:
                self.logger.error(f"Nie znaleziono produktu o ID {product_id}")
                return False
            
            # Aktualizuj opis
            product['description'] = description
            
            # Aktualizuj datę modyfikacji
            product['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Zapisz zmiany
            self._save_to_db()
            self.logger.info(f"Opis produktu {product.get('name')} (ID: {product_id}) został zaktualizowany")
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji opisu produktu (ID: {product_id}): {str(e)}")
            return False
    
    def get_product_from_xml(self, product_id):
        """
        Pobiera dane produktu bezpośrednio z pliku XML na podstawie ID.
        
        Args:
            product_id (str): ID produktu do znalezienia
            
        Returns:
            dict: Słownik z danymi produktu z XML lub None, jeśli produkt nie został znaleziony
        """
        try:
            if not os.path.exists(self.xml_path):
                self.logger.error(f"Plik XML nie istnieje: {self.xml_path}")
                return None
                
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            
            # Znajdź produkt po ID
            for product_elem in root.findall('.//offer'):
                xml_id = self._safe_get_xml_value(product_elem, 'id')
                if xml_id and str(xml_id) == str(product_id):
                    # Mapuj dane z XML do słownika
                    product = {
                        'xml_id': xml_id,
                        'id': xml_id,
                        'name': self._safe_get_xml_value(product_elem, 'name'),
                        'EAN': self._safe_get_xml_value(product_elem, 'EAN'),
                        'producer': self._safe_get_xml_value(product_elem, 'producer'),
                        'url': self._safe_get_xml_value(product_elem, 'url'),
                        'category': self._safe_get_xml_value(product_elem, 'category'),
                    }
                    
                    # Pobierz obrazy produktu
                    product['images'] = []
                    pictures_elem = product_elem.find('pictures')
                    if pictures_elem is not None:
                        for pic_elem in pictures_elem.findall('picture'):
                            if pic_elem.text and pic_elem.text.strip():
                                product['images'].append(pic_elem.text.strip())
                    
                    # Ustaw pierwszy obraz jako główny
                    if product['images']:
                        product['image'] = product['images'][0]
                    else:
                        product['image'] = None
                    
                    try:
                        price_net_xml = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                        discounted_price_net_xml = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                        
                        if discounted_price_net_xml == 0:
                            discounted_price_net_xml = price_net_xml
                            
                        product['price'] = self._calculate_gross_price(discounted_price_net_xml)
                        product['regular_price'] = self._calculate_gross_price(price_net_xml)
                    except ValueError:
                        product['price'] = 0.0
                        product['regular_price'] = 0.0
                        
                    try:
                        product['stock'] = int(self._safe_get_xml_value(product_elem, 'stock', '0'))
                    except ValueError:
                        product['stock'] = 0
                        
                    return product
            
            self.logger.warning(f"Produkt o ID {product_id} nie został znaleziony w XML")
            return None
            
        except ET.ParseError as e:
            self.logger.error(f"Błąd parsowania XML ({self.xml_path}): {e}")
            return None
        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd podczas pobierania produktu z XML (ID: {product_id}): {str(e)}")
            return None
    
    def get_product_lists(self):
        """
        Zwraca listy produktów zapisane w pliku JSON.
        
        Returns:
            list: Lista słowników reprezentujących listy produktów.
        """
        try:
            if os.path.exists(self.PRODUCT_LISTS_FILE) and os.path.getsize(self.PRODUCT_LISTS_FILE) > 0:
                with open(self.PRODUCT_LISTS_FILE, 'r', encoding='utf-8') as f:
                    product_lists = json.load(f)
                self.logger.info(f"Załadowano {len(product_lists)} list produktów")
                return product_lists
            else:
                self.logger.warning(f"Plik list produktów nie istnieje lub jest pusty: {self.PRODUCT_LISTS_FILE}")
                return []
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania list produktów: {str(e)}")
            return []
    
    def get_product_list(self, list_id):
        """
        Zwraca pojedynczą listę produktów o podanym ID.
        
        Args:
            list_id (int): ID listy produktów do pobrania.
            
        Returns:
            dict: Słownik reprezentujący listę produktów lub None, jeśli nie znaleziono.
        """
        product_lists = self.get_product_lists()
        for product_list in product_lists:
            if product_list.get('id') == list_id:
                return product_list
        return None
    
    def save_product_list(self, name, description, products_ids, markup_percent, product_markups=None):
        """
        Zapisuje nową listę produktów.
        
        Args:
            name (str): Nazwa listy produktów.
            description (str): Opis listy produktów.
            products_ids (list): Lista ID produktów.
            markup_percent (float): Domyślny narzut procentowy dla wszystkich produktów na liście.
            product_markups (dict, optional): Słownik z indywidualnymi narzutami dla produktów {id: markup_percent}.
            
        Returns:
            dict: Zapisana lista produktów lub None w przypadku błędu.
        """
        try:
            # Załaduj istniejące listy
            product_lists = self.get_product_lists()
            
            # Wygeneruj nowe ID
            new_id = 1
            if product_lists:
                max_id = max(pl.get('id', 0) for pl in product_lists)
                new_id = max_id + 1
            
            # Przygotuj nową listę produktów
            new_product_list = {
                'id': new_id,
                'name': name,
                'description': description,
                'products_ids': products_ids,
                'markup_percent': float(markup_percent),
                'product_markups': product_markups or {},
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Dodaj do istniejących list
            product_lists.append(new_product_list)
            
            # Zapisz do pliku
            os.makedirs(os.path.dirname(self.PRODUCT_LISTS_FILE), exist_ok=True)
            with open(self.PRODUCT_LISTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(product_lists, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Zapisano nową listę produktów: {new_product_list['name']} (ID: {new_product_list['id']})")
            return new_product_list
        
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania listy produktów: {str(e)}")
            return None
        
    def update_product_list(self, list_id, data):
        """
        Aktualizuje istniejącą listę produktów.
        
        Args:
            list_id (int): ID listy produktów do aktualizacji.
            data (dict): Dane do aktualizacji.
            
        Returns:
            dict: Zaktualizowana lista produktów lub None w przypadku błędu.
        """
        try:
            product_lists = self.get_product_lists()
            
            for i, product_list in enumerate(product_lists):
                if product_list.get('id') == list_id:
                    # Aktualizuj dane
                    for key, value in data.items():
                        if key == 'markup_percent':
                            product_lists[i][key] = float(value)
                        else:
                            product_lists[i][key] = value
                    
                    # Zapisz do pliku
                    with open(self.PRODUCT_LISTS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(product_lists, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"Zaktualizowano listę produktów ID: {list_id}")
                    return product_lists[i]
            
            self.logger.warning(f"Nie znaleziono listy produktów o ID: {list_id} do aktualizacji")
            return None
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji listy produktów: {str(e)}")
            return None
    
    def delete_product_list(self, list_id):
        """
        Usuwa listę produktów o podanym ID.
        
        Args:
            list_id (int): ID listy produktów do usunięcia.
            
        Returns:
            bool: True jeśli usunięto, False w przypadku błędu.
        """
        try:
            product_lists = self.get_product_lists()
            initial_count = len(product_lists)
            
            # Filtrowanie listy, aby usunąć element z podanym ID
            product_lists = [pl for pl in product_lists if pl.get('id') != list_id]
            
            if len(product_lists) == initial_count:
                self.logger.warning(f"Nie znaleziono listy produktów o ID: {list_id} do usunięcia")
                return False
            
            # Zapisz zaktualizowaną listę do pliku
            with open(self.PRODUCT_LISTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(product_lists, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Usunięto listę produktów o ID: {list_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas usuwania listy produktów: {str(e)}")
            return False
    
    def get_xml_products_by_ids(self, product_ids):
        """
        Pobiera produkty z danymi z pliku XML na podstawie listy identyfikatorów.
        
        Args:
            product_ids (list): Lista identyfikatorów produktów.
            
        Returns:
            list: Lista produktów z danymi z XML.
        """
        result = []
        for product_id in product_ids:
            # Szukaj produktu najpierw w bazie danych
            product = next((p for p in self.products if str(p.get('id')) == str(product_id)), None)
            
            if product:
                # Sprawdź, czy produkt jest już w sklepie
                product['is_in_shop'] = product.get('available_for_sale', False)
                result.append(product)
        
        return result
    
    def get_all_products(self, include_unavailable=True):
        """
        Zwraca wszystkie produkty
        
        Args:
            include_unavailable (bool): Czy zwracać produkty niedostępne do sprzedaży
            
        Returns:
            list: Lista produktów
        """
        if include_unavailable:
            return self.products
        else:
            return [p for p in self.products if p.get('available_for_sale', False)]
    
    def get_product_by_id(self, product_id, include_unavailable=True):
        """
        Zwraca produkt o podanym ID
        
        Args:
            product_id (int): ID produktu
            include_unavailable (bool): Czy zwracać produkt niedostępny do sprzedaży
            
        Returns:
            dict: Znaleziony produkt lub None
        """
        product_id_str = str(product_id)
        for product in self.products:
            if str(product.get('id')) == product_id_str:
                if include_unavailable or product.get('available_for_sale', False):
                    return product
                break
        return None
    
    def get_product_by_slug(self, slug, include_unavailable=True):
        """
        Zwraca produkt o podanym slugu (przyjaznej nazwie)
        
        Args:
            slug (str): Slug produktu
            include_unavailable (bool): Czy zwracać produkt niedostępny do sprzedaży
            
        Returns:
            dict: Znaleziony produkt lub None
        """
        from app import slugify
        
        for product in self.products:
            product_slug = slugify(product.get('name', ''))
            if product_slug == slug:
                if include_unavailable or product.get('available_for_sale', False):
                    return product
                break
        return None
    
    def get_products_by_category(self, category, include_unavailable=False):
        """
        Zwraca produkty z danej kategorii
        
        Args:
            category (str): Nazwa kategorii
            include_unavailable (bool): Czy zwracać produkty niedostępne do sprzedaży
            
        Returns:
            list: Lista produktów z danej kategorii
        """
        # Przeszukaj zarówno po głównej kategorii jak i po ścieżce kategorii
        products = []
        for p in self.products:
            is_in_category = (p.get('category') == category or 
                            (p.get('category_path') and category in p.get('category_path')))
            
            if is_in_category and (include_unavailable or p.get('available_for_sale', False)):
                products.append(p)
                
        return products
    
    def get_categories(self):
        """Zwraca listę unikalnych kategorii"""
        return list(set(p.get('category') for p in self.products if p.get('category')))
    
    def get_category_tree(self):
        """
        Zwraca hierarchiczną strukturę kategorii w formie drzewa
        
        Returns:
            dict: Struktura drzewa kategorii
        """
        category_tree = {}
        
        for product in self.products:
            # Pobierz ścieżkę kategorii
            category_path = product.get('category_path', [])
            
            if not category_path:
                continue
                
            # Buduj drzewo kategorii
            current_level = category_tree
            for i, category in enumerate(category_path):
                if category not in current_level:
                    # Jeśli to ostatni element ścieżki, ustaw wartość na pustą listę
                    current_level[category] = {} if i < len(category_path) - 1 else {}
                
                # Przejdź do następnego poziomu
                current_level = current_level[category]
        
        return category_tree
    
    def get_main_categories(self):
        """
        Zwraca listę głównych kategorii (pierwszego poziomu)
        
        Returns:
            list: Lista głównych kategorii
        """
        categories = set()
        for product in self.products:
            category_path = product.get('category_path', [])
            if category_path and len(category_path) > 0:
                categories.add(category_path[0])
        
        return list(categories)
        
    def get_featured_categories(self):
        """
        Zwraca listę wyróżnionych kategorii do wyświetlenia w sekcji 'Popularne kategorie'
        
        Returns:
            list: Lista wyróżnionych kategorii
        """
        # Sprawdź czy istnieje plik konfiguracyjny
        config_path = os.path.join('data', 'featured_categories.json')
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Jeśli brak konfiguracji, domyślnie zwracamy pierwsze 4 kategorie
                return self.get_main_categories()[:4]
        except Exception as e:
            self.logger.error(f"Błąd podczas wczytywania wyróżnionych kategorii: {str(e)}")
            return self.get_main_categories()[:4]
    
    def save_featured_categories(self, categories):
        """
        Zapisuje listę wyróżnionych kategorii
        
        Args:
            categories (list): Lista nazw kategorii do wyróżnienia
            
        Returns:
            bool: True jeśli operacja zakończyła się powodzeniem, False w przeciwnym razie
        """
        config_path = os.path.join('data', 'featured_categories.json')
        
        try:
            # Ogranicz liczbę kategorii do 6
            if len(categories) > 6:
                categories = categories[:6]
                
            # Upewnij się, że katalog istnieje
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Zapisz konfigurację do pliku
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(categories, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Zapisano {len(categories)} wyróżnionych kategorii")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania wyróżnionych kategorii: {str(e)}")
            return False
        
    def get_recent_products(self, limit=20, days=None):
        """
        Zwraca ostatnio dodane produkty
        
        Args:
            limit (int): Maksymalna liczba produktów do zwrócenia
            days (int, optional): Liczba dni wstecz do sprawdzenia
            
        Returns:
            list: Lista produktów
        """
        # Pobierz wszystkie produkty i posortuj według daty dodania (jeśli istnieje)
        # Używamy bezpiecznej funkcji do sortowania, która radzi sobie z różnymi typami danych
        def get_sort_key(product):
            if not product:
                return '2000-01-01'
                
            added_at = product.get('added_at')
            
            # Jeśli added_at nie istnieje
            if added_at is None:
                return '2000-01-01'
                
            # Jeśli added_at jest liczbą (timestamp), użyj jej
            if isinstance(added_at, (int, float)):
                try:
                    # Konwertuj timestamp na string daty
                    return datetime.fromtimestamp(added_at).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError, OverflowError):
                    return '2000-01-01'
                    
            # Jeśli added_at jest stringiem (data), użyj go
            elif isinstance(added_at, str):
                return added_at
                
            # W przeciwnym razie użyj wartości domyślnej
            return '2000-01-01'
                
        # Użyj try-except aby zabezpieczyć się przed nieprzewidzianymi błędami
        try:
            sorted_products = sorted(
                self.products, 
                key=get_sort_key, 
                reverse=True
            )
        except Exception as e:
            self.logger.error(f"Błąd podczas sortowania produktów: {str(e)}")
            # Jeśli sortowanie się nie powiedzie, zwróć nieposortowaną listę
            sorted_products = self.products[:limit]
        
        # Jeśli określono liczbę dni, sprawdź tylko te produkty
        if days:
            today = datetime.now()
            filtered_products = []
            
            for product in sorted_products:
                if 'added_at' in product:
                    try:
                        # Sprawdź typ added_at
                        if isinstance(product['added_at'], str):
                            # Próbuj parsować jako datę
                            try:
                                added_date = datetime.strptime(product['added_at'], '%Y-%m-%d %H:%M:%S')
                                days_diff = (today - added_date).days
                                if days_diff <= days:
                                    filtered_products.append(product)
                            except (ValueError, TypeError):
                                # Jeśli nie można przetworzyć jako format stringa, dodaj produkt (lepiej pokazać więcej niż mniej)
                                filtered_products.append(product)
                        elif isinstance(product['added_at'], (int, float)):
                            # Jeśli to timestamp, konwertuj na datę
                            try:
                                added_date = datetime.fromtimestamp(product['added_at'])
                                days_diff = (today - added_date).days
                                if days_diff <= days:
                                    filtered_products.append(product)
                            except (ValueError, TypeError, OverflowError):
                                # Jeśli konwersja timestamp się nie powiodła, dodaj produkt
                                filtered_products.append(product)
                        else:
                            # Nieznany format, dodaj produkt na wszelki wypadek
                            filtered_products.append(product)
                    except Exception as e:
                        # W przypadku jakiegokolwiek błędu, dodaj produkt
                        self.logger.error(f"Błąd podczas przetwarzania daty produktu: {str(e)}")
                        filtered_products.append(product)
                else:
                    # Jeśli nie ma added_at, dodaj produkt (nie możemy filtrować po dacie)
                    filtered_products.append(product)
            
            # Zwróć tylko określoną liczbę produktów
            return filtered_products[:limit]
        
        # W przeciwnym razie po prostu zwróć ostatnio dodane produkty według limitu
        return sorted_products[:limit]
    
    def add_product(self, product_data):
        """
        Dodaje nowy, ręcznie wprowadzony produkt do bazy danych.
        Obsługuje ceny netto, marże i ceny brutto.
        """
        try:
            new_product_id = self._get_next_id()
            self.logger.info(f"Attempting to add new product with proposed ID: {new_product_id}")

            vat_rate = float(product_data.get('vat', self.VAT_RATE))
            
            # Podstawowe informacje o produkcie
            final_product_info = {
                'id': new_product_id,
                'xml_id': None, # Ręcznie dodane produkty nie mają xml_id
                'name': product_data.get('name'),
                'category': product_data.get('category'),
                'description': product_data.get('description', ''),
                'stock': int(product_data.get('stock', 0)),
                'available_for_sale': product_data.get('available_for_sale', True),
                'vat': vat_rate,
                'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Dodatkowe pola, które mogą być przekazane
            optional_fields = ['image', 'shipping_time', 'shipping_cost', 'custom_name', 
                               'custom_category', 'EAN', 'producer', 'url', 'uuid', 'category_path']
            for field in optional_fields:
                if field in product_data:
                    final_product_info[field] = product_data[field]
            
            if 'shipping_cost' in final_product_info and final_product_info['shipping_cost'] is not None:
                try:
                    final_product_info['shipping_cost'] = float(final_product_info['shipping_cost'])
                except ValueError:
                    self.logger.warning(f"Invalid shipping_cost value for new product: {final_product_info['shipping_cost']}")
                    final_product_info['shipping_cost'] = 0.0


            # Logika cenowa
            price_net_cost = product_data.get('price_net_cost') # Cena netto zakupu
            markup_percent = product_data.get('markup_percent') # Marża procentowa
            final_gross_price_direct = product_data.get('price') # Bezpośrednio podana cena sprzedaży brutto

            if price_net_cost is not None:
                price_net_cost = float(price_net_cost)
                # original_price to cena bazowa brutto (po VAT, przed marżą sklepu)
                base_gross_price = self._calculate_gross_price(price_net_cost, vat_rate)
                final_product_info['original_price'] = base_gross_price
                # Zapisujemy cenę netto zakupu w polu price_net_xml (lub dedykowanym polu price_net_cost)
                final_product_info['price_net_xml'] = price_net_cost 

                if markup_percent is not None:
                    markup_percent = float(markup_percent)
                    final_product_info['markup_percent'] = markup_percent
                    # Cena sprzedaży brutto = cena bazowa brutto * (1 + marża/100)
                    final_product_info['price'] = round(base_gross_price * (1 + markup_percent / 100), 2)
                elif final_gross_price_direct is not None:
                    # Podano cenę sprzedaży brutto i cenę netto zakupu, obliczamy marżę
                    final_gross_price_direct = float(final_gross_price_direct)
                    final_product_info['price'] = final_gross_price_direct
                    if base_gross_price > 0:
                        final_product_info['markup_percent'] = round(((final_gross_price_direct / base_gross_price) - 1) * 100, 2)
                    else:
                        final_product_info['markup_percent'] = 0.0 # Marża 0, jeśli cena bazowa 0
                else:
                    # Podano tylko cenę netto zakupu, marża 0%
                    final_product_info['markup_percent'] = 0.0
                    final_product_info['price'] = base_gross_price # Cena sprzedaży = cena bazowa brutto
            
            elif final_gross_price_direct is not None:
                # Podano tylko cenę sprzedaży brutto, brak informacji o koszcie netto
                final_gross_price_direct = float(final_gross_price_direct)
                final_product_info['price'] = final_gross_price_direct
                # Nie można wiarygodnie obliczyć marży ani ceny bazowej brutto (original_price)
                # Ustawiamy original_price na cenę sprzedaży (marża 0% od tej bazy)
                final_product_info['original_price'] = final_gross_price_direct
                final_product_info['markup_percent'] = 0.0
                final_product_info['price_net_xml'] = None # Brak informacji o koszcie netto
            else:
                # Brak jakichkolwiek informacji o cenie
                self.logger.warning(f"No price information provided for new product {final_product_info.get('name')}. Setting prices to 0.")
                final_product_info['price'] = 0.0
                final_product_info['original_price'] = 0.0
                final_product_info['markup_percent'] = 0.0
                final_product_info['price_net_xml'] = None

            # Upewnienie się, że kluczowe pola cenowe są floatami i istnieją
            for key in ['price', 'original_price', 'markup_percent']:
                final_product_info[key] = float(final_product_info.get(key, 0.0) or 0.0)
            
            if final_product_info.get('price_net_xml') is not None:
                final_product_info['price_net_xml'] = float(final_product_info['price_net_xml'])
            else: # Jeśli price_net_xml jest None, upewnij się, że tak pozostaje
                 final_product_info['price_net_xml'] = None


            self.products.append(final_product_info)
            if self._save_to_db():
                self.logger.info(f"Pomyślnie dodano nowy produkt ID: {final_product_info['id']}, Nazwa: {final_product_info.get('name')}")
                return final_product_info
            else:
                self.logger.error(f"Nie udało się zapisać bazy danych po dodaniu produktu ID: {final_product_info['id']}")
                # Potencjalnie usuń produkt z self.products, jeśli zapis się nie powiódł, aby uniknąć niespójności
                self.products = [p for p in self.products if p.get('id') != final_product_info['id']]
                return None

        except Exception as e:
            self.logger.error(f"Krytyczny błąd podczas dodawania produktu: {str(e)}", exc_info=True)
            return None
            
    def _get_next_id(self):
        """
        Generuje nowe ID dla produktu (jako string).
        Szuka maksymalnego ID numerycznego wśród istniejących produktów.
        """
        if not self.products:
            return "1"
        
        max_id_num = 0
        for p in self.products:
            try:
                # Próbuje przekonwertować ID na liczbę, jeśli jest numeryczne
                current_id_str = p.get('id')
                if current_id_str and str(current_id_str).isdigit():
                    current_id_num = int(current_id_str)
                    if current_id_num > max_id_num:
                        max_id_num = current_id_num
            except (ValueError, TypeError):
                continue # Ignoruj ID, które nie są numeryczne lub nie można ich przekonwertować
        
        return str(max_id_num + 1)
        
    def add_product_from_xml(self, product_id, markup_percent=0, available_for_sale=True):
        """
        Dodaje produkt z pliku XML do sklepu z określonymi parametrami.
        
        Args:
            product_id (str): ID produktu z XML
            markup_percent (float): Narzut procentowy na cenę bazową
            available_for_sale (bool): Czy produkt ma być dostępny do sprzedaży
            
        Returns:
            dict: Zaktualizowany produkt lub None w przypadku błędu
        """
        try:
            # Szukaj produktu w bazie danych
            product = None
            for p in self.products:
                if str(p.get('id')) == str(product_id) or str(p.get('xml_id')) == str(product_id):
                    product = p
                    break
            
            if not product:
                self.logger.error(f"Nie znaleziono produktu o ID {product_id} w bazie danych")
                return None
            
            # Aktualizuj produkt
            product['available_for_sale'] = available_for_sale
            product['markup_percent'] = float(markup_percent)
            
            # Oblicz nową cenę sprzedaży z uwzględnieniem narzutu
            original_price = product.get('original_price', 0)
            product['price'] = round(original_price * (1 + markup_percent / 100), 2)
            
            # Aktualizacja daty modyfikacji
            product['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Zapisz zmiany
            if self._save_to_db():
                self.logger.info(f"Produkt {product.get('name')} (ID: {product_id}) został zaktualizowany. "
                               f"Dostępność: {available_for_sale}, Narzut: {markup_percent}%")
                return product
            else:
                self.logger.error(f"Błąd podczas zapisywania produktu ID: {product_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania produktu z XML (ID: {product_id}): {str(e)}")
            return None
            
    def add_products_from_list(self, list_id):
        """
        Dodaje wszystkie produkty z danej listy do sklepu.
        
        Args:
            list_id (int): ID listy produktów
            
        Returns:
            list: Lista zaktualizowanych produktów lub pusta lista w przypadku błędu
        """
        try:
            # Pobierz listę produktów
            product_list = self.get_product_list(list_id)
            if not product_list:
                self.logger.error(f"Nie znaleziono listy produktów o ID {list_id}")
                return []
            
            # Pobierz parametry listy
            markup_percent = product_list.get('markup_percent', 0)
            product_ids = product_list.get('products_ids', [])
            product_markups = product_list.get('product_markups', {})
            
            updated_products = []
            for product_id in product_ids:
                # Jeśli dla produktu zdefiniowano indywidualny narzut, użyj go
                individual_markup = product_markups.get(str(product_id), markup_percent)
                
                # Zaktualizuj produkt
                updated_product = self.add_product_from_xml(product_id, individual_markup, True)
                if updated_product:
                    updated_products.append(updated_product)
            
            self.logger.info(f"Dodano {len(updated_products)} produktów z listy ID: {list_id}")
            return updated_products
            
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania produktów z listy (ID: {list_id}): {str(e)}")
            return []
    
    def get_published_products(self):
        """
        Zwraca wszystkie produkty dostępne do sprzedaży (opublikowane).
        
        Returns:
            list: Lista produktów dostępnych do sprzedaży.
        """
        return [p for p in self.products if p.get('available_for_sale', False)]
    
    def get_last_update(self):
        """
        Returns the timestamp of the last product update based on XML file modification time
        or None if the XML file doesn't exist.
        """
        try:
            if os.path.exists(self.xml_path):
                # Get the modification time of the XML file
                mod_time = os.path.getmtime(self.xml_path)
                # Convert to datetime object
                last_update = datetime.fromtimestamp(mod_time)
                return last_update.strftime('%Y-%m-%d %H:%M:%S')
            else:
                self.logger.warning(f"XML file does not exist: {self.xml_path}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting last update time: {str(e)}")
            return None