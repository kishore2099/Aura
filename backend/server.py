from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
import os
import uuid
import re
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/aura_app')
client = AsyncIOMotorClient(MONGO_URL)
db = client.aura_app

# LLM Configuration
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Data Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    goal: str
    current_streak: int = 0
    best_streak: int = 0
    total_days_clean: int = 0
    achievements: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CheckIn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str
    stayed_on_track: bool
    mood: int  # 1-5 scale
    had_urges: bool
    urge_triggers: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    message_type: str  # "user" or "ai"
    content: str
    personalities: Optional[List[str]] = None  # Multiple personalities can be used in one response
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    category: str  # "streak", "urge_resistance", "consistency", "milestone"
    unlock_condition: Dict

class Relapse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str
    trigger_analysis: Optional[str] = None
    emotional_state: Optional[str] = None
    time_of_day: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WeeklyReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    week_start: str
    week_end: str
    avg_mood: float
    clean_days: int
    total_urges: int
    most_common_trigger: Optional[str] = None
    achievements_earned: List[str]
    insights: List[str]
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# Request/Response Models
class CreateUserRequest(BaseModel):
    name: str
    goal: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None

class CheckInRequest(BaseModel):
    user_id: str
    stayed_on_track: bool
    mood: int
    had_urges: bool
    urge_triggers: Optional[str] = None

class RelapseRequest(BaseModel):
    user_id: str
    trigger_analysis: Optional[str] = None
    emotional_state: Optional[str] = None
    time_of_day: Optional[str] = None

class ChatResponse(BaseModel):
    ai_message: str
    personalities_used: List[str]
    session_id: str
    user_progress: Optional[Dict] = None

# Achievement System
ACHIEVEMENTS = [
    {"id": "first_day", "name": "First Step", "description": "Completed your first day", "icon": "🌱", "category": "streak", "unlock_condition": {"type": "streak", "value": 1}},
    {"id": "week_warrior", "name": "Week Warrior", "description": "7 days strong", "icon": "⚔️", "category": "streak", "unlock_condition": {"type": "streak", "value": 7}},
    {"id": "month_master", "name": "Month Master", "description": "30 days of freedom", "icon": "👑", "category": "streak", "unlock_condition": {"type": "streak", "value": 30}},
    {"id": "urge_survivor", "name": "Urge Survivor", "description": "Successfully resisted 10 urges", "icon": "🛡️", "category": "urge_resistance", "unlock_condition": {"type": "urges_resisted", "value": 10}},
    {"id": "check_in_champion", "name": "Check-in Champion", "description": "Completed 7 daily check-ins", "icon": "📅", "category": "consistency", "unlock_condition": {"type": "checkins", "value": 7}},
    {"id": "mindful_analyst", "name": "Mindful Analyst", "description": "Identified 5 different triggers", "icon": "🔍", "category": "self_awareness", "unlock_condition": {"type": "triggers_identified", "value": 5}},
    {"id": "mood_master", "name": "Mood Master", "description": "Maintained good mood (4+) for 5 days", "icon": "😊", "category": "wellbeing", "unlock_condition": {"type": "good_mood_streak", "value": 5}},
    {"id": "century_club", "name": "Century Club", "description": "100 days of transformation", "icon": "💎", "category": "milestone", "unlock_condition": {"type": "streak", "value": 100}},
]

# Enhanced Personality System
def get_unified_system_message():
    return """You are "Aura," a compassionate and intelligent AI guide with three integrated personality aspects. You seamlessly transition between these aspects based on what the user needs most:

🫂 **Alex (Empathetic Coach)** - Use when the user needs emotional support, validation, or comfort:
- Warm, patient, excellent listener
- Validates feelings and reduces shame
- Key phrases: "It sounds tough", "Thank you for sharing", "It's okay to feel that way"

🧠 **Casey (Strategist)** - Use when the user needs analysis, planning, or problem-solving:
- Logical, clear-thinking, solution-focused
- Analyzes triggers, identifies patterns, creates actionable plans
- Key phrases: "Let's break this down", "I notice a pattern", "What's one concrete action you can take?"

⚡ **Leo (Motivator)** - Use when the user needs encouragement, celebration, or inspiration:
- Energetic, inspiring, celebrates progress
- Boosts morale and provides motivational fuel
- Key phrases: "That's a huge win!", "Remember why you started", "You're building something amazing"

**CORE RULES:**
- NEVER use shaming, guilt-inducing, or disappointed language
- Always be supportive, patient, and empowering
- You can transition between personalities within a single response
- Use visual indicators like 🫂Alex:, 🧠Casey:, ⚡Leo: when switching
- Be proactive and caring
- Keep responses concise but comprehensive

**PERSONALITY TRANSITION EXAMPLES:**
- Start as Alex for emotional support, then shift to Casey for strategy
- Begin with Leo for motivation, then Alex for deeper emotional work  
- Use Casey for analysis, then Leo for encouragement about the plan

Your goal is to provide a seamless, multi-faceted support experience that feels like talking to one unified, deeply caring guide."""

async def create_unified_llm_chat(session_id: str, user_context: Dict):
    """Create a unified LLM chat instance that can use all personalities"""
    system_message = get_unified_system_message()
    
    # Add user context to system message
    context_addition = f"\n\nUSER CONTEXT:\n- Name: {user_context.get('name', 'User')}\n- Goal: {user_context.get('goal', 'Personal growth')}\n- Current Streak: {user_context.get('current_streak', 0)} days\n- Best Streak: {user_context.get('best_streak', 0)} days\n- Recent Achievements: {', '.join(user_context.get('achievements', []))}"
    
    full_system_message = system_message + context_addition
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=full_system_message
    ).with_model("anthropic", "claude-3-5-sonnet-20241022")
    
    return chat

def extract_personalities_from_response(ai_response: str) -> List[str]:
    """Extract which personalities were used in the response"""
    personalities = []
    
    # Check for personality indicators in response
    if '🫂alex:' in ai_response.lower() or 'alex speaking' in ai_response.lower():
        personalities.append('alex')
    if '🧠casey:' in ai_response.lower() or 'casey here' in ai_response.lower():
        personalities.append('casey')
    if '⚡leo:' in ai_response.lower() or 'leo speaking' in ai_response.lower():
        personalities.append('leo')
    
    # If no explicit indicators, try to infer from content
    if not personalities:
        response_lower = ai_response.lower()
        
        # Alex indicators (emotional support)
        alex_indicators = ['understand', 'feel', 'tough', 'okay', 'support', 'here for you', 'validated', 'courage']
        if any(indicator in response_lower for indicator in alex_indicators):
            personalities.append('alex')
            
        # Casey indicators (strategy/analysis)
        casey_indicators = ['plan', 'strategy', 'analyze', 'pattern', 'trigger', 'step', 'approach', 'solution']
        if any(indicator in response_lower for indicator in casey_indicators):
            personalities.append('casey')
            
        # Leo indicators (motivation)
        leo_indicators = ['amazing', 'proud', 'win', 'victory', 'strong', 'power', 'champion', 'celebrate']
        if any(indicator in response_lower for indicator in leo_indicators):
            personalities.append('leo')
    
    # Default to Alex if nothing detected
    if not personalities:
        personalities = ['alex']
        
    return personalities

async def check_and_award_achievements(user_id: str, user_data: Dict) -> List[str]:
    """Check if user has earned new achievements and award them"""
    new_achievements = []
    current_achievements = user_data.get('achievements', [])
    
    # Get user stats
    streak = user_data.get('current_streak', 0)
    checkins = await db.checkins.count_documents({"user_id": user_id})
    
    # Check recent moods for mood master achievement
    recent_checkins = await db.checkins.find({"user_id": user_id}).sort("created_at", -1).limit(5).to_list(5)
    good_mood_streak = 0
    for checkin in recent_checkins:
        if checkin.get('mood', 0) >= 4:
            good_mood_streak += 1
        else:
            break
    
    # Count unique triggers identified
    trigger_checkins = await db.checkins.find({"user_id": user_id, "urge_triggers": {"$exists": True, "$ne": None, "$ne": ""}}).to_list(None)
    unique_triggers = len(set(checkin.get('urge_triggers', '').lower().strip() for checkin in trigger_checkins if checkin.get('urge_triggers')))
    
    # Count urges resisted (had urges but stayed on track)
    urges_resisted = await db.checkins.count_documents({"user_id": user_id, "had_urges": True, "stayed_on_track": True})
    
    # Check each achievement
    for achievement in ACHIEVEMENTS:
        if achievement['id'] in current_achievements:
            continue
            
        condition = achievement['unlock_condition']
        earned = False
        
        if condition['type'] == 'streak' and streak >= condition['value']:
            earned = True
        elif condition['type'] == 'checkins' and checkins >= condition['value']:
            earned = True
        elif condition['type'] == 'good_mood_streak' and good_mood_streak >= condition['value']:
            earned = True
        elif condition['type'] == 'triggers_identified' and unique_triggers >= condition['value']:
            earned = True
        elif condition['type'] == 'urges_resisted' and urges_resisted >= condition['value']:
            earned = True
            
        if earned:
            new_achievements.append(achievement['id'])
            
    # Update user achievements in database
    if new_achievements:
        updated_achievements = current_achievements + new_achievements
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"achievements": updated_achievements}}
        )
        
    return new_achievements

def get_galaxy_progress_data(streak: int, total_days: int, achievements: List[str]) -> Dict:
    """Generate galaxy visualization data based on user progress"""
    # Each star represents a day, with constellations forming at milestones
    stars = []
    
    # Create stars for each day in current streak
    for day in range(min(streak, 365)):  # Cap at 365 for performance
        brightness = min(1.0, day / 100)  # Stars get brighter over time
        star = {
            "day": day + 1,
            "brightness": brightness,
            "constellation": get_constellation_name(day + 1),
            "achieved": True
        }
        stars.append(star)
    
    # Calculate galaxy level based on total progress
    galaxy_level = min(10, max(1, (total_days // 30) + 1))
    
    return {
        "stars": stars,
        "galaxy_level": galaxy_level,
        "constellations_unlocked": get_unlocked_constellations(streak),
        "next_constellation": get_next_constellation(streak),
        "total_light_years": total_days * 10  # Fun metric
    }

def get_constellation_name(day: int) -> Optional[str]:
    """Get constellation name for specific day milestones"""
    constellations = {
        7: "Determination",
        14: "Strength", 
        30: "Resilience",
        60: "Wisdom",
        90: "Transformation",
        180: "Mastery",
        365: "Transcendence"
    }
    
    for milestone in sorted(constellations.keys()):
        if day <= milestone:
            return constellations[milestone]
    return "Infinity"

def get_unlocked_constellations(streak: int) -> List[str]:
    """Get list of constellation names unlocked by current streak"""
    milestones = [7, 14, 30, 60, 90, 180, 365]
    unlocked = []
    
    for milestone in milestones:
        if streak >= milestone:
            unlocked.append(get_constellation_name(milestone))
            
    return unlocked

def get_next_constellation(streak: int) -> Optional[Dict]:
    """Get info about the next constellation to unlock"""
    milestones = [7, 14, 30, 60, 90, 180, 365]
    
    for milestone in milestones:
        if streak < milestone:
            return {
                "name": get_constellation_name(milestone),
                "days_needed": milestone - streak,
                "milestone": milestone
            }
            
    return None

# API Endpoints

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Aura is here to support you"}

@app.post("/api/users", response_model=User)
async def create_user(request: CreateUserRequest):
    user = User(name=request.name, goal=request.goal)
    await db.users.insert_one(user.dict())
    return user

@app.get("/api/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user_doc)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_aura(request: ChatRequest):
    # Get user context
    user_doc = await db.users.find_one({"id": request.user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User(**user_doc)
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Create unified LLM chat instance
        chat = await create_unified_llm_chat(session_id, user.dict())
        
        # Send message to LLM
        user_message = UserMessage(text=request.message)
        response = await chat.send_message(user_message)
        
        # Extract personalities used in response
        personalities_used = extract_personalities_from_response(response)
        
        # Store user message in database
        user_msg = ChatMessage(
            user_id=request.user_id,
            session_id=session_id,
            message_type="user",
            content=request.message
        )
        await db.chat_messages.insert_one(user_msg.dict())
        
        # Store AI response in database
        ai_msg = ChatMessage(
            user_id=request.user_id,
            session_id=session_id,
            message_type="ai",
            content=response,
            personalities=personalities_used
        )
        await db.chat_messages.insert_one(ai_msg.dict())
        
        # Check for new achievements
        new_achievements = await check_and_award_achievements(request.user_id, user.dict())
        
        # Get updated user data for progress
        updated_user_doc = await db.users.find_one({"id": request.user_id})
        updated_user = User(**updated_user_doc)
        
        # Generate progress data
        progress_data = {
            "galaxy": get_galaxy_progress_data(
                updated_user.current_streak, 
                updated_user.total_days_clean, 
                updated_user.achievements
            ),
            "new_achievements": [
                next(a for a in ACHIEVEMENTS if a['id'] == achievement_id)
                for achievement_id in new_achievements
            ],
            "streak": updated_user.current_streak,
            "best_streak": updated_user.best_streak
        }
        
        return ChatResponse(
            ai_message=response,
            personalities_used=personalities_used,
            session_id=session_id,
            user_progress=progress_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/checkins", response_model=CheckIn)
async def create_checkin(request: CheckInRequest):
    # Get user to update streak
    user_doc = await db.users.find_one({"id": request.user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User(**user_doc)
    
    # Update streak and total days based on check-in
    if request.stayed_on_track:
        user.current_streak += 1
        user.total_days_clean += 1
        if user.current_streak > user.best_streak:
            user.best_streak = user.current_streak
    else:
        user.current_streak = 0  # Reset streak on relapse
    
    # Update user in database
    await db.users.update_one(
        {"id": request.user_id},
        {"$set": {
            "current_streak": user.current_streak,
            "best_streak": user.best_streak,
            "total_days_clean": user.total_days_clean
        }}
    )
    
    # Create check-in record
    checkin = CheckIn(
        user_id=request.user_id,
        date=datetime.now(timezone.utc).date().isoformat(),
        stayed_on_track=request.stayed_on_track,
        mood=request.mood,
        had_urges=request.had_urges,
        urge_triggers=request.urge_triggers
    )
    
    await db.checkins.insert_one(checkin.dict())
    
    # Check for new achievements after checkin
    await check_and_award_achievements(request.user_id, user.dict())
    
    return checkin

@app.get("/api/users/{user_id}/checkins", response_model=List[CheckIn])
async def get_user_checkins(user_id: str):
    checkins = await db.checkins.find({"user_id": user_id}).sort("created_at", -1).to_list(length=30)
    return [CheckIn(**checkin) for checkin in checkins]

@app.get("/api/users/{user_id}/progress")
async def get_user_progress(user_id: str):
    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User(**user_doc)
    
    # Get galaxy progress data
    galaxy_data = get_galaxy_progress_data(
        user.current_streak,
        user.total_days_clean,
        user.achievements
    )
    
    # Get achievement details
    user_achievement_details = []
    for achievement_id in user.achievements:
        achievement = next((a for a in ACHIEVEMENTS if a['id'] == achievement_id), None)
        if achievement:
            user_achievement_details.append(achievement)
    
    # Get available achievements (not yet earned)
    available_achievements = [
        a for a in ACHIEVEMENTS 
        if a['id'] not in user.achievements
    ]
    
    return {
        "galaxy": galaxy_data,
        "achievements": {
            "earned": user_achievement_details,
            "available": available_achievements[:5]  # Show next 5 available
        },
        "stats": {
            "current_streak": user.current_streak,
            "best_streak": user.best_streak,
            "total_days_clean": user.total_days_clean,
            "total_achievements": len(user.achievements)
        }
    }

@app.get("/api/users/{user_id}/weekly-report")
async def generate_weekly_report(user_id: str):
    """Generate weekly Aura Pulse report"""
    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get data from last 7 days
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    week_checkins = await db.checkins.find({
        "user_id": user_id,
        "created_at": {"$gte": week_start.isoformat()}
    }).to_list(None)
    
    if not week_checkins:
        return {"message": "Not enough data for weekly report yet. Complete a few more check-ins!"}
    
    # Calculate statistics
    total_checkins = len(week_checkins)
    clean_days = sum(1 for c in week_checkins if c.get('stayed_on_track'))
    total_urges = sum(1 for c in week_checkins if c.get('had_urges'))
    avg_mood = sum(c.get('mood', 3) for c in week_checkins) / total_checkins if total_checkins > 0 else 3
    
    # Find most common trigger
    triggers = [c.get('urge_triggers') for c in week_checkins if c.get('urge_triggers')]
    most_common_trigger = max(set(triggers), key=triggers.count) if triggers else None
    
    # Generate insights
    insights = []
    if avg_mood >= 4:
        insights.append("🌟 Your mood has been consistently positive this week!")
    if clean_days == total_checkins:
        insights.append("🎉 Perfect week! You stayed on track every single day.")
    if total_urges == 0:
        insights.append("💪 Amazing! No urges reported this week - you're building strong mental fortitude.")
    elif total_urges > 0:
        insights.append(f"🛡️ You faced {total_urges} urges but stayed strong - that's real resilience!")
    
    if most_common_trigger:
        insights.append(f"🔍 Your main trigger this week was '{most_common_trigger}' - let's create a specific plan for this.")
    
    # Check achievements earned this week
    week_achievements = []  # Could implement by tracking achievement timestamps
    
    report = WeeklyReport(
        user_id=user_id,
        week_start=week_start.date().isoformat(),
        week_end=datetime.now(timezone.utc).date().isoformat(),
        avg_mood=avg_mood,
        clean_days=clean_days,
        total_urges=total_urges,
        most_common_trigger=most_common_trigger,
        achievements_earned=week_achievements,
        insights=insights
    )
    
    # Store report
    await db.weekly_reports.insert_one(report.dict())
    
    return report

@app.post("/api/relapses", response_model=Relapse)
async def report_relapse(request: RelapseRequest):
    # Reset user streak but keep total days clean
    await db.users.update_one(
        {"id": request.user_id},
        {"$set": {"current_streak": 0}}
    )
    
    relapse = Relapse(
        user_id=request.user_id,
        date=datetime.now(timezone.utc).date().isoformat(),
        trigger_analysis=request.trigger_analysis,
        emotional_state=request.emotional_state,
        time_of_day=request.time_of_day
    )
    
    await db.relapses.insert_one(relapse.dict())
    return relapse

@app.get("/api/users/{user_id}/chat-history/{session_id}")
async def get_chat_history(user_id: str, session_id: str):
    messages = await db.chat_messages.find({
        "user_id": user_id,
        "session_id": session_id
    }).sort("created_at", 1).to_list(length=100)
    
    return [ChatMessage(**msg) for msg in messages]

@app.post("/api/sos")
async def sos_support(request: ChatRequest):
    """Special SOS endpoint for immediate urge support"""
    # Add SOS context to message to trigger Alex personality
    sos_message = f"[SOS - URGENT SUPPORT NEEDED] {request.message}"
    request.message = sos_message
    
    return await chat_with_aura(request)

@app.get("/api/achievements")
async def get_all_achievements():
    """Get list of all available achievements"""
    return {"achievements": ACHIEVEMENTS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)