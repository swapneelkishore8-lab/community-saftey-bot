"""
Community Safety & Misinformation Detection Chatbot
An AI-enabled chatbot for identifying misinformation, reporting cybercrime, 
understanding digital laws, and staying safe from online frauds.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'community-safety-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///community_safety.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300
}

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure Google Generative AI
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', 'YOUR_API_KEY_HERE')
genai.configure(api_key=GOOGLE_API_KEY)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    risk_level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReportedContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# AI Model Configuration
def get_bot_response(mode, user_message):
    """Generate AI response based on the selected mode"""
    
    mode_prompts = {
        'misinformation': f"""
You are a Misinformation Risk Checker assistant for the Community Safety Bot. 
Your role is to analyze messages and identify potential misinformation risks.
Analyze the following message for:
- Urgency indicators
- Emotional manipulation
- Lack of credible sources
- Forward-type patterns
- Suspicious claims

Provide a risk assessment (Low/Medium/High) with a brief explanation.
Do NOT claim to verify truth, only assess risk level.
Keep your response helpful and educational.
User's message: {user_message}
""",
        'cybercrime': f"""
You are a Cyber Crime Help & Reporting assistant for the Community Safety Bot.
Your role is to provide guidance on cybercrime reporting and prevention.
Include information about:
- Official reporting channels (cybercrime.gov.in, 1930 helpline)
- Step-by-step guidance for different scenarios
- Immediate actions to take
- What NOT to do in panic situations
- Legal resources and support

User's question: {user_message}
""",
        'abuse': f"""
You are an Online Abuse & Harassment Awareness assistant for the Community Safety Bot.
Your role is to educate users about online abuse, harassment, and their rights.
Explain in simple language:
- What counts as online abuse
- Types of online harassment
- User rights and legal protections
- When and how to report
- Safety guidelines and prevention
- Resources for help

User's question: {user_message}
""",
        'fraud': f"""
You are a Bank Fraud & Scam Awareness assistant for the Community Safety Bot.
Your role is to educate users about banking fraud and online scams.
Cover:
- Common scams: OTP fraud, fake KYC, UPI scams, job fraud
- Red flags to watch for
- Immediate actions if scammed
- Prevention tips
- How to verify legitimate communications

User's question: {user_message}
""",
        'general': f"""
You are the Community Safety Bot, an AI assistant helping communities stay safe online.
You can help with:
- Misinformation detection
- Cybercrime reporting guidance
- Online safety awareness
- Banking fraud prevention

Provide helpful, accurate, and empowering responses.
User's message: {user_message}
"""
    }
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = mode_prompts.get(mode, mode_prompts['general'])
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"I apologize, but I'm having trouble connecting to my AI brain right now. Please try again later. Error: {str(e)}"

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', user=current_user)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    mode = data.get('mode', 'general')
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Please enter a message'}), 400
    
    # Get bot response
    bot_response = get_bot_response(mode, message)
    
    # Determine risk level for misinformation mode
    risk_level = None
    if mode == 'misinformation':
        message_lower = message.lower()
        if any(word in message_lower for word in ['urgent', 'immediately', 'emergency', 'share', 'forward']):
            if any(word in message_lower for word in ['bank', 'account', 'otp', 'password', 'upi']):
                risk_level = 'high'
            else:
                risk_level = 'medium'
        else:
            risk_level = 'low'
    
    # Save to chat history
    chat_record = ChatHistory(
        user_id=current_user.id,
        mode=mode,
        user_message=message,
        bot_response=bot_response,
        risk_level=risk_level
    )
    db.session.add(chat_record)
    db.session.commit()
    
    return jsonify({
        'response': bot_response,
        'mode': mode,
        'risk_level': risk_level,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/chat/history')
@login_required
def chat_history():
    chats = ChatHistory.query.filter_by(user_id=current_user.id).order_by(
        ChatHistory.created_at.desc()
    ).limit(50).all()
    
    return jsonify([{
        'id': chat.id,
        'mode': chat.mode,
        'user_message': chat.user_message,
        'bot_response': chat.bot_response,
        'risk_level': chat.risk_level,
        'created_at': chat.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for chat in chats])

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        content_type = request.form.get('content_type')
        description = request.form.get('description')
        
        report = ReportedContent(
            user_id=current_user.id,
            content_type=content_type,
            description=description
        )
        db.session.add(report)
        db.session.commit()
        flash('Report submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/emergency')
def emergency():
    return render_template('emergency.html')

@app.route('/news')
def news():
    # Sample cyber security news (in production, fetch from API)
    cyber_news = [
        {
            'title': 'New Phishing Campaign Targets Banking Users',
            'description': 'Security experts warn of sophisticated phishing emails mimicking bank communications.',
            'date': '2024-01-15',
            'source': 'CyberWatch'
        },
        {
            'title': 'Government Launches Cyber Awareness Program',
            'description': 'New initiative to educate citizens about online safety and digital literacy.',
            'date': '2024-01-14',
            'source': 'Digital India News'
        },
        {
            'title': 'UPI Fraud Prevention Guidelines Released',
            'description': 'RBI issues new guidelines to prevent UPI-related frauds and protect users.',
            'date': '2024-01-13',
            'source': 'Finance Ministry'
        }
    ]
    return render_template('news.html', news=cyber_news)

@app.route('/about')
def about():
    return render_template('about.html')

# Admin routes
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    users = User.query.all()
    reports = ReportedContent.query.all()
    return render_template('admin.html', users=users, reports=reports)

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(username='admin', email='admin@communitysafety.com', 
                        password=hashed_password, is_admin=True)
            db.session.add(admin)
            db.session.commit()
            print("Admin user created with username: admin, password: admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)

