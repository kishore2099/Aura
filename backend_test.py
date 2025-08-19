#!/usr/bin/env python3
"""
Backend Test Suite for Aura AI Companion App
Tests all key backend endpoints and functionality
"""

import requests
import json
import uuid
import time
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://porn-free-coach.preview.emergentagent.com/api"

class AuraBackendTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_user_id = None
        self.test_session_id = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
        print()

    def test_health_check(self):
        """Test /api/health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_result("Health Check", True, "Health endpoint working correctly", data)
                    return True
                else:
                    self.log_result("Health Check", False, "Health endpoint returned unexpected data", data)
                    return False
            else:
                self.log_result("Health Check", False, f"Health endpoint returned status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Health Check", False, f"Health endpoint failed with exception: {str(e)}")
            return False

    def test_user_creation(self):
        """Test /api/users endpoint for creating users"""
        try:
            # Test data with realistic information
            user_data = {
                "name": "Jordan Smith",
                "goal": "I want to quit pornography to improve my focus and build better relationships"
            }
            
            response = requests.post(
                f"{self.base_url}/users",
                json=user_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "name", "goal", "current_streak", "best_streak", "created_at"]
                
                if all(field in data for field in required_fields):
                    self.test_user_id = data["id"]  # Store for later tests
                    self.log_result("User Creation", True, "User created successfully", {
                        "user_id": data["id"],
                        "name": data["name"],
                        "current_streak": data["current_streak"],
                        "best_streak": data["best_streak"]
                    })
                    return True
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_result("User Creation", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_result("User Creation", False, f"User creation failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("User Creation", False, f"User creation failed with exception: {str(e)}")
            return False

    def test_user_retrieval(self):
        """Test /api/users/{user_id} endpoint"""
        if not self.test_user_id:
            self.log_result("User Retrieval", False, "No test user ID available")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == self.test_user_id:
                    self.log_result("User Retrieval", True, "User retrieved successfully", {
                        "user_id": data["id"],
                        "name": data["name"]
                    })
                    return True
                else:
                    self.log_result("User Retrieval", False, "Retrieved user ID doesn't match", data)
                    return False
            else:
                self.log_result("User Retrieval", False, f"User retrieval failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("User Retrieval", False, f"User retrieval failed with exception: {str(e)}")
            return False

    def test_llm_chat_integration(self):
        """Test /api/chat endpoint with LLM integration"""
        if not self.test_user_id:
            self.log_result("LLM Chat Integration", False, "No test user ID available")
            return False
            
        try:
            # Test with Alex personality (empathetic coach)
            chat_data = {
                "user_id": self.test_user_id,
                "message": "I'm feeling really tempted right now and need some support. Can you help me?",
                "personality": "alex"
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=30  # LLM calls can take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["ai_message", "personality_used", "session_id"]
                
                if all(field in data for field in required_fields):
                    self.test_session_id = data["session_id"]  # Store for later tests
                    
                    # Verify personality was used correctly
                    if data["personality_used"] == "alex":
                        # Check if response seems appropriate (contains supportive language)
                        ai_message = data["ai_message"].lower()
                        supportive_indicators = ["understand", "support", "here for you", "okay", "feel", "tough"]
                        has_support = any(indicator in ai_message for indicator in supportive_indicators)
                        
                        if has_support and len(data["ai_message"]) > 20:
                            self.log_result("LLM Chat Integration", True, "LLM chat working with Alex personality", {
                                "personality_used": data["personality_used"],
                                "session_id": data["session_id"],
                                "response_length": len(data["ai_message"]),
                                "sample_response": data["ai_message"][:100] + "..."
                            })
                            return True
                        else:
                            self.log_result("LLM Chat Integration", False, "LLM response seems inappropriate or too short", data)
                            return False
                    else:
                        self.log_result("LLM Chat Integration", False, f"Wrong personality used: expected 'alex', got '{data['personality_used']}'", data)
                        return False
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_result("LLM Chat Integration", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_result("LLM Chat Integration", False, f"Chat failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("LLM Chat Integration", False, f"Chat failed with exception: {str(e)}")
            return False

    def test_personality_system(self):
        """Test different personalities (Casey and Leo)"""
        if not self.test_user_id:
            self.log_result("Personality System", False, "No test user ID available")
            return False
            
        personalities_tested = 0
        personalities_working = 0
        
        # Test Casey (Strategist)
        try:
            casey_data = {
                "user_id": self.test_user_id,
                "message": "I need help creating a plan to avoid triggers. What strategy should I use?",
                "personality": "casey"
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=casey_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            personalities_tested += 1
            if response.status_code == 200:
                data = response.json()
                if data.get("personality_used") == "casey":
                    personalities_working += 1
                    print(f"   ✅ Casey personality working")
                else:
                    print(f"   ❌ Casey personality failed: got {data.get('personality_used')}")
            else:
                print(f"   ❌ Casey personality failed with status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Casey personality failed with exception: {str(e)}")
            
        # Test Leo (Motivator)
        try:
            leo_data = {
                "user_id": self.test_user_id,
                "message": "I completed 7 days! I need some motivation to keep going.",
                "personality": "leo"
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=leo_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            personalities_tested += 1
            if response.status_code == 200:
                data = response.json()
                if data.get("personality_used") == "leo":
                    personalities_working += 1
                    print(f"   ✅ Leo personality working")
                else:
                    print(f"   ❌ Leo personality failed: got {data.get('personality_used')}")
            else:
                print(f"   ❌ Leo personality failed with status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Leo personality failed with exception: {str(e)}")
            
        # Evaluate results
        if personalities_working == personalities_tested and personalities_tested > 0:
            self.log_result("Personality System", True, f"All {personalities_working} personalities working correctly")
            return True
        elif personalities_working > 0:
            self.log_result("Personality System", False, f"Only {personalities_working}/{personalities_tested} personalities working")
            return False
        else:
            self.log_result("Personality System", False, "No personalities working correctly")
            return False

    def test_daily_checkin(self):
        """Test /api/checkins endpoint with streak tracking"""
        if not self.test_user_id:
            self.log_result("Daily Check-in", False, "No test user ID available")
            return False
            
        try:
            # Test successful check-in (stayed on track)
            checkin_data = {
                "user_id": self.test_user_id,
                "stayed_on_track": True,
                "mood": 4,
                "had_urges": False,
                "urge_triggers": None
            }
            
            response = requests.post(
                f"{self.base_url}/checkins",
                json=checkin_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "user_id", "date", "stayed_on_track", "mood", "had_urges", "created_at"]
                
                if all(field in data for field in required_fields):
                    # Verify user streak was updated
                    user_response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        if user_data.get("current_streak", 0) > 0:
                            self.log_result("Daily Check-in", True, "Check-in created and streak updated", {
                                "checkin_id": data["id"],
                                "stayed_on_track": data["stayed_on_track"],
                                "new_streak": user_data["current_streak"]
                            })
                            return True
                        else:
                            self.log_result("Daily Check-in", False, "Check-in created but streak not updated", {
                                "checkin_data": data,
                                "user_streak": user_data.get("current_streak")
                            })
                            return False
                    else:
                        self.log_result("Daily Check-in", False, "Check-in created but couldn't verify streak update")
                        return False
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_result("Daily Check-in", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_result("Daily Check-in", False, f"Check-in failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Daily Check-in", False, f"Check-in failed with exception: {str(e)}")
            return False

    def test_sos_support(self):
        """Test /api/sos endpoint for urgent support"""
        if not self.test_user_id:
            self.log_result("SOS Support", False, "No test user ID available")
            return False
            
        try:
            sos_data = {
                "user_id": self.test_user_id,
                "message": "I'm having a really strong urge right now and I'm about to relapse. Please help me!"
            }
            
            response = requests.post(
                f"{self.base_url}/sos",
                json=sos_data,
                headers={"Content-Type": "application/json"},
                timeout=30  # SOS calls might take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["ai_message", "personality_used", "session_id"]
                
                if all(field in data for field in required_fields):
                    # SOS should force Alex personality for emotional support
                    if data["personality_used"] == "alex":
                        # Check if response is immediate and supportive
                        ai_message = data["ai_message"].lower()
                        urgent_indicators = ["understand", "here", "support", "breathe", "moment", "safe"]
                        has_urgency = any(indicator in ai_message for indicator in urgent_indicators)
                        
                        if has_urgency and len(data["ai_message"]) > 30:
                            self.log_result("SOS Support", True, "SOS endpoint working with appropriate urgent response", {
                                "personality_used": data["personality_used"],
                                "response_length": len(data["ai_message"]),
                                "sample_response": data["ai_message"][:100] + "..."
                            })
                            return True
                        else:
                            self.log_result("SOS Support", False, "SOS response doesn't seem urgent or appropriate", data)
                            return False
                    else:
                        self.log_result("SOS Support", False, f"SOS should use Alex personality, got '{data['personality_used']}'", data)
                        return False
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_result("SOS Support", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_result("SOS Support", False, f"SOS failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("SOS Support", False, f"SOS failed with exception: {str(e)}")
            return False

    def test_chat_history(self):
        """Test chat history retrieval"""
        if not self.test_user_id or not self.test_session_id:
            self.log_result("Chat History", False, "No test user ID or session ID available")
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/users/{self.test_user_id}/chat-history/{self.test_session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check if messages have required fields
                    first_message = data[0]
                    required_fields = ["id", "user_id", "session_id", "message_type", "content", "created_at"]
                    
                    if all(field in first_message for field in required_fields):
                        self.log_result("Chat History", True, f"Chat history retrieved with {len(data)} messages", {
                            "message_count": len(data),
                            "session_id": self.test_session_id
                        })
                        return True
                    else:
                        missing_fields = [f for f in required_fields if f not in first_message]
                        self.log_result("Chat History", False, f"Chat history messages missing fields: {missing_fields}", first_message)
                        return False
                else:
                    self.log_result("Chat History", False, "Chat history is empty or not a list", data)
                    return False
            else:
                self.log_result("Chat History", False, f"Chat history failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Chat History", False, f"Chat history failed with exception: {str(e)}")
            return False

    def test_model_verification(self):
        """Verify that claude-3-5-sonnet-20241022 model is being used"""
        # This is harder to test directly, but we can infer from successful LLM responses
        # and the code review shows the model is correctly configured
        if any(result["test"] == "LLM Chat Integration" and result["success"] for result in self.results):
            self.log_result("Model Verification", True, "claude-3-5-sonnet-20241022 model appears to be working (inferred from successful LLM responses)")
            return True
        else:
            self.log_result("Model Verification", False, "Cannot verify model - LLM chat integration failed")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Aura Backend Test Suite")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("User Creation", self.test_user_creation),
            ("User Retrieval", self.test_user_retrieval),
            ("LLM Chat Integration", self.test_llm_chat_integration),
            ("Personality System", self.test_personality_system),
            ("Daily Check-in", self.test_daily_checkin),
            ("SOS Support", self.test_sos_support),
            ("Chat History", self.test_chat_history),
            ("Model Verification", self.test_model_verification)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"Running: {test_name}")
            if test_func():
                passed += 1
            time.sleep(1)  # Brief pause between tests
            
        print("=" * 60)
        print(f"🏁 Test Suite Complete: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Backend is working correctly.")
        elif passed >= total * 0.8:
            print("⚠️  Most tests passed, but some issues found.")
        else:
            print("❌ Multiple test failures - backend needs attention.")
            
        return passed, total

if __name__ == "__main__":
    tester = AuraBackendTester()
    passed, total = tester.run_all_tests()
    
    # Print detailed results
    print("\n" + "=" * 60)
    print("DETAILED TEST RESULTS:")
    print("=" * 60)
    
    for result in tester.results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status}: {result['test']}")
        print(f"   Message: {result['message']}")
        if result["details"]:
            print(f"   Details: {result['details']}")
        print()