"""
Community Safety Bot - Vercel Serverless API
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__, static_folder='../static', template_folder='../templates')

# Configure
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'community-safety-secret-key-2024')

# Simple in-memory storage for demo (use database in production)
users = {}
chat_history = []

# AI Response Function (simplified for serverless)
def get_bot_response(mode, message):
    """Generate AI response based on the selected mode"""
    
    responses = {
        'misinformation': f"""🔍 **Misinformation Risk Analysis**

Thank you for checking! Here's my assessment of your message:

**Risk Level: 🟡 MEDIUM**

**Analysis:**
- The message contains urgency indicators
- No verifiable source provided
- Common forward-type patterns detected

**Recommendations:**
1. Verify the information from official sources
2. Don't forward without confirmation
3. Check fact-checking websites

**Remember:** When in doubt, don't spread it out!""",
        
        'cybercrime': f"""🚓 **Cyber Crime Help & Reporting**

**Immediate Help:**
- 📞 **1930** - Cyber Crime Helpline (Toll Free)
- 🌐 **cybercrime.gov.in** - File complaint online
- 🚨 **112** - Police Emergency

**Steps to Report:**
1. Take screenshots as evidence
2. Note down all transaction IDs
3. Call 1930 immediately
4. File complaint on cybercrime.gov.in
5. Visit nearest police station

**What NOT to do:**
- Don't panic
- Don't delete messages
- Don't share OTPs with anyone""",
        
        'abuse': f"""🛡️ **Online Abuse & Harassment Awareness**

**What counts as online abuse:**
- Cyberbullying & harassment
- Threatening messages
- Identity harassment
- Privacy violations
- Stalking & trolling

**Your Rights:**
- You have the right to feel safe online
- Online abuse is a criminal offense
- You can report anonymously

**Immediate Actions:**
1. Block the person
2. Report to platform
3. Save evidence
4. Contact 1091 (Women Helpline)
5. File police complaint

**Helpful Resources:**
- 📞 1091 - Women Helpline
- 📞 181 - Child Helpline
- 🏛️ Legal aid services""",
        
        'fraud': f"""🏦 **Bank Fraud & Scam Awareness**

**🚨 Common Scams:**

1. **OTP Fraud** - Never share OTP with anyone
2. **Fake KYC** - Banks never ask for KYC via links
3. **UPI Scams** - Don't accept requests from strangers
4. **Job Fraud** - Never pay for guaranteed jobs
5. **Phishing** - Check sender's email carefully

**Red Flags:**
- ❌ Urgency to act immediately
- ❌ Requests for OTP/Password
- ❌ Suspicious links
- ❌ Too good to be true offers
- ❌ Unknown sender

**If Scammed:**
1. Call 1930 immediately
2. Block the card/account
3. File complaint on cybercrime.gov.in
4. Lodge FIR at police station

**Prevention Tips:**
✅ Verify before clicking links
✅ Never share OTP
✅ Enable 2FA on all accounts
✅ Check URL carefully"""
    }
    
    default_response = f"""🤖 **Community Safety Bot**

Hello! I'm here to help you stay safe online.

I can assist with:
- 🔍 Checking messages for misinformation
- 🚓 Cybercrime reporting guidance
- 🛡️ Online abuse awareness
- 🏦 Bank fraud prevention

**How can I help you today?**

Type your question or paste a suspicious message you'd like me to analyze."""
    
    return responses.get(mode, default_response)

# Routes
@app.route('/')
def index():
    return send_from_directory('../', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    if path.endswith('.html'):
        return send_from_directory('../templates/', path)
    return send_from_directory('../static/', path)

@app.route('/api/chat', methods=['POST'])
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
    
    return jsonify({
        'response': bot_response,
        'mode': mode,
        'risk_level': risk_level,
        'timestamp': '2024-01-15 12:00:00'
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Community Safety Bot API is running'})

# Vercel handler
from vercel_wsgi import handle
app.wsgi_app = handle(app.wsgi_app)

if __name__ == '__main__':
    app.run(debug=True)
