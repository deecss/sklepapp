from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import time
import uuid
import json
from xml_downloader_module import XmlDownloader
from admin_auth import AdminAuth
from product_manager import ProductManager
from payment_manager import PaymentManager
from backup_manager import BackupManager

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'sklep-internetowy-staly-klucz-sesji'  # Stały klucz sesji
socketio = SocketIO(app)

# Ustawienie czasu trwania sesji na 24 godziny
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Inicjalizacja modułu pobierania XML
xml_downloader = XmlDownloader(interval_minutes=10)

# Inicjalizacja modułu autoryzacji administratora
admin_auth = AdminAuth(app)

# Inicjalizacja menedżera produktów
product_manager = ProductManager()

# Inicjalizacja menedżera płatności
payment_manager = PaymentManager()

# Funkcja do wyróżnienia wyszukiwanego tekstu
def highlight_text(text, query):
    """
    Wyróżnia wyszukiwaną frazę w tekście za pomocą HTML
    
    Args:
        text (str): Tekst do przetworzenia
        query (str): Fraza do wyróżnienia
        
    Returns:
        str: Tekst z wyróżnioną frazą
    """
    if not query or not text:
        return text
        
    # Zabezpieczenie przed wyjątkami
    try:
        # Zamiana na małe litery dla wyszukiwania niewrażliwego na wielkość
        text_lower = text.lower()
        query_lower = query.lower()
        
        if query_lower not in text_lower:
            return text
            
        # Znajdź indeksy wszystkich wystąpień frazy
        start_idx = 0
        indices = []
        while True:
            idx = text_lower.find(query_lower, start_idx)
            if idx == -1:
                break
            indices.append((idx, idx + len(query_lower)))
            start_idx = idx + 1
            
        # Jeśli nie znaleziono frazy, zwróć oryginalny tekst
        if not indices:
            return text
            
        # Zbuduj wynikowy HTML z wyróżnieniami
        result = []
        last_end = 0
        for start, end in indices:
            result.append(text[last_end:start])
            result.append(f'<span class="bg-yellow-100 font-semibold">{text[start:end]}</span>')
            last_end = end
        result.append(text[last_end:])
        
        return ''.join(result)
    except:
        return text
        
# Inicjalizacja menedżera kopii zapasowych
backup_manager = BackupManager(interval_minutes=60)
backup_manager.start()  # Uruchom automatyczne tworzenie kopii zapasowych

# Sprawdzenie integralności bazy danych produktów
def check_products_db_integrity():
    db_path = os.path.join('data', 'products.json')
    if not os.path.exists(db_path):
        app.logger.warning(f"Plik bazy danych produktów nie istnieje: {db_path}")
        return False
        
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
            available_count = sum(1 for p in products if p.get('available_for_sale'))
            app.logger.info(f"Baza danych produktów zawiera {len(products)} produktów, w tym {available_count} dostępnych do sprzedaży")
            return True
    except Exception as e:
        app.logger.error(f"Błąd podczas sprawdzania bazy danych produktów: {str(e)}")
        return False

# Sprawdź integralność bazy danych przy starcie
check_products_db_integrity()

# Wczytaj produkty z XML jeśli istnieje
product_manager.parse_xml()

# Dummy products
PRODUCTS = [
    {"id": 1, "name": "Smartfon XYZ", "price": 1299, "category": "Elektronika"},
    {"id": 2, "name": "Słuchawki bezprzewodowe", "price": 299, "category": "Elektronika"},
    {"id": 3, "name": "Koszulka sportowa", "price": 89, "category": "Odzież"},
    {"id": 4, "name": "Buty do biegania", "price": 249, "category": "Obuwie"},
    {"id": 5, "name": "Laptop 15.6\"", "price": 3499, "category": "Elektronika"},
    {"id": 6, "name": "Tablet 10\"", "price": 899, "category": "Elektronika"},
]

# Add custom timestamp to date filter
@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    if not timestamp:
        return "Nieznana"
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

@app.template_filter('format_datetime')
def format_datetime_filter(value, format='%Y-%m-%d %H:%M:%S'):
    """Formats a timestamp or datetime object into a string."""
    if value is None:
        return ""
    if isinstance(value, (int, float)): # Assuming it's a timestamp
        try:
            return datetime.fromtimestamp(value).strftime(format)
        except (TypeError, ValueError):
            return str(value) # Fallback if timestamp is invalid
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value) # Fallback for other types

# Add custom slugify filter for templates
@app.template_filter('slugify')
def slugify_filter(text):
    """Convert text to slug format for use in URLs"""
    return slugify(text)

@app.route('/admin/products-xml', methods=['GET'])
@admin_auth.login_required
def admin_products_xml():
    # Sprawdzenie czy istnieje najnowszy plik XML
    xml_exists = os.path.exists(product_manager.xml_path)
    lists = product_manager.get_product_lists()
    
    return render_template('admin_products_xml.html', 
                          xml_exists=xml_exists,
                          lists=lists)

@app.route('/admin/save-product-list', methods=['POST'])
@admin_auth.login_required
def save_product_list():
    data = request.get_json()
    
    if not data or 'name' not in data or 'products_ids' not in data:
        return jsonify({'success': False, 'message': 'Brak wymaganych pól'})
    
    name = data.get('name')
    description = data.get('description', '')
    products_ids = data.get('products_ids')
    markup_percent = float(data.get('markup_percent', 0))
    product_markups = data.get('product_markups', {})
    
    # Zapisz listę produktów
    product_list = product_manager.save_product_list(name, description, products_ids, markup_percent, product_markups)
    
    if product_list:
        return jsonify({
            'success': True, 
            'message': f'Lista produktów "{name}" została zapisana',
            'product_list': product_list
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Wystąpił błąd podczas zapisywania listy produktów'
        })

@app.route('/admin/get-product-lists', methods=['GET'])
@admin_auth.login_required
def get_product_lists():
    lists = product_manager.get_product_lists()
    return jsonify({
        'success': True,
        'lists': lists
    })

@app.route('/admin/add-products-from-list', methods=['POST'])
@admin_auth.login_required
def add_products_from_list():
    data = request.get_json()
    
    if not data or 'list_id' not in data:
        return jsonify({'success': False, 'message': 'Brak wymaganego pola list_id'})
    
    list_id = int(data.get('list_id'))
    
    # Dodaj produkty z listy
    products = product_manager.add_products_from_list(list_id)
    
    if products is not None:
        return jsonify({
            'success': True, 
            'message': f'Dodano {len(products)} produktów do sklepu',
            'products_count': len(products)
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Wystąpił błąd podczas dodawania produktów'
        })

# Endpoint do ręcznego odświeżenia produktów z XML
@app.route('/admin/refresh-xml', methods=['GET'])
@admin_auth.login_required
def refresh_xml():
    try:
        xml_file = xml_downloader.download_xml()
        if xml_file:
            # Parsuj XML po pobraniu
            if product_manager.parse_xml(xml_file):
                return jsonify({
                    'success': True, 
                    'message': 'Plik XML został pobrany i sparsowany pomyślnie',
                    'products_count': len(product_manager.get_all_products())
                })
            else:
                return jsonify({'success': False, 'message': 'Plik XML został pobrany, ale wystąpił błąd podczas parsowania'})
        else:
            return jsonify({'success': False, 'message': 'Wystąpił błąd podczas pobierania XML'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Błąd: {str(e)}'})

@app.route('/admin/update-product', methods=['POST'])
@admin_auth.login_required
def update_product():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        price = data.get('price')
        vat = data.get('vat')
        delivery_time = data.get('delivery_time')
        delivery_cost = data.get('delivery_cost')
        markup_percent = data.get('markup_percent')
        
        # Sprawdź, czy wszystkie wymagane dane są dostępne
        if not all([product_id, (price is not None or markup_percent is not None), vat is not None, delivery_time, delivery_cost is not None]):
            return jsonify({
                'success': False,
                'message': 'Brak wymaganych danych'
            })
        
        # Aktualizuj produkt
        success = product_manager.update_product(
            product_id=product_id,
            price=price,
            vat=vat,
            delivery_time=delivery_time,
            delivery_cost=delivery_cost,
            markup_percent=markup_percent
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Produkt został zaktualizowany'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się zaktualizować produktu'
            })
    except Exception as e:
        app.logger.error(f"Błąd podczas aktualizacji produktu: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd: {str(e)}'
        })

@app.route('/admin/bulk-update-products', methods=['POST'])
@admin_auth.login_required
def bulk_update_products():
    try:
        data = request.get_json()
        product_ids = data.get('product_ids', [])
        price_data = data.get('price', {})
        markup_data = data.get('markup', {})
        vat = data.get('vat')
        delivery_time = data.get('delivery_time')
        delivery_cost_data = data.get('delivery_cost', {})
        
        if not product_ids:
            return jsonify({
                'success': False,
                'message': 'Nie wybrano produktów do aktualizacji'
            })
        
        # Licznik pomyślnie zaktualizowanych produktów
        updated_count = 0
        
        # Aktualizuj każdy produkt
        for product_id in product_ids:
            # Pobierz aktualny produkt
            product = product_manager.get_product_by_id(product_id)
            if not product:
                continue
                
            # Przygotuj dane do aktualizacji
            update_data = {}
            
            # Aktualizacja narzutu
            if markup_data and markup_data.get('operation') and markup_data.get('value') is not None:
                current_markup = product.get('markup_percent', 0)
                operation = markup_data.get('operation')
                value = float(markup_data.get('value', 0))
                
                if operation == 'add':
                    update_data['markup_percent'] = current_markup + value
                elif operation == 'subtract':
                    update_data['markup_percent'] = max(0, current_markup - value)
                elif operation == 'set':
                    update_data['markup_percent'] = value
            
            # Aktualizacja ceny
            if price_data and price_data.get('operation') and price_data.get('value') is not None:
                current_price = product.get('price', 0)
                operation = price_data.get('operation')
                value = float(price_data.get('value', 0))
                
                if operation == 'add':
                    update_data['price'] = current_price + value
                elif operation == 'subtract':
                    update_data['price'] = max(0, current_price - value)
                elif operation == 'percent_increase':
                    update_data['price'] = current_price * (1 + value / 100)
                elif operation == 'percent_decrease':
                    update_data['price'] = current_price * (1 - value / 100)
                elif operation == 'set':
                    update_data['price'] = value
            
            # Aktualizacja VAT
            if vat is not None:
                update_data['vat'] = int(vat)
                
            # Aktualizacja czasu dostawy
            if delivery_time:
                update_data['delivery_time'] = delivery_time
                
            # Aktualizacja kosztu dostawy
            if delivery_cost_data and delivery_cost_data.get('operation') and delivery_cost_data.get('value') is not None:
                operation = delivery_cost_data.get('operation')
                value = float(delivery_cost_data.get('value', 0))
                
                if operation == 'set':
                    update_data['delivery_cost'] = value                # Aktualizuj produkt jeśli są jakieś dane do aktualizacji
                if update_data:
                    success = product_manager.update_product(
                        product_id=product_id,
                        price=update_data.get('price'),
                        vat=update_data.get('vat'),
                        delivery_time=update_data.get('delivery_time'),
                        delivery_cost=update_data.get('delivery_cost'),
                        markup_percent=update_data.get('markup_percent')
                    )
                    
                    if success:
                        updated_count += 1
        
        if updated_count > 0:
            return jsonify({
                'success': True,
                'message': f'Zaktualizowano {updated_count} produktów'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się zaktualizować żadnego produktu'
            })
    
    except Exception as e:
        app.logger.error(f"Błąd podczas masowej aktualizacji produktów: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd: {str(e)}'
        })

@app.route('/admin/update-prices-with-markup', methods=['POST'])
@admin_auth.login_required
def update_prices_with_markup():
    """Aktualizuje ceny wszystkich produktów na podstawie cen z XML i zapisanych narzutów"""
    try:
        updated_count, error_count = product_manager.update_all_prices_with_markup()
        
        return jsonify({
            'success': True,
            'message': f'Zaktualizowano ceny {updated_count} produktów, błędów: {error_count}'
        })
    except Exception as e:
        app.logger.error(f"Błąd podczas aktualizacji cen z narzutem: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd: {str(e)}'
        })

@app.route('/admin/update-product-price-with-markup', methods=['POST'])
@admin_auth.login_required
def update_product_price_with_markup():
    """Aktualizuje cenę pojedynczego produktu na podstawie ceny z XML i zapisanego narzutu"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({
                'success': False,
                'message': 'Nie podano ID produktu'
            })
        
        success = product_manager.update_price_with_markup(product_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Cena produktu została zaktualizowana na podstawie XML i narzutu'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się zaktualizować ceny produktu'
            })
    except Exception as e:
        app.logger.error(f"Błąd podczas aktualizacji ceny produktu z narzutem: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd: {str(e)}'
        })

@app.context_processor
def inject_common_data():
    """Dodaje wspólne dane do wszystkich szablonów"""
    # Pobierz hierarchiczną strukturę kategorii
    main_categories = product_manager.get_main_categories()
    category_tree = product_manager.get_category_tree()
    categories = product_manager.get_categories()
    featured_categories = product_manager.get_featured_categories()
    
    return {
        'main_categories': main_categories,
        'category_tree': category_tree,
        'categories': categories,
        'featured_categories': featured_categories
    }

@app.route('/')
def home():
    # Pokazujemy tylko produkty dostępne do sprzedaży
    products = product_manager.get_all_products(include_unavailable=False)
    
    # Kategorie już są dostępne przez context_processor
    return render_template('home.html', products=products)

@app.route('/kategoria/<path:category_path>')
def category(category_path):
    # Sprawdź czy to ścieżka podkategorii (zawiera /)
    if '/' in category_path:
        # Rozdziel ścieżkę na poszczególne kategorie
        categories_list = category_path.split('/')
        # Ostatnia kategoria jest tą, której produkty chcemy wyświetlić
        current_category = categories_list[-1]
    else:
        # Pojedyncza kategoria
        current_category = category_path
        categories_list = [current_category]
    
    # Pobierz produkty dla wybranej kategorii
    products = product_manager.get_products_by_category(current_category, include_unavailable=False)
    
    # Kategorie już są dostępne przez context_processor
    return render_template('category.html', 
                          products=products, 
                          current_category=current_category,
                          categories_list=categories_list)

@app.route('/produkt/<int:pid>')
def product(pid):
    product = product_manager.get_product_by_id(pid, include_unavailable=False)
    if not product:
        flash('Produkt nie został znaleziony lub nie jest dostępny do sprzedaży')
        return redirect(url_for('home'))
    return render_template('product.html', product=product)

@app.route('/produkt/<slug>')
def product_by_slug(slug):
    # Znajdź produkt po slug (przyjaznej nazwie)
    products = product_manager.get_all_products(include_unavailable=False)
    found_product = None
    for p in products:
        product_slug = slugify(p.get('name', ''))
        if product_slug == slug:
            found_product = p
            break
    
    if not found_product:
        flash('Produkt nie został znaleziony lub nie jest dostępny do sprzedaży')
        return redirect(url_for('home'))
    
    return render_template('product.html', product=found_product)

def slugify(text):
    """Funkcja tworząca przyjazny URL ze tekstu"""
    # Usunięcie znaków specjalnych, zamiana spacji na myślniki
    import re
    import unicodedata
    
    # Normalizacja znaków, zamiana polskich liter na standardowe
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    # Zamiana białych znaków na myślnik
    text = re.sub(r'[-\s]+', '-', text).strip('-_')
    return text

@app.route('/koszyk')
def cart():
    cart = session.get('cart', [])
    # Aktualizacja cen w koszyku z aktualnej bazy produktów
    for item in cart:
        product = product_manager.get_product_by_id(item['id'], include_unavailable=True)
        if product:
            item.update(product)
    return render_template('cart.html', cart=cart)

@app.route('/dodaj/<int:pid>')
def add_to_cart(pid):
    cart = session.get('cart', [])
    product = product_manager.get_product_by_id(pid, include_unavailable=False)
    if product:
        cart.append(product)
        session['cart'] = cart
    return redirect(url_for('cart'))

# Usunięta poprzednia implementacja ajax_add_to_cart
    
    # Oblicz podsumy
    subtotal = sum(item.get('price', 0) for item in cart)
    delivery_cost = sum(float(item.get('delivery_cost', 0) or 0) for item in cart)
    total = subtotal + delivery_cost
    
    # Emit WebSocket event
    socketio.emit('cart_update', {
        'count': len(cart),
        'sum': total
    })
    
    return jsonify({
        'success': True,
        'message': f'Dodano {quantity} sztuk produktu do koszyka',
        'cart_count': len(cart),
        'cart_sum': total
    })

# API endpoint do dodawania produktów do koszyka
@app.route('/api/dodaj/<int:pid>')
def api_add_to_cart(pid):
    cart = session.get('cart', [])
    product = product_manager.get_product_by_id(pid, include_unavailable=False)
    if product:
        cart.append(product)
        session['cart'] = cart
        
        # Oblicz podsumy
        subtotal = sum(item['price'] for item in cart)
        delivery_cost = sum(float(item.get('delivery_cost', 0)) for item in cart)
        total = subtotal + delivery_cost
        
        # Emit WebSocket event
        socketio.emit('cart_update', {
            'count': len(cart),
            'sum': total
        })
        
        return jsonify({
            'success': True,
            'cart_count': len(cart),
            'cart_sum': total
        })
    return jsonify({'success': False})

# API endpoint do usuwania produktów z koszyka
@app.route('/api/usun/<int:pid>')
def api_remove_from_cart(pid):
    cart = session.get('cart', [])
    
    # Znajdź i usuń pierwszy produkt o podanym ID
    for i, item in enumerate(cart):
        if item['id'] == pid:
            del cart[i]
            break
            
    session['cart'] = cart
    
    # Oblicz podsumy
    subtotal = sum(item['price'] for item in cart)
    delivery_cost = sum(float(item.get('delivery_cost', 0)) for item in cart)
    total = subtotal + delivery_cost
    
    # Emit WebSocket event
    socketio.emit('cart_update', {
        'count': len(cart),
        'sum': total
    })
    
    return jsonify({
        'success': True,
        'cart_count': len(cart),
        'cart_sum': total,
        'subtotal': subtotal,
        'delivery_cost': delivery_cost
    })

# API endpoint dla polecanych produktów
@app.route('/api/polecane-produkty')
def api_recommended_products():
    # W rzeczywistej aplikacji można by używać algorytmu rekomendacji
    # Na potrzeby demo zwracamy losowe 3 produkty
    import random
    products = product_manager.get_all_products(include_unavailable=False)
    if products:
        recommended = random.sample(products, min(3, len(products)))
        return jsonify({'products': recommended})
    return jsonify({'products': []})

@app.route('/promocje')
def promotions():
    # Przykładowa strona promocji
    return render_template('promotions.html')

@app.route('/nowosci')
def new_products():
    # Przykładowa strona nowości
    return render_template('new_products.html')

@app.route('/zamowienie', methods=['GET', 'POST'])
def order():
    cart = session.get('cart', [])
    
    if not cart:
        flash('Twój koszyk jest pusty. Dodaj produkty przed złożeniem zamówienia.', 'warning')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Oblicz podsumy
        subtotal = sum(item['price'] for item in cart)
        delivery_cost = sum(float(item.get('delivery_cost', 0)) for item in cart)
        total = subtotal + delivery_cost
        
        # Process the order form
        order_data = {
            'id': str(uuid.uuid4()),
            'customer': {
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'postcode': request.form.get('postcode'),
                'city': request.form.get('city')
            },
            'items': cart,
            'subtotal': subtotal,
            'delivery_cost': delivery_cost,
            'total': total,
            'payment_method': request.form.get('payment_method'),
            'status': 'new', # Initial status
            'created_at': datetime.now().timestamp()
        }
        
        # Process payment
        payment_method = request.form.get('payment_method')
        payment = payment_manager.create_payment(
            order_id=order_data['id'],
            amount=order_data['total'],
            payment_method=payment_method,
            customer_data=order_data['customer']
        )
        
        # Store payment ID in order
        order_data['payment_id'] = payment['id']
        
        # Save order using AdminAuth
        if admin_auth.add_order(order_data):
            app.logger.info(f"Order {order_data['id']} successfully added via admin_auth.add_order.")
        else:
            app.logger.error(f"Failed to add order {order_data['id']} via admin_auth.add_order.")

        # Store order in session for confirmation page
        session['last_order'] = order_data
        
        # Clear the cart
        session['cart'] = []
        
        # Redirect to confirmation page
        return redirect(url_for('confirmation', order_id=order_data['id']))
    
    # GET request - show order form
    payment_config = payment_manager.config
    return render_template('order.html', cart=cart, payment_config=payment_config)

@app.route('/potwierdzenie/<order_id>')
def confirmation(order_id):
    # Get order from session
    order = session.get('last_order')
    
    if not order or order['id'] != order_id:
        flash('Nie znaleziono zamówienia', 'error')
        return redirect(url_for('home'))
    
    # Get payment data
    payment = payment_manager.get_payment_by_order_id(order['id'])
    
    # Get payment method name for display
    payment_method_name = "Przelew bankowy"
    if order['payment_method'] == 'cash_on_delivery':
        payment_method_name = "Płatność za pobraniem"
    
    return render_template('confirmation.html', 
                           order=order, 
                           payment=payment,
                           payment_method_name=payment_method_name,
                           payment_manager=payment_manager) # Added payment_manager to context

@app.route('/regulamin')
def terms():
    return render_template('terms.html')

@app.route('/polityka-prywatnosci')
def privacy():
    return render_template('privacy.html')

@app.route('/kontakt', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Process the contact form
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Here you could save the message to a database or send an email
        # For now, just show a flash message
        flash(f'Dziękujemy za wiadomość, {name}! Odpowiemy jak najszybciej.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

@app.route('/admin')
def admin_panel():
    if 'admin_logged_in' in session and session['admin_logged_in']:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin.html')

# Zarządzanie panelem administracyjnym

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if admin_auth.verify_password(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            error = 'Nieprawidłowa nazwa użytkownika lub hasło'
    
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Wylogowano pomyślnie')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_auth.login_required
def admin_dashboard():
    stats = admin_auth.get_stats()
    products = product_manager.get_all_products(include_unavailable=True)
    
    # Calculate product availability statistics
    total_products = len(products)
    available_products = len([p for p in products if p.get('available_for_sale', False)])
    unavailable_products = total_products - available_products
    availability_percentage = round((available_products / total_products) * 100) if total_products > 0 else 0
    
    # Add product availability data to stats
    stats['product_stats'] = {
        'total': total_products,
        'available': available_products,
        'unavailable': unavailable_products,
        'availability_percentage': availability_percentage
    }
    
    # Pobierz ostatnie 5 zamówień
    recent_orders = admin_auth.get_all_orders()[-5:] if len(admin_auth.get_all_orders()) > 0 else []
    recent_orders.reverse()  # Odwróć kolejność, aby najnowsze były na górze
    return render_template('admin_dashboard.html', stats=stats, products=products, recent_orders=recent_orders)

@app.route('/admin/products')
@admin_auth.login_required
def admin_products():
    products = product_manager.get_all_products(include_unavailable=True)
    categories = product_manager.get_categories()
    last_update = product_manager.get_last_update()
    
    # Sprawdzenie czy istnieje najnowszy plik XML
    xml_exists = os.path.exists(product_manager.xml_path)
    
    return render_template('admin_products.html', 
                          products=products, 
                          categories=categories,
                          last_update=last_update,
                          xml_exists=xml_exists)

@app.route('/admin/product-listing', methods=['GET'])
@admin_auth.login_required
def product_listing():
    # Sprawdzenie czy istnieje najnowszy plik XML
    xml_exists = os.path.exists(product_manager.xml_path)
    
    # Pobierz listy produktów
    product_lists = product_manager.get_product_lists()
    
    return render_template('admin_product_listing.html', 
                          xml_exists=xml_exists,
                          product_lists=product_lists)

@app.route('/admin/search-xml-products', methods=['GET'])
@admin_auth.login_required
def search_xml_products():
    query = request.args.get('query', '')
    field = request.args.get('field', 'any')
    page = int(request.args.get('page', 1))
    per_page = 20  # Produktów na stronę
    
    # Wyszukaj produkty w XML
    results = product_manager.search_xml_products(query, field)
    
    # Oblicz dane do paginacji
    total_results = len(results)
    total_pages = (total_results + per_page - 1) // per_page
    
    # Wytnij odpowiedni fragment wyników
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_results = results[start_idx:end_idx]
    
    return jsonify({
        'success': True,
        'products': paged_results,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_results': total_results,
            'total_pages': total_pages
        }
    })

@app.route('/admin/add-product-from-xml', methods=['POST'])
@admin_auth.login_required
def add_product_from_xml():
    data = request.get_json()
    
    if not data or 'product_id' not in data:
        return jsonify({'success': False, 'message': 'Brak wymaganego pola product_id'})
    
    product_id = data.get('product_id')
    markup_percent = float(data.get('markup_percent', 0))
    available_for_sale = data.get('available_for_sale', True)
    
    # Dodaj produkt z XML do sklepu
    product = product_manager.add_product_from_xml(product_id, markup_percent, available_for_sale)
    
    if product:
        return jsonify({
            'success': True, 
            'message': f'Produkt "{product["name"]}" został dodany do sklepu',
            'product': product
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Wystąpił błąd podczas dodawania produktu'
        })

@app.route('/admin/toggle-product-availability', methods=['POST'])
@admin_auth.login_required
def toggle_product_availability():
    data = request.get_json()
    
    if not data or 'product_id' not in data:
        return jsonify({'success': False, 'message': 'Brak wymaganego pola product_id'})
    
    product_id = int(data.get('product_id'))
    available = data.get('available')  # Może być None, wtedy przełączy na przeciwny stan
    
    # Zmień dostępność produktu
    product = product_manager.toggle_product_availability(product_id, available)
    
    if product:
        status = "dostępny" if product.get('available_for_sale', False) else "niedostępny"
        # Sprawdź czy zmiany zostały zapisane
        db_path = os.path.join('data', 'products.json')
        if os.path.exists(db_path):
            flash(f'Produkt "{product["name"]}" jest teraz {status}. Zmiany zostały zapisane.', 'success')
        else:
            flash(f'Produkt został zaktualizowany, ale wystąpił problem z zapisem do bazy danych.', 'warning')
            
        return jsonify({
            'success': True, 
            'message': f'Produkt "{product["name"]}" jest teraz {status}',
            'product': product
        })
    else:
        flash(f'Wystąpił błąd podczas zmiany dostępności produktu.', 'error')
        return jsonify({
            'success': False, 
            'message': 'Wystąpił błąd podczas zmiany dostępności produktu'
        })

@app.route('/admin/bulk-toggle-availability', methods=['POST'])
@admin_auth.login_required
def bulk_toggle_availability():
    data = request.get_json()
    
    if not data or 'product_ids' not in data or 'available' not in data:
        return jsonify({'success': False, 'message': 'Brak wymaganych pól'})
    
    product_ids = data.get('product_ids', [])
    available = data.get('available')
    
    success_count = 0
    failed_ids = []
    
    for product_id in product_ids:
        product = product_manager.toggle_product_availability(int(product_id), available)
        if product:
            success_count += 1
        else:
            failed_ids.append(product_id)
    
    if len(failed_ids) == 0:
        return jsonify({
            'success': True,
            'message': f'Pomyślnie zaktualizowano dostępność {success_count} produktów'
        })
    else:
        return jsonify({
            'success': True,
            'message': f'Zaktualizowano {success_count} produktów, {len(failed_ids)} nie udało się zaktualizować',
            'failed_ids': failed_ids
        })

@app.route('/admin/product-simple-test', methods=['GET'])
@admin_auth.login_required
def product_simple_test():
    # Pobierz wszystkie produkty, włączając te niedostępne
    products = product_manager.get_all_products(include_unavailable=True)
    
    return render_template('admin_product_simple_test.html', 
                          products=products)

@app.route('/admin/product-availability-test', methods=['GET'])
@admin_auth.login_required
def product_availability_test():
    # Pobierz wszystkie produkty, włączając te niedostępne
    products = product_manager.get_all_products(include_unavailable=True)
    categories = product_manager.get_categories()
    
    return render_template('admin_product_availability_test.html', 
                          products=products,
                          categories=categories)

@app.route('/admin/product-availability', methods=['GET'])
@admin_auth.login_required
def product_availability():
    # Pobierz wszystkie produkty, włączając te niedostępne
    products = product_manager.get_all_products(include_unavailable=True)
    categories = product_manager.get_categories()
    
    return render_template('admin_product_availability.html', 
                          products=products,
                          categories=categories)

@app.route('/admin/create-listing', methods=['GET'])
@admin_auth.login_required
def create_listing():
    # Pobierz wszystkie kategorie produktów
    categories = product_manager.get_categories()
    
    # Pobierz ostatnio dodane produkty, np. z ostatnich 7 dni lub ostatnich 20 produktów
    recent_products = product_manager.get_recent_products(limit=20)
    
    return render_template('admin_product_listing_new.html', 
                          categories=categories,
                          recent_products=recent_products)

@app.route('/admin/add-product', methods=['POST'])
@admin_auth.login_required
def add_product():
    try:
        # Sprawdź, czy mamy dane formularza multipart/form-data
        if 'name' not in request.form:
            return jsonify({'success': False, 'message': 'Brak wymaganych danych produktu'})
        
        # Zbierz dane z formularza
        product_data = {
            'name': request.form.get('name'),
            'category': request.form.get('category'),
            'description': request.form.get('description', ''),
            # 'price' (cena sprzedaży brutto) będzie teraz obliczana lub brana bezpośrednio
            'stock': int(request.form.get('stock', 0)),
            'available_for_sale': request.form.get('available_for_sale') == 'true'
        }
        
        # Ceny i marża
        if request.form.get('price'): # Bezpośrednio podana cena sprzedaży brutto
            product_data['price'] = float(request.form.get('price'))
        
        if request.form.get('original_price'): # Cena netto zakupu (przemianowane z original_price w formularzu)
            product_data['price_net_cost'] = float(request.form.get('original_price'))
        
        if request.form.get('markup_percent'):
            product_data['markup_percent'] = float(request.form.get('markup_percent'))

        # Opcjonalne pola
        if 'shipping_time' in request.form and request.form.get('shipping_time'):
            product_data['shipping_time'] = request.form.get('shipping_time')
        
        if 'shipping_cost' in request.form and request.form.get('shipping_cost'):
            product_data['shipping_cost'] = float(request.form.get('shipping_cost'))
        
        # Obsługa zdjęcia produktu
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Zapisz plik i uzyskaj URL
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # Upewnij się, że folder istnieje
                os.makedirs('static/uploads/products', exist_ok=True)
                
                # Zapisz plik
                file_path = os.path.join('static/uploads/products', filename)
                file.save(file_path)
                
                # Ustaw URL względny do folderu statycznego
                product_data['image'] = f"/static/uploads/products/{filename}"
        
        # Dodaj produkt do bazy
        new_product = product_manager.add_product(product_data)
        
        if new_product:
            return jsonify({
                'success': True,
                'message': f'Produkt "{new_product["name"]}" został dodany',
                'product': new_product
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Wystąpił błąd podczas dodawania produktu'
            })
    except Exception as e:
        import traceback
        print(f"Błąd podczas dodawania produktu: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd: {str(e)}'
        })

@app.route('/admin/orders')
@admin_auth.login_required
def admin_orders():
    orders = admin_auth.get_all_orders()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/order/<order_id>')
@admin_auth.login_required
def admin_order_detail(order_id):
    # Próba pobrania zamówienia po ID
    order = admin_auth.get_order(order_id)
    
    # Jeśli nie znaleziono, spróbuj znaleźć w liście zamówień
    if not order:
        for o in admin_auth.orders:
            if str(o.get('id')) == str(order_id):
                order = o
                break
    
    if not order:
        flash('Zamówienie nie zostało znalezione')
        return redirect(url_for('admin_orders'))
    
    # Pobierz dane płatności
    payment = payment_manager.get_payment_by_order_id(order_id)
    
    return render_template('admin_order_detail.html', order=order, payment=payment)

@app.route('/admin/order/<order_id>/update-status', methods=['POST'])
@admin_auth.login_required
def admin_update_order_status(order_id):
    new_status = request.form.get('status')
    if not new_status:
        flash('Nie podano nowego statusu')
        return redirect(url_for('admin_order_detail', order_id=order_id))
    
    # Próba aktualizacji przez metody AdminAuth
    if hasattr(admin_auth, 'update_order_status') and callable(getattr(admin_auth, 'update_order_status')):
        if admin_auth.update_order_status(order_id, new_status):
            flash('Status zamówienia został zaktualizowany')
        else:
            # Jeśli metoda nie zadziałała, użyj bezpośredniej aktualizacji
            for order in admin_auth.orders:
                if str(order.get('id')) == str(order_id):
                    order['status'] = new_status
                    admin_auth._save_data()
                    flash('Status zamówienia został zaktualizowany')
                    break
    else:
        # Bezpośrednia aktualizacja jeśli metoda nie istnieje
        for order in admin_auth.orders:
            if str(order.get('id')) == str(order_id):
                order['status'] = new_status
                admin_auth._save_data()
                flash('Status zamówienia został zaktualizowany')
                break
    
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/payment/<payment_id>/update-status', methods=['POST'])
@admin_auth.login_required
def admin_update_payment_status(payment_id):
    new_status = request.form.get('status')
    note = request.form.get('note', 'Status zmieniony przez administratora')
    
    if not new_status:
        flash('Nie podano nowego statusu')
        return redirect(url_for('admin_orders'))
    
    # Pobierz płatność
    payment = payment_manager.get_payment(payment_id)
    if not payment:
        flash('Płatność nie została znaleziona')
        return redirect(url_for('admin_orders'))
    
    # Aktualizuj status płatności
    if payment_manager.update_payment_status(payment_id, new_status, note):
        flash('Status płatności został zaktualizowany')
    else:
        flash('Wystąpił błąd podczas aktualizacji statusu płatności')
    
    return redirect(url_for('admin_order_detail', order_id=payment['order_id']))

@app.route('/admin/settings')
@admin_auth.login_required
def admin_settings():
    xml_status = xml_downloader.get_status()
    main_categories = product_manager.get_main_categories()
    featured_categories = product_manager.get_featured_categories()
    
    return render_template('admin_settings.html', 
                          xml_config=xml_status['config'],
                          last_update=xml_status['last_download'],
                          main_categories=main_categories,
                          featured_categories=featured_categories)

@app.route('/admin/update-xml-config', methods=['POST'])
@admin_auth.login_required
def update_xml_config():
    if request.method == 'POST':
        new_config = {
            'url': request.form.get('url', 'https://ergo.enode.ovh/products.xml'),
            'interval_minutes': int(request.form.get('interval_minutes', 10)),
            'auto_start': request.form.get('auto_start') == 'on'
        }
        
        xml_downloader.update_config(new_config)
        flash('Konfiguracja XML została zaktualizowana')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/toggle-xml-scheduler', methods=['POST'])
@admin_auth.login_required
def toggle_xml_scheduler():
    xml_downloader.toggle_auto_start()
    return '', 204

@app.route('/admin/featured-categories', methods=['POST'])
@admin_auth.login_required
def update_featured_categories():
    try:
        categories = request.form.getlist('featured_categories')
        success = product_manager.save_featured_categories(categories)
        if success:
            flash('Zapisano wyróżnione kategorie', 'success')
        else:
            flash('Wystąpił problem podczas zapisywania wyróżnionych kategorii', 'error')
    except Exception as e:
        app.logger.error(f"Błąd podczas aktualizacji wyróżnionych kategorii: {str(e)}")
        flash(f'Wystąpił błąd: {str(e)}', 'error')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/create-backup', methods=['POST'])
@admin_auth.login_required
def create_backup():
    """Tworzy kopię zapasową bazy danych produktów na żądanie"""
    try:
        success = backup_manager.create_backup()
        if success:
            flash('Kopia zapasowa została utworzona pomyślnie', 'success')
        else:
            flash('Wystąpił problem podczas tworzenia kopii zapasowej', 'error')
    except Exception as e:
        app.logger.error(f"Błąd podczas tworzenia kopii zapasowej: {str(e)}")
        flash(f'Wystąpił błąd: {str(e)}', 'error')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/generate-product-descriptions', methods=['POST'])
@admin_auth.login_required
def generate_product_descriptions():
    """Generuje opisy produktów pobierając je z zewnętrznej stronie"""
    try:
        data = request.get_json()
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({
                'success': False,
                'message': 'Nie wybrano produktów do aktualizacji opisów'
            })
            
        # Importuj funkcję do aktualizacji opisów produktów
        from product_descriptions import update_product_descriptions_batch
        
        # Aktualizuj opisy produktów
        results = update_product_descriptions_batch(product_manager, product_ids)
        
        if results['updated'] > 0:
            return jsonify({
                'success': True,
                'message': f'Zaktualizowano opisy {results["updated"]} produktów, błędy: {results["errors"]}',
                'details': results
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Nie udało się zaktualizować żadnego opisu. Błędy: {results["errors"]}',
                'details': results
            })
            
    except Exception as e:
        app.logger.error(f"Błąd podczas generowania opisów produktów: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Wystąpił błąd: {str(e)}'
        })

# Przykład emitowania powiadomienia o nowym produkcie (możesz wywołać to np. po dodaniu produktu z XML w przyszłości)
@socketio.on('announce_new_product')
def handle_new_product(data):
    socketio.emit('new_product', data)

# WebSocket event dla aktualizacji koszyka
@socketio.on('cart_updated')
def handle_cart_update(data):
    # Broadcast do wszystkich podłączonych klientów (symulacja synchronizacji koszyka)
    socketio.emit('cart_update', data, broadcast=True)

@app.route('/admin/product-list/<int:list_id>', methods=['GET'])
@admin_auth.login_required
def product_list_detail(list_id):
    # Pobierz konkretną listę produktów
    product_list = product_manager.get_product_list(list_id)
    
    if not product_list:
        flash('Lista produktów nie została znaleziona', 'error')
        return redirect(url_for('product_listing'))
    
    # Pobierz szczegóły produktów z XML
    products = product_manager.get_xml_products_by_ids(product_list.get('products_ids', []))
    
    # Pobierz wszystkie kategorie
    all_categories = set()
    for product in products:
        if 'category' in product and product['category']:
            all_categories.add(product['category'])
        if 'category_path' in product and product['category_path']:
            for category in product['category_path']:
                all_categories.add(category)
    
    categories = sorted(list(all_categories))
    
    return render_template('admin_product_list_detail.html', 
                          product_list=product_list,
                          products=products,
                          categories=categories)

@app.route('/admin/update-product-list/<int:list_id>', methods=['POST'])
@admin_auth.login_required
def update_product_list(list_id):
    # Pobierz dane z formularza
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Brak danych'})
    
    # Aktualizuj listę produktów
    updated_list = product_manager.update_product_list(list_id, data)
    
    if updated_list:
        return jsonify({
            'success': True,
            'message': f'Lista produktów "{updated_list["name"]}" została zaktualizowana',
            'product_list': updated_list
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Wystąpił błąd podczas aktualizacji listy produktów'
        })

@app.route('/admin/delete-product-list/<int:list_id>', methods=['POST'])
@admin_auth.login_required
def delete_product_list(list_id):
    # Usuń listę produktów
    success = product_manager.delete_product_list(list_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Lista produktów została usunięta'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Wystąpił błąd podczas usuwania listy produktów'
        })

@app.route('/admin/published-products', methods=['GET'])
@admin_auth.login_required
def published_products():
    # Pobierz wszystkie wystawione produkty
    products = product_manager.get_published_products()
    
    # Pobierz kategorie
    categories = product_manager.get_categories()
    
    return render_template('admin_published_products.html',
                          products=products,
                          categories=categories)

# Dodajemy nowy route admin_users, który był brakujący
@app.route('/admin/users')
@admin_auth.login_required
def admin_users():
    # Pobierz listę użytkowników
    users = admin_auth.get_all_users() if hasattr(admin_auth, 'get_all_users') else []
    
    # Jeśli nie ma metody get_all_users w admin_auth, tworzymy puste zestawienie
    if not users:
        users = []
    
    return render_template('admin_users.html', users=users)

@app.route('/admin/add-user', methods=['POST'])
@admin_auth.login_required
def admin_add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'user')
        
        # Walidacja danych
        if not username or not password:
            flash('Nazwa użytkownika i hasło są wymagane', 'error')
            return redirect(url_for('admin_users'))
            
        if password != confirm_password:
            flash('Hasła nie są identyczne', 'error')
            return redirect(url_for('admin_users'))
        
        # Sprawdź czy użytkownik o podanej nazwie już istnieje
        if hasattr(admin_auth, 'user_exists') and admin_auth.user_exists(username):
            flash(f'Użytkownik o nazwie {username} już istnieje', 'error')
            return redirect(url_for('admin_users'))
        
        # Dodaj użytkownika
        if hasattr(admin_auth, 'add_user') and admin_auth.add_user(username, password, role):
            flash(f'Użytkownik {username} został dodany pomyślnie', 'success')
        else:
            flash('Wystąpił problem podczas dodawania użytkownika', 'error')
        
        return redirect(url_for('admin_users'))
    
    return redirect(url_for('admin_users'))

@app.route('/admin/delete-user/<username>')
@admin_auth.login_required
def admin_delete_user(username):
    # Nie można usunąć siebie
    if username == session.get('admin_username'):
        flash('Nie możesz usunąć własnego konta', 'error')
        return redirect(url_for('admin_users'))
    
    # Usuń użytkownika
    if hasattr(admin_auth, 'delete_user') and admin_auth.delete_user(username):
        flash(f'Użytkownik {username} został usunięty', 'success')
    else:
        flash('Wystąpił problem podczas usuwania użytkownika', 'error')
    
    return redirect(url_for('admin_users'))

def slugify(text):
    """Konwertuje tekst na przyjazny URL (slug)"""
    # Zastąp polskie znaki
    replacements = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
        'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N',
        'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
    }
    for polish, latin in replacements.items():
        text = text.replace(polish, latin)
    
    # Zamień spacje na myślniki, usuń znaki specjalne, zmień na małe litery
    import re
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    
    return text

@app.route('/search')
def search():
    """Wyszukiwanie produktów"""
    query = request.args.get('q', '')
    sort = request.args.get('sort', 'relevance')
    available_only = request.args.get('available', 'false') == 'true'
    
    # Sprawdzenie czy zapytanie nie jest puste
    if not query or len(query.strip()) < 1:
        flash('Wprowadź frazę do wyszukania', 'warning')
        return redirect(url_for('home'))
    
    # Pobranie wyników wyszukiwania
    products = product_manager.find_products(query, include_unavailable=not available_only)
    
    # Wyróżnij zapytanie w nazwach i opisach produktów
    if query:
        for product in products:
            if 'name' in product:
                product['highlighted_name'] = highlight_text(product['name'], query)
            if 'description' in product:
                # Skrócona wersja opisu dla wyników wyszukiwania (pierwsze 250 znaków)
                short_desc = product['description'][:250] + ('...' if len(product['description']) > 250 else '')
                product['highlighted_description'] = highlight_text(short_desc, query)
    
    # Sortowanie wyników
    if sort == 'price-asc':
        products.sort(key=lambda p: float(p.get('price', 0)))
    elif sort == 'price-desc':
        products.sort(key=lambda p: float(p.get('price', 0)), reverse=True)
    elif sort == 'name-asc':
        products.sort(key=lambda p: p.get('name', '').lower())
    else:  # relevance (domyślnie)
        # Najpierw te, które mają frazę w nazwie
        if query:
            products.sort(key=lambda p: query.lower() not in p.get('name', '').lower())
    
    # Statystyki wyszukiwania
    search_stats = {
        'total': len(products),
        'available': sum(1 for p in products if p.get('stock', 0) > 0),
        'categories': {}
    }
    
    # Zliczanie produktów według kategorii
    for product in products:
        category = product.get('category', 'Bez kategorii')
        if category not in search_stats['categories']:
            search_stats['categories'][category] = 0
        search_stats['categories'][category] += 1
    
    return render_template('search_results.html', 
                          products=products,
                          query=query,
                          search_stats=search_stats,
                          sort=sort,
                          available_only=available_only)

@app.route('/api/search')
def api_search():
    """API dla podpowiedzi wyszukiwania"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    available_only = request.args.get('available', 'false') == 'true'
    
    if not query or len(query) < 2:
        return jsonify([])
    
    products = product_manager.find_products(query, include_unavailable=not available_only)
    
    # Sortowanie wyników - domyślnie wg. trafności
    # Najpierw te, które mają frazę w nazwie
    if query:
        products.sort(key=lambda p: query.lower() not in p.get('name', '').lower())
    
    # Ograniczenie wyników
    products = products[:limit]
    
    # Przygotowanie wyników w formacie JSON
    results = []
    for product in products:
        results.append({
            'id': product.get('id'),
            'name': product.get('name'),
            'price': product.get('price'),
            'image': product.get('image'),
            'category': product.get('category'),
            'stock': product.get('stock', 0),
            'available_for_sale': product.get('available_for_sale', True)
        })
    
    return jsonify(results)

@app.route('/add_to_cart', methods=['POST'])
def ajax_add_to_cart():
    """Dodawanie produktów do koszyka przez AJAX"""
    product_id = request.json.get('product_id')
    quantity = request.json.get('quantity', 1)
    
    if not product_id:
        return jsonify({'success': False, 'message': 'Brak identyfikatora produktu'})
    
    # Sprawdzenie czy produkt istnieje
    product = product_manager.get_product_by_id(product_id, include_unavailable=True)
    if not product:
        return jsonify({'success': False, 'message': 'Produkt nie został znaleziony'})
        
    # Sprawdzenie dostępności
    if product.get('stock', 0) <= 0 or not product.get('available_for_sale', True):
        return jsonify({
            'success': False, 
            'message': 'Produkt niedostępny'
        })
    
    # Inicjalizacja koszyka w sesji jeśli nie istnieje
    if 'cart' not in session:
        session['cart'] = []
    
    # Sprawdzenie czy produkt jest już w koszyku
    cart = session['cart']
    product_in_cart = False
    
    for item in cart:
        if item.get('id') == product_id:
            item['quantity'] = item.get('quantity', 1) + int(quantity)
            # Aktualizuj cenę i inne dane produktu, na wypadek gdyby się zmieniły
            item['price'] = product.get('price')
            item['name'] = product.get('name')
            item['image'] = product.get('image')
            product_in_cart = True
            break
    
    # Jeśli produkt nie jest w koszyku, dodaj go
    if not product_in_cart:
        cart.append({
            'id': product_id,
            'name': product.get('name'),
            'price': product.get('price'),
            'image': product.get('image'),
            'quantity': int(quantity)
        })
    
    # Zapisanie koszyka w sesji
    session['cart'] = cart
    
    # Obliczenie sumy koszyka
    total = sum(float(item.get('price', 0)) * item.get('quantity', 1) for item in cart)
    
    # Zwrócenie aktualnego stanu koszyka
    return jsonify({
        'success': True,
        'message': f'Dodano "{product.get("name")}" do koszyka',
        'cart_count': len(cart),
        'cart_sum': "{:.2f}".format(total)
    })

if __name__ == '__main__':
    # Uruchomienie pobierania XML w tle
    xml_downloader.start()
    
    # Uruchomienie aplikacji Flask
    socketio.run(app, host='0.0.0.0', port=5454, debug=True)
