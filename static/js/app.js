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
            selectedCategories: []
        },
        
        // UI state for filters
        showFilters: true, // Default show filters in sidebar
        availableFilters: {
            series: [],
            brands: [],
            glassThicknesses: ['6mm', '8mm'],
            doorTypes: ['Sliding', 'Pivot', 'Bypass'], // Only use the 3 door types from Excel
            categories: []
        },
        
        /**
         * Initialize the application
         */
        init() {
            // Initialize application
            this.$watch('searchInput', (value) => {
                if (value && value.length >= 3) {
                    this.getSuggestions(value);
                } else {
                    this.suggestions = [];
                    this.showSuggestions = false;
                }
            });
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
                this.showSuggestions = false;
            }
        },
        
        /**
         * Select a suggestion from the dropdown
         * @param {string} suggestion - The selected suggestion (display format: "SKU - Product Name")
         * @param {number} index - The index of the suggestion in the list
         */
        selectSuggestion(suggestion, index) {
            // If we have raw SKUs stored and the index is valid, use the raw SKU
            if (this.rawSkus && this.rawSkus.length > index && index >= 0) {
                this.searchInput = this.rawSkus[index];
            } else {
                // Otherwise extract the SKU from the suggestion text (everything before " - ")
                const skuMatch = suggestion.match(/^(.*?)(?:\s+-\s+|$)/);
                this.searchInput = skuMatch ? skuMatch[1].trim() : suggestion;
            }
            
            this.showSuggestions = false;
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
                    // Normalize product details to handle different property naming conventions
                    this.productDetails = this.normalizeProductProperties(data.product);

                    // Process compatible products
                    this.compatibleProducts = data.compatibles || [];
                    
                    // Ensure category information is attached to product details
                    if (this.productDetails && !this.productDetails.category && data.compatibles && data.compatibles.length > 0) {
                        console.log("Attempting to extract category from compatibles");
                        // Try to determine category from compatible products
                        const firstCategory = data.compatibles[0]?.category;
                        if (firstCategory && firstCategory.includes("Bathtubs")) {
                            this.productDetails.category = "Bathtubs";
                        } else if (firstCategory && firstCategory.includes("Shower Bases")) {
                            this.productDetails.category = "Shower Bases";
                        }
                    }
                    
                    console.log("Product details after normalization:", this.productDetails);
                    
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
         * Normalize product properties to handle inconsistencies in naming from different sources
         * Ensures consistent keys regardless of the source (API, Excel file, etc.)
         * @param {object} product - The product to normalize
         */
        normalizeProductProperties(product) {
            if (!product) return;
            
            // Standard property mappings (source -> target)
            const propertyMap = {
                'Product Name': 'name',
                'Glass Thickness': 'glass_thickness',
                'Door Type': 'door_type',
                'Image URL': 'image_url',
                'Brand': 'brand',
                'Series': 'series',
                'Nominal Dimensions': 'nominal_dimensions',
                'Width': 'width',
                'Height': 'height',
                'Depth': 'depth',
                'SKU': 'sku',
                'Product SKU': 'sku',
                'Product Description': 'description',
                'Category': 'category',
                'Product Category': 'category'
            };
            
            // Apply mappings - ensures each property exists in lowercase form for consistency
            for (const [sourceProp, targetProp] of Object.entries(propertyMap)) {
                // If the source property exists but the target doesn't, create it
                if (product[sourceProp] !== undefined && product[targetProp] === undefined) {
                    product[targetProp] = product[sourceProp];
                }
                // If the target property exists but the source doesn't, create it (for compatibility with old code)
                else if (product[targetProp] !== undefined && product[sourceProp] === undefined) {
                    product[sourceProp] = product[targetProp];
                }
            }
            
            // Special case for bathtub products - extract attributes from name if missing
            if (product.category === 'Tub Doors' || 
                (product.sku && typeof product.sku === 'string' && product.sku.startsWith('13')) ||
                (product.sku && typeof product.sku === 'number' && product.sku.toString().startsWith('13'))) {
                
                if ((!product.glass_thickness || product.glass_thickness === '') && product.name) {
                    const name = product.name.toLowerCase();
                    if (name.includes('8mm') || name.includes('8 mm')) {
                        product.glass_thickness = '8mm';
                        product['Glass Thickness'] = '8mm';
                    } else if (name.includes('6mm') || name.includes('6 mm')) {
                        product.glass_thickness = '6mm';
                        product['Glass Thickness'] = '6mm';
                    } else if (name.includes('10mm') || name.includes('10 mm')) {
                        product.glass_thickness = '10mm';
                        product['Glass Thickness'] = '10mm';
                    }
                }
                
                if ((!product.door_type || product.door_type === '') && product.name) {
                    const name = product.name.toLowerCase();
                    if (name.includes('pivot')) {
                        product.door_type = 'Pivot';
                        product['Door Type'] = 'Pivot';
                    } else if (name.includes('sliding')) {
                        product.door_type = 'Sliding';
                        product['Door Type'] = 'Sliding';
                    } else if (name.includes('bypass')) {
                        product.door_type = 'Bypass';
                        product['Door Type'] = 'Bypass';
                    }
                }
            }
            
            return product;
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
            
            // Normalize product keys first - this handles inconsistencies from different data sources
            // This is especially important for bathtub products
            this.normalizeProductProperties(product);
            
            // We shouldn't get combo products here, as they're handled in applyFilters
            // But just in case, we'll handle them properly
            if (this.isComboProduct(product) && product.main_product) {
                console.log("  Encountered combo product in filterMatchesProduct, forwarding to filterMatchesMainProduct");
                return this.filterMatchesMainProduct(product.main_product);
            }
            
            // Series filter - multi-select
            if (this.filters.selectedSeries.length > 0) {
                // Get series value from either lowercase or PascalCase property
                const seriesValue = product.series || product.Series || '';
                
                if (seriesValue) {
                    let seriesMatch = false;
                    for (let selectedSeries of this.filters.selectedSeries) {
                        if (seriesValue.toLowerCase() === selectedSeries.toLowerCase()) {
                            seriesMatch = true;
                            break;
                        }
                    }
                    if (!seriesMatch) return false;
                }
            }
            
            // Brand filter - multi-select
            if (this.filters.selectedBrands.length > 0) {
                // Get brand from either lowercase or PascalCase property
                const brandValue = product.brand || product.Brand || '';
                
                if (brandValue) {
                    let brandMatch = false;
                    for (let selectedBrand of this.filters.selectedBrands) {
                        if (brandValue.toLowerCase() === selectedBrand.toLowerCase()) {
                            brandMatch = true;
                            break;
                        }
                    }
                    if (!brandMatch) return false;
                }
            }
            
            // Glass thickness filter - multi-select
            if (this.filters.selectedGlassThicknesses.length > 0) {
                // Try to get glass thickness from property in any case format
                let glassThickness = product.glass_thickness || product['Glass Thickness'] || '';
                
                // For bathtub door products, try to extract from the name if not present
                if (!glassThickness && product.name && 
                    (product.category === 'Tub Doors' || 
                     (typeof product.sku === 'string' && product.sku.startsWith('13')) ||
                     (typeof product.sku === 'number' && product.sku.toString().startsWith('13')))) {
                    
                    const name = product.name.toLowerCase();
                    if (name.includes('8mm') || name.includes('8 mm')) {
                        glassThickness = '8mm';
                        // Store for future filtering
                        product.glass_thickness = '8mm';
                    } else if (name.includes('6mm') || name.includes('6 mm')) {
                        glassThickness = '6mm';
                        product.glass_thickness = '6mm';
                    } else if (name.includes('10mm') || name.includes('10 mm')) {
                        glassThickness = '10mm';
                        product.glass_thickness = '10mm';
                    }
                }
                
                if (glassThickness) {
                    let thicknessMatch = false;
                    for (let selectedThickness of this.filters.selectedGlassThicknesses) {
                        if (glassThickness.toLowerCase() === selectedThickness.toLowerCase()) {
                            thicknessMatch = true;
                            break;
                        }
                    }
                    if (!thicknessMatch) return false;
                } else {
                    // If glass thickness filters are selected but product doesn't have data
                    // Only apply to door-related categories
                    if (product.category && 
                        (product.category.toLowerCase().includes('door') || 
                         (typeof product.sku === 'string' && product.sku.toLowerCase().startsWith('gd')))) {
                        return false;
                    }
                }
            }
            
            // Door type filter - multi-select
            if (this.filters.selectedDoorTypes.length > 0) {
                // Try to get door type from property in any case format
                let doorType = product.door_type || product['Door Type'] || '';
                
                // For bathtub door products, try to extract from the name if not present
                if (!doorType && product.name && 
                    (product.category === 'Tub Doors' || 
                     (typeof product.sku === 'string' && product.sku.startsWith('13')) ||
                     (typeof product.sku === 'number' && product.sku.toString().startsWith('13')))) {
                    
                    const name = product.name.toLowerCase();
                    if (name.includes('pivot')) {
                        doorType = 'Pivot';
                        // Store for future filtering
                        product.door_type = 'Pivot';
                    } else if (name.includes('sliding')) {
                        doorType = 'Sliding';
                        product.door_type = 'Sliding';
                    } else if (name.includes('bypass')) {
                        doorType = 'Bypass';
                        product.door_type = 'Bypass';
                    }
                }
                
                if (doorType) {
                    let doorTypeMatch = false;
                    for (let selectedType of this.filters.selectedDoorTypes) {
                        if (doorType.toLowerCase() === selectedType.toLowerCase()) {
                            doorTypeMatch = true;
                            break;
                        }
                    }
                    if (!doorTypeMatch) return false;
                } else {
                    // If door type filters are selected but product doesn't have data
                    // Only apply to door-related categories
                    if (product.category && 
                        (product.category.toLowerCase().includes('door') || 
                         (typeof product.sku === 'string' && product.sku.toLowerCase().startsWith('gd')))) {
                        return false;
                    }
                }
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
            
            // First normalize the product properties to handle different naming conventions
            this.normalizeProductProperties(mainProduct);
            
            // Series filter - multi-select
            if (this.filters.selectedSeries.length > 0) {
                // Get series value from either lowercase or PascalCase property
                const seriesValue = mainProduct.series || mainProduct.Series || '';
                
                if (seriesValue) {
                    let seriesMatch = false;
                    for (let selectedSeries of this.filters.selectedSeries) {
                        if (seriesValue.toLowerCase() === selectedSeries.toLowerCase()) {
                            seriesMatch = true;
                            break;
                        }
                    }
                    if (!seriesMatch) return false;
                }
            }
            
            // Brand filter - multi-select
            if (this.filters.selectedBrands.length > 0) {
                // Get brand from either lowercase or PascalCase property
                const brandValue = mainProduct.brand || mainProduct.Brand || '';
                
                if (brandValue) {
                    let brandMatch = false;
                    for (let selectedBrand of this.filters.selectedBrands) {
                        if (brandValue.toLowerCase() === selectedBrand.toLowerCase()) {
                            brandMatch = true;
                            break;
                        }
                    }
                    if (!brandMatch) return false;
                }
            }
            
            // Glass thickness filter - multi-select
            if (this.filters.selectedGlassThicknesses.length > 0) {
                // Try to get glass thickness from property in any case format
                let glassThickness = mainProduct.glass_thickness || mainProduct['Glass Thickness'] || '';
                
                // For bathtub door products, try to extract from the name if not present
                if (!glassThickness && mainProduct.name && 
                    (mainProduct.category === 'Tub Doors' || 
                     (typeof mainProduct.sku === 'string' && mainProduct.sku.startsWith('13')) ||
                     (typeof mainProduct.sku === 'number' && mainProduct.sku.toString().startsWith('13')))) {
                    
                    const name = mainProduct.name.toLowerCase();
                    if (name.includes('8mm') || name.includes('8 mm')) {
                        glassThickness = '8mm';
                        // Store for future filtering
                        mainProduct.glass_thickness = '8mm';
                    } else if (name.includes('6mm') || name.includes('6 mm')) {
                        glassThickness = '6mm';
                        mainProduct.glass_thickness = '6mm';
                    } else if (name.includes('10mm') || name.includes('10 mm')) {
                        glassThickness = '10mm';
                        mainProduct.glass_thickness = '10mm';
                    }
                }
                
                if (glassThickness) {
                    let thicknessMatch = false;
                    for (let selectedThickness of this.filters.selectedGlassThicknesses) {
                        if (glassThickness.toLowerCase() === selectedThickness.toLowerCase()) {
                            thicknessMatch = true;
                            break;
                        }
                    }
                    if (!thicknessMatch) return false;
                } else {
                    // If glass thickness filters are selected but product doesn't have data
                    // Only apply to door-related categories
                    if (mainProduct.category && 
                        (mainProduct.category.toLowerCase().includes('door') || 
                         (typeof mainProduct.sku === 'string' && mainProduct.sku.toLowerCase().startsWith('gd')))) {
                        return false;
                    }
                }
            }
            
            // Door type filter - multi-select
            if (this.filters.selectedDoorTypes.length > 0) {
                // Try to get door type from property in any case format
                let doorType = mainProduct.door_type || mainProduct['Door Type'] || '';
                
                // For bathtub door products, try to extract from the name if not present
                if (!doorType && mainProduct.name && 
                    (mainProduct.category === 'Tub Doors' || 
                     (typeof mainProduct.sku === 'string' && mainProduct.sku.startsWith('13')) ||
                     (typeof mainProduct.sku === 'number' && mainProduct.sku.toString().startsWith('13')))) {
                    
                    const name = mainProduct.name.toLowerCase();
                    if (name.includes('pivot')) {
                        doorType = 'Pivot';
                        // Store for future filtering
                        mainProduct.door_type = 'Pivot';
                    } else if (name.includes('sliding')) {
                        doorType = 'Sliding';
                        mainProduct.door_type = 'Sliding';
                    } else if (name.includes('bypass')) {
                        doorType = 'Bypass';
                        mainProduct.door_type = 'Bypass';
                    }
                }
                
                if (doorType) {
                    let doorTypeMatch = false;
                    for (let selectedType of this.filters.selectedDoorTypes) {
                        if (doorType.toLowerCase() === selectedType.toLowerCase()) {
                            doorTypeMatch = true;
                            break;
                        }
                    }
                    if (!doorTypeMatch) return false;
                } else {
                    // If door type filters are selected but product doesn't have data
                    // Only apply to door-related categories
                    if (mainProduct.category && 
                        (mainProduct.category.toLowerCase().includes('door') || 
                         (typeof mainProduct.sku === 'string' && mainProduct.sku.toLowerCase().startsWith('gd')))) {
                        return false;
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
            console.log("Extracting filter options from compatible products:", this.compatibleProducts);
            
            // Reset available filters
            this.availableFilters.series = [];
            this.availableFilters.brands = [];
            this.availableFilters.categories = [];
            
            // Sets to collect unique values
            const seriesSet = new Set();
            const brandsSet = new Set();
            const glassThicknessSet = new Set(['6mm', '8mm']); // Default values
            const doorTypeSet = new Set([
                'Sliding', 'Pivot', 'Bypass'
            ]); // Only use the 3 door types from Excel
            
            // Categories come from the results
            this.compatibleProducts.forEach(category => {
                // Add category to available categories
                this.availableFilters.categories.push(category.category);
                
                // Process products within this category
                if (!category.products) return;
                
                category.products.forEach(product => {
                    // Normalize product properties first
                    this.normalizeProductProperties(product);
                    
                    // Handle combo products
                    if (this.isComboProduct(product)) {
                        if (product.main_product) {
                            // Normalize main product properties
                            this.normalizeProductProperties(product.main_product);
                            
                            if (product.main_product.series) seriesSet.add(product.main_product.series);
                            if (product.main_product.brand) brandsSet.add(product.main_product.brand);
                            if (product.main_product.glass_thickness) glassThicknessSet.add(product.main_product.glass_thickness);
                            // Only add door_type if it's one of our valid types
                            if (product.main_product.door_type && 
                                ['Sliding', 'Pivot', 'Bypass'].includes(product.main_product.door_type)) {
                                doorTypeSet.add(product.main_product.door_type);
                            }
                            
                            // If this is in Tub Doors category, extract info from product name if not present
                            if (category.category === 'Tub Doors' && product.main_product.name) {
                                const name = product.main_product.name.toLowerCase();
                                // Check for glass thickness in name
                                if (!product.main_product.glass_thickness) {
                                    if (name.includes('8mm') || name.includes('8 mm')) {
                                        product.main_product.glass_thickness = '8mm';
                                        glassThicknessSet.add('8mm');
                                    } else if (name.includes('6mm') || name.includes('6 mm')) {
                                        product.main_product.glass_thickness = '6mm';
                                        glassThicknessSet.add('6mm');
                                    }
                                }
                                
                                // Check for door type in name
                                if (!product.main_product.door_type) {
                                    if (name.includes('pivot')) {
                                        product.main_product.door_type = 'Pivot';
                                        doorTypeSet.add('Pivot');
                                    } else if (name.includes('sliding')) {
                                        product.main_product.door_type = 'Sliding';
                                        doorTypeSet.add('Sliding');
                                    } else if (name.includes('bypass')) {
                                        product.main_product.door_type = 'Bypass';
                                        doorTypeSet.add('Bypass');
                                    }
                                }
                            }
                        }
                        if (product.secondary_product) {
                            if (product.secondary_product.series) seriesSet.add(product.secondary_product.series);
                            if (product.secondary_product.brand) brandsSet.add(product.secondary_product.brand);
                            if (product.secondary_product.glass_thickness) glassThicknessSet.add(product.secondary_product.glass_thickness);
                            // Only add door_type if it's one of our valid types
                            if (product.secondary_product.door_type && 
                                ['Sliding', 'Pivot', 'Bypass'].includes(product.secondary_product.door_type)) {
                                doorTypeSet.add(product.secondary_product.door_type);
                            }
                        }
                    } 
                    // Regular products
                    else {
                        if (product.series) seriesSet.add(product.series);
                        if (product.brand) brandsSet.add(product.brand);
                        if (product.glass_thickness) glassThicknessSet.add(product.glass_thickness);
                        // Only add door_type if it's one of our valid types
                        if (product.door_type && 
                            ['Sliding', 'Pivot', 'Bypass'].includes(product.door_type)) {
                            doorTypeSet.add(product.door_type);
                        }
                        
                        // If this is in Tub Doors category, extract info from product name if not present
                        if (category.category === 'Tub Doors' && product.name) {
                            const name = product.name.toLowerCase();
                            // Check for glass thickness in name
                            if (!product.glass_thickness) {
                                if (name.includes('8mm') || name.includes('8 mm')) {
                                    product.glass_thickness = '8mm';
                                    glassThicknessSet.add('8mm');
                                } else if (name.includes('6mm') || name.includes('6 mm')) {
                                    product.glass_thickness = '6mm';
                                    glassThicknessSet.add('6mm');
                                } else if (name.includes('10mm') || name.includes('10 mm')) {
                                    product.glass_thickness = '10mm';
                                    glassThicknessSet.add('10mm');
                                }
                            }
                            
                            // Check for door type in name
                            if (!product.door_type) {
                                if (name.includes('pivot')) {
                                    product.door_type = 'Pivot';
                                    doorTypeSet.add('Pivot');
                                } else if (name.includes('sliding')) {
                                    product.door_type = 'Sliding';
                                    doorTypeSet.add('Sliding');
                                } else if (name.includes('bypass')) {
                                    product.door_type = 'Bypass';
                                    doorTypeSet.add('Bypass');
                                }
                            }
                        }
                    }
                });
            });
            
            // Convert sets to arrays
            this.availableFilters.series = [...seriesSet].sort();
            this.availableFilters.brands = [...brandsSet].sort();
            this.availableFilters.glassThicknesses = [...glassThicknessSet].filter(t => t).sort();
            this.availableFilters.doorTypes = [...doorTypeSet].filter(t => t).sort();
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
        }
    };
}

// Initialize AlpineJS data on page load
document.addEventListener('alpine:init', () => {
    // Any additional Alpine.js component registrations can go here
});
