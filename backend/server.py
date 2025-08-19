from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import os
import uuid
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
    personality: Optional[str] = None  # "alex", "casey", "leo"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Relapse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str
    trigger_analysis: Optional[str] = None
    emotional_state: Optional[str] = None
    time_of_day: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# Request/Response Models
class CreateUserRequest(BaseModel):
    name: str
    goal: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None
    personality: Optional[str] = None  # "alex", "casey", "leo", or None for auto

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
    personality_used: str
    session_id: str

# Personality System Messages
PERSONALITY_PROMPTS = {
    "alex": """You are "Alex," the Empathetic Coach personality of Aura. You are warm, patient, and an excellent listener. Your role is to validate feelings, offer comfort, and reduce shame. 

Key phrases you use:
- "It sounds like that was really tough. It's okay to feel that way."
- "Thank you for sharing that with me. It takes courage."
- "What's on your mind right now?"

Always be compassionate and non-judgmental. Focus on emotional support and validation.""",

    "casey": """You are "Casey," the Strategist personality of Aura. You are logical, clear-thinking, and a problem-solver. Your role is to analyze triggers, identify patterns, and co-create actionable plans.

Key phrases you use:
- "Let's break this down. What was happening right before the urge hit?"
- "I've noticed a pattern. Let's create a specific 'If-Then' plan for that time."
- "What is one small, concrete action you can take right now?"

Always be analytical and solution-focused. Help users understand their patterns and build strategies.""",

    "leo": """You are "Leo," the Motivator personality of Aura. You are energetic and inspiring, providing encouragement and celebrating progress. Your role is to boost morale, celebrate milestones, and provide motivational fuel.

Key phrases you use:
- "You've made it another 24 hours! That's a huge win, and you should be proud."
- "Remember why you started this journey. Think about the focus and freedom you're fighting for."
- "Here is a thought for today: 'A river cuts through rock, not because of its power, but because of its persistence.'"

Always be encouraging and inspirational. Focus on motivation and celebrating progress."""
}

def get_base_system_message():
    return """You are "Aura," a compassionate and intelligent AI guide. Your sole mission is to provide unwavering, non-judgmental support to users on their journey to quit pornography and reclaim their focus, energy, and life. You are a coach, a strategist, a motivator, and a safe space. Your primary goal is to empower the user to build a life they don't want to escape from.

CORE RULES:
- NEVER use shaming, guilt-inducing, or disappointed language
- Always be supportive, patient, and empowering
- Keep responses concise, clear, and actionable
- Be proactive and caring

You have access to the user's streak data, mood history, and previous conversations to provide personalized support."""

async def create_llm_chat(session_id: str, personality: str = None):
    """Create a new LLM chat instance with appropriate system message"""
    base_message = get_base_system_message()
    
    if personality and personality in PERSONALITY_PROMPTS:
        system_message = f"{base_message}\n\n{PERSONALITY_PROMPTS[personality]}"
    else:
        # Auto-select personality based on context or default to Alex
        system_message = f"{base_message}\n\n{PERSONALITY_PROMPTS['alex']}"
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message
    ).with_model("anthropic", "claude-3-5-sonnet-20241022")
    
    return chat

def determine_personality(message: str, user_context: dict = None):
    """Simple heuristic to determine which personality to use"""
    message_lower = message.lower()
    
    # Keywords that suggest needing Casey (Strategist)
    strategy_keywords = ["plan", "trigger", "pattern", "strategy", "how to", "what should", "analyze"]
    if any(keyword in message_lower for keyword in strategy_keywords):
        return "casey"
    
    # Keywords that suggest needing Leo (Motivator)
    motivate_keywords = ["motivation", "encourage", "celebrate", "proud", "achievement", "progress"]
    if any(keyword in message_lower for keyword in motivate_keywords):
        return "leo"
    
    # Keywords that suggest needing Alex (Empathetic Coach) or default
    return "alex"

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
    
    # Determine personality if not specified
    personality = request.personality or determine_personality(request.message, user.dict())
    
    try:
        # Create LLM chat instance
        chat = await create_llm_chat(session_id, personality)
        
        # Add user context to the message
        context_message = f"""User Context:
Name: {user.name}
Goal: {user.goal}
Current Streak: {user.current_streak} days
Best Streak: {user.best_streak} days

User Message: {request.message}"""
        
        # Send message to LLM
        user_message = UserMessage(text=context_message)
        response = await chat.send_message(user_message)
        
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
            personality=personality
        )
        await db.chat_messages.insert_one(ai_msg.dict())
        
        return ChatResponse(
            ai_message=response,
            personality_used=personality,
            session_id=session_id
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
    
    # Update streak based on check-in
    if request.stayed_on_track:
        user.current_streak += 1
        if user.current_streak > user.best_streak:
            user.best_streak = user.current_streak
    else:
        user.current_streak = 0  # Reset streak on relapse
    
    # Update user in database
    await db.users.update_one(
        {"id": request.user_id},
        {"$set": {
            "current_streak": user.current_streak,
            "best_streak": user.best_streak
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
    return checkin

@app.get("/api/users/{user_id}/checkins", response_model=List[CheckIn])
async def get_user_checkins(user_id: str):
    checkins = await db.checkins.find({"user_id": user_id}).sort("created_at", -1).to_list(length=30)
    return [CheckIn(**checkin) for checkin in checkins]

@app.post("/api/relapses", response_model=Relapse)
async def report_relapse(request: RelapseRequest):
    # Reset user streak
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
    # Force Alex personality for immediate emotional support
    request.personality = "alex"
    
    # Add SOS context to message
    sos_message = f"[SOS - URGENT SUPPORT NEEDED] {request.message}"
    request.message = sos_message
    
    return await chat_with_aura(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)