from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import bcrypt
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# موديل المستخدم
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

# صفحة HTML رئيسية
@app.route('/')
def home():
    return render_template('index.html')

# API: تسجيل حساب جديد
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'message': 'Signup successful',
        'user_id': new_user.id
    }), 200

# API: تسجيل الدخول
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({
            'message': 'Login successful',
            'user_id': user.id
        }), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# API: مقالات التوعية
awareness_articles = [
    {
        "title": "Positive Parenting Tips",
        "description": "Learn 5 essential positive parenting strategies to build a strong, loving, and respectful relationship with your child.",
        "video_url": "https://www.youtube.com/embed/BbXPrO2AlDk",
        "link": "https://happyyouhappyfamily.com/positive-parenting-videos/"
    },
    {
        "title": "Child Mental Health & Wellbeing",
        "description": "Discover top 10 tips to promote your child's mental health and wellbeing from a safeguarding expert.",
        "video_url": "https://www.youtube.com/embed/ld7tBeduqBI",
        "link": "https://www.youtube.com/watch?v=ld7tBeduqBI"
    },
    {
        "title": "Positive Parenting, Thriving Kids",
        "description": "Access a series of 20 videos featuring caregivers, kids, and experts discussing pressing parenting questions.",
        "video_url": "https://www.youtube.com/embed/gcP3dx8Jvpc",
        "link": "https://childmind.org/positiveparenting/"
    },
    {
        "title": "Essentials for Parenting",
        "description": "Explore CDC's resources offering expert advice, videos, and activities to help parents build nurturing relationships with their children.",
        "video_url": "https://www.youtube.com/embed/w1xHDmsSduA",
        "link": "https://www.cdc.gov/parents/essentials/index.html"
    },
]

@app.route("/api/articles")
def get_articles():
    return jsonify(awareness_articles)

# تشغيل السيرفر
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
