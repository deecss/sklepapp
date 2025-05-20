import requests
import os
import time
import schedule
import logging
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='xml_downloader.log',
    filemode='a'
)

logger = logging.getLogger('xml_downloader')

def download_xml():
    """Pobiera plik XML z produktami i zapisuje go na dysku"""
    url = "https://ergo.enode.ovh/products.xml"
    xml_dir = "data"
    
    # Upewnij się, że katalog istnieje
    if not os.path.exists(xml_dir):
        os.makedirs(xml_dir)
        logger.info(f"Utworzono katalog {xml_dir}")
    
    # Nazwa pliku z aktualną datą i godziną
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(xml_dir, f"products_{timestamp}.xml")
    
    # Nazwa pliku dla najnowszej wersji
    latest_filename = os.path.join(xml_dir, "products_latest.xml")
    
    try:
        # Pobieranie pliku
        response = requests.get(url)
        response.raise_for_status()  # Sprawdza, czy nie ma błędu HTTP
        
        # Zapisywanie pliku z timestampem
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        # Zapisywanie pliku jako najnowszej wersji
        with open(latest_filename, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Pomyślnie pobrano i zapisano plik XML: {filename}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pobrano plik XML")
        
        # Czyszczenie starych plików (pozostaw 24 ostatnie pliki - 4 godziny)
        cleanup_old_files(xml_dir)
        
    except Exception as e:
        logger.error(f"Błąd podczas pobierania pliku XML: {str(e)}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Błąd: {str(e)}")

def cleanup_old_files(directory, keep_last=24):
    """Usuwa stare pliki XML, zachowując określoną liczbę najnowszych"""
    try:
        # Pobierz wszystkie pliki XML z katalogu
        files = [os.path.join(directory, f) for f in os.listdir(directory) 
                if f.startswith("products_") and f.endswith(".xml") and not f == "products_latest.xml"]
        
        # Sortuj według daty modyfikacji
        files.sort(key=lambda x: os.path.getmtime(x))
        
        # Usuń stare pliki
        for old_file in files[:-keep_last]:
            os.remove(old_file)
            logger.info(f"Usunięto stary plik: {old_file}")
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia starych plików: {str(e)}")

def main():
    # Pobierz XML od razu przy starcie
    download_xml()
    
    # Zaplanuj pobieranie co 10 minut
    schedule.every(10).minutes.do(download_xml)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Uruchomiono pobieranie XML co 10 minut")
    logger.info("Uruchomiono harmonogram pobierania XML co 10 minut")
    
    # Pętla główna
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
