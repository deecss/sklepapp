import os
import time
import shutil
import threading
import logging

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='backup_manager.log',
    filemode='a'
)
logger = logging.getLogger('backup_manager')

class BackupManager:
    def __init__(self, interval_minutes=60):
        self.interval_minutes = interval_minutes
        self.db_path = os.path.join('data', 'products.json')
        self.backup_dir = os.path.join('data', 'backups')
        self.running = False
        self.thread = None
        
        # Utworzenie katalogu kopii zapasowych, jeśli nie istnieje
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def start(self):
        """Uruchamia automatyczne tworzenie kopii zapasowych"""
        if self.running:
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._backup_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Uruchomiono automatyczne tworzenie kopii zapasowych co {self.interval_minutes} minut")
        return True
        
    def stop(self):
        """Zatrzymuje automatyczne tworzenie kopii zapasowych"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        logger.info("Zatrzymano automatyczne tworzenie kopii zapasowych")
        return True
        
    def _backup_loop(self):
        """Pętla tworząca kopie zapasowe w określonych odstępach czasu"""
        while self.running:
            try:
                self.create_backup()
            except Exception as e:
                logger.error(f"Błąd podczas tworzenia kopii zapasowej: {str(e)}")
                
            # Czekaj określony czas przed utworzeniem kolejnej kopii
            for _ in range(self.interval_minutes * 60):
                if not self.running:
                    break
                time.sleep(1)
                
    def create_backup(self):
        """Tworzy kopię zapasową bazy danych produktów"""
        if not os.path.exists(self.db_path):
            logger.warning(f"Nie można utworzyć kopii zapasowej - plik {self.db_path} nie istnieje")
            return False
            
        # Format nazwy pliku kopii zapasowej: products_YYYYMMDD_HHMMSS.json
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"products_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Kopiowanie pliku
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Utworzono kopię zapasową: {backup_path}")
            
            # Usuń stare kopie zapasowe (zachowaj 10 najnowszych)
            self._cleanup_old_backups()
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia kopii zapasowej: {str(e)}")
            return False
            
    def _cleanup_old_backups(self, keep_count=10):
        """Usuwa stare kopie zapasowe, pozostawiając określoną liczbę najnowszych"""
        try:
            # Pobierz listę plików kopii zapasowych
            backup_files = [f for f in os.listdir(self.backup_dir) if f.startswith("products_") and f.endswith(".json")]
            
            # Sortuj według daty modyfikacji (od najstarszych do najnowszych)
            backup_files.sort(key=lambda f: os.path.getmtime(os.path.join(self.backup_dir, f)))
            
            # Usuń najstarsze kopie, pozostawiając określoną liczbę najnowszych
            files_to_delete = backup_files[:-keep_count] if len(backup_files) > keep_count else []
            
            for file in files_to_delete:
                file_path = os.path.join(self.backup_dir, file)
                os.remove(file_path)
                logger.info(f"Usunięto starą kopię zapasową: {file}")
                
        except Exception as e:
            logger.error(f"Błąd podczas czyszczenia starych kopii zapasowych: {str(e)}")
