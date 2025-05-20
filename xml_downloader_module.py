import requests
import os
import logging
import threading
import time
import schedule
import json
from datetime import datetime

class XmlDownloader:
    """Klasa do pobierania plików XML z produktami"""

    def __init__(self, interval_minutes=10):
        """Inicjalizacja z ustawionym interwałem w minutach"""
        self.interval = interval_minutes
        self.running = False
        self.thread = None
        self.config_path = os.path.join('data', 'xml_config.json')
        
        # Konfiguracja logowania
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='xml_downloader.log',
            filemode='a'
        )
        self.logger = logging.getLogger('xml_downloader')
        
        # Wczytaj konfigurację
        self._load_config()
        
        # Automatyczne uruchomienie harmonogramu, jeśli jest włączone
        if self.config.get('auto_start', False):
            self.start_scheduler()

    def _load_config(self):
        """Ładuje konfigurację z pliku JSON"""
        self.config = {
            'url': "https://ergo.enode.ovh/products.xml",
            'interval_minutes': self.interval,
            'auto_start': False,
            'last_download': None,
            'download_history': []
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                    self.interval = self.config['interval_minutes']
                    self.logger.info(f"Załadowano konfigurację z {self.config_path}")
            else:
                self._save_config()
                self.logger.info(f"Utworzono domyślną konfigurację w {self.config_path}")
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania konfiguracji: {str(e)}")
            self._save_config()
    
    def _save_config(self):
        """Zapisuje konfigurację do pliku JSON"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Zapisano konfigurację do {self.config_path}")
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania konfiguracji: {str(e)}")
    
    def update_config(self, new_config):
        """Aktualizuje konfigurację i zapisuje zmiany"""
        self.config.update(new_config)
        self.interval = self.config['interval_minutes']
        self._save_config()
        
        # Restart harmonogramu jeśli jest aktywny
        if self.running:
            self.stop_scheduler()
            self.start_scheduler()
        elif self.config.get('auto_start', False):
            self.start_scheduler()
            
        return self.config

    def download_xml(self):
        """Pobiera plik XML z produktami i zapisuje go na dysku"""
        url = self.config.get('url', "https://ergo.enode.ovh/products.xml")
        xml_dir = "data"
        
        # Upewnij się, że katalog istnieje
        if not os.path.exists(xml_dir):
            os.makedirs(xml_dir)
            self.logger.info(f"Utworzono katalog {xml_dir}")
        
        # Nazwa stałego pliku XML
        xml_filename = os.path.join(xml_dir, "products_latest.xml")
        
        # Aktualizacja czasu ostatniego pobrania
        self.config['last_download'] = datetime.now().isoformat()
        
        try:
            # Pobieranie pliku
            response = requests.get(url)
            response.raise_for_status()  # Sprawdza, czy nie ma błędu HTTP
            
            # Zapisywanie pliku (nadpisywanie istniejącego)
            with open(xml_filename, 'wb') as f:
                f.write(response.content)
                
            # Dodanie do historii pobrań
            self.config['download_history'].append({
                'timestamp': datetime.now().isoformat(),
                'filename': xml_filename,
                'success': True,
                'size_bytes': len(response.content)
            })
            
            # Ograniczenie historii do 100 ostatnich wpisów
            if len(self.config['download_history']) > 100:
                self.config['download_history'] = self.config['download_history'][-100:]
                
            # Zapisanie zaktualizowanej konfiguracji
            self._save_config()
                
            self.logger.info(f"Pomyślnie pobrano i zapisano plik XML: {xml_filename}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pobrano i zaktualizowano plik XML")
            
            return xml_filename
            
        except Exception as e:
            error_msg = f"Błąd podczas pobierania pliku XML: {str(e)}"
            
            # Dodanie do historii pobrań informacji o błędzie
            self.config['download_history'].append({
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            })
            
            # Zapisanie zaktualizowanej konfiguracji
            self._save_config()
            
            self.logger.error(error_msg)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Błąd: {str(e)}")
            return None

    def _scheduler_thread(self):
        """Wątek harmonogramu"""
        self.download_xml()  # Pobierz XML od razu
        
        # Zaplanuj pobieranie co X minut
        schedule.every(self.interval).minutes.do(self.download_xml)
        
        self.logger.info(f"Uruchomiono harmonogram pobierania XML co {self.interval} minut")
        
        # Pętla główna
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        """Uruchamia pobieranie XML w osobnym wątku"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_thread)
            self.thread.daemon = True  # Wątek zostanie zamknięty, gdy główny wątek się zakończy
            self.thread.start()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Uruchomiono pobieranie XML w tle co {self.interval} minut")
            return True
        return False

    def stop(self):
        """Zatrzymuje pobieranie XML"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1)
            self.logger.info("Zatrzymano harmonogram pobierania XML")
            return True
        return False

    def start_scheduler(self):
        """Uruchamia harmonogram pobierania XML"""
        if not self.running:
            self.running = True
            self.config['auto_start'] = True
            self._save_config()
            
            self.thread = threading.Thread(target=self._scheduler_thread)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info(f"Uruchomiono harmonogram pobierania XML co {self.interval} minut")
            return True
        return False
    
    def stop_scheduler(self):
        """Zatrzymuje harmonogram pobierania XML"""
        if self.running:
            self.running = False
            self.config['auto_start'] = False
            self._save_config()
            
            if self.thread:
                self.thread.join(timeout=1)
                
            self.logger.info("Zatrzymano harmonogram pobierania XML")
            return True
        return False
    
    def get_status(self):
        """Zwraca aktualny status modułu pobierania XML"""
        return {
            'running': self.running,
            'interval_minutes': self.interval,
            'config': self.config,
            'last_download': self.config.get('last_download'),
            'download_history': self.config.get('download_history', [])[-10:] # Ostatnie 10 wpisów
        }
