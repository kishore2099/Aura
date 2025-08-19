import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  // State Management
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('welcome'); // welcome, onboarding, dashboard, chat, progress
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userProgress, setUserProgress] = useState(null);
  const [weeklyReport, setWeeklyReport] = useState(null);
  const [checkinData, setCheckinData] = useState({
    stayed_on_track: true,
    mood: 3,
    had_urges: false,
    urge_triggers: ''
  });

  // Form States
  const [onboardingData, setOnboardingData] = useState({
    name: '',
    goal: ''
  });

  const chatEndRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);

  // Load user from localStorage
  useEffect(() => {
    const savedUser = localStorage.getItem('auraUser');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
      setCurrentView('dashboard');
      loadUserProgress(JSON.parse(savedUser).id);
    }
  }, []);

  // Helper Functions
  const saveUser = (userData) => {
    setUser(userData);
    localStorage.setItem('auraUser', JSON.stringify(userData));
  };

  const loadUserProgress = async (userId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${userId}/progress`);
      if (response.ok) {
        const progressData = await response.json();
        setUserProgress(progressData);
      }
    } catch (error) {
      console.error('Error loading user progress:', error);
    }
  };

  const loadWeeklyReport = async (userId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${userId}/weekly-report`);
      if (response.ok) {
        const reportData = await response.json();
        setWeeklyReport(reportData);
      }
    } catch (error) {
      console.error('Error loading weekly report:', error);
    }
  };

  const handleCreateUser = async () => {
    if (!onboardingData.name || !onboardingData.goal) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(onboardingData)
      });
      
      const userData = await response.json();
      saveUser(userData);
      await loadUserProgress(userData.id);
      setCurrentView('dashboard');
      
      // Send welcome message
      await sendMessage(`Hello Aura! I'm ${userData.name} and I just joined. I'm ready to start my journey toward ${userData.goal}. Please introduce yourself and help me understand how we'll work together.`, true);
    } catch (error) {
      console.error('Error creating user:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (message, isWelcome = false) => {
    if (!message.trim() && !isWelcome) return;
    
    const messageToSend = message || chatInput;
    setChatInput('');
    setIsLoading(true);
    
    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      message_type: 'user',
      content: messageToSend,
      created_at: new Date().toISOString()
    };
    
    if (!isWelcome) {
      setChatMessages(prev => [...prev, userMessage]);
    }
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          message: messageToSend,
          session_id: sessionId
        })
      });
      
      const result = await response.json();
      
      if (!sessionId) {
        setSessionId(result.session_id);
      }
      
      // Update user progress if returned
      if (result.user_progress) {
        setUserProgress(result.user_progress);
        
        // Show achievement notifications
        if (result.user_progress.new_achievements && result.user_progress.new_achievements.length > 0) {
          result.user_progress.new_achievements.forEach(achievement => {
            showAchievementNotification(achievement);
          });
        }
      }
      
      // Add AI response to chat
      const aiMessage = {
        id: Date.now() + 1,
        message_type: 'ai',
        content: result.ai_message,
        personalities: result.personalities_used || ['alex'],
        created_at: new Date().toISOString()
      };
      
      setChatMessages(prev => isWelcome ? [userMessage, aiMessage] : [...prev, aiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const showAchievementNotification = (achievement) => {
    // Create a toast notification for new achievement
    const notification = document.createElement('div');
    notification.className = 'achievement-notification';
    notification.innerHTML = `
      <div class="achievement-toast">
        <div class="achievement-icon">${achievement.icon}</div>
        <div class="achievement-content">
          <div class="achievement-title">Achievement Unlocked!</div>
          <div class="achievement-name">${achievement.name}</div>
          <div class="achievement-description">${achievement.description}</div>
        </div>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 5000);
  };

  const handleSOS = async () => {
    await sendMessage("I'm having a strong urge right now and I need immediate support. Please help me through this moment and give me strategies to get through it safely.");
    setCurrentView('chat');
  };

  const submitCheckin = async () => {
    setIsLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/checkins`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          ...checkinData
        })
      });
      
      // Refresh user data to get updated streak
      const userResponse = await fetch(`${BACKEND_URL}/api/users/${user.id}`);
      const updatedUser = await userResponse.json();
      saveUser(updatedUser);
      
      // Refresh progress data
      await loadUserProgress(user.id);
      
      // Reset form
      setCheckinData({
        stayed_on_track: true,
        mood: 3,
        had_urges: false,
        urge_triggers: ''
      });
      
      alert('Check-in completed! Keep building your galaxy of progress! ✨');
    } catch (error) {
      console.error('Error submitting check-in:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getPersonalityIcon = (personality) => {
    switch (personality) {
      case 'alex': return '🫂'; // Empathetic Coach
      case 'casey': return '🧠'; // Strategist
      case 'leo': return '⚡'; // Motivator
      default: return '🌟';
    }
  };

  const getPersonalityName = (personality) => {
    switch (personality) {
      case 'alex': return 'Alex';
      case 'casey': return 'Casey';
      case 'leo': return 'Leo';
      default: return 'Aura';
    }
  };

  const renderPersonalities = (personalities) => {
    if (!personalities || personalities.length === 0) return null;
    
    return (
      <div className="personality-indicators">
        {personalities.map((personality, index) => (
          <span key={index} className="personality-tag">
            {getPersonalityIcon(personality)} {getPersonalityName(personality)}
          </span>
        ))}
      </div>
    );
  };

  // Render Functions
  const renderWelcome = () => (
    <div className="welcome-container">
      <div className="hero-section">
        <div className="aura-logo">
          <div className="logo-circle">
            <span className="logo-text">Aura</span>
          </div>
        </div>
        <h1 className="hero-title">Your Compassionate AI Guide</h1>
        <p className="hero-subtitle">
          Reclaim your focus, energy, and life with unwavering, non-judgmental support
        </p>
        <button 
          className="btn btn-primary"
          onClick={() => setCurrentView('onboarding')}
        >
          Start Your Journey
        </button>
      </div>
      
      <div className="features-grid">
        <div className="feature-card">
          <div className="feature-icon">🫂</div>
          <h3>Empathetic Support</h3>
          <p>Alex provides compassionate guidance without judgment</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🧠</div>
          <h3>Smart Strategies</h3>
          <p>Casey offers personalized plans and trigger analysis</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">⚡</div>
          <h3>Daily Motivation</h3>
          <p>Leo celebrates progress and keeps you inspired</p>
        </div>
      </div>
    </div>
  );

  const renderOnboarding = () => (
    <div className="onboarding-container">
      <div className="onboarding-card">
        <div className="aura-logo-small">
          <span>Aura</span>
        </div>
        
        <h2>Welcome to Your Journey</h2>
        <p>Let's start by getting to know you better.</p>
        
        <div className="form-group">
          <label>What should I call you?</label>
          <input
            type="text"
            placeholder="Your name"
            value={onboardingData.name}
            onChange={(e) => setOnboardingData(prev => ({...prev, name: e.target.value}))}
            className="form-input"
          />
        </div>
        
        <div className="form-group">
          <label>What is your primary goal?</label>
          <textarea
            placeholder="e.g., I want to regain focus for my studies, improve my relationships, build better habits..."
            value={onboardingData.goal}
            onChange={(e) => setOnboardingData(prev => ({...prev, goal: e.target.value}))}
            className="form-textarea"
            rows={4}
          />
        </div>
        
        <button 
          className="btn btn-primary"
          onClick={handleCreateUser}
          disabled={!onboardingData.name || !onboardingData.goal || isLoading}
        >
          {isLoading ? 'Creating...' : 'Begin My Journey'}
        </button>
      </div>
    </div>
  );

  const renderGalaxyVisualization = () => {
    if (!userProgress?.galaxy) return null;
    
    const { galaxy } = userProgress;
    
    return (
      <div className="galaxy-container">
        <div className="galaxy-header">
          <h3>Your Personal Galaxy</h3>
          <p>Level {galaxy.galaxy_level} • {galaxy.total_light_years} Light Years Traveled</p>
        </div>
        
        <div className="galaxy-view">
          <div className="stars-container">
            {galaxy.stars.slice(0, 50).map((star, index) => (
              <div 
                key={index}
                className="star"
                style={{
                  opacity: star.brightness,
                  left: `${(star.day * 7) % 300}px`,
                  top: `${50 + (star.day * 3) % 100}px`,
                  animationDelay: `${star.day * 0.1}s`
                }}
              >
                ⭐
              </div>
            ))}
          </div>
          
          <div className="constellation-info">
            <h4>Constellations Unlocked:</h4>
            <div className="constellations">
              {galaxy.constellations_unlocked.map((constellation, index) => (
                <span key={index} className="constellation-badge">
                  ✨ {constellation}
                </span>
              ))}
            </div>
            
            {galaxy.next_constellation && (
              <div className="next-constellation">
                <p>Next: <strong>{galaxy.next_constellation.name}</strong></p>
                <p>{galaxy.next_constellation.days_needed} days to go</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderAchievements = () => {
    if (!userProgress?.achievements) return null;
    
    const { earned, available } = userProgress.achievements;
    
    return (
      <div className="achievements-section">
        <h3>Achievements</h3>
        
        <div className="earned-achievements">
          <h4>Unlocked ({earned.length})</h4>
          <div className="achievements-grid">
            {earned.map((achievement, index) => (
              <div key={index} className="achievement-card earned">
                <div className="achievement-icon">{achievement.icon}</div>
                <div className="achievement-name">{achievement.name}</div>
                <div className="achievement-description">{achievement.description}</div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="available-achievements">
          <h4>Coming Up</h4>
          <div className="achievements-grid">
            {available.slice(0, 3).map((achievement, index) => (
              <div key={index} className="achievement-card available">
                <div className="achievement-icon">{achievement.icon}</div>
                <div className="achievement-name">{achievement.name}</div>
                <div className="achievement-description">{achievement.description}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderProgressView = () => (
    <div className="progress-container">
      <div className="progress-header">
        <button 
          className="btn-back"
          onClick={() => setCurrentView('dashboard')}
        >
          ← Back to Dashboard
        </button>
        <h2>Your Journey Visualization</h2>
      </div>
      
      {renderGalaxyVisualization()}
      {renderAchievements()}
      
      <div className="weekly-report-section">
        <h3>Weekly Aura Pulse</h3>
        <button 
          className="btn btn-secondary"
          onClick={() => loadWeeklyReport(user.id)}
        >
          Generate This Week's Report
        </button>
        
        {weeklyReport && weeklyReport.insights && (
          <div className="weekly-report">
            <h4>Insights for This Week:</h4>
            <ul>
              {weeklyReport.insights.map((insight, index) => (
                <li key={index}>{insight}</li>
              ))}
            </ul>
            <div className="report-stats">
              <div className="stat">
                <span className="stat-number">{weeklyReport.clean_days}</span>
                <span className="stat-label">Clean Days</span>
              </div>
              <div className="stat">
                <span className="stat-number">{weeklyReport.avg_mood.toFixed(1)}</span>
                <span className="stat-label">Avg Mood</span>
              </div>
              <div className="stat">
                <span className="stat-number">{weeklyReport.total_urges}</span>
                <span className="stat-label">Urges Faced</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderDashboard = () => (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="user-welcome">
          <h1>Welcome back, {user.name}!</h1>
          <p>You're building a life you don't want to escape from.</p>
        </div>
        <div className="streak-display">
          <div className="streak-number">{user.current_streak}</div>
          <div className="streak-label">Day Streak</div>
          <div className="best-streak">Best: {user.best_streak} days</div>
          {userProgress && (
            <div className="galaxy-level">
              Galaxy Level {userProgress.galaxy?.galaxy_level || 1}
            </div>
          )}
        </div>
      </div>

      <div className="action-grid">
        <div className="action-card progress-card">
          <h3>🌌 Your Journey</h3>
          <p>Visualize your progress in your personal galaxy</p>
          {userProgress && (
            <div className="mini-galaxy">
              <p>{userProgress.galaxy.stars.length} stars earned</p>
              <p>{userProgress.achievements.earned.length} achievements unlocked</p>
            </div>
          )}
          <button 
            className="btn btn-secondary"
            onClick={() => setCurrentView('progress')}
          >
            View Progress
          </button>
        </div>
        
        <div className="action-card daily-checkin">
          <h3>📋 Daily Check-In</h3>
          <p>How are you doing today?</p>
          
          <div className="checkin-form">
            <div className="form-group">
              <label>Did you stay on track today?</label>
              <div className="radio-group">
                <label>
                  <input
                    type="radio"
                    checked={checkinData.stayed_on_track === true}
                    onChange={() => setCheckinData(prev => ({...prev, stayed_on_track: true}))}
                  />
                  Yes
                </label>
                <label>
                  <input
                    type="radio"
                    checked={checkinData.stayed_on_track === false}
                    onChange={() => setCheckinData(prev => ({...prev, stayed_on_track: false}))}
                  />
                  No
                </label>
              </div>
            </div>
            
            <div className="form-group">
              <label>Mood (1-5)</label>
              <select 
                value={checkinData.mood}
                onChange={(e) => setCheckinData(prev => ({...prev, mood: parseInt(e.target.value)}))}
                className="form-select"
              >
                <option value={1}>1 - Very Low</option>
                <option value={2}>2 - Low</option>
                <option value={3}>3 - Neutral</option>
                <option value={4}>4 - Good</option>
                <option value={5}>5 - Excellent</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Did you experience urges?</label>
              <div className="radio-group">
                <label>
                  <input
                    type="radio"
                    checked={checkinData.had_urges === false}
                    onChange={() => setCheckinData(prev => ({...prev, had_urges: false, urge_triggers: ''}))}
                  />
                  No
                </label>
                <label>
                  <input
                    type="radio"
                    checked={checkinData.had_urges === true}
                    onChange={() => setCheckinData(prev => ({...prev, had_urges: true}))}
                  />
                  Yes
                </label>
              </div>
            </div>
            
            {checkinData.had_urges && (
              <div className="form-group">
                <label>What triggered the urge?</label>
                <input
                  type="text"
                  placeholder="e.g., stress, boredom, specific situation..."
                  value={checkinData.urge_triggers}
                  onChange={(e) => setCheckinData(prev => ({...prev, urge_triggers: e.target.value}))}
                  className="form-input"
                />
              </div>
            )}
            
            <button 
              className="btn btn-primary"
              onClick={submitCheckin}
              disabled={isLoading}
            >
              {isLoading ? 'Submitting...' : 'Submit Check-In'}
            </button>
          </div>
        </div>
        
        <div className="action-card chat-card">
          <h3>💬 Chat with Aura</h3>
          <p>Talk to your unified AI guide - Alex, Casey, and Leo are all here to support you</p>
          <button 
            className="btn btn-secondary"
            onClick={() => setCurrentView('chat')}
          >
            Start Conversation
          </button>
        </div>
        
        <div className="action-card sos-card">
          <h3>🆘 Emergency Support</h3>
          <p>Feeling a strong urge? Get immediate help from Aura.</p>
          <button 
            className="btn btn-urgent"
            onClick={handleSOS}
          >
            I Need Help Now
          </button>
        </div>
      </div>
    </div>
  );

  const renderChat = () => (
    <div className="chat-container">
      <div className="chat-header">
        <button 
          className="btn-back"
          onClick={() => setCurrentView('dashboard')}
        >
          ← Back
        </button>
        <div className="chat-title">
          <div className="aura-avatar">🌟</div>
          <div>
            <h3>Chat with Aura</h3>
            <p>Alex • Casey • Leo - Your unified AI guide</p>
          </div>
        </div>
      </div>
      
      <div className="chat-messages">
        {chatMessages.map((message, index) => (
          <div 
            key={message.id || index} 
            className={`message ${message.message_type}`}
          >
            {message.message_type === 'ai' && (
              <div className="message-header">
                {renderPersonalities(message.personalities)}
              </div>
            )}
            <div className="message-content">{message.content}</div>
            <div className="message-time">
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message ai">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={chatEndRef} />
      </div>
      
      <div className="chat-input-container">
        <input
          type="text"
          placeholder="Share what's on your mind..."
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          className="chat-input"
          disabled={isLoading}
        />
        <button 
          className="btn-send"
          onClick={() => sendMessage()}
          disabled={!chatInput.trim() || isLoading}
        >
          Send
        </button>
      </div>
    </div>
  );

  // Main Render
  return (
    <div className="App">
      {currentView === 'welcome' && renderWelcome()}
      {currentView === 'onboarding' && renderOnboarding()}
      {currentView === 'dashboard' && renderDashboard()}
      {currentView === 'chat' && renderChat()}
      {currentView === 'progress' && renderProgressView()}
    </div>
  );
}

export default App;