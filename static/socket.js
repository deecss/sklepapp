// Skrypt do obsługi WebSocket (Flask-SocketIO)
var socket;

// Inicjalizacja Socket.IO z obsługą błędów
try {
    socket = io({
        transports: ['polling', 'websocket'],
        timeout: 20000,
        forceNew: true
    });
    
    socket.on('connect', function() {
        console.log('Socket.IO połączony pomyślnie');
    });
    
    socket.on('disconnect', function() {
        console.log('Socket.IO rozłączony');
    });
    
    socket.on('connect_error', function(error) {
        console.log('Błąd połączenia Socket.IO:', error);
    });
    
} catch (error) {
    console.log('Błąd inicjalizacji Socket.IO:', error);
    // Jeśli Socket.IO nie może się połączyć, aplikacja powinna działać bez niego
}

// Przykład: powiadomienie o nowym produkcie
if (socket) {
    socket.on('new_product', function(data) {
        showNotification(`Nowy produkt: ${data.name} (${data.price} zł)`, 'info');
    });

    // Aktualizacja koszyka
    socket.on('cart_update', function(data) {
        const cartCount = document.getElementById('cart-count');
        const cartSum = document.getElementById('cart-sum');
        
        if (cartCount) cartCount.textContent = data.count;
        if (cartSum) cartSum.textContent = data.sum;
    });
}

// Funkcja do wyświetlania powiadomień
function showNotification(message, type = 'info') {
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) return;
    
    const notification = document.createElement('div');
    
    notification.className = `p-4 rounded-lg shadow-lg mb-3 transition-all duration-500 transform translate-x-0 ${
        type === 'success' ? 'bg-green-500 text-white' : 
        type === 'error' ? 'bg-red-500 text-white' : 
        'bg-blue-500 text-white'
    }`;
    
    notification.textContent = message;
    notificationArea.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}
