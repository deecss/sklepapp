#!/usr/bin/env python3
import os
import glob

def cleanup_old_xml_files():
    """
    Funkcja do czyszczenia starych plików XML.
    Zostawia tylko products_latest.xml i products.json
    """
    # Ścieżka do katalogu z danymi
    data_dir = os.path.join('data')
    
    # Sprawdź czy katalog istnieje
    if not os.path.exists(data_dir):
        print(f"Katalog {data_dir} nie istnieje")
        return
    
    # Znajdź wszystkie pliki XML zaczynające się od 'products_' oprócz 'products_latest.xml'
    xml_files = glob.glob(os.path.join(data_dir, 'products_*.xml'))
    latest_file = os.path.join(data_dir, 'products_latest.xml')
    
    # Usuń stare pliki XML, pozostawiając tylko products_latest.xml
    for file_path in xml_files:
        if os.path.basename(file_path) != 'products_latest.xml':
            try:
                os.remove(file_path)
                print(f"Usunięto stary plik: {file_path}")
            except Exception as e:
                print(f"Nie można usunąć pliku {file_path}: {str(e)}")

if __name__ == "__main__":
    print("Rozpoczynam czyszczenie starych plików XML...")
    cleanup_old_xml_files()
    print("Zakończono czyszczenie plików.")
