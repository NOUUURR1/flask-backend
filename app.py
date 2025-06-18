from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import bcrypt
import os
import secrets
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Mail, Message
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise ValueError("SECRET_KEY environment variable is not set. It is required for security.")
s = URLSafeTimedSerializer(secret_key)

app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    birthdate = db.Column(db.String(20))
    profile_image_url = db.Column(db.String(500))
    reset_code = db.Column(db.String(100), nullable=True)
    reset_code_expires_at = db.Column(db.DateTime, nullable=True)


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return render_template('index.html')


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

    return jsonify({
        'message': 'Signup successful',
        'user_id': new_user.id
    }), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'message': 'Login successful',
            'user_id': user.id,
            'access_token': access_token
        }), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/profile/<int:user_id>', methods=['GET'])
@jwt_required()
def get_profile(user_id):
    print(f"DEBUG: In get_profile - Type of user_id: {type(user_id)}, Value: {user_id}") 
    
    current_user_id = get_jwt_identity()
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

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


@app.route('/profile/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_profile(user_id):
    current_user_id = get_jwt_identity()
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    user.full_name = data.get("full_name", user.full_name)
    user.birthdate = data.get("birthdate", user.birthdate)
    user.profile_image_url = data.get("profile_image_url", user.profile_image_url)

    db.session.commit()

    return jsonify({"message": "Profile updated successfully"}), 200


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


@app.route('/api/v1/password/forgot', methods=['POST'])
def send_reset_code_to_email():
    email = request.json.get('email')
    if not email:
        return jsonify({"status": "error", "message": "Email is required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status": "success", "message": "If your email is registered, a reset code has been sent."}), 200

    reset_code = secrets.token_hex(3).upper()
    expires_at = datetime.now() + timedelta(minutes=15)

    user.reset_code = reset_code
    user.reset_code_expires_at = expires_at

    print(f"DEBUG: Saved reset_code for {email}: {user.reset_code}")
    print(f"DEBUG: Expires at for {email}: {user.reset_code_expires_at}")

    db.session.commit()

    try:
        msg = Message("Your Password Reset Code",
                      recipients=[user.email])
        msg.body = f"Hello {user.full_name},\n\nYour password reset code is: {reset_code}\n\nThis code will expire in 15 minutes. If you did not request a password reset, please ignore this email.\n\nRegards,\nYour App Team"
        mail.send(msg)
        print(f"DEBUG: Email sent to {user.email} with code: {reset_code}")
        return jsonify({"status": "success", "message": "If your email is registered, a reset code has been sent."}), 200
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({"status": "error", "message": "Failed to send reset code. Please try again later."}), 500


@app.route('/api/v1/password/verify-reset-code', methods=['POST'])
def verify_reset_code():
    email = request.json.get('email')
    code = request.json.get('code')

    print(f"DEBUG: Received verification request for email: {email}, code: {code}")

    if not email or not code:
        return jsonify({"status": "error", "message": "Email and code are required."}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        print(f"DEBUG: User not found for email: {email}")
        return jsonify({"status": "error", "message": "Invalid or expired reset code."}), 400

    print(f"DEBUG: User found. Stored code: {user.reset_code}, Expiry: {user.reset_code_expires_at}, Current Time: {datetime.now()}")

    if user.reset_code != code:
        print(f"DEBUG: Code mismatch. Received: {code}, Stored: {user.reset_code}")
        return jsonify({"status": "error", "message": "Invalid or expired reset code."}), 400

    if not user.reset_code_expires_at or user.reset_code_expires_at < datetime.now():
        print(f"DEBUG: Code expired or no expiry set. Expiry: {user.reset_code_expires_at}, Current: {datetime.now()}")
        return jsonify({"status": "error", "message": "Invalid or expired reset code."}), 400

    reset_token = s.dumps({'email': user.email, 'action': 'reset_password'})
    print(f"DEBUG: Code verified successfully for {email}. Reset token generated.")

    return jsonify({
        "status": "success",
        "message": "Code verified successfully.",
        "resetToken": reset_token
    }), 200


@app.route('/api/v1/password/reset', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('newPassword')
    confirm_new_password = data.get('confirmNewPassword')
    reset_token = data.get('resetToken')

    if not email or not new_password or not confirm_new_password or not reset_token:
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

    if new_password != confirm_new_password:
        return jsonify({"status": "error", "message": "Passwords do not match."}), 400

    if len(new_password) < 8 or not any(char.isdigit() for char in new_password) \
            or not any(char.isupper() for char in new_password) or not any(char.islower() for char in new_password):
        return jsonify({"status": "error", "message": "Password must be at least 8 characters long and contain uppercase, lowercase, and numbers."}), 400

    try:
        token_data = s.loads(reset_token, max_age=300)
        if token_data['email'] != email or token_data['action'] != 'reset_password':
            raise BadTimeSignature
    except SignatureExpired:
        return jsonify({"status": "error", "message": "Reset token has expired."}), 400
    except BadTimeSignature:
        return jsonify({"status": "error", "message": "Invalid reset token."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    user.reset_code = None
    user.reset_code_expires_at = None

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password = hashed_password
    db.session.commit()

    return jsonify({"status": "success", "message": "Your password has been reset successfully."}), 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
