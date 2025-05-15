// Layout spacing fix - applies additional spacing between filter panel and content
document.addEventListener('DOMContentLoaded', function() {
    // Function to apply layout fixes
    function applyLayoutFixes() {
        // Add spacing between filter panel and content area
        const filterPanel = document.querySelector('.filter-sidebar-container');
        const resultsContainer = document.querySelector('.results-container');
        
        if (filterPanel && resultsContainer) {
            // Add margins
            resultsContainer.style.marginLeft = '80px';
            
            // Ensure the spacer div has proper width
            const spacerDiv = document.querySelector('.spacer-div');
            if (spacerDiv) {
                spacerDiv.style.minWidth = '80px';
                spacerDiv.style.width = '80px';
            }
        }
    }
    
    // Apply fixes initially
    applyLayoutFixes();
    
    // Also apply fixes whenever Alpine.js updates the DOM
    document.addEventListener('alpine:initialized', applyLayoutFixes);
    
    // Monitor for changes in the DOM that might affect layout
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' || mutation.type === 'attributes') {
                applyLayoutFixes();
            }
        });
    });
    
    // Start observing the document with the configured parameters
    observer.observe(document.body, { 
        childList: true, 
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'class']
    });
});