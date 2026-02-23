import os
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'community-safety-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///community_safety.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Google Gemini Configuration ---
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Check your .env file.")

genai.configure(api_key=GOOGLE_API_KEY)

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReportedContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Robust AI Interaction Logic ---
def get_bot_response(mode, user_message):
    prompt = f"Role: {mode} Safety Expert. User Message: {user_message}"

    model_candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)

            if response and hasattr(response, "text") and response.text:
                return response.text

        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
                try:
                    model = genai.GenerativeModel(model_name)
                    retry = model.generate_content(prompt)
                    if retry and hasattr(retry, "text"):
                        return retry.text
                except:
                    pass
            print(f"Model {model_name} failed: {e}")
            continue

    return "The AI service is temporarily busy. Please try again."

# --- App Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        new_user = User(username=request.form['username'], email=request.form['email'], password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except:
            flash('User already exists.', 'error')
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    mode = data.get('mode', 'general')
    msg = data.get('message', '')
    bot_res = get_bot_response(mode, msg)
    
    # Save to history
    db.session.add(ChatHistory(user_id=current_user.id, mode=mode, user_message=msg, bot_response=bot_res))
    db.session.commit()
    return jsonify({'response': bot_res})

# Fixed routes for the index.html navigation
@app.route('/about')
def about(): return render_template('about.html')

@app.route('/news')
def news(): return render_template('news.html')

@app.route('/emergency')
def emergency(): return render_template('emergency.html')

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        db.session.add(ReportedContent(
            user_id=current_user.id,
            content_type=request.form['content_type'],
            description=request.form['description']
        ))
        db.session.commit()
        flash('Report submitted successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(
                username='admin', 
                email='admin@safety.com', 
                password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                is_admin=True
            ))
            db.session.commit()
    
    app.run(debug=True, host='0.0.0.0', port=5000)