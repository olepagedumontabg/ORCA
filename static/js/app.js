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
        results: [],
        searchHistory: [],
        productInfo: {},
        
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
                    this.results = data.data;
                    this.currentSku = data.sku;
                    this.productInfo = data.product || {};
                    this.errorMessage = '';
                } else {
                    // Display error message
                    this.results = [];
                    this.productInfo = {};
                    this.errorMessage = data.message || 'An error occurred during the search';
                }
            })
            .catch(error => {
                console.error('Search error:', error);
                this.isLoading = false;
                this.results = [];
                this.productInfo = {};
                this.errorMessage = 'A network error occurred. Please try again.';
            });
        },
    };
}

// Initialize AlpineJS data on page load
document.addEventListener('alpine:init', () => {
    // Any additional Alpine.js component registrations can go here
});
