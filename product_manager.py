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
                # Najpierw zapisujemy do pliku tymczasowego
                temp_db_path = f"{self.db_path}.tmp"
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                
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
                        os.replace(self.db_path, backup_path)
                    except Exception as e:
                        self.logger.warning(f"Nie udało się utworzyć kopii zapasowej: {str(e)}")
                
                # Przemianowujemy plik tymczasowy na właściwy
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
                    
                return True
            except Exception as e:
                self.logger.error(f"Błąd podczas zapisywania produktów do bazy danych: {str(e)}")
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

                    product['price'] = price_gross_xml # Cena brutto (po VAT, przed dodatkowym narzutem sklepu)
                    product['discounted_price'] = discounted_price_gross_xml # Cena promocyjna brutto (po VAT)
                    
                    # original_price to cena brutto z XML, która będzie bazą do dalszych narzutów sklepowych
                    product['original_price'] = price_gross_xml 
                    
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
                        for field in ['delivery_time', 'delivery_cost', 'custom_name', 'custom_category']: # Dodaj inne pola wg potrzeb
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
            self._save_to_db()
            self.logger.info(f"Produkt {product.get('name')} (ID: {product_id}) został zaktualizowany")
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji produktu (ID: {product_id}): {str(e)}")
            return False
        
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