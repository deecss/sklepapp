import xml.etree.ElementTree as ET
import json
import os
import time
from datetime import datetime
import logging
import threading  # Dodajemy obsługę wątków

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
        
        # Ścieżki do plików
        self.xml_path = os.path.join('data', 'products_latest.xml')
        self.db_path = os.path.join('data', 'products.json')
        
        # Lista produktów
        self.products = []
        
        # Dodajemy blokadę dla bezpiecznego zapisu wielowątkowego
        self.save_lock = threading.Lock()
        
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
            for product_elem in root.findall('.//offer'):
                product = {}
                
                # Bezpośrednie mapowanie pól
                product['id'] = self._safe_get_xml_value(product_elem, 'id')
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
                
                # Obsługa stanu magazynowego
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
                
                # Tylko produkty dostępne na magazynie
                if product['stock'] > 0:
                    new_products.append(product)
            
            # Zachowaj dostępność produktów i ich opisy z poprzedniej wersji
            restored_count = 0
            preserved_descriptions = 0
            if hasattr(self, 'products') and self.products:
                # Tworzymy mapę istniejących produktów dla szybkiego dostępu
                existing_products_map = {}
                for p in self.products:
                    if 'xml_id' in p:
                        existing_products_map[p['xml_id']] = p
                    else:
                        existing_products_map[str(p.get('id', ''))] = p
                
                # Przenosimy dostępność i opisy z istniejących produktów
                for new_product in new_products:
                    product_id = str(new_product.get('id', ''))
                    existing_product = existing_products_map.get(product_id)
                    
                    if existing_product:
                        # Zachowaj status dostępności
                        if existing_product.get('available_for_sale', False):
                            new_product['available_for_sale'] = True
                            restored_count += 1
                        
                        # Zachowaj opis produktu
                        if 'description' in existing_product and existing_product['description']:
                            new_product['description'] = existing_product['description']
                            preserved_descriptions += 1
                            
                        # Zachowaj inne istotne pola
                        for field in ['markup_percent', 'original_price']:
                            if field in existing_product:
                                new_product[field] = existing_product[field]
                
                self.logger.info(f"Zachowano dostępność dla {restored_count} produktów i {preserved_descriptions} opisów produktów")
            
            # Aktualizuj produkty
            self.products = new_products
            
            # Przechowaj produkty XML dla późniejszego użycia przez get_product_from_xml
            self.xml_products = new_products
            
            # Dodaj timestamp aktualizacji
            self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Zapisz do bazy danych
            self._save_to_db()
            
            self.logger.info(f"Pomyślnie sparsowano plik XML {xml_path}, znaleziono {len(new_products)} produktów")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas parsowania pliku XML {xml_path}: {str(e)}")
            return False
    
    def _safe_get_xml_value(self, elem, tag, default=None):
        """Bezpiecznie pobiera wartość z elementu XML"""
        child = elem.find(tag)
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
        Dodaje produkt z XML do sklepu z zadanym narzutem procentowym
        
        Args:
            xml_product_id (str): ID produktu w XML
            markup_percent (float): Procentowy narzut na cenę
            available_for_sale (bool): Czy produkt ma być dostępny do sprzedaży
            xml_path (str, optional): Ścieżka do pliku XML
            
        Returns:
            dict: Dodany produkt lub None w przypadku błędu
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
                self.logger.error(f"Nie znaleziono produktu o ID {xml_product_id} w pliku XML")
                return None
            
            # Sprawdź czy produkt już istnieje w bazie
            for existing_product in self.products:
                if existing_product.get('xml_id') == xml_product_id:
                    self.logger.info(f"Produkt o ID {xml_product_id} już istnieje w bazie")
                    return existing_product
            
            # Parsuj produkt
            product = {}
            product['xml_id'] = self._safe_get_xml_value(product_elem, 'id')
            product['id'] = len(self.products) + 1
            product['uuid'] = self._safe_get_xml_value(product_elem, 'uuid')
            product['name'] = self._safe_get_xml_value(product_elem, 'name')
            product['EAN'] = self._safe_get_xml_value(product_elem, 'EAN')
            product['producer'] = self._safe_get_xml_value(product_elem, 'producer')
            product['url'] = self._safe_get_xml_value(product_elem, 'url')
            product['added_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Obsługa kategorii
            category_text = self._safe_get_xml_value(product_elem, 'category')
            if category_text:
                category_text = category_text.replace('&amp;gt;', '>')
                categories = [cat.strip() for cat in category_text.split('>')]
                product['category'] = categories[-1] if categories else "Bez kategorii"
                product['category_path'] = categories
            else:
                product['category'] = "Bez kategorii"
                product['category_path'] = ["Bez kategorii"]
            
            # Obsługa cen z narzutem
            try:
                base_price = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                if base_price == 0:
                    base_price = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                
                # Dodaj narzut procentowy
                markup_multiplier = 1 + (markup_percent / 100)
                product['price'] = round(base_price * markup_multiplier, 2)
                product['original_price'] = base_price
                product['markup_percent'] = markup_percent
            except ValueError:
                product['price'] = 0
                product['original_price'] = 0
                product['markup_percent'] = 0
            
            # Ustaw dostępność
            product['available_for_sale'] = available_for_sale
            
            # Dodaj timestamp dodania
            product['added_at'] = time.time()
            
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
            
            # Dodaj produkt do bazy
            self.products.append(product)
            self._save_to_db()
            
            self.logger.info(f"Dodano produkt {product['name']} (ID: {product['id']}) z pliku XML")
            return product
            
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania produktu z XML: {str(e)}")
            return None
    
    def save_product_list(self, name, description, products_ids, markup_percent=0, product_markups=None):
        """
        Zapisuje listę produktów do późniejszego użycia
        
        Args:
            name (str): Nazwa listy
            description (str): Opis listy
            products_ids (list): Lista ID produktów z XML
            markup_percent (float): Domyślny narzut procentowy
            product_markups (dict, optional): Słownik zawierający indywidualne narzuty dla produktów {product_id: markup_percent}
            
        Returns:
            dict: Zapisana lista lub None w przypadku błędu
        """
        try:
            # Załaduj istniejące listy
            lists_path = os.path.join('data', 'product_lists.json')
            product_lists = []
            
            if os.path.exists(lists_path):
                with open(lists_path, 'r', encoding='utf-8') as f:
                    product_lists = json.load(f)
            
            # Utwórz nową listę
            new_list = {
                'id': len(product_lists) + 1,
                'name': name,
                'description': description,
                'products_ids': products_ids,
                'markup_percent': markup_percent,
                'product_markups': product_markups or {},
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Dodaj listę
            product_lists.append(new_list)
            
            # Zapisz listy
            os.makedirs(os.path.dirname(lists_path), exist_ok=True)
            with open(lists_path, 'w', encoding='utf-8') as f:
                json.dump(product_lists, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Zapisano listę produktów '{name}' z {len(products_ids)} produktami")
            return new_list
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania listy produktów: {str(e)}")
            return None
    
    def get_product_lists(self):
        """Zwraca wszystkie zapisane listy produktów"""
        lists_path = os.path.join('data', 'product_lists.json')
        
        if os.path.exists(lists_path):
            try:
                with open(lists_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Błąd podczas wczytywania list produktów: {str(e)}")
        
        return []
    
    def add_products_from_list(self, list_id):
        """
        Dodaje wszystkie produkty z listy do sklepu
        
        Args:
            list_id (int): ID listy produktów
            
        Returns:
            list: Lista dodanych produktów lub None w przypadku błędu
        """
        try:
            # Załaduj listy produktów
            lists = self.get_product_lists()
            
            # Znajdź listę
            product_list = None
            for lst in lists:
                if lst.get('id') == list_id:
                    product_list = lst
                    break
            
            if not product_list:
                self.logger.error(f"Nie znaleziono listy produktów o ID {list_id}")
                return None
            
            # Dodaj produkty
            added_products = []
            markup_percent = product_list.get('markup_percent', 0)
            product_markups = product_list.get('product_markups', {})
            
            for xml_id in product_list.get('products_ids', []):
                # Sprawdź czy produkt ma indywidualny narzut
                individual_markup = product_markups.get(xml_id, markup_percent)
                
                # Produkty dodawane z listy są domyślnie dostępne do sprzedaży
                product = self.add_product_from_xml(xml_id, individual_markup, available_for_sale=True)
                if product:
                    added_products.append(product)
            
            self.logger.info(f"Dodano {len(added_products)} produktów z listy '{product_list.get('name')}'")
            return added_products
            
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania produktów z listy: {str(e)}")
            return None

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
    
    def update_product(self, product_id, price=None, vat=None, delivery_time=None, delivery_cost=None, markup_percent=None):
        """
        Aktualizuje dane produktu
        
        Args:
            product_id (str): ID produktu do aktualizacji
            price (float, optional): Nowa cena produktu
            vat (int, optional): Nowa stawka VAT
            delivery_time (str, optional): Nowy czas dostawy
            delivery_cost (float, optional): Nowy koszt dostawy
            markup_percent (float, optional): Nowy procent narzutu
        
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
            
            # Aktualizuj pola produktu
            if price is not None:
                product['price'] = float(price)
                
                # Jeśli produkt ma XML ID i podana jest nowa cena, aktualizujemy narzut
                if product.get('xml_id') and product.get('original_price', 0) > 0:
                    original_price = product.get('original_price')
                    if original_price > 0:
                        # Oblicz nowy procent narzutu na podstawie ceny
                        new_markup = ((float(price) / original_price) - 1) * 100
                        product['markup_percent'] = round(new_markup, 2)
                
                # Jeśli nie ma promocyjnej ceny, ustaw ją taką samą jak podstawowa
                if product.get('discounted_price', 0) == 0 or product.get('discounted_price') == product.get('price'):
                    product['discounted_price'] = float(price)
            
            # Jeśli podano nowy procent narzutu, aktualizujemy cenę
            if markup_percent is not None and product.get('xml_id') and product.get('original_price', 0) > 0:
                product['markup_percent'] = float(markup_percent)
                markup_multiplier = 1 + (float(markup_percent) / 100)
                original_price = product.get('original_price')
                product['price'] = round(original_price * markup_multiplier, 2)
                
                # Jeśli nie ma promocyjnej ceny, ustaw ją taką samą jak podstawowa
                if product.get('discounted_price', 0) == 0 or product.get('discounted_price') == product.get('price'):
                    product['discounted_price'] = product['price']
            
            if vat is not None:
                product['vat'] = int(vat)
            
            if delivery_time:
                product['delivery_time'] = delivery_time
            
            if delivery_cost is not None:
                product['delivery_cost'] = float(delivery_cost)
            
            # Zapisz zmiany w bazie danych
            self._save_to_db()
            
            self.logger.info(f"Zaktualizowano produkt ID: {product_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji produktu: {str(e)}")
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
        Aktualizuje cenę produktu na podstawie aktualnej ceny z XML i zachowanego procentu narzutu
        
        Args:
            product_id (str): ID produktu do aktualizacji
        
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
            
            # Pobierz XML ID produktu
            xml_id = product.get('xml_id')
            if not xml_id:
                self.logger.error(f"Produkt o ID {product_id} nie ma przypisanego XML ID")
                return False
            
            # Pobierz zapisany procent narzutu
            markup_percent = product.get('markup_percent', 0)
            
            # Pobierz aktualną cenę z XML
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            
            product_elem = root.find(f".//offer[id='{xml_id}']")
            if product_elem is None:
                self.logger.error(f"Nie znaleziono produktu o XML ID {xml_id} w pliku XML")
                return False
            
            # Pobierz aktualną cenę z XML
            try:
                new_base_price = float(self._safe_get_xml_value(product_elem, 'discounted_price', '0'))
                if new_base_price == 0:
                    new_base_price = float(self._safe_get_xml_value(product_elem, 'price', '0'))
                
                # Oblicz nową cenę z narzutem
                markup_multiplier = 1 + (markup_percent / 100)
                new_price = round(new_base_price * markup_multiplier, 2)
                
                # Aktualizuj cenę i zapisz oryginalną cenę
                product['price'] = new_price
                product['original_price'] = new_base_price
                
                # Jeśli nie ma promocyjnej ceny, ustaw ją taką samą jak podstawowa
                if product.get('discounted_price', 0) == 0 or product.get('discounted_price') == product.get('price'):
                    product['discounted_price'] = new_price
                
                # Zapisz zmiany w bazie danych
                self._save_to_db()
                
                self.logger.info(f"Zaktualizowano cenę produktu ID: {product_id} z narzutem {markup_percent}%")
                return True
            except ValueError as e:
                self.logger.error(f"Błąd podczas przetwarzania ceny produktu: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji ceny produktu z narzutem: {str(e)}")
            return False
    
    def update_all_prices_with_markup(self):
        """
        Aktualizuje ceny wszystkich produktów na podstawie aktualnych cen z XML i zachowanych procentów narzutu
        
        Returns:
            tuple: (int, int) - (liczba zaktualizowanych produktów, liczba błędów)
        """
        updated_count = 0
        error_count = 0
        
        for product in self.products:
            # Pomiń produkty bez XML ID lub bez narzutu
            if not product.get('xml_id') or product.get('markup_percent', 0) == 0:
                continue
            
            success = self.update_price_with_markup(product.get('id'))
            if success:
                updated_count += 1
            else:
                error_count += 1
        
        self.logger.info(f"Zaktualizowano ceny {updated_count} produktów, błędów: {error_count}")
        return (updated_count, error_count)
    
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
    
    def set_product_availability(self, product_id, is_available, emit_notification=True):
        """
        Ustawia dostępność produktu i emituje powiadomienie przez Socket.IO
        
        Args:
            product_id: ID produktu
            is_available (bool): Czy produkt jest dostępny
            emit_notification (bool): Czy emitować powiadomienie WebSocket
            
        Returns:
            bool: True jeśli operacja się powiodła, False w przeciwnym razie
        """
        try:
            product_id = str(product_id)
            product_found = False
            product_name = None
            
            # Aktualizacja w pamięci
            for p in self.products:
                if str(p.get('id')) == product_id:
                    old_status = p.get('available_for_sale', False)
                    p['available_for_sale'] = is_available
                    product_found = True
                    product_name = p.get('name', f'Produkt #{product_id}')
                    
                    # Zapisz log zmiany
                    status_change = "dostępny" if is_available else "niedostępny"
                    self.logger.info(f"Zmieniono status produktu {product_id} ({product_name}) na {status_change}")
                    break
            
            if not product_found:
                self.logger.warning(f"Nie znaleziono produktu o ID {product_id} do zmiany dostępności")
                return False
                
            # Zapisz zmiany do pliku JSON
            try:
                with open('data/products.json', 'w', encoding='utf-8') as f:
                    json.dump(self.products, f, ensure_ascii=False, indent=4)
            except Exception as e:
                self.logger.error(f"Błąd podczas zapisywania pliku JSON: {str(e)}")
                return False
                
            # Emituj powiadomienie przez Socket.IO
            if emit_notification:
                try:
                    # Import musi być tutaj, aby uniknąć problemów z cyklicznym importem
                    from app import notify_product_availability_change
                    notify_product_availability_change(product_id, is_available, product_name)
                except ImportError:
                    self.logger.warning(f"Nie można zaimportować notify_product_availability_change z app.py")
                except Exception as e:
                    self.logger.error(f"Błąd podczas emitowania powiadomienia Socket.IO: {str(e)}")
                    
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas ustawiania dostępności produktu: {str(e)}")
            return False
