/**
 * Ulepszona obsługa wyszukiwarki produktów
 * Ten skrypt implementuje interaktywną wyszukiwarkę produktów z podpowiedziami
 * Obsługuje zarówno wersję desktopową jak i mobilną
 * @version 1.2.0
 */

document.addEventListener('DOMContentLoaded', function() {
    // Desktop search elements
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const searchSuggestions = document.getElementById('search-suggestions');
    const searchButton = document.getElementById('search-button');
    const clearButton = document.getElementById('search-clear');
    
    // Mobile search elements
    const mobileSearchForm = document.getElementById('mobile-search-form');
    const mobileSearchInput = document.getElementById('mobile-search-input');
    const mobileSearchSuggestions = document.getElementById('mobile-search-suggestions');
    const mobileSearchClear = document.getElementById('mobile-search-clear');
    
    // Cache dla wyników wyszukiwania - ograniczenie zapytań sieciowych
    const searchCache = new Map();
    let debounceTimer;
    
    // Stałe konfiguracyjne
    const MAX_RECENT_SEARCHES = 3;
    const MAX_SUGGESTIONS = 7;
    
    // Obsługa wyszukiwania
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            if (!searchInput.value.trim()) {
                e.preventDefault();
            } else {
                // Zapisz wyszukiwanie w lokalnym magazynie
                saveRecentSearch(searchInput.value.trim());
            }
        });
    }
    
    if (mobileSearchForm) {
        mobileSearchForm.addEventListener('submit', function(e) {
            if (!mobileSearchInput.value.trim()) {
                e.preventDefault();
            } else {
                // Zapisz wyszukiwanie w lokalnym magazynie
                saveRecentSearch(mobileSearchInput.value.trim());
            }
        });
    }
    
    // Sprawdzenie czy elementy istnieją
    if (!searchInput || !searchSuggestions) return;
    
    // Funkcja do konfiguracji wyszukiwarki
    function setupSearch(input, clear, suggestions, form) {
        if (!input) return;
        
        // Wyświetlanie/ukrywanie przycisku czyszczenia
        input.addEventListener('input', function() {
            if (this.value.length > 0) {
                if (clear) clear.classList.remove('hidden');
            } else {
                if (clear) clear.classList.add('hidden');
                hideSearchSuggestions(suggestions);
            }
            
            // Debounce - opóźnienie wyszukiwania
            clearTimeout(debounceTimer);
            if (this.value.length < 2) {
                if (this.value.length === 0) {
                    // Pokaż ostatnio wyszukiwane
                    displayRecentSearches(suggestions);
                } else {
                    hideSearchSuggestions(suggestions);
                }
                return;
            }
            
            debounceTimer = setTimeout(() => {
                fetchSuggestions(this.value.trim(), suggestions);
            }, 300);
        });
        
        // Pokaż ostatnio wyszukiwane po kliknięciu w puste pole
        input.addEventListener('focus', function() {
            if (this.value.length === 0) {
                displayRecentSearches(suggestions);
            }
        });
        
        // Obsługa przycisku czyszczenia
        if (clear) {
            clear.addEventListener('click', function() {
                input.value = '';
                input.focus();
                clear.classList.add('hidden');
                // Pokaż ostatnio wyszukiwane
                displayRecentSearches(suggestions);
            });
        }
        
        // Ukrywanie podpowiedzi po kliknięciu poza wyszukiwarką
        if (form) {
            document.addEventListener('click', function(e) {
                if (!form.contains(e.target)) {
                    hideSearchSuggestions(suggestions);
                }
            });
        }
        
        // Obsługa nawigacji klawiaturą
        input.addEventListener('keydown', function(e) {
            if (suggestions.classList.contains('hidden')) return;
            
            // Strzałka w dół - przejdź do pierwszej podpowiedzi
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const firstSuggestion = suggestions.querySelector('a');
                if (firstSuggestion) firstSuggestion.focus();
            }
            
            // Escape - ukryj podpowiedzi
            if (e.key === 'Escape') {
                hideSearchSuggestions(suggestions);
            }
        });
        
        // Nawigacja po podpowiedziach
        if (suggestions) {
            suggestions.addEventListener('keydown', function(e) {
                const suggestionLinks = suggestions.querySelectorAll('a:not(.filter-option)');
                const currentIndex = Array.from(suggestionLinks).indexOf(document.activeElement);
                
                // Strzałka w dół - przejście do następnej podpowiedzi
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (currentIndex < suggestionLinks.length - 1) {
                        suggestionLinks[currentIndex + 1].focus();
                    }
                }
                
                // Strzałka w górę - przejście do poprzedniej podpowiedzi lub pola wyszukiwania
                if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (currentIndex > 0) {
                        suggestionLinks[currentIndex - 1].focus();
                    } else {
                        input.focus();
                    }
                }
                
                // Escape - ukryj podpowiedzi i wróć do pola wyszukiwania
                if (e.key === 'Escape') {
                    hideSearchSuggestions(suggestions);
                    input.focus();
                }
            });
        }
    }
    
    // Konfiguracja wyszukiwarki na pulpicie
    setupSearch(searchInput, clearButton, searchSuggestions, searchForm);
    
    // Konfiguracja wyszukiwarki mobilnej
    setupSearch(mobileSearchInput, mobileSearchClear, mobileSearchSuggestions, mobileSearchForm);
    
    // Zarządzanie ostatnimi wyszukiwaniami
    function saveRecentSearch(query) {
        if (!query || query.length < 2) return;
        
        try {
            let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
            // Usuń duplikaty
            recentSearches = recentSearches.filter(item => item.toLowerCase() !== query.toLowerCase());
            // Dodaj nowy wpis
            recentSearches.unshift(query);
            // Ogranicz liczbę wpisów
            recentSearches = recentSearches.slice(0, MAX_RECENT_SEARCHES);
            
            localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
        } catch (error) {
            console.error('Błąd zapisu ostatnio wyszukiwanych:', error);
        }
    }
    
    function getRecentSearches() {
        try {
            return JSON.parse(localStorage.getItem('recentSearches') || '[]');
        } catch (error) {
            console.error('Błąd odczytu ostatnio wyszukiwanych:', error);
            return [];
        }
    }
    
    function displayRecentSearches(suggestionsContainer) {
        if (!suggestionsContainer) return;
        
        const recentSearches = getRecentSearches();
        if (recentSearches.length === 0) return;
        
        // Wyczyść kontener
        suggestionsContainer.innerHTML = '';
        
        // Dodaj nagłówek
        const header = document.createElement('div');
        header.className = 'text-xs uppercase font-bold text-gray-500 px-4 py-2 border-b border-gray-200 flex justify-between items-center';
        header.innerHTML = `
            <span>Ostatnie wyszukiwania</span>
            <button type="button" class="text-blue-600 hover:text-blue-800 text-xs" id="clear-recent-searches">
                Wyczyść
            </button>
        `;
        suggestionsContainer.appendChild(header);
        
        // Dodaj elementy
        recentSearches.forEach(query => {
            const item = document.createElement('a');
            item.href = `/search?q=${encodeURIComponent(query)}`;
            item.className = 'flex items-center px-4 py-2 hover:bg-blue-50 transition-colors duration-200';
            
            item.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="text-gray-700">${query}</span>
            `;
            
            suggestionsContainer.appendChild(item);
        });
        
        // Obsługa czyszczenia historii
        const clearButton = document.getElementById('clear-recent-searches');
        if (clearButton) {
            clearButton.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                localStorage.removeItem('recentSearches');
                hideSearchSuggestions(suggestionsContainer);
            });
        }
        
        // Pokaż kontener
        showSearchSuggestions(suggestionsContainer);
    }
    
    // Pobieranie podpowiedzi z serwera z wykorzystaniem cache
    function fetchSuggestions(query, suggestionsContainer) {
        // Sprawdź czy mamy już te wyniki w cache (ograniczenie liczby zapytań)
        if (searchCache.has(query)) {
            const cachedData = searchCache.get(query);
            if (cachedData.length > 0) {
                displaySuggestions(cachedData, query, suggestionsContainer);
            } else {
                hideSearchSuggestions(suggestionsContainer);
            }
            return;
        }
        
        // Pokazanie wskaźnika ładowania
        suggestionsContainer.innerHTML = `
            <div class="flex justify-center items-center p-4">
                <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                <span class="ml-2 text-sm text-gray-600">Wyszukiwanie...</span>
            </div>
        `;
        showSearchSuggestions(suggestionsContainer);
        
        // Pobierz dane z serwera
        fetch(`/api/search?q=${encodeURIComponent(query)}&limit=${MAX_SUGGESTIONS}`)
            .then(response => response.json())
            .then(data => {
                // Zapisz wyniki w cache aby uniknąć ponownych zapytań
                searchCache.set(query, data);
                
                if (data.length > 0) {
                    displaySuggestions(data, query, suggestionsContainer);
                } else {
                    // Pokaż informację o braku wyników
                    suggestionsContainer.innerHTML = `
                        <div class="flex flex-col items-center justify-center py-6 px-4 text-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p class="text-gray-500 mb-1">Brak wyników dla "${query}"</p>
                            <p class="text-gray-400 text-sm">Spróbuj użyć innych słów kluczowych</p>
                        </div>
                    `;
                    showSearchSuggestions(suggestionsContainer);
                }
            })
            .catch(err => {
                console.error('Błąd podczas pobierania podpowiedzi:', err);
                hideSearchSuggestions(suggestionsContainer);
                
                // Opcjonalnie: pokazanie informacji o błędzie
                if (window.showNotification) {
                    window.showNotification('Wystąpił błąd podczas wyszukiwania', 'error', 3000);
                }
            });
    }
    
    // Wyświetlanie podpowiedzi
    function displaySuggestions(products, query, suggestionsContainer) {
        if (!suggestionsContainer) return;
        
        // Kategorie do filtrowania
        const categories = products.reduce((acc, product) => {
            const category = product.category || 'Ogólna';
            if (!acc.includes(category)) acc.push(category);
            return acc;
        }, []);
        
        // Wyczyść poprzednie podpowiedzi
        suggestionsContainer.innerHTML = '';
        
        // Dodaj nagłówek podpowiedzi z liczbą znalezionych produktów
        const suggestionHeader = document.createElement('div');
        suggestionHeader.className = 'text-xs uppercase font-bold text-gray-500 px-4 py-2 border-b border-gray-200 flex justify-between items-center';
        suggestionHeader.innerHTML = `
            <span>Sugerowane produkty</span>
            <span class="text-blue-600">${products.length} znalezionych</span>
        `;
        suggestionsContainer.appendChild(suggestionHeader);
        
        // Dodaj filtry kategorii jeśli jest więcej niż jedna
        if (categories.length > 1) {
            const filterContainer = document.createElement('div');
            filterContainer.className = 'flex flex-wrap gap-1 px-3 py-2 bg-gray-50 border-b border-gray-200';
            
            // Przycisk "Wszystkie"
            const allFilter = document.createElement('a');
            allFilter.href = '#';
            allFilter.className = 'filter-option text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors duration-200';
            allFilter.textContent = 'Wszystkie';
            allFilter.addEventListener('click', function(e) {
                e.preventDefault();
                // Usuń klasę aktywną z wszystkich przycisków
                filterContainer.querySelectorAll('.filter-option').forEach(btn => {
                    btn.classList.remove('bg-blue-600', 'text-white');
                    btn.classList.add('bg-blue-100', 'text-blue-800');
                });
                // Dodaj klasę aktywną do tego przycisku
                this.classList.remove('bg-blue-100', 'text-blue-800');
                this.classList.add('bg-blue-600', 'text-white');
                // Pokaż wszystkie produkty
                suggestionsContainer.querySelectorAll('.product-suggestion').forEach(item => {
                    item.classList.remove('hidden');
                });
            });
            
            // Dodaj klasę aktywną do przycisku "Wszystkie"
            allFilter.classList.remove('bg-blue-100', 'text-blue-800');
            allFilter.classList.add('bg-blue-600', 'text-white');
            
            filterContainer.appendChild(allFilter);
            
            // Przyciski dla kategorii
            categories.forEach(category => {
                const filter = document.createElement('a');
                filter.href = '#';
                filter.className = 'filter-option text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors duration-200';
                filter.textContent = category;
                filter.setAttribute('data-category', category);
                
                filter.addEventListener('click', function(e) {
                    e.preventDefault();
                    const selectedCategory = this.getAttribute('data-category');
                    
                    // Usuń klasę aktywną z wszystkich przycisków
                    filterContainer.querySelectorAll('.filter-option').forEach(btn => {
                        btn.classList.remove('bg-blue-600', 'text-white');
                        btn.classList.add('bg-blue-100', 'text-blue-800');
                    });
                    
                    // Dodaj klasę aktywną do tego przycisku
                    this.classList.remove('bg-blue-100', 'text-blue-800');
                    this.classList.add('bg-blue-600', 'text-white');
                    
                    // Ukryj/pokaż odpowiednie produkty
                    suggestionsContainer.querySelectorAll('.product-suggestion').forEach(item => {
                        const itemCategory = item.getAttribute('data-category') || 'Ogólna';
                        if (itemCategory === selectedCategory) {
                            item.classList.remove('hidden');
                        } else {
                            item.classList.add('hidden');
                        }
                    });
                });
                
                filterContainer.appendChild(filter);
            });
            
            suggestionsContainer.appendChild(filterContainer);
        }
        
        // Dodaj listę produktów
        const productsList = document.createElement('div');
        productsList.className = 'max-h-[280px] overflow-y-auto';
        
        // Dodaj podpowiedzi
        products.forEach(product => {
            const item = document.createElement('a');
            item.href = `/produkt/${product.id}`;
            item.className = 'product-suggestion flex items-center px-4 py-3 hover:bg-blue-50 transition-colors duration-200';
            item.setAttribute('data-category', product.category || 'Ogólna');
            
            // Wyróżnienie wyszukiwanej frazy
            const highlightedName = product.name.replace(
                new RegExp(query, 'gi'),
                match => `<span class="bg-yellow-100 font-semibold">${match}</span>`
            );
            
            // Tworzenie HTML dla podpowiedzi
            let imageHtml = '';
            if (product.image) {
                imageHtml = `
                    <div class="w-16 h-16 flex-shrink-0 bg-white overflow-hidden rounded border border-gray-200 mr-3 p-1">
                        <img src="${product.image}" class="w-full h-full object-contain" alt="${product.name}" loading="lazy">
                    </div>
                `;
            } else {
                imageHtml = `
                    <div class="w-16 h-16 flex-shrink-0 bg-gray-100 flex items-center justify-center rounded mr-3">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                    </div>
                `;
            }
            
            // Formatowanie ceny z przecinkiem zamiast kropki
            const formattedPrice = typeof product.price === 'number' ? 
                product.price.toFixed(2).replace('.', ',') : 
                product.price?.toString().replace('.', ',') || '0,00';
            
            // Sprawdzenie dostępności produktu
            const isAvailable = product.available_for_sale && product.stock > 0;
            const availabilityClass = isAvailable ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600';
            const availabilityText = isAvailable ? 'Dostępny' : 'Niedostępny';
            
            item.innerHTML = `
                ${imageHtml}
                <div class="flex-grow overflow-hidden">
                    <div class="text-sm font-medium text-gray-800 line-clamp-2 mb-1">${highlightedName}</div>
                    <div class="flex flex-wrap items-center gap-2">
                        <span class="font-semibold text-blue-700">${formattedPrice} zł</span>
                        <span class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">${product.category || 'Ogólna'}</span>
                        <span class="text-xs ${availabilityClass} px-2 py-0.5 rounded-full">${availabilityText}</span>
                    </div>
                </div>
                <div class="ml-2 self-center flex flex-col gap-2">
                    ${isAvailable ? `
                    <button type="button" class="add-to-cart-btn p-1.5 rounded-full bg-blue-50 hover:bg-blue-100 transition-colors" 
                           data-product-id="${product.id}" title="Dodaj do koszyka">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                    </button>
                    ` : ''}
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                </div>
            `;
            
            productsList.appendChild(item);
        });
        
        suggestionsContainer.appendChild(productsList);
        
        // Dodaj link "Pokaż wszystkie wyniki"
        const viewAllItem = document.createElement('a');
        viewAllItem.href = `/search?q=${encodeURIComponent(query)}`;
        viewAllItem.className = 'block text-center py-3 text-blue-600 hover:text-blue-800 border-t border-gray-200 font-medium text-sm';
        
        // Wybieramy odpowiedni tekst w zależności od liczby wyników
        viewAllItem.innerHTML = `Przejdź do strony wyników (${products.length})`;
        
        suggestionsContainer.appendChild(viewAllItem);
        
        // Pokaż podpowiedzi
        showSearchSuggestions(suggestionsContainer);
    }
    
    // Pokazywanie kontenerа podpowiedzi
    function showSearchSuggestions(container) {
        if (!container) return;
        container.classList.remove('hidden');
        container.classList.add('animate-fadeIn');
    }
    
    // Ukrywanie kontenerа podpowiedzi
    function hideSearchSuggestions(container) {
        if (!container) return;
        container.classList.add('hidden');
        container.classList.remove('animate-fadeIn');
    }
    
    // Szybkie dodawanie do koszyka z podpowiedzi wyszukiwania
    function setupQuickAddToCart() {
        document.addEventListener('click', function(e) {
            // Sprawdź czy kliknięto przycisk dodawania do koszyka
            if (e.target.closest('.add-to-cart-btn')) {
                e.preventDefault();
                e.stopPropagation();
                
                const button = e.target.closest('.add-to-cart-btn');
                const productId = button.getAttribute('data-product-id');
                
                // Animacja przycisku
                button.classList.add('animate-pulse');
                
                // Wysłanie żądania AJAX
                fetch('/add_to_cart', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        product_id: productId,
                        quantity: 1
                    })
                })
                .then(response => response.json())
                .then(data => {
                    // Zatrzymaj animację
                    button.classList.remove('animate-pulse');
                    
                    if (data.success) {
                        // Aktualizacja licznika koszyka i sumy
                        const cartCountElements = document.querySelectorAll('#cart-count');
                        cartCountElements.forEach(el => {
                            el.textContent = data.cart_count;
                            // Dodaj animację
                            el.classList.add('animate-pulse');
                            setTimeout(() => el.classList.remove('animate-pulse'), 1000);
                        });
                        
                        const cartSumElements = document.querySelectorAll('#cart-sum');
                        cartSumElements.forEach(el => {
                            el.textContent = data.cart_sum;
                        });
                        
                        // Pokaż powiadomienie
                        if (window.showNotification) {
                            window.showNotification(data.message, 'success', 3000);
                        }
                    } else {
                        // Pokaż błąd
                        if (window.showNotification) {
                            window.showNotification(data.message, 'error', 4000);
                        }
                    }
                })
                .catch(error => {
                    console.error('Błąd podczas dodawania do koszyka:', error);
                    button.classList.remove('animate-pulse');
                    
                    // Pokaż błąd
                    if (window.showNotification) {
                        window.showNotification('Wystąpił błąd podczas dodawania do koszyka', 'error', 4000);
                    }
                });
            }
        });
    }
    
    // Inicjalizacja szybkiego dodawania do koszyka
    setupQuickAddToCart();
});
