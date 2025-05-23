/**
 * Enhanced Notification System v1.1.0
 * A reusable notification system for the shop application
 * 
 * Features:
 * - Centralized notifications appearing in the same location
 * - Four notification types: success, error, warning, info
 * - Animation effects
 * - Auto-dismiss with progress indicator
 * - Manual dismiss
 * - Pause on hover
 * - Notification stacking and queue management
 * 
 * Usage:
 * 1. Include this script in your application
 * 2. Use showNotification(message, type, duration) to display notifications
 * 
 * Example:
 * showNotification('Product saved successfully', 'success');
 * showNotification('An error occurred', 'error');
 * showNotification('This is a warning', 'warning');
 * showNotification('For your information', 'info');
 */

document.addEventListener('DOMContentLoaded', function() {
    // Create styles for notifications
    createNotificationStyles();
    
    // Create container for notifications
    createNotificationContainer();
    
    // Notification queue for managing multiple notifications
    const notificationQueue = [];
    const MAX_VISIBLE_NOTIFICATIONS = 3;
    
    /**
     * Wyświetla powiadomienie użytkownikowi
     * @param {string} message - Treść powiadomienia
     * @param {string} type - Typ powiadomienia: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Czas wyświetlania w milisekundach, 0 dla powiadomień trwałych
     * @returns {HTMLElement} Element powiadomienia
     */
    window.showNotification = function(message, type = 'info', duration = 5000) {
        // If container doesn't exist, create it
        let container = document.querySelector('.toast-container');
        if (!container) {
            createNotificationContainer();
            container = document.querySelector('.toast-container');
        }
        
        // Check if we should queue this notification
        const visibleNotifications = document.querySelectorAll('.toast-notification.show').length;
        
        if (visibleNotifications >= MAX_VISIBLE_NOTIFICATIONS) {
            // Queue the notification for later
            notificationQueue.push({ message, type, duration });
            return null;
        }
        
        // Set appropriate icon based on notification type
        let icon = getNotificationIcon(type);
        
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        
        // Create content structure
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
                <span class="toast-close">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </span>
            </div>
            <div class="toast-progress"></div>
        `;
        
        // Add to container
        container.appendChild(toast);
        
        // Add event listener to close button
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            closeNotification(toast);
        });
        
        // Add the show class to trigger animation after a short delay
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Automatically remove the toast after specified duration (default: 5 seconds)
        if (duration > 0) {
            const toastTimeout = setTimeout(() => {
                closeNotification(toast);
            }, duration);
            
            // Store timeout reference on the toast element
            toast.toastTimeout = toastTimeout;
            
            // Set the duration for the progress bar animation
            const progressBar = toast.querySelector('.toast-progress');
            progressBar.style.animation = `progress ${duration / 1000}s linear forwards`;
            
            // Pause timeout on hover and resume on mouseout
            toast.addEventListener('mouseenter', () => {
                clearTimeout(toast.toastTimeout);
                // Also pause progress bar animation
                progressBar.style.animationPlayState = 'paused';
            });
            
            toast.addEventListener('mouseleave', () => {
                toast.toastTimeout = setTimeout(() => closeNotification(toast), duration / 2);
                // Resume progress bar animation
                progressBar.style.animationPlayState = 'running';
            });
        } else {
            // If duration is 0 or negative, remove the progress bar
            const progressBar = toast.querySelector('.toast-progress');
            if (progressBar) progressBar.remove();
        }
        
        return toast;
    };
    
    /**
     * Zamyka powiadomienie z animacją
     * @param {HTMLElement} toast - Element powiadomienia
     */
    function closeNotification(toast) {
        if (!toast || !toast.parentNode) return;
        
        // Clear any existing timeout
        if (toast.toastTimeout) {
            clearTimeout(toast.toastTimeout);
        }
        
        // Add hide class for exit animation
        toast.classList.add('hide');
        toast.classList.remove('show');
        
        // Remove from DOM after animation completes
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
            // Process the queue after a toast is removed
            processNotificationQueue();
        }, 300);
    }
    
    /**
     * Process the notification queue
     */
    function processNotificationQueue() {
        if (notificationQueue.length > 0 && document.querySelectorAll('.toast-notification.show').length < MAX_VISIBLE_NOTIFICATIONS) {
            const next = notificationQueue.shift();
            showNotification(next.message, next.type, next.duration);
            
            // Continue processing if there are more in queue
            setTimeout(processNotificationQueue, 500);
        }
    }
    
    /**
     * Create the notification container
     */
    function createNotificationContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
    
    /**
     * Create the notification styles
     */
    function createNotificationStyles() {
        if (document.getElementById('notification-styles')) return;
        
        const styleElement = document.createElement('style');
        styleElement.id = 'notification-styles';
        styleElement.textContent = `
            /* Toast Container */
            .toast-container {
                position: fixed;
                bottom: 1.5rem;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
                z-index: 9999;
                width: 100%;
                max-width: 400px;
                pointer-events: none;
            }
            
            /* Toast Notification */
            .toast-notification {
                position: relative;
                padding: 1rem 1.25rem;
                color: white;
                border-radius: 0.375rem;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                opacity: 0;
                transform: translateY(30px) scale(0.9);
                transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), 
                            opacity 0.3s ease;
                width: 100%;
                display: flex;
                align-items: center;
                border-left: 4px solid rgba(255,255,255,0.5);
                pointer-events: auto;
                min-height: 60px;
                overflow: hidden;
            }
            
            .toast-notification:before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(to right, rgba(255,255,255,0.1), transparent);
                pointer-events: none;
            }
            
            .toast-notification.show {
                transform: translateY(0) scale(1);
                opacity: 1;
                animation: slideInUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
            }
            
            .toast-notification.hide {
                animation: slideOutDown 0.3s forwards;
            }
            
            /* Notification Types */
            .toast-notification.success {
                background-color: #10b981;
                border-left-color: #059669;
            }
            
            .toast-notification.error {
                background-color: #ef4444;
                border-left-color: #b91c1c;
            }
            
            .toast-notification.warning {
                background-color: #f59e0b;
                border-left-color: #b45309;
            }
            
            .toast-notification.info {
                background-color: #3b82f6;
                border-left-color: #1d4ed8;
            }
            
            /* Content Structure */
            .toast-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                width: 100%;
            }
            
            .toast-icon {
                flex-shrink: 0;
                margin-right: 0.75rem;
                animation: pulse 2s infinite;
            }
            
            .toast-message {
                flex-grow: 1;
                font-weight: 500;
            }
            
            .toast-close {
                flex-shrink: 0;
                margin-left: 0.75rem;
                opacity: 0.7;
                cursor: pointer;
                transition: opacity 0.2s;
            }
            
            .toast-close:hover {
                opacity: 1;
            }
            
            /* Progress Bar */
            .toast-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background-color: rgba(255,255,255,0.3);
                width: 100%;
                animation: progress 5s linear forwards;
            }
            
            /* Stacked notification effect */
            .toast-container .toast-notification:nth-child(n+2) {
                margin-top: -40px;
                z-index: calc(9999 - var(--index, 0));
            }
            
            .toast-container .toast-notification.show:nth-child(n+2) {
                margin-top: 0.75rem;
                transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), 
                           opacity 0.3s ease,
                           margin-top 0.3s ease 0.1s;
            }
            
            /* Hover effect */
            .toast-notification:hover {
                transform: translateY(-3px) scale(1.02) !important;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
            
            /* Animations */
            @keyframes slideInUp {
                from {
                    transform: translateY(50px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOutDown {
                from {
                    transform: translateY(0);
                    opacity: 1;
                }
                to {
                    transform: translateY(50px);
                    opacity: 0;
                }
            }
            
            @keyframes pulse {
                0% {
                    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.4);
                }
                70% {
                    box-shadow: 0 0 0 10px rgba(255, 255, 255, 0);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
                }
            }
            
            @keyframes progress {
                from { width: 100%; }
                to { width: 0%; }
            }
        `;
        
        document.head.appendChild(styleElement);
    }
    
    /**
     * Get the appropriate icon for a notification type
     * @param {string} type - Notification type
     * @returns {string} HTML for the icon
     */
    function getNotificationIcon(type) {
        switch (type) {
            case 'success':
                return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>`;
            case 'error':
                return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>`;
            case 'warning':
                return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>`;
            case 'info':
            default:
                return `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>`;
        }
    }
    
    // Convenience functions for different notification types
    window.showSuccessNotification = function(message, duration) {
        return showNotification(message, 'success', duration);
    };
    
    window.showErrorNotification = function(message, duration) {
        return showNotification(message, 'error', duration);
    };
    
    window.showWarningNotification = function(message, duration) {
        return showNotification(message, 'warning', duration);
    };
    
    window.showInfoNotification = function(message, duration) {
        return showNotification(message, 'info', duration);
    };
});
