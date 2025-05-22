import hashlib
import os
import json
import time
from functools import wraps
from flask import request, redirect, url_for, session, flash

# Klasa obsługująca uwierzytelnianie administratora
class AdminAuth:
    def __init__(self, app=None):
        self.app = app
        
        # Lista użytkowników
        self.users = [
            {
                "username": "admin",
                "password_hash": self._hash_password("admin123"),
                "role": "admin",
                "created_at": time.time()
            }
        ]
        
        # Lista zapisanych zamówień
        self.orders = []
        
        # Statystyki
        self.stats = {
            "total_orders": 0,
            "total_revenue": 0,
            "most_popular_product": None
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        
        # Tu można dodać inicjalizację z pliku konfiguracyjnego lub bazy danych
        self._load_data()
    
    def _load_data(self):
        """Ładuje dane z pliku JSON"""
        try:
            if os.path.exists('data/admin_data.json'):
                with open('data/admin_data.json', 'r') as f:
                    data = json.load(f)
                    self.users = data.get('users', self.users)
                    self.orders = data.get('orders', self.orders)
                    self.stats = data.get('stats', self.stats)
        except Exception as e:
            print(f"Błąd podczas ładowania danych: {e}")
    
    def _save_data(self):
        """Zapisuje dane do pliku JSON"""
        try:
            os.makedirs('data', exist_ok=True)
            with open('data/admin_data.json', 'w') as f:
                json.dump({
                    'users': self.users,
                    'orders': self.orders,
                    'stats': self.stats
                }, f, indent=2)
        except Exception as e:
            print(f"Błąd podczas zapisywania danych: {e}")
    
    def _hash_password(self, password):
        # Prosty mechanizm hashowania hasła (w produkcji należy użyć lepszego rozwiązania, np. bcrypt)
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, username, password):
        # Sprawdzenie, czy dane logowania są poprawne
        for user in self.users:
            if user['username'] == username:
                return user['password_hash'] == self._hash_password(password)
        return False
    
    def change_password(self, username, new_password):
        # Zmiana hasła użytkownika
        for user in self.users:
            if user['username'] == username:
                user['password_hash'] = self._hash_password(new_password)
                self._save_data()
                return True
        return False
    
    def add_user(self, username, password, role='user'):
        # Sprawdź, czy użytkownik o takiej nazwie już istnieje
        if any(user['username'] == username for user in self.users):
            return False
        
        # Dodaj nowego użytkownika
        self.users.append({
            'username': username,
            'password_hash': self._hash_password(password),
            'role': role,
            'created_at': time.time()
        })
        
        self._save_data()
        return True
    
    def delete_user(self, username):
        # Nie pozwól na usunięcie ostatniego administratora
        admin_count = sum(1 for user in self.users if user['role'] == 'admin')
        user_to_delete = next((user for user in self.users if user['username'] == username), None)
        
        if user_to_delete and user_to_delete['role'] == 'admin' and admin_count <= 1:
            return False
        
        # Usuń użytkownika
        self.users = [user for user in self.users if user['username'] != username]
        self._save_data()
        return True
    
    def get_users(self):
        # Pobierz listę użytkowników
        return self.users
    
    def login_required(self, f):
        # Dekorator do zabezpieczenia endpointów administracyjnych
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('admin_logged_in'):
                flash('Sesja wygasła. Zaloguj się ponownie.', 'warning')
                return redirect(url_for('admin_login', next=request.url))
            
            # Odśwież czas wygaśnięcia sesji przy każdym żądaniu
            session.modified = True
            
            return f(*args, **kwargs)
        return decorated_function
    
    def add_order(self, order_data):
        # Dodanie nowego zamówienia do listy
        # Używamy ID z order_data, jeśli istnieje, w przeciwnym razie generujemy nowe
        # W tym przypadku order_data['id'] jest już unikalnym UUID
        
        # Sprawdź czy zamówienie o tym ID już istnieje, aby uniknąć duplikatów
        if any(o.get('id') == order_data.get('id') for o in self.orders):
            self.app.logger.warning(f"Order with ID {order_data.get('id')} already exists. Skipping add.")
            return False # Lub zaktualizuj istniejące zamówienie

        self.orders.append(order_data) # Zapisujemy cały słownik order_data
        
        # Aktualizacja statystyk
        self.stats["total_orders"] = len(self.orders) # Poprawione liczenie
        self.stats["total_revenue"] += order_data.get("total", 0)
        
        # Aktualizacja najpopularniejszego produktu (logika może pozostać taka sama lub być uproszona)
        product_counts = {}
        for o in self.orders: # Przelicz na podstawie wszystkich zamówień
            for item in o.get("items", []):
                product_id = item.get("id") # Zakładamy, że item ma 'id'
                if product_id: # Upewnij się, że product_id istnieje
                    product_counts[product_id] = product_counts.get(product_id, 0) + 1
        
        if product_counts:
            # Znajdź produkt z największą liczbą wystąpień
            most_popular_id = max(product_counts, key=product_counts.get)
            # Możesz chcieć zapisać ID produktu lub jego nazwę, jeśli masz dostęp do ProductManager
            self.stats["most_popular_product"] = str(most_popular_id) 
        else:
            self.stats["most_popular_product"] = None
        
        self._save_data() # Zapisz dane po dodaniu zamówienia
        self.app.logger.info(f"Order {order_data.get('id')} added and data saved. Total orders: {len(self.orders)}")
        return True # Zwracamy True jeśli dodano pomyślnie

    def get_order(self, order_id):
        # Pobranie zamówienia po ID
        for order in self.orders:
            if str(order.get("id")) == str(order_id): # Porównujemy stringi dla pewności
                return order
        self.app.logger.warning(f"Order with ID {order_id} not found in self.orders.")
        return None
    
    def update_order_status(self, order_id, new_status):
        # Aktualizacja statusu zamówienia
        order_found = False
        for order in self.orders:
            if str(order.get("id")) == str(order_id):
                order["status"] = new_status
                order_found = True
                break
        if order_found:
            self._save_data() # Zapisz zmiany
            self.app.logger.info(f"Order {order_id} status updated to {new_status} and data saved.")
            return True
        self.app.logger.warning(f"Failed to update status for order {order_id}. Order not found.")
        return False
    
    def get_all_orders(self):
        # Pobranie wszystkich zamówień, posortowane od najnowszego
        sorted_orders = sorted(self.orders, key=lambda o: o.get('created_at', 0), reverse=True)
        self.app.logger.info(f"Retrieving all orders. Count: {len(sorted_orders)}")
        return sorted_orders
    
    def get_stats(self):
        # Pobranie statystyk
        return self.stats
    
    def user_exists(self, username):
        """Sprawdza czy użytkownik o podanej nazwie już istnieje"""
        return any(user['username'] == username for user in self.users)
    
    def get_all_users(self):
        """Zwraca listę wszystkich użytkowników"""
        return self.users
