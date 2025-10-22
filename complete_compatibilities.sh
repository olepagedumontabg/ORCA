#!/bin/bash
#
# Complete Compatibility Computation Script
#
# This script runs compatibility computation in small batches
# to avoid timeout/resource issues.
#
# Usage: bash complete_compatibilities.sh
#

echo "=================================="
echo "Compatibility Computation Runner"
echo "=================================="
echo ""

# Run 20 iterations of 100 products each (2000 products total)
for i in {1..20}; do
    echo "Running batch iteration $i/20..."
    python3 batch_compute_compatibilities.py --batch-size 100 --max-batches 1 --resume 2>&1 | tail -15
    
    if [ $? -ne 0 ]; then
        echo "Error in iteration $i - stopping"
        break
    fi
    
    echo ""
    echo "Batch $i complete. Sleeping 2 seconds..."
    sleep 2
done

echo ""
echo "=================================="
echo "Final Statistics"
echo "=================================="
python3 db_migrate.py --stats
