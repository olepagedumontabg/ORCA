// Layout spacing fix - applies additional spacing between filter panel and content
document.addEventListener('DOMContentLoaded', function() {
    // Function to apply layout fixes
    function applyLayoutFixes() {
        // Convert main container to a table layout
        const mainContainer = document.querySelector('.main-content-container');
        if (mainContainer) {
            mainContainer.style.display = 'table';
            mainContainer.style.width = '100%';
            mainContainer.style.tableLayout = 'fixed';
            mainContainer.style.borderCollapse = 'separate';
            mainContainer.style.borderSpacing = '60px 0';
        }
        
        // Convert sidebar and content area to table cells
        const filterPanel = document.querySelector('.filter-sidebar-container');
        const resultsContainer = document.querySelector('.results-container');
        
        if (filterPanel) {
            filterPanel.style.display = 'table-cell';
            filterPanel.style.verticalAlign = 'top';
            filterPanel.style.width = '260px';
            filterPanel.style.maxWidth = '260px';
            
            // Add a right border for visual separation
            filterPanel.style.borderRight = '1px solid #e5e7eb';
            filterPanel.style.paddingRight = '20px';
        }
        
        if (resultsContainer) {
            resultsContainer.style.display = 'table-cell';
            resultsContainer.style.verticalAlign = 'top';
            resultsContainer.style.paddingLeft = '40px';
        }
        
        // Remove any spacer divs, as they're not needed with table layout
        const spacerDiv = document.querySelector('.spacer-div');
        if (spacerDiv) {
            spacerDiv.style.display = 'none';
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