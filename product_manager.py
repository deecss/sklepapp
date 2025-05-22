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
            # Znajdź maksymalne istniejące ID numeryczne
            max_id = 0
            for p in self.products:
                try:
                    current_id = int(p.get('id', 0))
                    if current_id > max_id:
                        max_id = current_id
                except ValueError:
                    pass # Ignoruj ID, które nie są liczbami
            next_id = max_id + 1

        for product in self.products:
            if 'id' not in product or not product['id']: # Lub jeśli chcemy mieć osobne ID od xml_id
                product['id'] = str(next_id)
                next_id += 1
            # Upewnij się, że ID jest stringiem, jeśli konwertujemy z int
            product['id'] = str(product.get('id'))


    def _calculate_gross_price(self, net_price, vat_rate=None):
        """Oblicza cenę brutto na podstawie ceny netto i stawki VAT."""
        if vat_rate is None:
            vat_rate = self.VAT_RATE
        if net_price is None:
            return 0.0
        return round(float(net_price) * (1 + vat_rate / 100), 2)

    def _safe_get_xml_value(self, element, tag_name, default=''):
        """Bezpiecznie pobiera wartość z elementu XML"""
        child = element.find(tag_name)
        if child is not None and child.text is not None:
            return child.text
        return default
    
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
        for product in self.products:
            if product.get('id') == product_id:
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
        Dodaje nowy produkt do bazy danych
        
        Args:
            product_data (dict): Dane produktu
            
        Returns:
            dict: Dodany produkt z przydzielonym ID lub None w przypadku błędu
        """
        try:
            # Generuj nowe ID produktu
            product_id = self._get_next_id()
            
            # Przygotuj dane produktu
            new_product = {
                'id': product_id,
                'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                **product_data
            }
            
            # Dodaj produkt do listy
            self.products.append(new_product)
            
            # Zapisz zmiany w bazie danych
            self._save_to_db()
            
            self.logger.info(f"Dodano nowy produkt ID: {product_id}, Nazwa: {product_data.get('name')}")
            
            return new_product
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania produktu: {str(e)}")
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