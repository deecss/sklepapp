"""
Payment Manager Module for the Flask-based e-commerce application
This module handles payment processing, status tracking, and confirmation.
"""

import json
import os
import time
import uuid
import logging
from datetime import datetime

class PaymentManager:
    """Klasa zarządzająca płatnościami w sklepie"""
    
    def __init__(self):
        """Inicjalizacja menedżera płatności"""
        # Konfiguracja logowania
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='payment_manager.log',
            filemode='a'
        )
        self.logger = logging.getLogger('payment_manager')
        
        # Ścieżki do plików danych
        self.db_path = os.path.join('data', 'payments.json')
        self.config_path = os.path.join('data', 'payment_config.json')
        
        # Lista płatności
        self.payments = []
        
        # Konfiguracja płatności
        self.config = {
            'bank_transfer': {
                'enabled': True,
                'account_number': '12 3456 7890 1234 5678 9012 3456',
                'account_owner': 'Sklep Internetowy Sp. z o.o.',
                'title_prefix': 'Zamówienie '
            },
            'cash_on_delivery': {
                'enabled': True,
                'fee': 12.99
            },
            'admin_email': 'admin@sklep.pl'
        }
        
        # Próba załadowania istniejących danych
        self._load_payments()
        self._load_config()
    
    def _load_payments(self):
        """Ładuje płatności z lokalnej bazy danych JSON"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.payments = json.load(f)
                self.logger.info(f"Załadowano {len(self.payments)} płatności z bazy danych")
            else:
                self.payments = []
                self.logger.info("Nie znaleziono pliku bazy danych płatności, utworzono pustą listę")
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania płatności z bazy danych: {str(e)}")
            self.payments = []
    
    def _save_payments(self):
        """Zapisuje płatności do lokalnej bazy danych JSON"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.payments, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Zapisano {len(self.payments)} płatności do bazy danych")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania płatności do bazy danych: {str(e)}")
            return False
    
    def _load_config(self):
        """Ładuje konfigurację płatności z pliku JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                self.logger.info(f"Załadowano konfigurację płatności z {self.config_path}")
            else:
                self._save_config()
                self.logger.info(f"Utworzono domyślną konfigurację płatności w {self.config_path}")
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania konfiguracji płatności: {str(e)}")
            self._save_config()
    
    def _save_config(self):
        """Zapisuje konfigurację płatności do pliku JSON"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Zapisano konfigurację płatności do {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania konfiguracji płatności: {str(e)}")
            return False
    
    def update_config(self, new_config):
        """Aktualizuje konfigurację płatności i zapisuje zmiany"""
        try:
            self.config.update(new_config)
            self._save_config()
            self.logger.info("Zaktualizowano konfigurację płatności")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji konfiguracji płatności: {str(e)}")
            return False
    
    def create_payment(self, order_id, amount, payment_method, customer_data=None):
        """
        Tworzy nową płatność
        
        Args:
            order_id (str): Identyfikator zamówienia
            amount (float): Kwota płatności
            payment_method (str): Metoda płatności ('bank_transfer' lub 'cash_on_delivery')
            customer_data (dict, optional): Dane klienta
        
        Returns:
            dict: Dane utworzonej płatności
        """
        try:
            payment_id = str(uuid.uuid4())
            
            payment = {
                'id': payment_id,
                'order_id': order_id,
                'amount': amount,
                'payment_method': payment_method,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'customer_data': customer_data,
                'history': [
                    {
                        'status': 'pending',
                        'timestamp': datetime.now().isoformat(),
                        'note': 'Płatność utworzona'
                    }
                ]
            }
            
            # Dodaj specyficzne dane dla metody płatności
            if payment_method == 'bank_transfer':
                payment['payment_details'] = {
                    'account_number': self.config['bank_transfer']['account_number'],
                    'account_owner': self.config['bank_transfer']['account_owner'],
                    'title': f"{self.config['bank_transfer']['title_prefix']}{order_id}"
                }
            elif payment_method == 'cash_on_delivery':
                payment['payment_details'] = {
                    'fee': self.config['cash_on_delivery']['fee'],
                    'total_amount': amount + self.config['cash_on_delivery']['fee']
                }
            
            self.payments.append(payment)
            self._save_payments()
            
            self.logger.info(f"Utworzono płatność {payment_id} dla zamówienia {order_id}")
            return payment
        except Exception as e:
            self.logger.error(f"Błąd podczas tworzenia płatności: {str(e)}")
            return None
    
    def update_payment_status(self, payment_id, new_status, note=None):
        """
        Aktualizuje status płatności
        
        Args:
            payment_id (str): Identyfikator płatności
            new_status (str): Nowy status płatności ('pending', 'paid', 'failed', 'refunded')
            note (str, optional): Dodatkowa notatka
        
        Returns:
            bool: True jeśli pomyślnie zaktualizowano status, False w przeciwnym razie
        """
        try:
            payment = self.get_payment(payment_id)
            if not payment:
                self.logger.error(f"Nie znaleziono płatności o ID {payment_id}")
                return False
            
            # Aktualizuj status
            payment['status'] = new_status
            payment['updated_at'] = datetime.now().isoformat()
            
            # Dodaj wpis do historii
            history_entry = {
                'status': new_status,
                'timestamp': datetime.now().isoformat()
            }
            
            if note:
                history_entry['note'] = note
            
            payment['history'].append(history_entry)
            
            # Zapisz zmiany
            self._save_payments()
            
            self.logger.info(f"Zaktualizowano status płatności {payment_id} na {new_status}")
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji statusu płatności: {str(e)}")
            return False
    
    def get_payment(self, payment_id):
        """
        Pobiera dane płatności na podstawie ID
        
        Args:
            payment_id (str): Identyfikator płatności
        
        Returns:
            dict: Dane płatności lub None, jeśli nie znaleziono
        """
        for payment in self.payments:
            if payment['id'] == payment_id:
                return payment
        return None
    
    def get_payment_by_order_id(self, order_id):
        """
        Zwraca płatność dla danego zamówienia
        
        Args:
            order_id (str): Identyfikator zamówienia
            
        Returns:
            dict: Dane płatności lub None
        """
        for payment in self.payments:
            if payment.get('order_id') == order_id:
                return payment
        return None
    
    def get_all_payments(self, status=None, limit=100, sort_by='created_at', sort_dir='desc'):
        """
        Pobiera listę płatności z możliwością filtrowania i sortowania
        
        Args:
            status (str, optional): Filtrowanie po statusie
            limit (int, optional): Maksymalna liczba zwracanych płatności
            sort_by (str, optional): Pole, po którym sortować
            sort_dir (str, optional): Kierunek sortowania ('asc' lub 'desc')
        
        Returns:
            list: Lista płatności
        """
        # Filtruj płatności po statusie, jeśli podano
        if status:
            filtered_payments = [p for p in self.payments if p['status'] == status]
        else:
            filtered_payments = self.payments.copy()
        
        # Sortuj płatności
        reverse = sort_dir.lower() == 'desc'
        filtered_payments.sort(key=lambda p: p.get(sort_by), reverse=reverse)
        
        # Ogranicz liczbę zwracanych płatności
        return filtered_payments[:limit]
