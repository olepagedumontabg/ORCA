// Debug script to check product data
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Alpine to initialize
    setTimeout(function() {
        // Check if Alpine and app data are available
        if (window.Alpine && document.querySelector('[x-data="setupProductFinder()"]')) {
            // Get the Alpine component
            const appElement = document.querySelector('[x-data="setupProductFinder()"]');
            const appData = Alpine.$data(appElement);
            
            // Debug listener for product data
            const debugInterval = setInterval(function() {
                if (appData.compatibleProducts && appData.compatibleProducts.length > 0) {
                    console.log('DEBUG: Compatible Products Data:', JSON.stringify(appData.compatibleProducts));
                    
                    // Check if products have product_page_url
                    appData.compatibleProducts.forEach((category, catIndex) => {
                        console.log(`DEBUG: Category ${catIndex}: ${category.category}`);
                        category.products.forEach((product, prodIndex) => {
                            console.log(`DEBUG: Product ${prodIndex}: SKU=${product.sku}, has URL=${!!product.product_page_url}, URL=${product.product_page_url}`);
                        });
                    });
                    
                    // Only run once
                    clearInterval(debugInterval);
                }
            }, 2000); // Check every 2 seconds
        }
    }, 1000); // Wait for Alpine to initialize
});