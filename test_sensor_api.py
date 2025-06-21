#!/usr/bin/env python3
"""
Test script for Sensor Control API
"""
import requests
import json
import time

# API endpoint
BASE_URL = "http://localhost:5000"
SENSOR_API = f"{BASE_URL}/api/control/sensor"

def test_api_call(action, interval=None):
    """Test a sensor API call"""
    payload = {"action": action}
    if interval is not None:
        payload["interval"] = interval
    
    try:
        print(f"\n🧪 Testing: {action}" + (f" with interval {interval}ms" if interval else ""))
        print(f"📤 Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(SENSOR_API, json=payload, timeout=5)
        
        print(f"📥 Response Status: {response.status_code}")
        print(f"📥 Response Body: {json.dumps(response.json(), indent=2)}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_error_cases():
    """Test error cases"""
    print("\n" + "="*50)
    print("🚨 Testing Error Cases")
    print("="*50)
    
    # Test missing action
    print("\n🧪 Testing: Missing action")
    try:
        response = requests.post(SENSOR_API, json={}, timeout=5)
        print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test invalid action
    print("\n🧪 Testing: Invalid action")
    try:
        response = requests.post(SENSOR_API, json={"action": "invalid"}, timeout=5)
        print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test interval without value
    print("\n🧪 Testing: Interval without value")
    try:
        response = requests.post(SENSOR_API, json={"action": "interval"}, timeout=5)
        print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test invalid interval
    print("\n🧪 Testing: Invalid interval")
    try:
        response = requests.post(SENSOR_API, json={"action": "interval", "interval": -1}, timeout=5)
        print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main test function"""
    print("🚀 Sensor Control API Test")
    print("="*50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not running or not healthy")
            return
        print("✅ Server is running and healthy")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Make sure the pi-server is running on localhost:5000")
        return
    
    print("\n" + "="*50)
    print("🧪 Testing Valid API Calls")
    print("="*50)
    
    # Test all valid actions
    test_results = []
    
    # Test start
    test_results.append(test_api_call("start"))
    time.sleep(1)
    
    # Test stop  
    test_results.append(test_api_call("stop"))
    time.sleep(1)
    
    # Test interval
    test_results.append(test_api_call("interval", 1000))
    time.sleep(1)
    
    # Test different interval values
    test_results.append(test_api_call("interval", 500))
    time.sleep(1)
    
    test_results.append(test_api_call("interval", 2000))
    time.sleep(1)
    
    # Test status
    print("\n" + "="*30)
    print("🔍 Testing Status (Enhanced)")
    print("="*30)
    status_success = test_api_call("status")
    test_results.append(status_success)
    
    # Additional status response analysis
    if status_success:
        try:
            print("\n📋 Analyzing Status Response...")
            response = requests.post(SENSOR_API, json={"action": "status"}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Status Details:")
                print(f"   • Sensor Status: {data.get('sensor_status', 'N/A')}")
                print(f"   • Is Running: {data.get('is_running', 'N/A')}")
                print(f"   • Interval: {data.get('interval', 'N/A')}ms")
                if data.get('raw_responses'):
                    print(f"   • Arduino Responses ({len(data['raw_responses'])} lines):")
                    for i, response_line in enumerate(data['raw_responses'], 1):
                        print(f"     {i}. {response_line}")
                else:
                    print("   • No Arduino responses received")
        except Exception as e:
            print(f"   ⚠️  Could not analyze status details: {e}")
    
    time.sleep(1)
    
    # Test error cases
    test_error_cases()
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)
    successful_tests = sum(test_results)
    total_tests = len(test_results)
    print(f"✅ Successful tests: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main() 