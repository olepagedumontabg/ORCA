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
        
        // On initialization, fix the filter panel width
        init() {
            // Initial fix for filter panel width
            this.fixFilterPanelWidth();
            
            // Fix width after DOM loaded
            document.addEventListener('DOMContentLoaded', () => {
                this.fixFilterPanelWidth();
            });
            
            // Also fix filter panel width after each search
            this.$watch('compatibleProducts', () => {
                // Fix immediately and then again after a short delay
                this.fixFilterPanelWidth();
                setTimeout(() => this.fixFilterPanelWidth(), 100);
                setTimeout(() => this.fixFilterPanelWidth(), 500);
            });
            
            // Fix width when filters change
            this.$watch('filters', () => {
                // Fix immediately and then again after a short delay
                this.fixFilterPanelWidth();
                setTimeout(() => this.fixFilterPanelWidth(), 100);
            }, { deep: true });
            
            // Fix width on window resize
            window.addEventListener('resize', () => {
                this.fixFilterPanelWidth();
            });
            
            // Set an interval to check and fix the width periodically
            setInterval(() => {
                if (this.compatibleProducts.length > 0) {
                    this.fixFilterPanelWidth();
                }
            }, 1000);
        },
        
        // Function to enforce fixed width on the filter panel
        fixFilterPanelWidth() {
            // Fix the sidebar width - more aggressive approach
            const sidebar = document.querySelector('.filter-sidebar');
            if (sidebar) {
                sidebar.style.cssText = "width: 260px !important; min-width: 260px !important; max-width: 260px !important; flex: 0 0 260px !important; padding: 0 !important; margin: 0 !important; box-sizing: border-box !important; overflow: hidden !important;";
            }
            
            // Fix the sticky container inside sidebar
            const stickyContainer = document.querySelector('.filter-sidebar > div');
            if (stickyContainer) {
                stickyContainer.style.cssText = "width: 260px !important; min-width: 260px !important; max-width: 260px !important; padding: 0 !important; margin: 0 !important; box-sizing: border-box !important; overflow: hidden !important;";
            }
            
            // Fix every filter-related element
            document.querySelectorAll('.filter-header, .filter-container, .filter-section').forEach(el => {
                el.style.cssText = "width: 260px !important; min-width: 260px !important; max-width: 260px !important; padding: 0 !important; box-sizing: border-box !important; overflow: hidden !important;";
            });
            
            // Fix the header table and its contents
            const headerTable = document.querySelector('.filter-header table');
            if (headerTable) {
                headerTable.style.cssText = "width: 260px !important; min-width: 260px !important; max-width: 260px !important; border-collapse: collapse !important; border-spacing: 0 !important; padding: 0 !important; margin: 0 !important;";
                
                // Set specific width for the first row in the table
                const headerRow = headerTable.querySelector('tr');
                if (headerRow) {
                    headerRow.style.cssText = "width: 260px !important; padding: 0 !important; margin: 0 !important;";
                }
                
                // Set specific widths for the cells
                const headerCells = headerTable.querySelectorAll('td');
                if (headerCells.length >= 2) {
                    headerCells[0].style.cssText = "width: 130px !important; text-align: left !important; padding: 0 0 8px 0 !important; margin: 0 !important;";
                    headerCells[1].style.cssText = "width: 130px !important; text-align: right !important; padding: 0 0 8px 0 !important; margin: 0 !important;";
                }
            }
        },
        
        // Make all filter labels fixed width
        makeLabelWidthConsistent() {
            document.querySelectorAll('.filter-label').forEach(label => {
                Object.assign(label.style, {
                    width: '190px',
                    minWidth: '190px',
                    maxWidth: '190px',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    display: 'inline-block',
                    fontWeight: 'normal'
                });
            });
            
            // Also fix the filter groups themselves
            document.querySelectorAll('.filter-container > div').forEach(group => {
                Object.assign(group.style, {
                    width: '260px',
                    maxWidth: '260px',
                    overflow: 'hidden',
                    borderBottom: '1px solid #eaeaea',
                    paddingBottom: '1rem',
                    marginBottom: '1rem'
                });
                
                // Add class for styling
                group.classList.add('filter-section');
            });
        },
        
        // Autocomplete suggestions
        suggestions: [],
        rawSkus: [],         // Array to store the raw SKU values
        showSuggestions: false,
        highlightedSuggestion: -1,
        
        // Filtering options
        filters: {
            selectedSeries: [],
            selectedBrands: [],
            selectedGlassThicknesses: [],
            selectedDoorTypes: [],
            selectedCategories: [],
            selectedMaterials: []
        },
        
        // UI state for filters
        showFilters: true, // Default show filters in sidebar
        
        // Dynamic filter visibility flags
        hasGlassFilter: false,  // Show glass thickness filter (for doors and panels)
        hasDoorsFilter: false,  // Show door type filter (for doors)
        hasMaterialFilter: false, // Show material filter (for bathtubs, bases, showers)
        
        availableFilters: {
            series: [],
            brands: [],
            glassThicknesses: ['6mm', '8mm'],
            doorTypes: ['Sliding', 'Pivot', 'Bypass'], // Only use the 3 door types from Excel
            categories: [],
            materials: []
        },
        
        /**
         * Convert decimal inches to a fraction format (e.g., 58.375 to "58 3/8")
         * @param {number|string} value - The decimal value to convert
         * @return {string} - The formatted value with fraction
         */
        formatInchFraction(value) {
            // If value is not a valid number, return it as is
            const num = parseFloat(value);
            if (isNaN(num)) return value;
            
            // Extract the whole number part
            const wholeNumber = Math.floor(num);
            
            // Get the decimal part
            const decimal = num - wholeNumber;
            
            // Return just the whole number if there's no decimal
            if (decimal === 0) return wholeNumber.toString();
            
            // Common fractions map with precision of 1/16
            const fractions = {
                0.0625: "1/16", 0.125: "1/8", 0.1875: "3/16", 0.25: "1/4",
                0.3125: "5/16", 0.375: "3/8", 0.4375: "7/16", 0.5: "1/2",
                0.5625: "9/16", 0.625: "5/8", 0.6875: "11/16", 0.75: "3/4",
                0.8125: "13/16", 0.875: "7/8", 0.9375: "15/16"
            };
            
            // Find the closest fraction
            let closestDiff = 1;
            let closestFraction = "";
            
            for (const [frac, notation] of Object.entries(fractions)) {
                const diff = Math.abs(decimal - parseFloat(frac));
                if (diff < closestDiff) {
                    closestDiff = diff;
                    closestFraction = notation;
                }
            }
            
            // Format the result
            return `${wholeNumber} ${closestFraction}`;
        },
        
        /**
         * Initialize the application
         */
        init() {
            // Add a global click listener to close suggestions when clicking outside
            document.addEventListener('click', (event) => {
                const containers = [
                    document.getElementById('suggestionsContainer'),
                    document.getElementById('suggestionsCompactContainer')
                ];
                
                const inputs = [
                    document.getElementById('skuInput'),
                    document.getElementById('skuInputCompact')
                ];
                
                // If the click is outside containers and inputs, hide suggestions
                if (!containers.some(container => container && container.contains(event.target)) &&
                    !inputs.some(input => input && input.contains(event.target))) {
                    this.closeSuggestions();
                }
            });
        },
        
        /**
         * Close all suggestion dropdowns
         */
        closeSuggestions() {
            const containers = [
                document.getElementById('suggestionsContainer'),
                document.getElementById('suggestionsCompactContainer')
            ];
            
            containers.forEach(container => {
                if (container) {
                    container.classList.add('hidden');
                }
            });
            
            this.highlightedSuggestion = -1;
            this.suggestions = [];
        },
        
        /**
         * Clear search input and suggestions
         */
        clearSearch() {
            this.searchInput = '';
            this.closeSuggestions();
        },
        
        /**
         * Handle input events on search fields
         * @param {Event} event - Input event
         */
        onSearchInput(event) {
            const value = event.target.value;
            
            if (value.length >= 3) {
                this.getSuggestionsDirect(value, event.target.id);
            } else {
                this.closeSuggestions();
            }
        },
        
        /**
         * Get suggestions and update DOM directly
         * @param {string} query - The search query
         * @param {string} inputId - ID of the input field that triggered the search
         */
        getSuggestionsDirect(query, inputId) {
            // Don't fetch if query is too short
            if (!query || query.length < 3) {
                this.closeSuggestions();
                return;
            }
            
            fetch(`/suggest?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    // Store raw SKUs for selection
                    this.rawSkus = data.suggestions || [];
                    
                    // Use display suggestions (SKU - Product Name) for showing in dropdown
                    this.suggestions = data.displaySuggestions || this.rawSkus;
                    
                    // Determine which container to use based on input ID
                    const isCompact = inputId === 'skuInputCompact';
                    const containerSelector = isCompact ? 'suggestionsCompactContainer' : 'suggestionsContainer';
                    const listSelector = isCompact ? 'suggestionsCompactList' : 'suggestionsList';
                    
                    const container = document.getElementById(containerSelector);
                    const list = document.getElementById(listSelector);
                    
                    if (container && list) {
                        // Clear previous suggestions
                        list.innerHTML = '';
                        
                        if (this.suggestions.length > 0) {
                            // Add new suggestions
                            this.suggestions.forEach((suggestion, index) => {
                                const li = document.createElement('li');
                                li.className = 'px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer';
                                li.textContent = suggestion;
                                
                                // Add click handler
                                li.addEventListener('click', (e) => {
                                    e.stopPropagation();
                                    this.selectSuggestionDirect(suggestion, index);
                                });
                                
                                list.appendChild(li);
                            });
                            
                            // Show the container
                            container.classList.remove('hidden');
                        } else {
                            // Hide the container if no suggestions
                            container.classList.add('hidden');
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching suggestions:', error);
                    this.closeSuggestions();
                });
        },
        
        /**
         * Handle keyboard events for search and suggestions
         * @param {Event} event - Keyboard event
         */
        onSearchKeydown(event) {
            // Determine which container to use
            const isCompact = event.target.id === 'skuInputCompact';
            const containerSelector = isCompact ? 'suggestionsCompactContainer' : 'suggestionsContainer';
            const listSelector = isCompact ? 'suggestionsCompactList' : 'suggestionsList';
            
            const container = document.getElementById(containerSelector);
            const list = document.getElementById(listSelector);
            
            if (!container || container.classList.contains('hidden')) {
                // If Enter key is pressed and we're not showing suggestions, submit the form
                if (event.keyCode === 13) {
                    this.submitSearch();
                    return;
                }
                
                return;
            }
            
            const items = list.querySelectorAll('li');
            
            // Arrow down
            if (event.keyCode === 40) {
                event.preventDefault();
                this.highlightedSuggestion = Math.min(
                    this.highlightedSuggestion + 1, 
                    items.length - 1
                );
                this.updateHighlightedItem(items);
            }
            // Arrow up
            else if (event.keyCode === 38) {
                event.preventDefault();
                this.highlightedSuggestion = Math.max(this.highlightedSuggestion - 1, -1);
                this.updateHighlightedItem(items);
            }
            // Enter key
            else if (event.keyCode === 13) {
                if (this.highlightedSuggestion >= 0 && this.highlightedSuggestion < items.length) {
                    event.preventDefault();
                    const suggestion = items[this.highlightedSuggestion].textContent;
                    this.selectSuggestionDirect(suggestion, this.highlightedSuggestion);
                } else if (items.length === 1) {
                    event.preventDefault();
                    const suggestion = items[0].textContent;
                    this.selectSuggestionDirect(suggestion, 0);
                } else {
                    this.submitSearch();
                }
            }
            // Escape key
            else if (event.keyCode === 27) {
                event.preventDefault();
                this.closeSuggestions();
            }
        },
        
        /**
         * Update the highlighted item in the suggestions list
         * @param {NodeList} items - List items to update
         */
        updateHighlightedItem(items) {
            items.forEach((item, index) => {
                if (index === this.highlightedSuggestion) {
                    item.classList.add('bg-gray-100');
                    // Scroll item into view if needed
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('bg-gray-100');
                }
            });
        },
        
        /**
         * Select a suggestion directly from DOM elements
         * @param {string} suggestion - The selected suggestion text
         * @param {number} index - The index of the suggestion
         */
        selectSuggestionDirect(suggestion, index) {
            // Extract just the SKU part (everything before the " - ")
            const skuMatch = suggestion.match(/^(.*?)(?:\s+-\s+|$)/);
            const extractedSku = skuMatch ? skuMatch[1].trim() : suggestion;
            
            // Update the search input with just the SKU
            this.searchInput = extractedSku;
            
            // Close suggestions dropdown
            this.closeSuggestions();
        },
        
        /**
         * Get SKU suggestions as user types
         * @param {string} query - The search query
         */
        getSuggestions(query) {
            // Reset highlighted suggestion
            this.highlightedSuggestion = -1;
            
            // Don't fetch if query is too short
            if (!query || query.length < 3) {
                this.suggestions = [];
                this.showSuggestions = false;
                return;
            }
            
            fetch(`/suggest?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    // Store raw SKUs for selection
                    this.rawSkus = data.suggestions || [];
                    
                    // Use display suggestions (SKU - Product Name) for showing in dropdown
                    this.suggestions = data.displaySuggestions || this.rawSkus;
                    
                    this.showSuggestions = this.suggestions.length > 0;
                })
                .catch(error => {
                    console.error('Error fetching suggestions:', error);
                    this.suggestions = [];
                    this.rawSkus = [];
                    this.showSuggestions = false;
                });
        },
        
        /**
         * Handle keyboard navigation for suggestions
         * @param {Event} event - Keyboard event
         */
        handleSuggestionKeydown(event) {
            if (!this.showSuggestions) return;
            
            // Arrow down
            if (event.keyCode === 40) {
                event.preventDefault();
                this.highlightedSuggestion = Math.min(
                    this.highlightedSuggestion + 1, 
                    this.suggestions.length - 1
                );
            }
            // Arrow up
            else if (event.keyCode === 38) {
                event.preventDefault();
                this.highlightedSuggestion = Math.max(this.highlightedSuggestion - 1, -1);
            }
            // Enter key
            else if (event.keyCode === 13 && this.highlightedSuggestion >= 0) {
                event.preventDefault();
                this.selectSuggestion(this.suggestions[this.highlightedSuggestion], this.highlightedSuggestion);
            }
            // Escape key
            else if (event.keyCode === 27) {
                this.suggestions = [];
                this.showSuggestions = false;
            }
        },
        
        /**
         * Select a suggestion from the dropdown (DEPRECATED - keeping for backward compatibility)
         * @param {string} suggestion - The selected suggestion (display format: "SKU - Product Name")
         * @param {number} index - The index of the suggestion in the list
         */
        selectAndSearch(suggestion, index) {
            // Replaced with selectSuggestion
            console.warn("selectAndSearch is deprecated - use selectSuggestion instead");
            this.selectSuggestion(suggestion, index);
        },
        
        /**
         * Select a suggestion from the dropdown
         * @param {string} suggestion - The selected suggestion (display format: "SKU - Product Name")
         * @param {number} index - The index of the suggestion in the list
         */
        selectSuggestion(suggestion, index) {
            // First, clear the dropdown
            this.suggestions = [];
            this.showSuggestions = false;
            
            // If we have raw SKUs stored and the index is valid, use the raw SKU
            if (this.rawSkus && this.rawSkus.length > index && index >= 0) {
                this.searchInput = this.rawSkus[index];
            } else {
                // Otherwise extract the SKU from the suggestion text (everything before " - ")
                const skuMatch = suggestion.match(/^(.*?)(?:\s+-\s+|$)/);
                this.searchInput = skuMatch ? skuMatch[1].trim() : suggestion;
            }
            
            // Force UI update to clear any hanging dropdown elements
            setTimeout(() => {
                this.showSuggestions = false;
            }, 100);
        },
        
        /**
         * Submit the search form
         */
        submitSearch() {
            if (!this.searchInput.trim()) {
                this.errorMessage = 'Please enter a SKU number';
                return;
            }
            
            // Hide suggestions dropdown when submitting
            this.showSuggestions = false;
            
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
            
            // Send the search request using JSON format
            fetch('/search', {
                method: 'POST',
                body: JSON.stringify({ sku: sku }),
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                // Check if the response is ok before trying to parse as JSON
                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                // Verify that we're getting JSON - check the content type
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error(`Expected JSON response but got ${contentType}`);
                }
                return response.json();
            })
            .then(data => {
                this.isLoading = false;
                
                // Search history has been removed
                
                if (data.success) {
                    // Display results
                    this.productDetails = data.product;
                    console.log("Product details received:", this.productDetails);
                    this.compatibleProducts = data.compatibles || [];
                    this.filteredCompatibleProducts = [...this.compatibleProducts]; // Initialize filtered results
                    this.currentSku = data.sku;
                    this.errorMessage = '';
                    
                    // Extract filter options from results
                    this.extractFilterOptions();
                    
                    // Set dynamic filter visibility based on product categories
                    this.setDynamicFilterVisibility();
                    
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
                
                // Provide a more specific error message
                if (error.message.includes('content-type') || error.message.includes('JSON')) {
                    this.errorMessage = 'Server returned an invalid response format. Please try again or contact support.';
                } else if (error.message.includes('status')) {
                    this.errorMessage = `Server error: ${error.message}. Please try again later.`;
                } else {
                    this.errorMessage = 'A network error occurred. Please try again.';
                }
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
            console.log("Applying filters:", this.filters);
            // Start with a copy of the original compatible products
            this.filteredCompatibleProducts = JSON.parse(JSON.stringify(this.compatibleProducts));
            
            // Apply category filters if any are selected
            if (this.filters.selectedCategories.length > 0) {
                console.log("Filtering by categories:", this.filters.selectedCategories);
                this.filteredCompatibleProducts = this.filteredCompatibleProducts.filter(category => 
                    this.filters.selectedCategories.includes(category.category)
                );
            }
            
            // Apply product-level filters to each category's products
            this.filteredCompatibleProducts.forEach(category => {
                if (!category.products) return;
                
                console.log(`Filtering products in category: ${category.category}`);
                
                // Filter the products in this category
                const originalCount = category.products.length;
                
                category.products = category.products.filter(product => {
                    // Return early if it's a combo product - special handling
                    if (this.isComboProduct(product)) {
                        // For combo products, use main_product for filtering attributes
                        if (product.main_product) {
                            const matches = this.filterMatchesMainProduct(product.main_product);
                            console.log(`  Combo product ${product.sku} match: ${matches}`, product.main_product);
                            return matches;
                        }
                        return false;
                    }
                    
                    // Regular product filtering
                    const matches = this.filterMatchesProduct(product);
                    console.log(`  Regular product ${product.sku} match: ${matches}`, product);
                    return matches;
                });
                
                console.log(`  Category ${category.category}: ${originalCount} products → ${category.products.length} after filtering`);
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
            
            console.log("filterMatchesProduct checking product:", product);
            
            // We shouldn't get combo products here, as they're handled in applyFilters
            // But just in case, we'll handle them properly
            if (this.isComboProduct(product) && product.main_product) {
                console.log("  Encountered combo product in filterMatchesProduct, forwarding to filterMatchesMainProduct");
                return this.filterMatchesMainProduct(product.main_product);
            }
            
            // Series filter - multi-select
            if (this.filters.selectedSeries.length > 0 && product.series) {
                let seriesMatch = false;
                for (let selectedSeries of this.filters.selectedSeries) {
                    if (product.series.toLowerCase() === selectedSeries.toLowerCase()) {
                        seriesMatch = true;
                        break;
                    }
                }
                if (!seriesMatch) return false;
            }
            
            // Brand filter - multi-select
            if (this.filters.selectedBrands.length > 0 && product.brand) {
                let brandMatch = false;
                for (let selectedBrand of this.filters.selectedBrands) {
                    if (product.brand.toLowerCase() === selectedBrand.toLowerCase()) {
                        brandMatch = true;
                        break;
                    }
                }
                if (!brandMatch) return false;
            }
            
            // Glass thickness filter - multi-select
            if (this.filters.selectedGlassThicknesses.length > 0) {
                // Skip glass thickness filtering if the product doesn't have glass_thickness
                if (!product.glass_thickness) {
                    console.log(`  Product ${product.sku} has no glass_thickness, skipping filter`);
                    // No glass thickness defined, so this product doesn't match the filter
                    return false;
                }
                
                let thicknessMatch = false;
                for (let selectedThickness of this.filters.selectedGlassThicknesses) {
                    if (product.glass_thickness.toLowerCase() === selectedThickness.toLowerCase()) {
                        thicknessMatch = true;
                        break;
                    }
                }
                if (!thicknessMatch) return false;
            }
            
            // Door type filter - multi-select
            if (this.filters.selectedDoorTypes.length > 0) {
                // Skip door type filtering if the product doesn't have a door_type
                if (!product.door_type) {
                    console.log(`  Product ${product.sku} has no door_type, skipping filter`);
                    // No door type defined, so this product doesn't match the filter
                    return false;
                }
                
                let doorTypeMatch = false;
                for (let selectedType of this.filters.selectedDoorTypes) {
                    if (product.door_type.toLowerCase() === selectedType.toLowerCase()) {
                        doorTypeMatch = true;
                        break;
                    }
                }
                if (!doorTypeMatch) return false;
            }
            
            // Material filter - multi-select
            if (this.filters.selectedMaterials.length > 0) {
                // Skip material filtering if the product doesn't have a material
                if (!product.material) {
                    console.log(`  Product ${product.sku} has no material, skipping filter`);
                    // No material defined, so this product doesn't match the filter
                    return false;
                }
                
                let materialMatch = false;
                for (let selectedMaterial of this.filters.selectedMaterials) {
                    if (product.material.toLowerCase() === selectedMaterial.toLowerCase()) {
                        materialMatch = true;
                        break;
                    }
                }
                if (!materialMatch) return false;
            }
            
            // All filters passed
            return true;
        },
        
        /**
         * Check if a main product in a combo matches the filters
         * @param {object} mainProduct - The main product to check
         * @returns {boolean} True if the product matches all filters
         */
        filterMatchesMainProduct(mainProduct) {
            if (!mainProduct) return false;
            
            // Series filter - multi-select
            if (this.filters.selectedSeries.length > 0 && mainProduct.series) {
                let seriesMatch = false;
                for (let selectedSeries of this.filters.selectedSeries) {
                    if (mainProduct.series.toLowerCase() === selectedSeries.toLowerCase()) {
                        seriesMatch = true;
                        break;
                    }
                }
                if (!seriesMatch) return false;
            }
            
            // Brand filter - multi-select
            if (this.filters.selectedBrands.length > 0 && mainProduct.brand) {
                let brandMatch = false;
                for (let selectedBrand of this.filters.selectedBrands) {
                    if (mainProduct.brand.toLowerCase() === selectedBrand.toLowerCase()) {
                        brandMatch = true;
                        break;
                    }
                }
                if (!brandMatch) return false;
            }
            
            // Glass thickness filter - multi-select
            if (this.filters.selectedGlassThicknesses.length > 0) {
                // Skip glass thickness filtering if the product doesn't have glass_thickness
                if (!mainProduct.glass_thickness) {
                    console.log(`  Main Product ${mainProduct.sku} has no glass_thickness, skipping filter`);
                    // No glass thickness defined, so this product doesn't match the filter
                    return false;
                }
                
                let thicknessMatch = false;
                for (let selectedThickness of this.filters.selectedGlassThicknesses) {
                    if (mainProduct.glass_thickness.toLowerCase() === selectedThickness.toLowerCase()) {
                        thicknessMatch = true;
                        break;
                    }
                }
                if (!thicknessMatch) return false;
            }
            
            // Door type filter - multi-select
            if (this.filters.selectedDoorTypes.length > 0) {
                // Skip door type filtering if the product doesn't have a door_type
                if (!mainProduct.door_type) {
                    console.log(`  Main Product ${mainProduct.sku} has no door_type, skipping filter`);
                    // No door type defined, so this product doesn't match the filter
                    return false;
                }
                
                let doorTypeMatch = false;
                for (let selectedType of this.filters.selectedDoorTypes) {
                    if (mainProduct.door_type.toLowerCase() === selectedType.toLowerCase()) {
                        doorTypeMatch = true;
                        break;
                    }
                }
                if (!doorTypeMatch) return false;
            }
            
            // Material filter - multi-select
            if (this.filters.selectedMaterials.length > 0) {
                // Skip material filtering if the product doesn't have a material
                if (!mainProduct.material) {
                    console.log(`  Main Product ${mainProduct.sku} has no material, skipping filter`);
                    // No material defined, so this product doesn't match the filter
                    return false;
                }
                
                let materialMatch = false;
                for (let selectedMaterial of this.filters.selectedMaterials) {
                    if (mainProduct.material.toLowerCase() === selectedMaterial.toLowerCase()) {
                        materialMatch = true;
                        break;
                    }
                }
                if (!materialMatch) return false;
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
            this.availableFilters.materials = [];
            
            // Sets to collect unique values
            const seriesSet = new Set();
            const brandsSet = new Set();
            const glassThicknessSet = new Set(['6mm', '8mm']); // Default values
            const doorTypeSet = new Set([
                'Sliding', 'Pivot', 'Bypass'
            ]); // Only use the 3 door types from Excel
            const materialSet = new Set();
            
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
                            if (product.main_product.glass_thickness) glassThicknessSet.add(product.main_product.glass_thickness);
                            if (product.main_product.material) materialSet.add(product.main_product.material);
                            // Add door_type if it exists
                            if (product.main_product.door_type && product.main_product.door_type.trim()) {
                                doorTypeSet.add(product.main_product.door_type);
                            }
                        }
                        if (product.secondary_product) {
                            if (product.secondary_product.series) seriesSet.add(product.secondary_product.series);
                            if (product.secondary_product.brand) brandsSet.add(product.secondary_product.brand);
                            if (product.secondary_product.glass_thickness) glassThicknessSet.add(product.secondary_product.glass_thickness);
                            if (product.secondary_product.material) materialSet.add(product.secondary_product.material);
                            // Add door_type if it exists
                            if (product.secondary_product.door_type && product.secondary_product.door_type.trim()) {
                                doorTypeSet.add(product.secondary_product.door_type);
                            }
                        }
                    } 
                    // Regular products
                    else {
                        if (product.series) seriesSet.add(product.series);
                        if (product.brand) brandsSet.add(product.brand);
                        if (product.glass_thickness) glassThicknessSet.add(product.glass_thickness);
                        if (product.material) materialSet.add(product.material);
                        // Add door_type if it exists
                        if (product.door_type && product.door_type.trim()) {
                            doorTypeSet.add(product.door_type);
                        }
                    }
                });
            });
            
            // Convert sets to arrays
            this.availableFilters.series = [...seriesSet].sort();
            this.availableFilters.brands = [...brandsSet].sort();
            this.availableFilters.glassThicknesses = [...glassThicknessSet].filter(t => t).sort();
            // Filter out wall kit types from door types
            const wallTypes = ["Alcove Shower Wall Kit", "Corner Shower Wall Kit", "Tub Wall Kit"];
            this.availableFilters.doorTypes = [...doorTypeSet]
                .filter(t => t && !wallTypes.includes(t))
                .sort();
            this.availableFilters.materials = [...materialSet].filter(m => m).sort();
        },
        
        /**
         * Reset all filters to default values
         */
        resetFilters() {
            this.filters = {
                selectedSeries: [],
                selectedBrands: [],
                selectedGlassThicknesses: [],
                selectedDoorTypes: [],
                selectedCategories: [],
                selectedMaterials: []
            };
            
            // Apply the reset filters
            this.applyFilters();
        },
        
        /**
         * Set filter visibility based on product categories
         * This makes filters appear/disappear dynamically based on product type
         */
        setDynamicFilterVisibility() {
            // Reset all filter visibility flags first
            this.hasGlassFilter = false;
            this.hasDoorsFilter = false;
            this.hasMaterialFilter = false;
            
            // Get unique categories from compatible products
            const categories = this.compatibleProducts.map(category => category.category);
            
            // Also check product details to determine filters
            const sourceProductType = this.productDetails?.productType;
            
            // Check for specific product types to determine which filters to show
            if (categories.includes('Shower Doors') || 
                categories.includes('Tub Doors') ||
                categories.includes('Return Panels') ||
                sourceProductType === 'Shower Door' ||
                sourceProductType === 'Tub Door' ||
                sourceProductType === 'Return Panel') {
                // Door products should have glass thickness filter
                this.hasGlassFilter = true;
            }
            
            if (categories.includes('Shower Doors') || 
                categories.includes('Tub Doors') ||
                sourceProductType === 'Shower Door' ||
                sourceProductType === 'Tub Door') {
                // Show door type filter for doors only
                this.hasDoorsFilter = true;
            }
            
            if (categories.includes('Bathtubs') || 
                categories.includes('Shower Bases') ||
                categories.includes('Showers') ||
                categories.includes('Tub Showers') ||
                sourceProductType === 'Bathtub' ||
                sourceProductType === 'Shower Base' ||
                sourceProductType === 'Shower' ||
                sourceProductType === 'Tub Shower') {
                // Material filter for bathtubs, bases, showers, and tub showers
                this.hasMaterialFilter = true;
            }
            
            console.log('Filter visibility set based on categories:', {
                categories,
                hasGlassFilter: this.hasGlassFilter,
                hasDoorsFilter: this.hasDoorsFilter, 
                hasMaterialFilter: this.hasMaterialFilter
            });
        },
        
        /**
         * Toggle a filter section's visibility
         * @param {Event} event - Click event
         */
        toggleFilterSection(event) {
            const header = event.currentTarget;
            const section = header.closest('.filter-section');
            const content = section.querySelector('.filter-checkbox-container');
            const indicator = header.querySelector('span');
            
            // If display style is not yet set, defaulting to visible (empty string)
            const isCurrentlyHidden = content.style.display === 'none';
            
            if (isCurrentlyHidden) {
                // Show the content
                content.style.display = '';
                indicator.textContent = '−'; // Minus sign
            } else {
                // Hide the content
                content.style.display = 'none';
                indicator.textContent = '+'; // Plus sign
            }
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
        },
        
        /**
         * Toggle a series selection in filters
         * @param {string} series - The series to toggle
         */
        toggleSeriesFilter(series) {
            const index = this.filters.selectedSeries.indexOf(series);
            if (index === -1) {
                // Series not selected, add it
                this.filters.selectedSeries.push(series);
            } else {
                // Series already selected, remove it
                this.filters.selectedSeries.splice(index, 1);
            }
            
            // Apply the updated filters
            this.applyFilters();
        },
        
        /**
         * Toggle a brand selection in filters
         * @param {string} brand - The brand to toggle
         */
        toggleBrandFilter(brand) {
            const index = this.filters.selectedBrands.indexOf(brand);
            if (index === -1) {
                // Brand not selected, add it
                this.filters.selectedBrands.push(brand);
            } else {
                // Brand already selected, remove it
                this.filters.selectedBrands.splice(index, 1);
            }
            
            // Apply the updated filters
            this.applyFilters();
        },
        
        /**
         * Toggle a glass thickness selection in filters
         * @param {string} thickness - The glass thickness to toggle
         */
        toggleGlassThicknessFilter(thickness) {
            const index = this.filters.selectedGlassThicknesses.indexOf(thickness);
            if (index === -1) {
                // Thickness not selected, add it
                this.filters.selectedGlassThicknesses.push(thickness);
            } else {
                // Thickness already selected, remove it
                this.filters.selectedGlassThicknesses.splice(index, 1);
            }
            
            // Apply the updated filters
            this.applyFilters();
        },
        
        /**
         * Toggle a door type selection in filters
         * @param {string} doorType - The door type to toggle
         */
        toggleDoorTypeFilter(doorType) {
            const index = this.filters.selectedDoorTypes.indexOf(doorType);
            if (index === -1) {
                // Door type not selected, add it
                this.filters.selectedDoorTypes.push(doorType);
            } else {
                // Door type already selected, remove it
                this.filters.selectedDoorTypes.splice(index, 1);
            }
            
            // Apply the updated filters
            this.applyFilters();
        },
        
        /**
         * Toggle a material selection in filters
         * @param {string} material - The material to toggle
         */
        toggleMaterialFilter(material) {
            const index = this.filters.selectedMaterials.indexOf(material);
            if (index === -1) {
                // Material not selected, add it
                this.filters.selectedMaterials.push(material);
            } else {
                // Material already selected, remove it
                this.filters.selectedMaterials.splice(index, 1);
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
