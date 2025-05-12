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
        filteredCompatibleProducts: [],
        searchHistory: [],
        
        // Filtering options
        filters: {
            series: '',
            brand: '',
            glassThickness: '',
            dimensionMin: '',
            dimensionMax: '',
            selectedCategories: []
        },
        
        // UI state for filters
        showFilters: false,
        availableFilters: {
            series: [],
            brands: [],
            glassThicknesses: ['6mm', '8mm'],
            categories: []
        },
        
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
                    this.filteredCompatibleProducts = [...this.compatibleProducts]; // Initialize filtered results
                    this.currentSku = data.sku;
                    this.errorMessage = '';
                    
                    // Extract filter options from results
                    this.extractFilterOptions();
                    
                    // Reset filters to default
                    this.resetFilters();
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
         * Uses a better product-specific placeholder based on the product name if available
         * @param {string} productName - Optional product name to use in the placeholder
         * @returns {string} The placeholder image URL
         */
        getPlaceholderImage(productName) {
            // Check if we can determine a category-based image
            if (productName) {
                // Look for key words in the product name to determine image type
                productName = productName.toLowerCase();
                
                if (productName.includes('b3round') || (productName.includes('round') && productName.includes('base'))) {
                    return '/static/images/products/b3round.jpg';
                }
                
                if (productName.includes('b3square') || (productName.includes('square') && productName.includes('base'))) {
                    return '/static/images/products/b3square.jpg';
                }
                
                if (productName.includes('door')) {
                    return '/static/images/products/shower_door.jpg';
                }
                
                if (productName.includes('wall')) {
                    return '/static/images/products/shower_wall.jpg';
                }
                
                if (productName.includes('panel') || productName.includes('return')) {
                    return '/static/images/products/return_panel.jpg';
                }
                
                if (productName.includes('base') || productName.includes('shower base')) {
                    return '/static/images/products/b3square.jpg';
                }
                
                // If no matching category, create a generic placeholder with the product name
                const cleanName = productName.replace(/[^a-zA-Z0-9 ]/g, '')
                                           .replace(/\s+/g, '+')
                                           .substring(0, 20);
                return `https://via.placeholder.com/300x200?text=${cleanName}`;
            }
            
            return '/static/images/products/b3square.jpg'; // Default
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
        },
        
        /**
         * Apply filters to compatible products
         */
        applyFilters() {
            // Start with a copy of the original compatible products
            this.filteredCompatibleProducts = JSON.parse(JSON.stringify(this.compatibleProducts));
            
            // Apply category filters if any are selected
            if (this.filters.selectedCategories.length > 0) {
                this.filteredCompatibleProducts = this.filteredCompatibleProducts.filter(category => 
                    this.filters.selectedCategories.includes(category.category)
                );
            }
            
            // Apply product-level filters to each category's products
            this.filteredCompatibleProducts.forEach(category => {
                if (!category.products) return;
                
                // Filter the products in this category
                category.products = category.products.filter(product => {
                    // Return early if it's a combo product - special handling
                    if (this.isComboProduct(product)) {
                        return this.filterMatchesProduct(product.main_product) || 
                               this.filterMatchesProduct(product.secondary_product);
                    }
                    
                    // Regular product filtering
                    return this.filterMatchesProduct(product);
                });
            });
            
            // Remove empty categories
            this.filteredCompatibleProducts = this.filteredCompatibleProducts.filter(
                category => category.products && category.products.length > 0
            );
        },
        
        /**
         * Check if a product matches the current filters
         * @param {object} product - The product to check
         * @returns {boolean} True if the product matches all filters
         */
        filterMatchesProduct(product) {
            if (!product) return false;
            
            // Series filter
            if (this.filters.series && product.series) {
                if (!product.series.toLowerCase().includes(this.filters.series.toLowerCase())) {
                    return false;
                }
            }
            
            // Brand filter
            if (this.filters.brand && product.brand) {
                if (!product.brand.toLowerCase().includes(this.filters.brand.toLowerCase())) {
                    return false;
                }
            }
            
            // Glass thickness filter
            if (this.filters.glassThickness && product.name) {
                if (!product.name.toLowerCase().includes(this.filters.glassThickness.toLowerCase())) {
                    return false;
                }
            }
            
            // Dimension range filters
            if (product.nominal_dimensions) {
                const dimensions = product.nominal_dimensions;
                
                // Extract numeric values from dimensions
                // Typical format: "48 x 36" or "56-59 x 71"
                const match = dimensions.match(/(\d+)(?:-\d+)?\s*x\s*(\d+)/);
                if (match) {
                    const width = parseInt(match[1]);
                    const height = parseInt(match[2]);
                    
                    // Check min width filter
                    if (this.filters.dimensionMin && !isNaN(parseInt(this.filters.dimensionMin))) {
                        if (width < parseInt(this.filters.dimensionMin)) {
                            return false;
                        }
                    }
                    
                    // Check max width filter
                    if (this.filters.dimensionMax && !isNaN(parseInt(this.filters.dimensionMax))) {
                        if (width > parseInt(this.filters.dimensionMax)) {
                            return false;
                        }
                    }
                }
            }
            
            // All filters passed
            return true;
        },
        
        /**
         * Extract available filter options from the results
         */
        extractFilterOptions() {
            // Reset available filters
            this.availableFilters.series = [];
            this.availableFilters.brands = [];
            this.availableFilters.categories = [];
            
            // Series & brands come from all products
            const seriesSet = new Set();
            const brandsSet = new Set();
            
            // Categories come from the results
            this.compatibleProducts.forEach(category => {
                // Add category to available categories
                this.availableFilters.categories.push(category.category);
                
                // Process products within this category
                if (!category.products) return;
                
                category.products.forEach(product => {
                    // Handle combo products
                    if (this.isComboProduct(product)) {
                        if (product.main_product) {
                            if (product.main_product.series) seriesSet.add(product.main_product.series);
                            if (product.main_product.brand) brandsSet.add(product.main_product.brand);
                        }
                        if (product.secondary_product) {
                            if (product.secondary_product.series) seriesSet.add(product.secondary_product.series);
                            if (product.secondary_product.brand) brandsSet.add(product.secondary_product.brand);
                        }
                    } 
                    // Regular products
                    else {
                        if (product.series) seriesSet.add(product.series);
                        if (product.brand) brandsSet.add(product.brand);
                    }
                });
            });
            
            // Convert sets to arrays
            this.availableFilters.series = [...seriesSet].sort();
            this.availableFilters.brands = [...brandsSet].sort();
        },
        
        /**
         * Reset all filters to default values
         */
        resetFilters() {
            this.filters = {
                series: '',
                brand: '',
                glassThickness: '',
                dimensionMin: '',
                dimensionMax: '',
                selectedCategories: []
            };
            
            // Apply the reset filters
            this.applyFilters();
        },
        
        /**
         * Toggle a category selection in filters
         * @param {string} category - The category to toggle
         */
        toggleCategoryFilter(category) {
            const index = this.filters.selectedCategories.indexOf(category);
            if (index === -1) {
                // Category not selected, add it
                this.filters.selectedCategories.push(category);
            } else {
                // Category already selected, remove it
                this.filters.selectedCategories.splice(index, 1);
            }
            
            // Apply the updated filters
            this.applyFilters();
        }
    };
}

// Initialize AlpineJS data on page load
document.addEventListener('alpine:init', () => {
    // Any additional Alpine.js component registrations can go here
});
