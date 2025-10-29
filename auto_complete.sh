#!/bin/bash
# Auto-completing script - keeps running until database is 100% complete

echo "Auto-completion process starting..."
echo "This will run until all 2,193 products are processed"
echo ""

while true; do
    # Check current status
    CURRENT=$(python -c "from models import get_session, ProductCompatibility; s = get_session(); count = s.query(ProductCompatibility.base_product_id).distinct().count(); s.close(); print(count)")
    
    echo "Current: $CURRENT/2193 products"
    
    # Check if complete
    if [ "$CURRENT" -ge "2193" ]; then
        echo ""
        echo "✓ COMPLETE! All products processed"
        
        # Clear API cache
        python -c "import app; app.clear_api_cache(); print('API cache cleared')" 2>/dev/null || echo "Note: Cache clear attempted"
        break
    fi
    
    # Run the smart compute script
    echo "Running batch computation..."
    timeout 120 python -u smart_compute.py 2>&1 | tail -10
    
    # Wait a bit before next iteration
    sleep 2
done

echo ""
echo "Final status:"
python -c "from models import get_session, ProductCompatibility; s = get_session(); products = s.query(ProductCompatibility.base_product_id).distinct().count(); total = s.query(ProductCompatibility).count(); s.close(); print(f'{products}/2193 products with {total:,} compatibilities')"
