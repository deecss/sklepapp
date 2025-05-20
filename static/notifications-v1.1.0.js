/**
 * System powiadomień dla sklepu
 * Dodaje funkcję showNotification do globalnego obiektu window
 * 
 * @version 1.1.0
 * @changelog
 * 1.1.0 - Dodano obsługę pointer-events-auto i poprawiono animacje
 * 1.0.0 - Pierwsza wersja
 */

document.addEventListener('DOMContentLoaded', function() {
    /**
     * Wyświetla powiadomienie użytkownikowi
     * @param {string} message - Treść powiadomienia
     * @param {string} type - Typ powiadomienia: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Czas wyświetlania w milisekundach, 0 dla powiadomień trwałych
     * @returns {HTMLElement} Element powiadomienia
     */
    window.showNotification = function(message, type = 'info', duration = 5000) {
        const notificationArea = document.getElementById('notification-area');
        if (!notificationArea) return null;
        
        // Wybierz odpowiednie kolory i ikony zależnie od typu powiadomienia
        const typeStyles = {
            success: {
                bg: 'bg-green-100',
                border: 'border-green-500',
                text: 'text-green-800',
                icon: '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />'
            },
            error: {
                bg: 'bg-red-100',
                border: 'border-red-500',
                text: 'text-red-800',
                icon: '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />'
            },
            warning: {
                bg: 'bg-yellow-100',
                border: 'border-yellow-500',
                text: 'text-yellow-800',
                icon: '<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />'
            },
            info: {
                bg: 'bg-blue-100',
                border: 'border-blue-500',
                text: 'text-blue-800',
                icon: '<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />'
            }
        };
        
        // Użyj domyślnego stylu, jeśli podany typ nie istnieje
        const style = typeStyles[type] || typeStyles.info;
        
        // Utwórz element powiadomienia z animacją
        const notification = document.createElement('div');
        notification.className = `p-4 mb-3 rounded-lg flex items-center shadow-lg transition transform translate-x-0 
                                ${style.bg} ${style.text} border-l-4 ${style.border} pointer-events-auto`;
        
        notification.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 ${style.text}" viewBox="0 0 20 20" fill="currentColor">
                ${style.icon}
            </svg>
            <div class="flex-grow">${message}</div>
            <button class="text-gray-500 hover:text-gray-700 focus:outline-none ml-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
            </button>
        `;
        
        // Utwórz animację wejścia
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        
        // Dodanie obsługi zamknięcia powiadomienia
        notification.querySelector('button').addEventListener('click', function() {
            closeNotification(notification);
        });
        
        // Dodanie do obszaru powiadomień
        notificationArea.appendChild(notification);
        
        // Uruchom animację wejścia
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        }, 10);
        
        // Automatyczne usunięcie po określonym czasie
        if (duration > 0) {
            setTimeout(() => {
                closeNotification(notification);
            }, duration);
        }
        
        return notification;
    };
    
    /**
     * Zamyka powiadomienie z animacją
     * @param {HTMLElement} notification - Element powiadomienia
     */
    function closeNotification(notification) {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }
});
