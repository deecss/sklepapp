// Category dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    // Add a fade-in animation class to the stylesheet
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
            animation: fadeIn 0.2s ease-out forwards;
        }
    `;
    document.head.appendChild(style);

    // Mobile categories toggle
    const mobileCategories = document.getElementById('mobileCategories');
    const mobileCategoriesList = document.getElementById('mobileCategoriesList');
    const mobileCategoriesIcon = document.getElementById('mobileCategoriesIcon');
    
    if (mobileCategories && mobileCategoriesList && mobileCategoriesIcon) {
        mobileCategories.addEventListener('click', function() {
            mobileCategoriesList.classList.toggle('hidden');
            mobileCategoriesIcon.classList.toggle('rotate-180');
            
            // Apply animation class if showing
            if (!mobileCategoriesList.classList.contains('hidden')) {
                mobileCategoriesList.classList.add('animate-fadeIn');
            }
        });
    }
    
    // Mobile main category toggle in the mobile menu
    const mobileDropdown = document.querySelector('.mobile-dropdown');
    if (mobileDropdown) {
        const dropdownIcon = mobileDropdown.querySelector('.mobile-dropdown-main-icon');
        const dropdownMenu = mobileDropdown.querySelector('.mobile-categories-menu');
        
        mobileDropdown.querySelector('div').addEventListener('click', function() {
            dropdownMenu.classList.toggle('hidden');
            dropdownIcon.classList.toggle('rotate-180');
            
            // Apply animation class if showing
            if (!dropdownMenu.classList.contains('hidden')) {
                dropdownMenu.classList.add('animate-fadeIn');
            }
        });
    }
    
    // Category dropdowns (mobile)
    const mobileCategoryToggles = document.querySelectorAll('.mobile-category-toggle');
    mobileCategoryToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            // Get the icon and the menu
            const icon = this.querySelector('.mobile-dropdown-icon');
            const menu = this.parentElement.querySelector('.mobile-subcategory-menu');
            
            // Only handle the click if it's on the toggle area itself or the icon, not on the link
            if (e.target === this || e.target === icon || (e.target.nodeName !== 'A' && this.contains(e.target))) {
                e.preventDefault();
                
                // Toggle the icon rotation
                if (icon) icon.classList.toggle('rotate-180');
                
                // Toggle the menu
                if (menu) {
                    menu.classList.toggle('hidden');
                    
                    // Apply animation class if showing
                    if (!menu.classList.contains('hidden')) {
                        menu.classList.add('animate-fadeIn');
                    }
                }
            }
        });
    });
    
    // Subcategory dropdowns (mobile)
    const mobileSubcategoryToggles = document.querySelectorAll('.mobile-subcategory-toggle');
    mobileSubcategoryToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            // Get the icon and the menu
            const icon = this.querySelector('.mobile-dropdown-icon');
            const menu = this.parentElement.querySelector('.mobile-subsubcategory-menu');
            
            // Only handle the click if it's on the toggle area itself or the icon, not on the link
            if (e.target === this || e.target === icon || (e.target.nodeName !== 'A' && this.contains(e.target))) {
                e.preventDefault();
                
                // Toggle the icon rotation
                if (icon) icon.classList.toggle('rotate-180');
                
                // Toggle the menu
                if (menu) {
                    menu.classList.toggle('hidden');
                    
                    // Apply animation class if showing
                    if (!menu.classList.contains('hidden')) {
                        menu.classList.add('animate-fadeIn');
                    }
                }
            }
        });
    });
    
    // Category dropdowns (desktop)
    const categoryDropdowns = document.querySelectorAll('.category-dropdown');
    categoryDropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('div');
        const icon = dropdown.querySelector('.dropdown-icon');
        const menu = dropdown.querySelector('.subcategory-menu');
        
        if (toggle && menu) {
            toggle.addEventListener('click', function(e) {
                // Prevent opening the link when toggling the dropdown
                if (e.target === this || e.target === icon || (e.target.nodeName !== 'A' && this.contains(e.target))) {
                    e.preventDefault();
                    
                    // Close all other open category menus
                    categoryDropdowns.forEach(otherDropdown => {
                        if (otherDropdown !== dropdown) {
                            const otherMenu = otherDropdown.querySelector('.subcategory-menu');
                            const otherIcon = otherDropdown.querySelector('.dropdown-icon');
                            
                            if (otherMenu && !otherMenu.classList.contains('hidden')) {
                                otherMenu.classList.add('hidden');
                                if (otherIcon) otherIcon.classList.remove('rotate-180');
                            }
                        }
                    });
                    
                    // Toggle the rotation of the icon
                    if (icon) icon.classList.toggle('rotate-180');
                    
                    // Toggle the subcategory menu
                    menu.classList.toggle('hidden');
                    
                    // Apply animation class if showing
                    if (!menu.classList.contains('hidden')) {
                        menu.classList.add('animate-fadeIn');
                    }
                }
            });
        }
    });
    
    // Subcategory dropdowns (desktop)
    const subcategoryDropdowns = document.querySelectorAll('.subcategory-dropdown');
    subcategoryDropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('div');
        const icon = dropdown.querySelector('.dropdown-icon');
        const menu = dropdown.querySelector('.subsubcategory-menu');
        
        if (toggle && menu) {
            toggle.addEventListener('click', function(e) {
                // Prevent opening the link when toggling the dropdown
                if (e.target === this || e.target === icon || (e.target.nodeName !== 'A' && this.contains(e.target))) {
                    e.preventDefault();
                    
                    // Close all other open subcategory menus at this level
                    const parentSubcategoryList = dropdown.parentElement;
                    if (parentSubcategoryList) {
                        const siblingDropdowns = parentSubcategoryList.querySelectorAll('.subcategory-dropdown');
                        siblingDropdowns.forEach(otherDropdown => {
                            if (otherDropdown !== dropdown) {
                                const otherMenu = otherDropdown.querySelector('.subsubcategory-menu');
                                const otherIcon = otherDropdown.querySelector('.dropdown-icon');
                                
                                if (otherMenu && !otherMenu.classList.contains('hidden')) {
                                    otherMenu.classList.add('hidden');
                                    if (otherIcon) otherIcon.classList.remove('rotate-180');
                                }
                            }
                        });
                    }
                    
                    // Toggle the rotation of the icon
                    if (icon) icon.classList.toggle('rotate-180');
                    
                    // Toggle the subsubcategory menu
                    menu.classList.toggle('hidden');
                    
                    // Apply animation class if showing
                    if (!menu.classList.contains('hidden')) {
                        menu.classList.add('animate-fadeIn');
                    }
                }
            });
        }
    });
});
