# Zarządzanie dostępnością produktów w sklepie

Ten dokument opisuje, jak zarządzać dostępnością produktów w sklepie internetowym.

## Wprowadzenie

Sklep wyświetla na stronie głównej oraz w kategoriach tylko te produkty, które mają ustawioną flagę `available_for_sale` na `true`. 
Produkty, które mają tę flagę ustawioną na `false`, nie są widoczne dla klientów.

## Narzędzia do zarządzania dostępnością

W systemie dostępne są dwa narzędzia do zarządzania dostępnością produktów:

1. **Panel administracyjny** - umożliwia zarządzanie dostępnością pojedynczych produktów przez interfejs graficzny
2. **Skrypt zarządzający** - umożliwia masowe zarządzanie dostępnością produktów przez wiersz poleceń

## Zarządzanie przez panel administracyjny

1. Zaloguj się do panelu administracyjnego
2. Przejdź do sekcji "Produkty"
3. Kliknij na przycisk "Dostępność" przy wybranym produkcie, aby zmienić jego status
4. Możesz również zaznaczyć wiele produktów i użyć przycisku "Zmień dostępność masowo"

## Zarządzanie przez skrypt

W katalogu głównym sklepu znajduje się skrypt `manage_product_availability.py`, który umożliwia masowe zarządzanie dostępnością produktów.

### Dostępne komendy:

#### Zliczanie produktów dostępnych do sprzedaży:
```bash
python3 manage_product_availability.py count
```

#### Resetowanie dostępności wszystkich produktów (ustawienie wszystkich jako niedostępne):
```bash
python3 manage_product_availability.py reset_all
```

#### Ustawianie dostępności produktów z danej kategorii:
```bash
# Ustawienie wszystkich produktów z kategorii "Okapy kuchenne" jako dostępne
python3 manage_product_availability.py set_category "Okapy kuchenne" true

# Ustawienie wszystkich produktów z kategorii "Elektronika" jako niedostępne
python3 manage_product_availability.py set_category "Elektronika" false
```

#### Ustawianie dostępności konkretnego produktu po ID:
```bash
# Ustawienie produktu o ID "FILTR-BR-R" jako dostępny
python3 manage_product_availability.py set_product "FILTR-BR-R" true

# Ustawienie produktu o ID "FILTR-BR-R" jako niedostępny
python3 manage_product_availability.py set_product "FILTR-BR-R" false
```

## Dobre praktyki

1. Przed masową zmianą dostępności produktów, zaleca się wykonanie kopii zapasowej bazy danych.
2. Skrypt automatycznie tworzy kopię zapasową przy użyciu komendy `reset_all`.
3. Zaleca się okresową kontrolę dostępności produktów, aby upewnić się, że tylko odpowiednie produkty są widoczne w sklepie.
4. Po wprowadzeniu zmian, upewnij się, że strona główna i kategorie wyświetlają właściwe produkty.

## Rozwiązywanie problemów

Jeśli po zmianie dostępności produktów nie widzisz oczekiwanych efektów:

1. Upewnij się, że aplikacja Flask została zrestartowana po wprowadzeniu zmian.
2. Sprawdź liczbę dostępnych produktów za pomocą komendy `count`.
3. Sprawdź logi aplikacji w poszukiwaniu błędów.
