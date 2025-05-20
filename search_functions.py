# Uzupełnienie implementacji funkcji wyszukiwania w app.py
# Skopiuj ten kod do pliku app.py, zastępując istniejące funkcje search i api_search

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
    
    if not query or len(query) < 2:
        return jsonify([])
    
    products = product_manager.find_products(query)
    
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
            'category': product.get('category')
        })
    
    return jsonify(results)
