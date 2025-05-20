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
            'price': float(request.form.get('price', 0)),
            'stock': int(request.form.get('stock', 0)),
            'available_for_sale': request.form.get('available_for_sale') == 'true'
        }
        
        # Opcjonalne pola
        if 'original_price' in request.form and request.form.get('original_price'):
            product_data['original_price'] = float(request.form.get('original_price'))
        
        if 'markup_percent' in request.form and request.form.get('markup_percent'):
            product_data['markup_percent'] = float(request.form.get('markup_percent'))
        
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
