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
        order_id = len(self.orders) + 1
        order = {
            "id": order_id,
            "data": order_data,
            "status": "nowe"
        }
        self.orders.append(order)
        
        # Aktualizacja statystyk
        self.stats["total_orders"] += 1
        self.stats["total_revenue"] += order_data.get("total", 0)
        
        # Aktualizacja najpopularniejszego produktu
        product_counts = {}
        for item in order_data.get("items", []):
            product_id = item.get("id")
            if product_id in product_counts:
                product_counts[product_id] += 1
            else:
                product_counts[product_id] = 1
        
        if product_counts:
            most_popular = max(product_counts.items(), key=lambda x: x[1])
            self.stats["most_popular_product"] = most_popular[0]
        
        return order_id
    
    def get_order(self, order_id):
        # Pobranie zamówienia po ID
        for order in self.orders:
            if order["id"] == order_id:
                return order
        return None
    
    def update_order_status(self, order_id, new_status):
        # Aktualizacja statusu zamówienia
        for order in self.orders:
            if order["id"] == order_id:
                order["status"] = new_status
                return True
        return False
    
    def get_all_orders(self):
        # Pobranie wszystkich zamówień
        return self.orders
    
    def get_stats(self):
        # Pobranie statystyk
        return self.stats
    
    def user_exists(self, username):
        """Sprawdza czy użytkownik o podanej nazwie już istnieje"""
        return any(user['username'] == username for user in self.users)
    
    def get_all_users(self):
        """Zwraca listę wszystkich użytkowników"""
        return self.users
