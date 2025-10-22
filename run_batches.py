"""
Simple batch runner to complete all compatibilities.

Runs small batches repeatedly until all products are processed.
"""

import subprocess
import time
import sys

def get_stats():
    """Get current stats from database."""
    result = subprocess.run(
        ['python3', 'db_migrate.py', '--stats'],
        capture_output=True,
        text=True
    )
    
    stats = {}
    for line in result.stdout.split('\n'):
        if 'total_products:' in line:
            try:
                stats['total'] = int(line.split(':')[-1].strip())
            except:
                pass
        if 'products_with_compatibilities:' in line:
            try:
                stats['completed'] = int(line.split(':')[-1].strip())
            except:
                pass
        if 'products_without_compatibilities:' in line:
            try:
                stats['remaining'] = int(line.split(':')[-1].strip())
            except:
                pass
        if 'total_compatibilities:' in line:
            try:
                stats['compatibilities'] = int(line.split(':')[-1].strip())
            except:
                pass
        if 'avg_compatibilities:' in line:
            try:
                stats['avg'] = float(line.split(':')[-1].strip())
            except:
                pass
    
    return stats

def run_batch(batch_size=10):
    """Run one batch of compatibility computation."""
    result = subprocess.run(
        ['python3', 'batch_compute_compatibilities.py', 
         '--batch-size', str(batch_size), 
         '--max-batches', '1',
         '--resume'],
        capture_output=True,
        text=True,
        timeout=120  # 2 minute timeout per batch
    )
    return result.returncode == 0

def main():
    batch_size = 10
    batch_num = 0
    max_batches = 220  # 220 batches × 10 products = 2,200 products
    
    print("=" * 80)
    print("RESUMABLE BATCH COMPATIBILITY RUNNER")
    print("=" * 80)
    print(f"Batch size: {batch_size} products")
    print(f"Max batches: {max_batches}")
    print("")
    
    # Get initial stats
    print("Checking current status...")
    stats = get_stats()
    print(f"✓ Total products: {stats.get('total', 0)}")
    print(f"✓ Completed: {stats.get('completed', 0)}")
    print(f"✓ Remaining: {stats.get('remaining', 0)}")
    print(f"✓ Total compatibilities: {stats.get('compatibilities', 0)}")
    print(f"✓ Average per product: {stats.get('avg', 0):.1f}")
    print("")
    
    start_time = time.time()
    
    while batch_num < max_batches:
        batch_num += 1
        
        # Check if we're done
        stats = get_stats()
        remaining = stats.get('remaining', 0)
        
        if remaining == 0:
            print(f"\n✅ All products processed!")
            break
        
        print(f"Batch {batch_num}/{max_batches} - {remaining} products remaining...")
        
        try:
            success = run_batch(batch_size)
            if not success:
                print(f"  ⚠️  Batch {batch_num} failed - retrying...")
                time.sleep(2)
                success = run_batch(batch_size)
                if not success:
                    print(f"  ❌ Batch {batch_num} failed twice - stopping")
                    break
        
        except subprocess.TimeoutExpired:
            print(f"  ⏱️  Batch {batch_num} timed out - skipping")
            continue
        except Exception as e:
            print(f"  ❌ Error in batch {batch_num}: {e}")
            break
        
        # Show progress every 10 batches
        if batch_num % 10 == 0:
            stats = get_stats()
            elapsed = time.time() - start_time
            rate = stats.get('completed', 0) / (elapsed / 60) if elapsed > 0 else 0
            
            print(f"\n--- Progress Report (Batch {batch_num}) ---")
            print(f"  Completed: {stats.get('completed', 0)}/{stats.get('total', 0)}")
            print(f"  Remaining: {stats.get('remaining', 0)}")
            print(f"  Compatibilities: {stats.get('compatibilities', 0):,}")
            print(f"  Avg/product: {stats.get('avg', 0):.1f}")
            print(f"  Rate: {rate:.1f} products/minute")
            print(f"  Elapsed: {elapsed/60:.1f} minutes")
            print("")
        
        # Small delay between batches
        time.sleep(1)
    
    # Final stats
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    stats = get_stats()
    print(f"Total products: {stats.get('total', 0)}")
    print(f"Completed: {stats.get('completed', 0)}")
    print(f"Remaining: {stats.get('remaining', 0)}")
    print(f"Total compatibilities: {stats.get('compatibilities', 0):,}")
    print(f"Average per product: {stats.get('avg', 0):.1f}")
    print(f"Total time: {(time.time() - start_time)/60:.1f} minutes")
    print("=" * 80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user - progress has been saved!")
        print("Run this script again to resume where you left off.")
        sys.exit(0)
