import requests
import sys
import time
from datetime import datetime

class LocoAPITester:
    def __init__(self, base_url="https://train-data-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {str(response_data)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check endpoint"""
        return self.run_test("Health Check", "GET", "", 200)

    def test_status_endpoint(self):
        """Test status endpoint"""
        return self.run_test("Status Check", "GET", "status", 200)

    def test_search_suggestions(self, partial_loco="278"):
        """Test search suggestions endpoint"""
        success, response = self.run_test(
            f"Search Suggestions for '{partial_loco}'", 
            "GET", 
            f"search/{partial_loco}", 
            200
        )
        if success and 'suggestions' in response:
            print(f"   Found {len(response['suggestions'])} suggestions")
            if response['suggestions']:
                print(f"   Sample suggestions: {response['suggestions'][:3]}")
        return success, response

    def test_loco_summary(self, loco_no):
        """Test loco summary endpoint"""
        success, response = self.run_test(
            f"Loco Summary for {loco_no}", 
            "GET", 
            f"loco/{loco_no}", 
            200,
            timeout=60  # Longer timeout for data fetching
        )
        if success:
            details_count = len(response.get('details', []))
            schedules_count = len(response.get('schedules', []))
            failures_count = len(response.get('failures', []))
            print(f"   Details: {details_count}, Schedules: {schedules_count}, Failures: {failures_count}")
        return success, response

    def test_loco_not_found(self, invalid_loco="99999"):
        """Test loco summary with invalid loco number"""
        return self.run_test(
            f"Invalid Loco Number {invalid_loco}", 
            "GET", 
            f"loco/{invalid_loco}", 
            404
        )

    def test_manual_refresh(self):
        """Test manual refresh endpoint"""
        print("\n⚠️  Manual refresh may take 30-60 seconds...")
        return self.run_test(
            "Manual Data Refresh", 
            "POST", 
            "refresh", 
            200,
            timeout=120  # Extended timeout for refresh
        )

def main():
    print("🚂 Starting Locomotive Data Summary API Tests")
    print("=" * 60)
    
    tester = LocoAPITester()
    
    # Test 1: Health Check
    tester.test_health_check()
    
    # Test 2: Status Check
    tester.test_status_endpoint()
    
    # Test 3: Search Suggestions
    tester.test_search_suggestions("278")
    tester.test_search_suggestions("277")
    
    # Test 4: Valid Loco Numbers (from requirements)
    test_locos = ["27865", "27767"]
    for loco in test_locos:
        tester.test_loco_summary(loco)
    
    # Test 5: Invalid Loco Number
    tester.test_loco_not_found("99999")
    
    # Test 6: Manual Refresh (optional - takes time)
    print("\n🔄 Testing manual refresh (this may take a while)...")
    print("⏭️  Skipping manual refresh test for automated testing")
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    
    if tester.failed_tests:
        print("\n❌ FAILED TESTS:")
        for i, failure in enumerate(tester.failed_tests, 1):
            print(f"   {i}. {failure}")
    else:
        print("\n✅ All tests passed!")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())