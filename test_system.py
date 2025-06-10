#!/usr/bin/env python3
"""
System Testing and Verification Script for Pi MQTT Server
Tests all major components and provides detailed health check
"""

import requests
import json
import time
import sys
import os
from pathlib import Path
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple

class SystemTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, name: str, status: str, message: str = "", details: str = ""):
        """Log test result"""
        result = {
            "test": name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if status == "PASS":
            self.passed_tests += 1
            print(f"✅ {name}: {message}")
        elif status == "FAIL":
            self.failed_tests += 1
            print(f"❌ {name}: {message}")
            if details:
                print(f"   Details: {details}")
        else:
            print(f"⚠️  {name}: {message}")
            
    def test_server_running(self) -> bool:
        """Test if server is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Server Health", "PASS", f"Server is running - Status: {data.get('status', 'Unknown')}")
                return True
            else:
                self.log_test("Server Health", "FAIL", f"Server returned status code: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log_test("Server Health", "FAIL", "Cannot connect to server. Is it running?")
            return False
        except Exception as e:
            self.log_test("Server Health", "FAIL", f"Error connecting to server: {str(e)}")
            return False
            
    def test_firebase_connection(self) -> bool:
        """Test Firebase connectivity"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                services = data.get('services', {})
                firebase_status = services.get('firebase', 'unknown')
                
                if firebase_status == 'connected':
                    self.log_test("Firebase Connection", "PASS", "Firebase is connected and accessible")
                    return True
                else:
                    self.log_test("Firebase Connection", "FAIL", f"Firebase status: {firebase_status}")
                    return False
            else:
                self.log_test("Firebase Connection", "FAIL", "Cannot get health status")
                return False
        except Exception as e:
            self.log_test("Firebase Connection", "FAIL", f"Error checking Firebase: {str(e)}")
            return False
            
    def test_sensors_endpoint(self) -> bool:
        """Test sensors API endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/sensors", timeout=5)
            if response.status_code == 200:
                data = response.json()
                sensor_count = len(data.get('sensors', []))
                self.log_test("Sensors API", "PASS", f"Found {sensor_count} sensors")
                return True
            else:
                self.log_test("Sensors API", "FAIL", f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Sensors API", "FAIL", f"Error: {str(e)}")
            return False
            
    def test_device_control(self) -> bool:
        """Test device control endpoints"""
        test_passed = True
        
        # Test blower control
        try:
            payload = {"action": "status"}
            response = requests.post(
                f"{self.base_url}/api/control/blower",
                json=payload,
                timeout=5
            )
            if response.status_code in [200, 201]:
                self.log_test("Blower Control", "PASS", "Blower control endpoint responsive")
            else:
                self.log_test("Blower Control", "FAIL", f"Status code: {response.status_code}")
                test_passed = False
        except Exception as e:
            self.log_test("Blower Control", "FAIL", f"Error: {str(e)}")
            test_passed = False
            
        # Test actuator control
        try:
            payload = {"action": "status"}
            response = requests.post(
                f"{self.base_url}/api/control/actuator",
                json=payload,
                timeout=5
            )
            if response.status_code in [200, 201]:
                self.log_test("Actuator Control", "PASS", "Actuator control endpoint responsive")
            else:
                self.log_test("Actuator Control", "FAIL", f"Status code: {response.status_code}")
                test_passed = False
        except Exception as e:
            self.log_test("Actuator Control", "FAIL", f"Error: {str(e)}")
            test_passed = False
            
        return test_passed
        
    def test_camera_endpoints(self) -> bool:
        """Test camera-related endpoints"""
        try:
            response = requests.post(f"{self.base_url}/api/camera/photo", timeout=10)
            if response.status_code in [200, 201]:
                self.log_test("Camera Photo", "PASS", "Camera photo endpoint responsive")
                return True
            elif response.status_code == 404:
                self.log_test("Camera Photo", "SKIP", "Camera not available (expected on some setups)")
                return True
            else:
                self.log_test("Camera Photo", "FAIL", f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Camera Photo", "SKIP", f"Camera not available: {str(e)}")
            return True  # Camera is optional
            
    def test_serial_communication(self) -> bool:
        """Test serial communication if available"""
        try:
            response = requests.get(f"{self.base_url}/api/serial/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                self.log_test("Serial Communication", "PASS", f"Serial status: {status}")
                return True
            elif response.status_code == 404:
                self.log_test("Serial Communication", "SKIP", "Serial endpoint not available")
                return True
            else:
                self.log_test("Serial Communication", "FAIL", f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Serial Communication", "SKIP", f"Serial not available: {str(e)}")
            return True  # Serial is optional
            
    def test_firebase_sync(self) -> bool:
        """Test Firebase sync functionality"""
        try:
            response = requests.post(f"{self.base_url}/api/sensors/sync", timeout=15)
            if response.status_code in [200, 201]:
                data = response.json()
                self.log_test("Firebase Sync", "PASS", f"Sync successful: {data.get('message', '')}")
                return True
            else:
                self.log_test("Firebase Sync", "FAIL", f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Firebase Sync", "FAIL", f"Error: {str(e)}")
            return False
            
    def test_system_resources(self) -> bool:
        """Test system resources and performance"""
        try:
            # Check disk space
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    usage_line = lines[1].split()
                    if len(usage_line) >= 5:
                        usage_percent = usage_line[4].rstrip('%')
                        if int(usage_percent) < 90:
                            self.log_test("Disk Space", "PASS", f"Disk usage: {usage_percent}%")
                        else:
                            self.log_test("Disk Space", "FAIL", f"High disk usage: {usage_percent}%")
                            return False
                    
            # Check if required files exist
            required_files = ['main.py', 'requirements.txt', '.env']
            missing_files = []
            for file in required_files:
                if not os.path.exists(file):
                    missing_files.append(file)
                    
            if not missing_files:
                self.log_test("Required Files", "PASS", "All required files present")
            else:
                self.log_test("Required Files", "FAIL", f"Missing files: {', '.join(missing_files)}")
                return False
                
            return True
        except Exception as e:
            self.log_test("System Resources", "FAIL", f"Error checking resources: {str(e)}")
            return False
            
    def test_environment_config(self) -> bool:
        """Test environment configuration"""
        try:
            env_file = Path('.env')
            if env_file.exists():
                with open(env_file, 'r') as f:
                    content = f.read()
                    
                required_vars = ['FIREBASE_ADMIN_SDK_PATH', 'FIREBASE_DATABASE_URL', 'FIREBASE_PROJECT_ID']
                missing_vars = []
                
                for var in required_vars:
                    if var not in content:
                        missing_vars.append(var)
                        
                if not missing_vars:
                    self.log_test("Environment Config", "PASS", "All required environment variables configured")
                    return True
                else:
                    self.log_test("Environment Config", "FAIL", f"Missing variables: {', '.join(missing_vars)}")
                    return False
            else:
                self.log_test("Environment Config", "FAIL", ".env file not found")
                return False
        except Exception as e:
            self.log_test("Environment Config", "FAIL", f"Error checking config: {str(e)}")
            return False
            
    def run_all_tests(self):
        """Run all system tests"""
        print("🧪 Starting Pi MQTT Server System Tests")
        print("=" * 50)
        
        # Basic connectivity tests
        if not self.test_server_running():
            print("\n❌ Server not running. Cannot proceed with other tests.")
            return self.generate_report()
            
        # Core functionality tests
        self.test_firebase_connection()
        self.test_sensors_endpoint()
        self.test_device_control()
        self.test_camera_endpoints()
        self.test_serial_communication()
        self.test_firebase_sync()
        
        # System health tests
        self.test_system_resources()
        self.test_environment_config()
        
        return self.generate_report()
        
    def generate_report(self) -> Dict:
        """Generate test report"""
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 All tests passed! System is healthy.")
        else:
            print(f"\n⚠️  {self.failed_tests} test(s) failed. Check the details above.")
            
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "success_rate": success_rate
            },
            "detailed_results": self.test_results
        }
        
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📄 Detailed report saved to: test_report.json")
        
        return report

def main():
    """Main function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"
        
    print(f"🔍 Testing server at: {base_url}")
    
    tester = SystemTester(base_url)
    report = tester.run_all_tests()
    
    # Exit with appropriate code
    if report["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main() 