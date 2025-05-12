/**
 * Compatibility Finder Application
 * Main JavaScript functionality
 */

function compatibilityApp() {
    return {
        searchInput: '',
        isLoading: false,
        hasSearched: false,
        errorMessage: '',
        currentSku: '',
        productDetails: null,
        compatibleProducts: [],
        searchHistory: [],
        
        /**
         * Initialize the application
         */
        init() {
            // Get search history from server-side rendered data
            const historyList = document.getElementById('historyList');
            if (historyList && historyList.dataset.history) {
                try {
                    this.searchHistory = JSON.parse(historyList.dataset.history);
                } catch (e) {
                    console.error('Error parsing search history:', e);
                    this.searchHistory = [];
                }
            }
        },
        
        /**
         * Submit the search form
         */
        submitSearch() {
            if (!this.searchInput.trim()) {
                this.errorMessage = 'Please enter a SKU number';
                return;
            }
            
            this.searchSku(this.searchInput);
        },
        
        /**
         * Search for a specific SKU
         * @param {string} sku - The SKU to search for
         */
        searchSku(sku) {
            this.isLoading = true;
            this.errorMessage = '';
            this.hasSearched = true;
            this.currentSku = sku;
            
            // Create form data for the request
            const formData = new FormData();
            formData.append('sku', sku);
            
            // Send the search request
            fetch('/search', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                this.isLoading = false;
                
                // Update search history
                if (data.search_history) {
                    this.searchHistory = data.search_history;
                }
                
                if (data.success) {
                    // Display results
                    this.productDetails = data.product;
                    this.compatibleProducts = data.compatibles || [];
                    this.currentSku = data.sku;
                    this.errorMessage = '';
                } else {
                    // Display error message
                    this.productDetails = null;
                    this.compatibleProducts = [];
                    this.errorMessage = data.message || 'An error occurred during the search';
                }
            })
            .catch(error => {
                console.error('Search error:', error);
                this.isLoading = false;
                this.productDetails = null;
                this.compatibleProducts = [];
                this.errorMessage = 'A network error occurred. Please try again.';
            });
        },
        
        /**
         * Check if a product is a combo (has main + secondary product)
         * @param {object} product - The product to check
         * @returns {boolean} True if the product is a combo
         */
        isComboProduct(product) {
            return product && product.is_combo === true;
        },
        
        /**
         * Get a placeholder image URL for products without images
         * @returns {string} The placeholder image URL
         */
        getPlaceholderImage() {
            return 'https://via.placeholder.com/150x150?text=No+Image';
        },
        
        /**
         * Format a product display name
         * @param {object} product - The product object
         * @returns {string} The formatted name with dimensions
         */
        formatProductName(product) {
            if (!product) return '';
            let name = product.name || '';
            if (product.nominal_dimensions) {
                name += ` (${product.nominal_dimensions})`;
            }
            return name;
        }
    };
}

// Initialize AlpineJS data on page load
document.addEventListener('alpine:init', () => {
    // Any additional Alpine.js component registrations can go here
});
