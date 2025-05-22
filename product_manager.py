import xml.etree.ElementTree as ET
import logging
import time # Dodane dla time.time()
import os
import json
from datetime import datetime, timedelta # Dodano timedelta

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
        Generuje nowe ID dla produktu
        
        Returns:
            int: Nowe ID produktu
        """
        if not self.products:
            return 1
        
        # Znajdź najwyższe ID i zwiększ o 1
        max_id = max(p.get('id', 0) for p in self.products)
        return max_id + 1
    
    def find_products(self, query, include_unavailable=False):
        """
        Wyszukuje produkty po nazwie lub opisie
        
        Args:
            query (str): Fraza do wyszukania
            include_unavailable (bool): Czy uwzględniać produkty niedostępne do sprzedaży
            
        Returns:
            list: Lista znalezionych produktów
        """
        query = query.lower()
        results = []
        
        for product in self.products:
            name = product.get('name', '').lower()
            description = product.get('description', '').lower()
            
            if (query in name or query in description) and (include_unavailable or product.get('available_for_sale', False)):
                results.append(product)
                
        return results
    
    def get_last_update(self):
        """Zwraca czas ostatniej aktualizacji"""
        return getattr(self, 'last_update', 'Nigdy')
        
    def search_xml_products(self, query, field='name', xml_path=None):
        """
        Wyszukiwanie produktów w pliku XML
        
        Args:
            query (str): Fraza do wyszukania
            field (str): Pole, w którym szukamy (name, id, EAN)
            xml_path (str, optional): Ścieżka do pliku XML
            
        Returns:
            list: Lista znalezionych produktów (tylko te ze stanem > 0)
        """
        if not query:
            return []
            
        if xml_path is None:
            xml_path = self.xml_path
            
        if not os.path.exists(xml_path):
            self.logger.error(f"Plik XML nie istnieje: {xml_path}")
            return []
            
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            results = []
            for product_elem in root.findall('.//offer'):
                # Sprawdzamy czy produkt pasuje do wyszukiwania
                if field == 'any':
                    # Szukanie w dowolnym polu
                    match = False
                    for search_field in ['id', 'name', 'EAN']:
                        field_value = self._safe_get_xml_value(product_elem, search_field, '').lower()
                        if query.lower() in field_value:
                            match = True
                            break
                    if not match:
                        continue
                else:
                    # Szukanie w konkretnym polu
                    field_value = self._safe_get_xml_value(product_elem, field, '').lower()
                    if query.lower() not in field_value:
                        continue
                
                # Sprawdź dostępność produktu
                try:
                    stock = int(self._safe_get_xml_value(product_elem, 'stock', '0'))
                    if stock <= 0:
                        continue
                except ValueError:
                    continue
                
                # Parsuj produkt
                product = {}
                product['id'] = self._safe_get_xml_value(product_elem, 'id')
                product['uuid'] = self._safe_get_xml_value(product_elem, 'uuid')
                product['name'] = self._safe_get_xml_value(product_elem, 'name')
                product['EAN'] = self._safe_get_xml_value(product_elem, 'EAN')
                product['producer'] = self._safe_get_xml_value(product_elem, 'producer')
                product['url'] = self._safe_get_xml_value(product_elem, 'url')
                
                # Obsługa kategorii
                category_text = self._safe_get_xml_value(product_elem, 'category')
                if category_text:
                    # Zamień encje HTML na znaki
                    category_text = category_text.replace('&amp;gt;', '>').replace('&gt;', '>')
                    categories = [cat.strip() for cat in category_text.split('>')]
                    product['category'] = categories[-1] if categories else ""
                    product['category_path'] = categories
                else:
                    product['category'] = "Bez kategorii"
                    product['category_path'] = ["Bez kategorii"]
                
                # Obsługa cen
                try:
                    product['price'] = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                    product['discounted_price'] = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                    if product['discounted_price'] == 0:
                        product['discounted_price'] = product['price']
                except ValueError:
                    product['price'] = 0
                    product['discounted_price'] = 0
                
                # Stan magazynowy
                product['stock'] = stock
                
                # Obsługa obrazków
                pictures_elem = product_elem.find('pictures')
                if pictures_elem is not None:
                    product['images'] = [pic.text for pic in pictures_elem.findall('picture') if pic.text]
                    product['image'] = product['images'][0] if product['images'] else None
                else:
                    product['images'] = []
                    product['image'] = None
                
                # Sprawdź czy produkt jest już dodany do sklepu
                product['is_in_shop'] = self._is_product_in_shop(product['id'])
                
                results.append(product)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wyszukiwania w pliku XML {xml_path}: {str(e)}")
            return []
    
    def _is_product_in_shop(self, xml_id):
        """Sprawdza czy produkt o danym XML ID jest już w sklepie"""
        for product in self.products:
            if product.get('xml_id') == xml_id:
                return True
        return False
    
    def add_product_from_xml(self, xml_product_id, markup_percent=0, available_for_sale=False, xml_path=None):
        """
        Dodaje produkt z XML do sklepu z zadanym narzutem procentowym.
        Cena z XML jest traktowana jako NETTO, najpierw doliczany jest VAT, potem narzut.
        """
        if xml_path is None:
            xml_path = self.xml_path
            
        if not os.path.exists(xml_path):
            self.logger.error(f"Plik XML nie istnieje: {xml_path}")
            return None
            
        try:
            # Znajdź produkt w XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            product_elem = root.find(f".//offer[id='{xml_product_id}']")
            if product_elem is None:
                self.logger.error(f"Nie znaleziono produktu o XML ID {xml_product_id} w pliku XML")
                return None

            # Sprawdź, czy produkt już istnieje w bazie sklepu
            existing_product = self.get_product_by_xml_id(xml_product_id)
            if existing_product:
                self.logger.info(f"Produkt o XML ID {xml_product_id} już istnieje w sklepie. ID: {existing_product['id']}")
                # Można by tu zaktualizować istniejący produkt zamiast zwracać None lub błąd
                # Na razie zwracamy None, aby uniknąć duplikatów przez tę funkcję
                return None 

            product = {}
            product['xml_id'] = xml_product_id
            
            # Mapowanie podstawowych pól
            product['name'] = self._safe_get_xml_value(product_elem, 'name')
            product['EAN'] = self._safe_get_xml_value(product_elem, 'EAN')
            product['producer'] = self._safe_get_xml_value(product_elem, 'producer')
            product['url'] = self._safe_get_xml_value(product_elem, 'url')
            product['uuid'] = self._safe_get_xml_value(product_elem, 'uuid')
            product['added_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Obsługa kategorii
            category_text = self._safe_get_xml_value(product_elem, 'category')
            if category_text:
                category_text = category_text.replace('&amp;gt;', '>').replace('&gt;', '>')
                categories = [cat.strip() for cat in category_text.split('>') if cat.strip()]
                product['category'] = categories[-1] if categories else "Bez kategorii"
                product['category_path'] = categories if categories else ["Bez kategorii"]
            else:
                product['category'] = "Bez kategorii"
                product['category_path'] = ["Bez kategorii"]
            
            # Obsługa cen z narzutem (cena z XML to NETTO)
            try:
                base_price_net_xml = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                if base_price_net_xml == 0:
                    base_price_net_xml = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                
                product['price_net_xml'] = base_price_net_xml

                # 1. Dolicz VAT do ceny netto z XML
                base_price_gross_xml = self._calculate_gross_price(base_price_net_xml)
                product['original_price'] = base_price_gross_xml # Cena brutto z XML (po VAT, przed narzutem sklepu)
                
                # 2. Dolicz narzut sklepu do ceny brutto z XML
                markup_multiplier = 1 + (float(markup_percent) / 100)
                final_price_with_markup = round(base_price_gross_xml * markup_multiplier, 2)
                
                product['price'] = final_price_with_markup # Finalna cena brutto (po VAT i po narzucie sklepu)
                product['markup_percent'] = float(markup_percent)

                # discounted_price powinno być równe cenie, chyba że jest specjalna promocja
                # Na razie ustawiamy równe finalnej cenie
                product['discounted_price'] = final_price_with_markup

            except ValueError:
                self.logger.error(f"Błąd konwersji ceny dla produktu XML ID {xml_product_id} przy dodawaniu.")
                product['price_net_xml'] = 0.0
                product['original_price'] = 0.0
                product['price'] = 0.0
                product['markup_percent'] = 0.0
                product['discounted_price'] = 0.0
            
            # VAT
            vat_xml = self._safe_get_xml_value(product_elem, 'tax')
            try:
                product['vat'] = int(vat_xml) if vat_xml else self.VAT_RATE
            except ValueError:
                product['vat'] = self.VAT_RATE

            # Ustaw dostępność
            product['available_for_sale'] = available_for_sale
            
            # Dodaj timestamp dodania
            product['added_at'] = time.time()
            
            # Stan magazynowy
            try:
                product['stock'] = int(self._safe_get_xml_value(product_elem, 'stock', '0'))
            except ValueError:
                product['stock'] = 0
            
            # Opis produktu (może być pobrany później lub z XML)
            product['description'] = self._safe_get_xml_value(product_elem, 'description', '') # Pobierz opis jeśli jest w <description>

            # Dodaj produkt do listy i przypisz ID sklepu
            # Znajdź następne dostępne ID numeryczne
            max_id = 0
            for p_existing in self.products:
                try:
                    if int(p_existing.get('id', 0)) > max_id:
                        max_id = int(p_existing.get('id', 0))
                except ValueError: # Ignoruj ID, które nie są liczbami
                    pass
            
            product['id'] = str(max_id + 1) # Nowe unikalne ID w sklepie

            self.products.append(product)
            self._save_to_db()
            
            self.logger.info(f"Dodano nowy produkt z XML ID {xml_product_id} do sklepu jako ID {product['id']} z narzutem {markup_percent}%.")
            return product

        except ET.ParseError as e:
            self.logger.error(f"Błąd parsowania XML ({xml_path}) przy dodawaniu produktu: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Nieoczekiwany błąd podczas dodawania produktu z XML ({xml_product_id}): {str(e)}")
            return None
    
    def update_product(self, product_id, price=None, vat=None, delivery_time=None, delivery_cost=None, markup_percent=None, available_for_sale=None, name=None, description=None, category_path=None, ean=None, producer=None, stock=None, custom_fields=None):
        """
        Aktualizuje dane produktu.
        Jeśli 'price' jest podane, jest to finalna cena brutto.
        Jeśli 'markup_percent' jest podane, cena jest przeliczana na podstawie 'original_price' (brutto z XML).
        """
        try:
            product_id_str = str(product_id)
            product_found = False
            for p in self.products:
                if str(p.get('id')) == product_id_str:
                    product = p
                    product_found = True
                    break
            
            if not product_found:
                self.logger.error(f"Nie znaleziono produktu o ID: {product_id_str}")
                return False
            
            # Aktualizuj pola produktu
            if name is not None:
                product['name'] = name
            if description is not None:
                product['description'] = description
            if category_path is not None and isinstance(category_path, list):
                product['category_path'] = category_path
                product['category'] = category_path[-1] if category_path else "Bez kategorii"
            if ean is not None:
                product['EAN'] = ean
            if producer is not None:
                product['producer'] = producer
            if stock is not None:
                try:
                    product['stock'] = int(stock)
                except ValueError:
                    self.logger.warning(f"Nieprawidłowa wartość dla stanu magazynowego: {stock} dla produktu ID {product_id_str}")


            if price is not None:
                try:
                    new_final_price = round(float(price), 2)
                    product['price'] = new_final_price
                    
                    # Jeśli produkt ma 'original_price' (cena brutto z XML przed narzutem sklepu)
                    # i jest ona większa od zera, możemy przeliczyć 'markup_percent'
                    if product.get('original_price') and float(product['original_price']) > 0:
                        original_gross_price = float(product['original_price'])
                        # (new_final_price / original_gross_price - 1) * 100 = markup_percent
                        new_markup = ((new_final_price / original_gross_price) - 1) * 100
                        product['markup_percent'] = round(new_markup, 2)
                    else:
                        # Jeśli nie ma original_price, nie możemy obliczyć narzutu,
                        # ale cena została ustawiona. Możemy wyzerować narzut lub zostawić.
                        # Dla spójności, jeśli cena jest ustawiana ręcznie, a nie ma bazy, narzut może być niejednoznaczny.
                        # Ustawmy narzut na None lub 0, jeśli nie można go wyliczyć.
                        product['markup_percent'] = 0.0 # lub None

                    # Aktualizujemy discounted_price, jeśli nie ma innej logiki promocyjnej
                    # Zakładamy, że jeśli cena jest aktualizowana, to discounted_price też powinna (chyba że jest promocja)
                    if product.get('discounted_price') == product.get('price') or not product.get('discounted_price'): # Proste założenie
                         product['discounted_price'] = new_final_price

                except ValueError:
                    self.logger.error(f"Nieprawidłowa wartość ceny dla produktu ID {product_id_str}: {price}")
                    return False

            # Jeśli podano nowy procent narzutu, przeliczamy cenę na podstawie 'original_price'
            elif markup_percent is not None: # Używamy elif, bo 'price' ma pierwszeństwo
                try:
                    markup_percent = float(markup_percent)
                    product['markup_percent'] = markup_percent
                    
                    if product.get('original_price') and float(product['original_price']) > 0:
                        original_gross_price = float(product['original_price'])
                        markup_multiplier = 1 + (markup_percent / 100)
                        new_final_price = round(original_gross_price * markup_multiplier, 2)
                        product['price'] = new_final_price
                        
                        # Aktualizujemy discounted_price
                        if product.get('discounted_price') == original_gross_price or not product.get('discounted_price'): # Proste założenie
                            product['discounted_price'] = new_final_price
                    else:
                        # Nie można obliczyć ceny na podstawie narzutu, jeśli brakuje original_price
                        self.logger.warning(f"Nie można zaktualizować ceny produktu ID {product_id_str} na podstawie narzutu, "
                                            f"ponieważ brakuje 'original_price' (ceny brutto z XML).")
                        # Cena nie jest zmieniana, tylko narzut jest zapisywany.
                except ValueError:
                    self.logger.error(f"Nieprawidłowa wartość procentowa narzutu dla produktu ID {product_id_str}: {markup_percent}")
                    return False
            
            if vat is not None:
                try:
                    product['vat'] = int(vat)
                except ValueError:
                     self.logger.warning(f"Nieprawidłowa wartość VAT: {vat} dla produktu ID {product_id_str}")
            if delivery_time is not None:
                product['delivery_time'] = delivery_time
            if delivery_cost is not None:
                try:
                    product['delivery_cost'] = round(float(delivery_cost), 2)
                except ValueError:
                    self.logger.warning(f"Nieprawidłowa wartość kosztu dostawy: {delivery_cost} dla produktu ID {product_id_str}")

            if available_for_sale is not None:
                product['available_for_sale'] = bool(available_for_sale)

            if custom_fields and isinstance(custom_fields, dict):
                for key, value in custom_fields.items():
                    product[key] = value
            
            product['updated_at'] = time.time() # Dodajemy znacznik czasu aktualizacji
            self._save_to_db()
            self.logger.info(f"Zaktualizowano produkt ID: {product_id_str}")
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji produktu ID {product_id_str}: {str(e)}")
            return False
    
    def toggle_product_availability(self, product_id, available=None):
        """
        Zmienia dostępność produktu na sprzedaż
        
        Args:
            product_id (int): ID produktu
            available (bool, optional): Nowy stan dostępności (jeśli None, to zmienia na przeciwny)
            
        Returns:
            dict: Zaktualizowany produkt lub None w przypadku błędu
        """
        try:
            # Znajdź produkt
            product = None
            for p in self.products:
                if p.get('id') == product_id:
                    product = p
                    break
            
            if not product:
                self.logger.error(f"Nie znaleziono produktu o ID {product_id}")
                return None
            
            # Ustaw dostępność
            if available is None:
                product['available_for_sale'] = not product.get('available_for_sale', True)
            else:
                product['available_for_sale'] = bool(available)
            
            # Zapisz zmiany
            self._save_to_db()
            
            status = "dostępny" if product['available_for_sale'] else "niedostępny"
            self.logger.info(f"Zmieniono dostępność produktu {product['name']} (ID: {product['id']}) na: {status}")
            return product
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zmiany dostępności produktu: {str(e)}")
            return None

    def get_product_list(self, list_id):
        """
        Zwraca konkretną listę produktów po ID
        
        Args:
            list_id (int): ID listy produktów
            
        Returns:
            dict: Lista produktów lub None jeśli nie znaleziono
        """
        lists = self.get_product_lists()
        for lst in lists:
            if lst.get('id') == list_id:
                return lst
        return None
        
    def update_product_list(self, list_id, list_data):
        """
        Aktualizuje listę produktów
        
        Args:
            list_id (int): ID listy produktów
            list_data (dict): Nowe dane listy
            
        Returns:
            dict: Zaktualizowana lista lub None w przypadku błędu
        """
        try:
            # Załaduj istniejące listy
            lists_path = os.path.join('data', 'product_lists.json')
            if not os.path.exists(lists_path):
                self.logger.error(f"Plik z listami produktów nie istnieje: {lists_path}")
                return None
                
            with open(lists_path, 'r', encoding='utf-8') as f:
                product_lists = json.load(f)
            
            # Znajdź listę do zaktualizowania
            for i, lst in enumerate(product_lists):
                if lst.get('id') == list_id:
                    # Aktualizuj dane
                    if 'name' in list_data:
                        product_lists[i]['name'] = list_data['name']
                    if 'description' in list_data:
                        product_lists[i]['description'] = list_data['description']
                    if 'markup_percent' in list_data:
                        product_lists[i]['markup_percent'] = list_data['markup_percent']
                    if 'products_ids' in list_data:
                        product_lists[i]['products_ids'] = list_data['products_ids']
                    if 'product_markups' in list_data:
                        product_lists[i]['product_markups'] = list_data['product_markups']
                    
                    # Zapisz zaktualizowane listy
                    with open(lists_path, 'w', encoding='utf-8') as f:
                        json.dump(product_lists, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"Zaktualizowano listę produktów '{product_lists[i]['name']}' (ID: {list_id})")
                    return product_lists[i]
            
            self.logger.error(f"Nie znaleziono listy produktów o ID {list_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji listy produktów: {str(e)}")
            return None
            
    def delete_product_list(self, list_id):
        """
        Usuwa listę produktów
        
        Args:
            list_id (int): ID listy produktów
            
        Returns:
            bool: True jeśli usunięto pomyślnie, False w przeciwnym razie
        """
        try:
            # Załaduj istniejące listy
            lists_path = os.path.join('data', 'product_lists.json')
            if not os.path.exists(lists_path):
                self.logger.error(f"Plik z listami produktów nie istnieje: {lists_path}")
                return False
                
            with open(lists_path, 'r', encoding='utf-8') as f:
                product_lists = json.load(f)
            
            # Znajdź i usuń listę
            for i, lst in enumerate(product_lists):
                if lst.get('id') == list_id:
                    del product_lists[i]
                    
                    # Zapisz zaktualizowane listy
                    with open(lists_path, 'w', encoding='utf-8') as f:
                        json.dump(product_lists, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"Usunięto listę produktów o ID {list_id}")
                    return True
            
            self.logger.error(f"Nie znaleziono listy produktów o ID {list_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Błąd podczas usuwania listy produktów: {str(e)}")
            return False
    
    def get_published_products(self):
        """
        Zwraca listę wystawionych (opublikowanych) produktów
        
        Returns:
            list: Lista wystawionych produktów
        """
        return [p for p in self.products if p.get('available_for_sale', False)]
        
    def get_xml_products_by_ids(self, product_ids, xml_path=None):
        """
        Zwraca szczegóły produktów z XML na podstawie listy ID
        
        Args:
            product_ids (list): Lista ID produktów
            xml_path (str, optional): Ścieżka do pliku XML
            
        Returns:
            list: Lista produktów z XML
        """
        if not product_ids:
            return []
            
        if xml_path is None:
            xml_path = self.xml_path
            
        if not os.path.exists(xml_path):
            self.logger.error(f"Plik XML nie istnieje: {xml_path}")
            return []
            
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            result_products = []
            
            for product_id in product_ids:
                # Znajdź produkt w XML
                product_elem = root.find(f".//offer[id='{product_id}']")
                if product_elem is None:
                    self.logger.warning(f"Nie znaleziono produktu o ID {product_id} w pliku XML")
                    continue
                
                # Parsuj produkt
                product = {}
                product['id'] = self._safe_get_xml_value(product_elem, 'id')
                product['uuid'] = self._safe_get_xml_value(product_elem, 'uuid')
                product['name'] = self._safe_get_xml_value(product_elem, 'name')
                product['EAN'] = self._safe_get_xml_value(product_elem, 'EAN')
                product['producer'] = self._safe_get_xml_value(product_elem, 'producer')
                product['url'] = self._safe_get_xml_value(product_elem, 'url')
                
                # Obsługa kategorii
                category_text = self._safe_get_xml_value(product_elem, 'category')
                if category_text:
                    # Zamień encje HTML na znaki
                    category_text = category_text.replace('&amp;gt;', '>').replace('&gt;', '>')
                    categories = [cat.strip() for cat in category_text.split('>')]
                    product['category'] = categories[-1] if categories else ""
                    product['category_path'] = categories
                else:
                    product['category'] = "Bez kategorii"
                    product['category_path'] = ["Bez kategorii"]
                
                # Obsługa cen
                try:
                    product['price'] = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                    product['discounted_price'] = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                    if product['discounted_price'] == 0:
                        product['discounted_price'] = product['price']
                except ValueError:
                    product['price'] = 0
                    product['discounted_price'] = 0
                
                # Stan magazynowy
                try:
                    product['stock'] = int(self._safe_get_xml_value(product_elem, 'stock', '0'))
                except ValueError:
                    product['stock'] = 0
                
                # Obsługa obrazków
                pictures_elem = product_elem.find('pictures')
                if pictures_elem is not None:
                    product['images'] = [pic.text for pic in pictures_elem.findall('picture') if pic.text]
                    product['image'] = product['images'][0] if product['images'] else None
                else:
                    product['images'] = []
                    product['image'] = None
                
                # Sprawdź czy produkt jest już dodany do sklepu
                product['is_in_shop'] = self._is_product_in_shop(product['id'])
                
                result_products.append(product)
            
            return result_products
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania produktów z XML: {str(e)}")
            return []

    def update_price_with_markup(self, product_id):
        """
        Aktualizuje cenę produktu na podstawie aktualnej ceny z XML (NETTO),
        dolicza VAT, a następnie stosuje zachowany procent narzutu sklepu.
        """
        try:
            product_id_str = str(product_id)
            product = None
            for p_item in self.products:
                if str(p_item.get('id')) == product_id_str:
                    product = p_item
                    break
            
            if not product:
                self.logger.error(f"Nie znaleziono produktu o ID: {product_id_str} do aktualizacji ceny z narzutem.")
                return False
            
            xml_id = product.get('xml_id')
            if not xml_id:
                self.logger.error(f"Produkt o ID {product_id_str} nie ma przypisanego XML ID. Nie można zaktualizować ceny z XML.")
                return False
            
            markup_percent = float(product.get('markup_percent', 0.0)) # Narzut sklepu
            
            # Pobierz aktualną cenę NETTO z XML
            if not os.path.exists(self.xml_path):
                self.logger.error(f"Plik XML nie istnieje: {self.xml_path}")
                return False

            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            
            product_elem = root.find(f".//offer[id='{xml_id}']")
            if product_elem is None:
                self.logger.error(f"Nie znaleziono produktu o XML ID {xml_id} w pliku XML do aktualizacji ceny.")
                return False
            
            try:
                new_base_price_net_xml = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                if new_base_price_net_xml == 0:
                    new_base_price_net_xml = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                
                # 1. Zaktualizuj cenę netto z XML w produkcie
                product['price_net_xml'] = new_base_price_net_xml
                
                # 2. Oblicz nową cenę brutto z XML (po VAT) - to będzie nowa 'original_price'
                new_base_price_gross_xml = self._calculate_gross_price(new_base_price_net_xml, product.get('vat', self.VAT_RATE))
                product['original_price'] = new_base_price_gross_xml
                
                # 3. Oblicz nową finalną cenę brutto z narzutem sklepu
                markup_multiplier = 1 + (markup_percent / 100)
                new_final_price = round(new_base_price_gross_xml * markup_multiplier, 2)
                
                product['price'] = new_final_price
                
                # Aktualizuj discounted_price, jeśli jest powiązana
                # Proste założenie: jeśli discounted_price było równe starej cenie brutto z XML, aktualizujemy je
                # Można to uszczegółowić w zależności od logiki promocji
                if product.get('discounted_price') == product.get('original_price') or product.get('discounted_price') == 0:
                     product['discounted_price'] = new_final_price
                
                product['updated_at'] = time.time()
                self._save_to_db()
                
                self.logger.info(f"Zaktualizowano cenę produktu ID: {product_id_str} (XML ID: {xml_id}) "
                                 f"na podstawie XML. Nowa cena netto XML: {new_base_price_net_xml}, "
                                 f"nowa cena brutto XML (original_price): {new_base_price_gross_xml}, "
                                 f"finalna cena z narzutem {markup_percent}%: {new_final_price}.")
                return True
            except ValueError as e:
                self.logger.error(f"Błąd podczas przetwarzania ceny produktu XML ID {xml_id}: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji ceny produktu ID {product_id_str} z narzutem: {str(e)}")
            return False

    def update_all_prices_with_markup(self):
        """
        Aktualizuje ceny wszystkich produktów, które mają zdefiniowany `xml_id` i `markup_percent`,
        na podstawie aktualnych cen z XML (NETTO + VAT) i zachowanych procentów narzutu sklepu.
        """
        updated_count = 0
        error_count = 0
        
        # Tworzymy kopię listy ID produktów do iteracji, aby uniknąć problemów z modyfikacją podczas iteracji
        product_ids_to_update = [p.get('id') for p in self.products if p.get('xml_id') and 'markup_percent' in p]

        for product_id in product_ids_to_update:
            if not product_id: continue # Pomiń jeśli ID jest None lub puste

            # Znajdź produkt po ID na świeżo, na wypadek gdyby lista self.products się zmieniła
            current_product = self.get_product_by_id(product_id)
            if not current_product:
                error_count +=1
                self.logger.warning(f"Nie znaleziono produktu o ID {product_id} podczas update_all_prices_with_markup.")
                continue

            # Pomiń produkty bez XML ID lub bez zapisanego narzutu (choć filtr wyżej powinien to załatwić)
            if not current_product.get('xml_id') or current_product.get('markup_percent') is None:
                continue
            
            success = self.update_price_with_markup(current_product.get('id'))
            if success:
                updated_count += 1
            else:
                error_count += 1
        
        if updated_count > 0 or error_count > 0:
             self._save_to_db() # Zapisz zmiany zbiorczo po wszystkich aktualizacjach
        
        self.logger.info(f"Zakończono aktualizację cen wszystkich produktów z narzutem. "
                         f"Zaktualizowano: {updated_count}, Błędów: {error_count}")
        return (updated_count, error_count)

    def add_custom_product(self, product_data):
        """
        Dodaje własny produkt do sklepu (bez korzystania z XML)
        
        Args:
            product_data (dict): Dane produktu (name, price, category, description, stock, image)
            
        Returns:
            dict: Dodany produkt lub None w przypadku błędu
        """
        try:
            # Utworzenie nowego produktu
            product = {
                'id': len(self.products) + 1,
                'custom': True,  # Oznaczenie, że to własny produkt
                'name': product_data.get('name', 'Nowy produkt'),
                'description': product_data.get('description', ''),
                'category': product_data.get('category', 'Inne'),
                'category_path': [product_data.get('category', 'Inne')],
                'price': float(product_data.get('price', 0)),
                'stock': int(product_data.get('stock', 0)),
                'image': product_data.get('image', None),
                'images': [product_data.get('image', None)] if product_data.get('image') else [],
                'added_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'available_for_sale': True  # Domyślnie produkt jest dostępny
            }
            
            # Dodaj produkt do bazy
            self.products.append(product)
            self._save_to_db()
            
            self.logger.info(f"Dodano własny produkt {product['name']} (ID: {product['id']})")
            return product
            
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania własnego produktu: {str(e)}")
            return None
    
    def update_product_description(self, product_id, description_html):
        """
        Aktualizuje opis produktu pobrany z zewnętrznej strony
        
        Args:
            product_id (str): ID produktu do aktualizacji
            description_html (str): HTML z opisem produktu
        
        Returns:
            bool: True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        try:
            # Znajdź produkt po ID
            product = None
            for p in self.products:
                if str(p.get('id')) == str(product_id):
                    product = p
                    break
            
            if not product:
                self.logger.error(f"Nie znaleziono produktu o ID: {product_id}")
                return False
            
            # Aktualizuj opis produktu
            product['description'] = description_html
            
            # Ustaw produkt jako dostępny do sprzedaży, jeśli jeszcze nie jest
            if not product.get('available_for_sale', False):
                product['available_for_sale'] = True
                self.logger.info(f"Produkt ID: {product_id} został automatycznie oznaczony jako dostępny po dodaniu opisu")
                
            # Zapisz zmiany w pliku JSON
            self._save_to_db()
            
            self.logger.info(f"Zaktualizowano opis produktu o ID: {product_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji opisu produktu {product_id}: {str(e)}")
            return False
            
    def get_product_from_xml(self, product_id):
        """
        Pobiera dane produktu z pliku XML na podstawie ID
        
        Args:
            product_id (str): ID produktu do pobrania
        
        Returns:
            dict: Dane produktu z XML lub None, jeśli nie znaleziono
        """
        try:
            # Sprawdź, czy mamy wczytane dane XML
            if not hasattr(self, 'xml_products') or not self.xml_products:
                self.parse_xml()
                
            if not self.xml_products:
                self.logger.error("Brak produktów XML")
                return None
                
            # Znajdź produkt po ID
            for product in self.xml_products:
                if str(product.get('id')) == str(product_id):
                    return product
                    
            self.logger.warning(f"Nie znaleziono produktu o ID {product_id} w XML")
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania produktu z XML {product_id}: {str(e)}")
            return None
