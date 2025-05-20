import requests
from bs4 import BeautifulSoup
import os
import re
import time
import urllib.parse
import logging
import json
from concurrent.futures import ThreadPoolExecutor

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('product_descriptions.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('product_descriptions')

def fetch_description_from_url(product_manager, product_id, max_retries=3):
    """
    Pobiera opis produktu z URL zawartego w XML.
    
    Args:
        product_manager: Instancja ProductManager
        product_id: ID produktu, dla którego pobieramy opis
        max_retries: Maksymalna liczba ponownych prób w przypadku błędu
    
    Returns:
        dict: Słownik z kluczami 'success', 'description' i opcjonalnie 'message'
    """
    logger.info(f"Rozpoczynam pobieranie opisu dla produktu ID: {product_id}")
    try:
        # Pobierz produkt z XML
        logger.debug(f"Próba pobrania produktu {product_id} z XML...")
        xml_product = product_manager.get_product_from_xml(product_id)
        if not xml_product:
            logger.error(f"Produkt ID: {product_id} nie został znaleziony w XML")
            return {'success': False, 'message': 'Produkt nie został znaleziony w XML'}
        logger.debug(f"Znaleziono produkt w XML: {xml_product.get('name')}")
        
        # Pobierz URL produktu
        product_url = xml_product.get('url')
        if not product_url:
            logger.error(f"Produkt ID: {product_id} nie zawiera URL w danych XML")
            return {'success': False, 'message': 'Produkt nie zawiera URL w danych XML'}
        
        logger.info(f"Pobieranie strony z URL: {product_url}")
        
        # Próba pobrania strony
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Dodajemy User-Agent, żeby uniknąć blokowania jako bot
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml',
                    'Accept-Language': 'pl,en-US;q=0.9,en;q=0.8'
                }
                response = requests.get(product_url, headers=headers, timeout=15)
                response.raise_for_status()
                logger.info(f"Strona pobrana pomyślnie, status: {response.status_code}")
                break
            except requests.RequestException as e:
                retry_count += 1
                logger.warning(f"Próba {retry_count}/{max_retries} nieudana: {str(e)}")
                if retry_count >= max_retries:
                    logger.error(f"Nie udało się pobrać strony po {max_retries} próbach: {str(e)}")
                    return {'success': False, 'message': f'Błąd pobierania strony po {max_retries} próbach: {str(e)}'}
                # Czekaj przed kolejną próbą (zwiększający się czas)
                time.sleep(2 * retry_count)
        
        # Parsowanie HTML
        logger.info(f"Rozpoczynam parsowanie HTML dla produktu ID: {product_id}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Znajdź div z id="opis-import"
        logger.info(f"Szukam elementu div z id='opis-import' w HTML (długość: {len(response.text)} znaków)")
        opis_div = soup.find('div', id='opis-import')
        if not opis_div:
            logger.error(f"Nie znaleziono elementu div o id='opis-import' dla produktu ID: {product_id}")
            # Zapisz fragment HTML dla diagności
            sample_html = response.text[:1000] + "..." if len(response.text) > 1000 else response.text
            logger.info(f"Fragment HTML strony: {sample_html}")
            return {'success': False, 'message': 'Nie znaleziono elementu div o id="opis-import"'}
        
        # Pobierz HTML z diva
        description_html = str(opis_div)
        logger.info(f"Znaleziono opis dla produktu ID: {product_id}, długość HTML: {len(description_html)} znaków")
        
        # Pobierz i zapisz obrazy
        logger.info(f"Rozpoczynam pobieranie i zamianę obrazków dla produktu ID: {product_id}")
        description_html = download_and_replace_images(product_manager, description_html, product_id)
        
        logger.info(f"Zakończono generowanie opisu dla produktu ID: {product_id}")
        return {
            'success': True,
            'description': description_html
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania opisu produktu {product_id}: {str(e)}", exc_info=True)
        return {'success': False, 'message': f'Wystąpił błąd: {str(e)}'}

def download_and_replace_images(product_manager, html_content, product_id):
    """
    Pobiera obrazy z HTML i zastępuje ich URL-e lokalnymi ścieżkami.
    
    Args:
        product_manager: Instancja ProductManager
        html_content: Zawartość HTML z opisem produktu
        product_id: ID produktu
    
    Returns:
        str: Zaktualizowana zawartość HTML z lokalnymi ścieżkami do obrazów
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    logger.info(f"Znaleziono {len(images)} obrazków do pobrania dla produktu ID: {product_id}")
    
    # Sprawdź atrybuty obrazów w HTML
    for i, img in enumerate(images):
        logger.info(f"Obraz {i+1}: atrybuty = {img.attrs}")
    
    # Sprawdź ścieżkę roboczą
    current_dir = os.getcwd()
    logger.info(f"Katalog roboczy: {current_dir}")
    
    # Utwórz główny katalog dla obrazów
    img_folder = os.path.join(current_dir, 'static', 'uploads', 'products')
    os.makedirs(img_folder, exist_ok=True)
    os.chmod(img_folder, 0o755)
    logger.info(f"Utworzono/sprawdzono główny katalog obrazów: {img_folder}")

    # Utwórz katalog dla konkretnego produktu
    product_img_folder = os.path.join(img_folder, str(product_id))
    os.makedirs(product_img_folder, exist_ok=True)
    os.chmod(product_img_folder, 0o755)
    logger.info(f"Utworzono/sprawdzono katalog dla produktu: {product_img_folder}")

    for img in images:
        # Obsługa zarówno src jak i data-src (lazy loading)
        src = None
        if 'src' in img.attrs and img['src'] and not img['src'].startswith('data:'):
            src = img['src']
        elif 'data-src' in img.attrs and img['data-src']:
            src = img['data-src']
            
        if src:
            logger.info(f"Przetwarzanie obrazu: {src}")
            try:
                # Jeśli URL jest względny, dodaj bazowy URL
                if not src.startswith(('http://', 'https://')):
                    base_url = "https://janshop.pl"
                    src = urllib.parse.urljoin(base_url, src)
                    logger.info(f"Przekształcony URL względny na bezwzględny: {src}")
                
                # Pobierz obraz
                logger.info(f"Próba pobrania obrazu z URL: {src}")
                img_response = requests.get(src, timeout=10)
                img_response.raise_for_status()
                logger.info(f"Obraz pobrany pomyślnie: {len(img_response.content)} bajtów")
                
                # Wygeneruj nazwę pliku na podstawie oryginalnej ścieżki
                filename = os.path.basename(urllib.parse.urlparse(src).path)
                logger.info(f"Oryginalna nazwa pliku: {filename}")
                
                # Dodaj timestamp dla uniknięcia konfliktów nazw
                timestamp = int(time.time())
                name, ext = os.path.splitext(filename)
                if not ext or ext == '':  # Jeśli brak rozszerzenia, domyślnie .jpg
                    ext = '.jpg'
                    logger.info(f"Brak rozszerzenia, ustawiam domyślnie na .jpg")
                filename = f"{name}_{timestamp}{ext}"
                logger.info(f"Nowa nazwa pliku: {filename}")
                
                # Zapisz obraz - używaj pełnej ścieżki
                img_path = os.path.join(product_img_folder, filename)
                logger.info(f"Zapisuję obraz do: {img_path}")
                try:
                    with open(img_path, 'wb') as f:
                        f.write(img_response.content)
                    os.chmod(img_path, 0o644)  # Ustaw odpowiednie uprawnienia dla pliku
                    logger.info(f"Obraz zapisany pomyślnie: {os.path.exists(img_path)}, rozmiar: {os.path.getsize(img_path)} bajtów")
                except Exception as e:
                    logger.error(f"Błąd podczas zapisywania obrazu do {img_path}: {str(e)}")
                    continue
                
                # Zaktualizuj atrybut src w HTML
                new_src = f"/static/uploads/products/{product_id}/{filename}"
                
                # Obsługa zarówno src jak i data-src
                if 'src' in img.attrs:
                    logger.info(f"Aktualizuję atrybut src z '{img['src']}' na '{new_src}'")
                    img['src'] = new_src
                elif 'data-src' in img.attrs:
                    logger.info(f"Aktualizuję atrybut data-src z '{img['data-src']}' na '{new_src}'")
                    # Przy okazji dodajemy również normalny atrybut src
                    img['src'] = new_src
                    # Można usunąć data-src, ponieważ już nie jest potrzebny
                    del img['data-src']
                
                img['loading'] = 'lazy'  # Dodaj lazy loading dla obrazów
                
                logger.info(f"Przetworzono obraz pomyślnie: {filename}")
            except requests.RequestException as e:
                logger.error(f"Błąd podczas pobierania obrazu z {src}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd podczas przetwarzania obrazu {src}: {str(e)}")
                continue
    
    logger.info(f"Zakończono przetwarzanie obrazów dla produktu {product_id}")
    return str(soup)

def update_product_descriptions_batch(product_manager, product_ids, max_workers=4):
    """
    Aktualizuje opisy wielu produktów równolegle.
    
    Args:
        product_manager: Instancja ProductManager
        product_ids: Lista ID produktów do aktualizacji
        max_workers: Maksymalna liczba równoległych wątków
    
    Returns:
        dict: Wyniki operacji z liczbą zaktualizowanych i błędnych produktów
    """
    logger.info(f"Rozpoczynam aktualizację opisów dla {len(product_ids)} produktów")
    results = {
        'updated': 0,
        'errors': 0,
        'error_details': []
    }
    
    def process_product(product_id):
        result = fetch_description_from_url(product_manager, product_id)
        if result['success']:
            # Aktualizuj opis produktu
            success = product_manager.update_product_description(product_id, result['description'])
            if success:
                return {'success': True, 'product_id': product_id}
            else:
                return {'success': False, 'product_id': product_id, 'message': 'Nie udało się zaktualizować opisu produktu'}
        else:
            return {'success': False, 'product_id': product_id, 'message': result.get('message', 'Nieznany błąd')}
    
    # Użyj puli wątków do równoległego przetwarzania
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_results = {executor.submit(process_product, pid): pid for pid in product_ids}
        
        for future in future_results:
            try:
                result = future.result()
                if result['success']:
                    results['updated'] += 1
                else:
                    results['errors'] += 1
                    results['error_details'].append({
                        'product_id': result['product_id'],
                        'message': result.get('message', 'Nieznany błąd')
                    })
            except Exception as e:
                product_id = future_results[future]
                results['errors'] += 1
                results['error_details'].append({
                    'product_id': product_id,
                    'message': str(e)
                })
    
    return results
