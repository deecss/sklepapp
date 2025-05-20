# Sklep Internetowy (Flask + WebSocket + Tailwind)

Bardzo prosty sklep internetowy oparty na Flask, Flask-SocketIO (websocket) i Tailwind CSS. 

## Funkcje
- Lista produktów
- Szczegóły produktu
- Koszyk
- Zamówienie (przelew, pobranie)
- Potwierdzenie zamówienia
- Regulamin
- Polityka prywatności
- Kontakt

## Uruchomienie
1. Zainstaluj zależności:
   ```bash
   pip install flask flask-socketio eventlet
   npm install -D tailwindcss
   npx tailwindcss init
   ```
2. Uruchom aplikację:
   ```bash
   python app.py
   ```
3. Otwórz przeglądarkę i przejdź do `http://localhost:5000`

## Wygląd
Prosty, nowoczesny, responsywny (Tailwind CSS).

## TODO
- Integracja z XML do pobierania produktów (w kolejnych krokach)
