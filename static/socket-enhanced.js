/**
 * Rozszerzona obsługa WebSocket (Flask-SocketIO)
 * Zapewnia funkcje w czasie rzeczywistym:
 * - Aktualizacje koszyka
 * - Powiadomienia o nowych produktach
 * - Powiadomienia o dostępności produktów
 * - Monitorowanie stanu połączenia
 * 
 * @version 1.2.0
 */

// Status połączenia WebSocket
let socketConnected = false;
let connectionAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let reconnectionTimer = null;

// Automatycznie wykrywamy bieżący host i protokół
const socketUrl = window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : '');
console.log('Attempting to connect to Socket.IO server at:', socketUrl);

// Inicjalizacja socketu z opcjami
const socket = io(socketUrl, {
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    timeout: 10000,
    transports: ['websocket', 'polling'], // Najpierw spróbuj WebSocket, potem polling
    path: '/socket.io', // Explicytna ścieżka do Socket.IO
    autoConnect: true,   // Automatyczne połączenie przy inicjalizacji
    reconnection: true,  // Automatyczne ponowne próby połączenia
    reconnectionDelay: 1000, // Początkowe opóźnienie ponownego połączenia w ms
    reconnectionDelayMax: 5000, // Maksymalne opóźnienie ponownego połączenia w ms
});

// ----- OBSŁUGA POŁĄCZENIA -----
socket.on('connect', function() {
    console.log('Socket.IO connection established');
    socketConnected = true;
    connectionAttempts = 0;
    
    // Zatrzymaj timer ponownego połączenia jeśli był aktywny
    if (reconnectionTimer) {
        clearTimeout(reconnectionTimer);
        reconnectionTimer = null;
    }
    
    // Zaktualizuj status połączenia na stronie
    updateConnectionStatus('connected');
    
    // Powiadomienie o udanym połączeniu (opcjonalnie)
    // showDebugNotification('Połączono z serwerem w czasie rzeczywistym');
    
    // Zapisz sesję użytkownika na serwerze (jeśli użytkownik jest zalogowany)
    if (typeof userId !== 'undefined' && userId) {
        socket.emit('register_user', { user_id: userId });
    }
});

socket.on('connect_error', function(error) {
    console.error('Socket.IO connection error:', error);
    socketConnected = false;
    connectionAttempts++;
    
    // Zaktualizuj status połączenia
    updateConnectionStatus('error');
    
    // Dodaj więcej informacji diagnostycznych w konsoli
    let errorMessage = 'Nieznany błąd';
    
    if (error && error.message) {
        errorMessage = error.message;
        console.log('Socket.IO error details:', {
            message: error.message,
            type: error.type,
            description: error.description
        });
    }
    
    // Pokaż powiadomienie o błędzie po kilku próbach
    if (connectionAttempts >= MAX_RECONNECT_ATTEMPTS) {
        if (window.showNotification && connectionAttempts === MAX_RECONNECT_ATTEMPTS) {
            window.showNotification('Problem z połączeniem do serwera. Powiadomienia w czasie rzeczywistym mogą nie działać poprawnie.', 'warning');
        }
        
        // Własna logika ponownego połączenia po osiągnięciu limitu prób
        if (!reconnectionTimer) {
            reconnectionTimer = setTimeout(() => {
                console.log('Attempting custom reconnection...');
                socket.connect();
                reconnectionTimer = null;
            }, 10000); // Próba ponownego połączenia co 10 sekund
        }
    }
});

socket.on('disconnect', function(reason) {
    console.log('Socket.IO disconnected. Reason:', reason);
    socketConnected = false;
    updateConnectionStatus('disconnected');
    
    // Powiadomienie tylko gdy rozłączenie nie było zamierzone
    if (reason !== 'io client disconnect') {
        console.log('Unintentional disconnection');
    }
});

socket.on('reconnect', function(attemptNumber) {
    console.log('Socket.IO reconnected after', attemptNumber, 'attempts');
    socketConnected = true;
    connectionAttempts = 0;
    updateConnectionStatus('connected');
    
    // Opcjonalne powiadomienie o ponownym połączeniu
    // if (window.showNotification) {
    //     window.showNotification('Połączenie z serwerem zostało przywrócone', 'success');
    // }
});

// ----- OBSŁUGA POWIADOMIEŃ -----

// Powiadomienie o nowym produkcie
socket.on('new_product', function(data) {
    console.log('Received new product notification:', data);
    
    // Pokaż powiadomienie
    if (window.showNotification) {
        const message = `
            <div class="flex items-center">
                <div class="mr-3">
                    ${data.image ? `<img src="${data.image}" class="w-10 h-10 object-contain rounded" alt="${data.name}">` : ''}
                </div>
                <div>
                    <div class="font-medium">Nowy produkt</div>
                    <div>${data.name} - ${data.price} zł</div>
                </div>
            </div>
        `;
        window.showNotification(message, 'info', 7000);
    }
    
    // Jeśli jesteśmy na stronie z listą produktów, możemy odświeżyć listę
    if (document.getElementById('product-list-container')) {
        // Odśwież listę produktów lub dodaj nowy produkt na górze listy
    }
});

// Aktualizacja koszyka 
socket.on('cart_update', function(data) {
    console.log('Received cart update:', data);
    
    // Aktualizacja licznika koszyka
    const cartCountElements = document.querySelectorAll('#cart-count');
    cartCountElements.forEach(el => {
        if (el) {
            el.textContent = data.count;
            // Animate the counter
            el.classList.add('animate-pulse');
            setTimeout(() => el.classList.remove('animate-pulse'), 1000);
        }
    });
    
    // Aktualizacja sumy koszyka
    const cartSumElements = document.querySelectorAll('#cart-sum');
    cartSumElements.forEach(el => {
        if (el) el.textContent = data.sum;
    });
    
    // Opcjonalnie: pokaż powiadomienie lub animację
    if (data.product && window.showNotification) {
        const message = `Dodano do koszyka: ${data.product.name}`;
        window.showNotification(message, 'success', 3000);
    }
});

// Powiadomienie o dostępności produktu
socket.on('product_availability', function(data) {
    console.log('Product availability update:', data);
    
    // Aktualizacja interfejsu (jeśli jesteśmy na stronie produktu)
    const productId = data.product_id;
    const isAvailable = data.available;
    
    // Jeśli jesteśmy na stronie szczegółów tego produktu
    const productContainer = document.querySelector(`[data-product-id="${productId}"]`);
    if (productContainer) {
        const availabilityElement = productContainer.querySelector('.product-availability');
        if (availabilityElement) {
            if (isAvailable) {
                availabilityElement.textContent = 'Dostępny';
                availabilityElement.className = 'product-availability text-green-600 bg-green-50 px-2 py-1 rounded-md text-sm';
            } else {
                availabilityElement.textContent = 'Niedostępny';
                availabilityElement.className = 'product-availability text-red-600 bg-red-50 px-2 py-1 rounded-md text-sm';
            }
        }
        
        // Aktualizacja przycisku "Dodaj do koszyka"
        const addToCartBtn = productContainer.querySelector('.add-to-cart-btn');
        if (addToCartBtn) {
            if (isAvailable) {
                addToCartBtn.disabled = false;
                addToCartBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                addToCartBtn.classList.add('hover:bg-blue-700');
            } else {
                addToCartBtn.disabled = true;
                addToCartBtn.classList.add('opacity-50', 'cursor-not-allowed');
                addToCartBtn.classList.remove('hover:bg-blue-700');
            }
        }
    }
    
    // Pokaż powiadomienie tylko jeśli wcześniej obserwowaliśmy ten produkt
    if (data.notify && window.showNotification) {
        const message = isAvailable
            ? `Produkt "${data.name}" jest już dostępny!`
            : `Produkt "${data.name}" jest obecnie niedostępny.`;
        
        window.showNotification(message, isAvailable ? 'success' : 'warning', 8000);
    }
});

// ----- FUNKCJE POMOCNICZE -----

// Aktualizacja statusu połączenia
function updateConnectionStatus(status) {
    // Jeśli istnieje element do wyświetlania statusu
    const statusIndicator = document.getElementById('socket-status');
    if (!statusIndicator) return;
    
    // Dostosuj wygląd wskaźnika
    statusIndicator.classList.remove('bg-green-500', 'bg-red-500', 'bg-yellow-500', 'bg-gray-500', 'animate-pulse');
    
    if (status === 'connected') {
        statusIndicator.classList.add('bg-green-500');
        statusIndicator.title = 'Połączono z systemem powiadomień';
        // Animacja zanikająca po połączeniu
        statusIndicator.classList.add('animate-pulse');
        setTimeout(() => statusIndicator.classList.remove('animate-pulse'), 2000);
    } else if (status === 'disconnected') {
        statusIndicator.classList.add('bg-yellow-500');
        statusIndicator.title = 'Rozłączono - próba ponownego połączenia';
        statusIndicator.classList.add('animate-pulse');
    } else if (status === 'error') {
        statusIndicator.classList.add('bg-red-500');
        statusIndicator.title = 'Błąd połączenia z serwerem powiadomień';
    } else if (status === 'connecting') {
        statusIndicator.classList.add('bg-gray-500');
        statusIndicator.title = 'Łączenie z serwerem...';
        statusIndicator.classList.add('animate-pulse');
    }
    
    // Zapisz status połączenia w localStorage aby śledzić problemy
    try {
        const connectionLog = JSON.parse(localStorage.getItem('socket_connection_log') || '[]');
        connectionLog.push({
            status: status,
            timestamp: new Date().toISOString()
        });
        
        // Zachowaj ostatnie 20 wpisów
        if (connectionLog.length > 20) {
            connectionLog.shift();
        }
        
        localStorage.setItem('socket_connection_log', JSON.stringify(connectionLog));
    } catch (e) {
        console.error('Failed to log connection status:', e);
    }
}

// Funkcja do wysyłania powiadomienia o aktualizacji koszyka
function emitCartUpdate(productData, count, sum) {
    if (!socketConnected) return;
    
    socket.emit('cart_updated', {
        product: productData,
        count: count,
        sum: sum
    });
}

// Funkcja do śledzenia dostępności produktu
function watchProductAvailability(productId) {
    if (!socketConnected) {
        console.warn('Not connected to Socket.IO server. Cannot watch product availability.');
        return false;
    }
    
    socket.emit('watch_product', { product_id: productId });
    console.log('Now watching availability for product:', productId);
    return true;
}

// Funkcja do wyświetlania powiadomień debugowych
function showDebugNotification(message) {
    // Pokaż powiadomienia debugowe tylko gdy włączony jest tryb debug
    if (localStorage.getItem('socket_debug_mode') === 'true' && window.showNotification) {
        window.showNotification('Debug: ' + message, 'info', 3000);
    }
}

// Funkcja do sprawdzenia statusu połączenia
function getConnectionStatus() {
    return {
        connected: socketConnected,
        attempts: connectionAttempts,
        id: socket.id
    };
}

// Eksport funkcji do globalnego obiektu window
window.socketEmitCartUpdate = emitCartUpdate;
window.socketWatchProductAvailability = watchProductAvailability;
window.socketDebugMode = function(enable) {
    localStorage.setItem('socket_debug_mode', enable ? 'true' : 'false');
    console.log('Socket.IO debug mode:', enable ? 'enabled' : 'disabled');
    return enable;
};
window.socketGetStatus = getConnectionStatus;
