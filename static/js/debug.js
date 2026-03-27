// Debug script to check product data and fix missing product page URLs
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Alpine to initialize
    setTimeout(function() {
        // Check if Alpine and app data are available
        if (window.Alpine && document.querySelector('[x-data="setupProductFinder()"]')) {
            // Get the Alpine component
            const appElement = document.querySelector('[x-data="setupProductFinder()"]');
            const appData = Alpine.$data(appElement);
            
            // Debug listener for product data and fix URLs
            const debugInterval = setInterval(function() {
                if (appData.compatibleProducts && appData.compatibleProducts.length > 0) {
                    console.log('DEBUG: Compatible Products Data:', JSON.stringify(appData.compatibleProducts));
                    
                    // Check and fix products with missing product_page_url
                    let fixedCount = 0;
                    appData.compatibleProducts.forEach((category, catIndex) => {
                        console.log(`DEBUG: Category ${catIndex}: ${category.category}`);
                        category.products.forEach((product, prodIndex) => {
                            // Add URL if missing (using the brand's URL)
                            if (!product.product_page_url && product.brand) {
                                product.product_page_url = "https://maax.com/";
                                fixedCount++;
                            }
                            console.log(`DEBUG: Product ${prodIndex}: SKU=${product.sku}, has URL=${!!product.product_page_url}, URL=${product.product_page_url}`);
                        });
                    });
                    
                    console.log(`DEBUG: Fixed ${fixedCount} products with missing URLs`);
                    
                    // Only run once
                    clearInterval(debugInterval);
                }
            }, 1000); // Check every second
        }
    }, 500); // Wait for Alpine to initialize
});