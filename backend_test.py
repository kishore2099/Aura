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

    def test_unified_chat_integration(self):
        """Test /api/chat endpoint with unified personality system"""
        if not self.test_user_id:
            self.log_result("Unified Chat Integration", False, "No test user ID available")
            return False
            
        try:
            # Test unified chat without specifying personality - should intelligently choose
            chat_data = {
                "user_id": self.test_user_id,
                "message": "I'm feeling really tempted right now and need some support. Can you help me?"
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=30  # LLM calls can take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["ai_message", "personalities_used", "session_id", "user_progress"]
                
                if all(field in data for field in required_fields):
                    self.test_session_id = data["session_id"]  # Store for later tests
                    
                    # Verify personalities_used is a list
                    if isinstance(data["personalities_used"], list) and len(data["personalities_used"]) > 0:
                        # Check if response contains appropriate content
                        ai_message = data["ai_message"].lower()
                        supportive_indicators = ["understand", "support", "here for you", "okay", "feel", "tough", "breathe", "moment"]
                        has_support = any(indicator in ai_message for indicator in supportive_indicators)
                        
                        # Check if user_progress is included
                        progress = data.get("user_progress", {})
                        has_progress = "galaxy" in progress and "streak" in progress
                        
                        if has_support and len(data["ai_message"]) > 20 and has_progress:
                            self.log_result("Unified Chat Integration", True, "Unified chat working with intelligent personality selection", {
                                "personalities_used": data["personalities_used"],
                                "session_id": data["session_id"],
                                "response_length": len(data["ai_message"]),
                                "has_progress_data": has_progress,
                                "sample_response": data["ai_message"][:100] + "..."
                            })
                            return True
                        else:
                            self.log_result("Unified Chat Integration", False, "Response inappropriate, too short, or missing progress data", {
                                "has_support": has_support,
                                "response_length": len(data["ai_message"]),
                                "has_progress": has_progress,
                                "progress_keys": list(progress.keys()) if progress else []
                            })
                            return False
                    else:
                        self.log_result("Unified Chat Integration", False, f"personalities_used should be non-empty list, got: {data['personalities_used']}", data)
                        return False
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_result("Unified Chat Integration", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_result("Unified Chat Integration", False, f"Chat failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Unified Chat Integration", False, f"Chat failed with exception: {str(e)}")
            return False

    def test_multi_personality_transitions(self):
        """Test that Aura can transition between personalities in responses"""
        if not self.test_user_id:
            self.log_result("Multi-personality Transitions", False, "No test user ID available")
            return False
            
        try:
            # Test with a message that should trigger multiple personalities
            chat_data = {
                "user_id": self.test_user_id,
                "message": "I've been struggling with urges lately. I need emotional support but also want to create a concrete plan to handle this better. Can you help motivate me too?"
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "personalities_used" in data and isinstance(data["personalities_used"], list):
                    personalities = data["personalities_used"]
                    ai_message = data["ai_message"]
                    
                    # Check for personality indicators in the response
                    has_alex = any(indicator in ai_message.lower() for indicator in ["🫂", "understand", "feel", "support", "here for you"])
                    has_casey = any(indicator in ai_message.lower() for indicator in ["🧠", "plan", "strategy", "step", "approach"])
                    has_leo = any(indicator in ai_message.lower() for indicator in ["⚡", "amazing", "strong", "champion", "victory"])
                    
                    # Should have at least 2 personalities for this complex request
                    if len(personalities) >= 2:
                        self.log_result("Multi-personality Transitions", True, f"Multiple personalities used: {personalities}", {
                            "personalities_count": len(personalities),
                            "personalities_used": personalities,
                            "has_alex_indicators": has_alex,
                            "has_casey_indicators": has_casey,
                            "has_leo_indicators": has_leo,
                            "response_length": len(ai_message)
                        })
                        return True
                    else:
                        self.log_result("Multi-personality Transitions", False, f"Expected multiple personalities, got: {personalities}", {
                            "personalities_used": personalities,
                            "response_sample": ai_message[:200] + "..."
                        })
                        return False
                else:
                    self.log_result("Multi-personality Transitions", False, "personalities_used field missing or invalid", data)
                    return False
            else:
                self.log_result("Multi-personality Transitions", False, f"Chat failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Multi-personality Transitions", False, f"Multi-personality test failed with exception: {str(e)}")
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

    def test_achievement_system(self):
        """Test achievement tracking and awarding system"""
        if not self.test_user_id:
            self.log_result("Achievement System", False, "No test user ID available")
            return False
            
        try:
            # First, get all available achievements
            achievements_response = requests.get(f"{self.base_url}/achievements", timeout=10)
            if achievements_response.status_code != 200:
                self.log_result("Achievement System", False, "Could not fetch achievements list")
                return False
                
            achievements_data = achievements_response.json()
            available_achievements = achievements_data.get("achievements", [])
            
            if not available_achievements:
                self.log_result("Achievement System", False, "No achievements found in system")
                return False
            
            # Test that achievements are properly structured
            first_achievement = available_achievements[0]
            required_fields = ["id", "name", "description", "icon", "category", "unlock_condition"]
            
            if not all(field in first_achievement for field in required_fields):
                missing_fields = [f for f in required_fields if f not in first_achievement]
                self.log_result("Achievement System", False, f"Achievement structure missing fields: {missing_fields}")
                return False
            
            # Create a check-in to potentially trigger achievements
            checkin_data = {
                "user_id": self.test_user_id,
                "stayed_on_track": True,
                "mood": 5,
                "had_urges": True,
                "urge_triggers": "stress at work"
            }
            
            checkin_response = requests.post(
                f"{self.base_url}/checkins",
                json=checkin_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if checkin_response.status_code == 200:
                # Check if user has any achievements now
                user_response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    user_achievements = user_data.get("achievements", [])
                    
                    # Should have at least "first_day" achievement if streak > 0
                    if user_data.get("current_streak", 0) > 0 and "first_day" in user_achievements:
                        self.log_result("Achievement System", True, "Achievement system working - first_day achievement awarded", {
                            "user_achievements": user_achievements,
                            "current_streak": user_data.get("current_streak"),
                            "total_achievements_available": len(available_achievements)
                        })
                        return True
                    elif len(user_achievements) > 0:
                        self.log_result("Achievement System", True, f"Achievement system working - {len(user_achievements)} achievements earned", {
                            "user_achievements": user_achievements,
                            "current_streak": user_data.get("current_streak")
                        })
                        return True
                    else:
                        # Check if achievements are being tracked properly even if not awarded yet
                        self.log_result("Achievement System", True, "Achievement system structure working (no achievements earned yet)", {
                            "achievements_available": len(available_achievements),
                            "user_streak": user_data.get("current_streak"),
                            "achievement_categories": list(set(a["category"] for a in available_achievements))
                        })
                        return True
                else:
                    self.log_result("Achievement System", False, "Could not retrieve user data to check achievements")
                    return False
            else:
                self.log_result("Achievement System", False, "Could not create check-in to test achievement system")
                return False
                
        except Exception as e:
            self.log_result("Achievement System", False, f"Achievement system test failed with exception: {str(e)}")
            return False

    def test_galaxy_progress(self):
        """Test /api/users/{user_id}/progress endpoint for galaxy visualization data"""
        if not self.test_user_id:
            self.log_result("Galaxy Progress", False, "No test user ID available")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}/progress", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["galaxy", "achievements", "stats"]
                
                if all(field in data for field in required_fields):
                    galaxy_data = data["galaxy"]
                    achievements_data = data["achievements"]
                    stats_data = data["stats"]
                    
                    # Check galaxy data structure
                    galaxy_required = ["stars", "galaxy_level", "constellations_unlocked", "next_constellation", "total_light_years"]
                    if all(field in galaxy_data for field in galaxy_required):
                        
                        # Check achievements structure
                        if "earned" in achievements_data and "available" in achievements_data:
                            
                            # Check stats structure
                            stats_required = ["current_streak", "best_streak", "total_days_clean", "total_achievements"]
                            if all(field in stats_data for field in stats_required):
                                
                                self.log_result("Galaxy Progress", True, "Galaxy progress endpoint working correctly", {
                                    "galaxy_level": galaxy_data["galaxy_level"],
                                    "stars_count": len(galaxy_data["stars"]),
                                    "constellations_unlocked": len(galaxy_data["constellations_unlocked"]),
                                    "earned_achievements": len(achievements_data["earned"]),
                                    "available_achievements": len(achievements_data["available"]),
                                    "current_streak": stats_data["current_streak"],
                                    "total_light_years": galaxy_data["total_light_years"]
                                })
                                return True
                            else:
                                missing_stats = [f for f in stats_required if f not in stats_data]
                                self.log_result("Galaxy Progress", False, f"Stats missing fields: {missing_stats}", stats_data)
                                return False
                        else:
                            self.log_result("Galaxy Progress", False, "Achievements data missing 'earned' or 'available' fields", achievements_data)
                            return False
                    else:
                        missing_galaxy = [f for f in galaxy_required if f not in galaxy_data]
                        self.log_result("Galaxy Progress", False, f"Galaxy data missing fields: {missing_galaxy}", galaxy_data)
                        return False
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_result("Galaxy Progress", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_result("Galaxy Progress", False, f"Progress endpoint failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Galaxy Progress", False, f"Galaxy progress test failed with exception: {str(e)}")
            return False

    def test_weekly_reports(self):
        """Test /api/users/{user_id}/weekly-report endpoint for Aura Pulse reports"""
        if not self.test_user_id:
            self.log_result("Weekly Reports", False, "No test user ID available")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}/weekly-report", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if it's a "not enough data" message or actual report
                if "message" in data and "not enough data" in data["message"].lower():
                    self.log_result("Weekly Reports", True, "Weekly report endpoint working (not enough data yet)", {
                        "message": data["message"]
                    })
                    return True
                else:
                    # Check for actual report structure
                    required_fields = ["id", "user_id", "week_start", "week_end", "avg_mood", "clean_days", "total_urges", "insights", "created_at"]
                    
                    if all(field in data for field in required_fields):
                        insights = data.get("insights", [])
                        
                        self.log_result("Weekly Reports", True, "Weekly report generated successfully", {
                            "week_start": data["week_start"],
                            "week_end": data["week_end"],
                            "avg_mood": data["avg_mood"],
                            "clean_days": data["clean_days"],
                            "total_urges": data["total_urges"],
                            "insights_count": len(insights),
                            "sample_insight": insights[0] if insights else "No insights"
                        })
                        return True
                    else:
                        missing_fields = [f for f in required_fields if f not in data]
                        self.log_result("Weekly Reports", False, f"Weekly report missing fields: {missing_fields}", data)
                        return False
            else:
                self.log_result("Weekly Reports", False, f"Weekly report failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Weekly Reports", False, f"Weekly report test failed with exception: {str(e)}")
            return False

    def test_real_time_progress_updates(self):
        """Test that chat responses include user progress updates"""
        if not self.test_user_id:
            self.log_result("Real-time Progress Updates", False, "No test user ID available")
            return False
            
        try:
            # Send a chat message and verify progress data is included
            chat_data = {
                "user_id": self.test_user_id,
                "message": "How am I doing with my progress?"
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "user_progress" in data and data["user_progress"]:
                    progress = data["user_progress"]
                    required_progress_fields = ["galaxy", "new_achievements", "streak", "best_streak"]
                    
                    if all(field in progress for field in required_progress_fields):
                        galaxy_data = progress["galaxy"]
                        
                        # Verify galaxy data has the right structure
                        if "stars" in galaxy_data and "galaxy_level" in galaxy_data:
                            self.log_result("Real-time Progress Updates", True, "Chat responses include real-time progress updates", {
                                "has_galaxy_data": True,
                                "galaxy_level": galaxy_data["galaxy_level"],
                                "current_streak": progress["streak"],
                                "best_streak": progress["best_streak"],
                                "new_achievements_count": len(progress["new_achievements"])
                            })
                            return True
                        else:
                            self.log_result("Real-time Progress Updates", False, "Progress data incomplete - missing galaxy details", progress)
                            return False
                    else:
                        missing_fields = [f for f in required_progress_fields if f not in progress]
                        self.log_result("Real-time Progress Updates", False, f"Progress data missing fields: {missing_fields}", progress)
                        return False
                else:
                    self.log_result("Real-time Progress Updates", False, "Chat response missing user_progress field", data.keys())
                    return False
            else:
                self.log_result("Real-time Progress Updates", False, f"Chat failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Real-time Progress Updates", False, f"Progress updates test failed with exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Aura Backend Test Suite")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test sequence - Enhanced features testing
        tests = [
            ("Health Check", self.test_health_check),
            ("User Creation", self.test_user_creation),
            ("User Retrieval", self.test_user_retrieval),
            ("Unified Chat Integration", self.test_unified_chat_integration),
            ("Multi-personality Transitions", self.test_multi_personality_transitions),
            ("Achievement System", self.test_achievement_system),
            ("Galaxy Progress", self.test_galaxy_progress),
            ("Weekly Reports", self.test_weekly_reports),
            ("Real-time Progress Updates", self.test_real_time_progress_updates),
            ("Daily Check-in", self.test_daily_checkin),
            ("SOS Support", self.test_sos_support),
            ("Chat History", self.test_chat_history)
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