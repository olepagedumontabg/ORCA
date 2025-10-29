#!/usr/bin/env python3
"""
Performance Testing Script
Tests database sync speed, API response times, and overall system performance
"""

import time
import sys
from models import get_session, Product, ProductCompatibility
from data_loader import load_compatible_products_from_database


def test_database_coverage():
    """Test how many products have compatibility data"""
    print("=" * 70)
    print("DATABASE COVERAGE TEST")
    print("=" * 70)
    
    session = get_session()
    
    total = session.query(Product).count()
    with_forward = session.query(Product.id).join(
        ProductCompatibility, Product.id == ProductCompatibility.base_product_id
    ).filter(ProductCompatibility.compatibility_score > 0).distinct().count()
    
    total_compat_records = session.query(ProductCompatibility).count()
    
    session.close()
    
    coverage = (with_forward / total * 100) if total > 0 else 0
    
    print(f"Total products: {total:,}")
    print(f"Products with forward compatibility: {with_forward:,} ({coverage:.1f}%)")
    print(f"Total compatibility records: {total_compat_records:,}")
    print(f"Bidirectional matches: ~{total_compat_records // 2:,}")
    print()
    
    return coverage >= 70  # Success if >= 70% coverage


def test_api_query_performance():
    """Test raw database query performance"""
    print("=" * 70)
    print("API QUERY PERFORMANCE TEST")
    print("=" * 70)
    
    # Find a test product
    session = get_session()
    test_product = session.query(Product).join(
        ProductCompatibility, Product.id == ProductCompatibility.base_product_id
    ).filter(ProductCompatibility.compatibility_score > 0).first()
    session.close()
    
    if not test_product:
        print("⚠ No products with compatibility found")
        return False
    
    sku = test_product.sku
    print(f"Testing with SKU: {sku}")
    print()
    
    # Warm up
    load_compatible_products_from_database(sku)
    
    # Measure 10 queries
    times = []
    for i in range(10):
        start = time.time()
        result = load_compatible_products_from_database(sku)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
    
    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"Results (10 queries):")
    print(f"  Average: {avg:.1f}ms")
    print(f"  Min: {min_time:.1f}ms")
    print(f"  Max: {max_time:.1f}ms")
    print()
    
    # Success if average under 500ms (uncached database queries)
    # Cached API requests will be ~3-5ms
    if avg < 500:
        print(f"✓ PASS: Average {avg:.1f}ms < 500ms threshold")
        print(f"  (Cached API requests will be ~3-5ms)")
        return True
    else:
        print(f"✗ FAIL: Average {avg:.1f}ms >= 500ms threshold")
        return False


def test_api_endpoint_with_cache():
    """Test actual API endpoint with caching"""
    print("=" * 70)
    print("API ENDPOINT CACHING TEST")
    print("=" * 70)
    
    try:
        import requests
        
        # Test endpoint
        url = "http://localhost:5000/api/compatible/FR03260M"
        
        # First request (uncached)
        start = time.time()
        resp1 = requests.get(url, timeout=5)
        first_time = (time.time() - start) * 1000
        
        if resp1.status_code != 200:
            print(f"✗ API returned status {resp1.status_code}")
            return False
        
        # Second request (cached)
        start = time.time()
        resp2 = requests.get(url, timeout=5)
        cached_time = (time.time() - start) * 1000
        
        print(f"Results:")
        print(f"  First request (uncached): {first_time:.1f}ms")
        print(f"  Second request (cached): {cached_time:.1f}ms")
        print(f"  Cache speedup: {(first_time/cached_time):.1f}x faster")
        print()
        
        if cached_time < 100:
            print(f"✓ PASS: Cached response {cached_time:.1f}ms < 100ms")
            return True
        else:
            print(f"✗ FAIL: Cached response {cached_time:.1f}ms >= 100ms")
            return False
            
    except Exception as e:
        print(f"✗ Error testing API endpoint: {e}")
        print("  (Make sure the application is running)")
        return False


def run_all_tests():
    """Run all performance tests"""
    print()
    print("*" * 70)
    print("BATHROOM COMPATIBILITY FINDER - PERFORMANCE TESTS")
    print("*" * 70)
    print()
    
    results = {}
    
    # Test 1: Database Coverage
    results['coverage'] = test_database_coverage()
    time.sleep(1)
    
    # Test 2: Query Performance
    results['query_performance'] = test_api_query_performance()
    time.sleep(1)
    
    # Test 3: API Caching
    results['api_caching'] = test_api_endpoint_with_cache()
    
    # Summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 70)
    print()
    
    return all(results.values())


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
