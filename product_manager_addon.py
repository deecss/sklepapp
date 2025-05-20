    def get_recent_products(self, limit=20, days=None):
        """
        Zwraca ostatnio dodane produkty
        
        Args:
            limit (int): Maksymalna liczba produktów do zwrócenia
            days (int, optional): Liczba dni wstecz do sprawdzenia
            
        Returns:
            list: Lista produktów
        """
        # Pobierz wszystkie produkty i posortuj według daty dodania (jeśli istnieje)
        sorted_products = sorted(
            self.products, 
            key=lambda p: p.get('added_at', '2000-01-01'), 
            reverse=True
        )
        
        # Jeśli określono liczbę dni, sprawdź tylko te produkty
        if days:
            today = datetime.now()
            filtered_products = []
            
            for product in sorted_products:
                if 'added_at' in product:
                    try:
                        added_date = datetime.strptime(product['added_at'], '%Y-%m-%d %H:%M:%S')
                        days_diff = (today - added_date).days
                        if days_diff <= days:
                            filtered_products.append(product)
                    except (ValueError, TypeError):
                        # Jeśli nie można przetworzyć daty, pomiń produkt
                        pass
            
            # Zwróć tylko określoną liczbę produktów
            return filtered_products[:limit]
        
        # W przeciwnym razie po prostu zwróć ostatnio dodane produkty według limitu
        return sorted_products[:limit]
    
    def add_product(self, product_data):
        """
        Dodaje nowy produkt do bazy danych
        
        Args:
            product_data (dict): Dane produktu
            
        Returns:
            dict: Dodany produkt z przydzielonym ID lub None w przypadku błędu
        """
        try:
            # Generuj nowe ID produktu
            product_id = self._get_next_id()
            
            # Przygotuj dane produktu
            new_product = {
                'id': product_id,
                'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                **product_data
            }
            
            # Dodaj produkt do listy
            self.products.append(new_product)
            
            # Zapisz zmiany w bazie danych
            self._save_to_db()
            
            self.logger.info(f"Dodano nowy produkt ID: {product_id}, Nazwa: {product_data.get('name')}")
            
            return new_product
        except Exception as e:
            self.logger.error(f"Błąd podczas dodawania produktu: {str(e)}")
            return None
    
    def _get_next_id(self):
        """
        Generuje nowe ID dla produktu
        
        Returns:
            int: Nowe ID produktu
        """
        if not self.products:
            return 1
        
        # Znajdź najwyższe ID i zwiększ o 1
        max_id = max(p.get('id', 0) for p in self.products)
        return max_id + 1
