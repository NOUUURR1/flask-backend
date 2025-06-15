from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail, Message
import bcrypt
import os
import random

app = Flask(name, static_folder='static', template_folder='templates')
CORS(app)

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# إعدادات الإيميل
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'youremail@gmail.com'  # ← غيره لإيميلك
app.config['MAIL_PASSWORD'] = 'your_app_password'    # ← باسورد التطبيق من Gmail
mail = Mail(app)

# جدول المستخدم
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    birthdate = db.Column(db.String(20))
    profile_image_url = db.Column(db.String(500))
    reset_code = db.Column(db.String(10))  # ← كود استرجاع كلمة المرور

# إنشاء الجداول
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

# Signup API
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')

    if not email or not password or not full_name:
        return jsonify({'message': 'Full name, email, and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(full_name=full_name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Signup successful', 'user_id': new_user.id}), 200

# Login API
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({'message': 'Login successful', 'user_id': user.id}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# Get Profile
@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "birthdate": user.birthdate,
        "profile_image_url": user.profile_image_url
    }), 200

# Update Profile
@app.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    user.full_name = data.get("full_name", user.full_name)
    user.birthdate = data.get("birthdate", user.birthdate)
    user.profile_image_url = data.get("profile_image_url", user.profile_image_url)

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200

# Awareness Articles API
awareness_articles = [
    {
        "title": "Positive Parenting Tips",
        "description": "Learn 5 essential positive parenting strategies...",
        "video_url": "https://www.youtube.com/embed/BbXPrO2AlDk",
        "link": "https://happyyouhappyfamily.com/positive-parenting-videos/"
    },
{
        "title": "Child Mental Health & Wellbeing",
        "description": "Discover top 10 tips to promote your child's mental health...",
        "video_url": "https://www.youtube.com/embed/ld7tBeduqBI",
        "link": "https://www.youtube.com/watch?v=ld7tBeduqBI"
    },
    {
        "title": "Positive Parenting, Thriving Kids",
        "description": "Access a series of 20 videos featuring caregivers...",
        "video_url": "https://www.youtube.com/embed/gcP3dx8Jvpc",
        "link": "https://childmind.org/positiveparenting/"
    },
    {
        "title": "Essentials for Parenting",
        "description": "Explore CDC's resources offering expert advice...",
        "video_url": "https://www.youtube.com/embed/w1xHDmsSduA",
        "link": "https://www.cdc.gov/parents/essentials/index.html"
    },
]

@app.route("/api/articles")
def get_articles():
    return jsonify(awareness_articles)

# 1️⃣ Send Reset Code
@app.route('/send-reset-code', methods=['POST'])
def send_reset_code():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'Email not found'}), 404

    code = str(random.randint(1000, 9999))
    user.reset_code = code
    db.session.commit()

    msg = Message('Password Reset Code',
                  sender='youremail@gmail.com',
                  recipients=[email])
    msg.body = f'Your reset code is: {code}'
    mail.send(msg)

    return jsonify({'message': 'Reset code sent successfully'}), 200

# 2️⃣ Verify Code
@app.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')

    user = User.query.filter_by(email=email).first()
    if not user or user.reset_code != code:
        return jsonify({'message': 'Invalid code'}), 400

    return jsonify({'message': 'Code verified successfully'}), 200

# 3️⃣ Reset Password
@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('new_password')
    code = data.get('code')

    user = User.query.filter_by(email=email).first()
    if not user or user.reset_code != code:
        return jsonify({'message': 'Invalid reset attempt'}), 400

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password = hashed_password
    user.reset_code = None
    db.session.commit()

    return jsonify({'message': 'Password reset successful'}), 200

# Run server
if name == 'main':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
