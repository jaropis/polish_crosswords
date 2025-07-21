import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
import time
from werkzeug.security import generate_password_hash, check_password_hash
from db import init_db, get_db, close_db
import sqlite3
import uuid
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# loading environment variables from .env file
load_dotenv()
app = Flask(__name__)
CORS(app)  # enabling cross-origin requests for development
app.teardown_appcontext(close_db)
jwt_secret_key=os.environ.get("JWT_SECRET_KEY")
if not jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY environment variable is not set. The application cannot start without it.")
app.config['JWT_SECRET_KEY'] = jwt_secret_key

app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['FRONTEND_URL'] = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """
    Check if the token is in the blacklist
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM BlacklistedTokens WHERE id = ?', (jwt_payload['jti'],))
        return cursor.fetchone() is not None
    except Exception as e:
        app.logger.error(f"Error checking token blacklist: {str(e)}")
        return False

# dictionary cache to improve performance
word_cache = {}
dictionary_loaded = False

def load_dictionary():
    """
    Load and cache the dictionary words by length for faster searches
    """
    global word_cache, dictionary_loaded
    
    start_time = time.time()
    print("Loading dictionary...")
    
    word_cache = {}  # resetting cache
    
    try:
        with open("pl_PL.dic", encoding="iso-8859-2") as file:
            for line in file:
                # parsing the dictionary entry
                slash_pos = line.find('/')
                if slash_pos != -1:
                    word = line[:slash_pos]
                else:
                    word = line.strip()
                
                # skipping empty words
                if not word:
                    continue
                
                # organizing by word length
                length = len(word)
                if length not in word_cache:
                    word_cache[length] = []
                
                word_cache[length].append(word.lower())
        
        dictionary_loaded = True
        elapsed = time.time() - start_time
        word_count = sum(len(words) for words in word_cache.values())
        print(f"Dictionary loaded in {elapsed:.2f}s - {word_count} words total")
    
    except Exception as e:
        print(f"Error loading dictionary: {str(e)}")
        dictionary_loaded = False

def send_verification_email(email, token):
    """
    Send email verification using Gmail SMTP
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = email
        msg['Subject'] = "Verify your crossword account"
        
        verification_url = f"{app.config['FRONTEND_URL']}/verify?token={token}"
        body = f"""
        Welcome to Crossword Helper!
        
        Please click the link below to verify your email address:
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create this account, please ignore this email.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        print(f"Verification email sent to {email}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

@app.route('/search', methods=['POST'])
@jwt_required()
def search_words():
    try:
        # loading dictionary if not already loaded
        if not dictionary_loaded:
            load_dictionary()
            if not dictionary_loaded:
                return jsonify({'error': 'Failed to load dictionary'}), 500
        
        data = request.json
        word_length = data.get('wordLength')
        known_letters = data.get('knownLetters', [])
        
        # validating input
        if not word_length or word_length <= 0:
            return jsonify({'error': 'Invalid word length'}), 400
        
        # creating a dictionary for looking up by position
        letter_dict = {item['position']: item['letter'].lower() for item in known_letters}
        
        # getting words of the specified length from cache
        candidates = word_cache.get(word_length, [])
        
        # filtering by known letters
        results = []
        for word in candidates:
            match = True
            for pos, letter in letter_dict.items():
                if pos >= len(word) or word[pos] != letter:
                    match = False
                    break
            
            if match:
                results.append(word)
        
        return jsonify({'results': results})
    
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """
    Get dictionary statistics
    """
    if not dictionary_loaded:
        load_dictionary()
    
    stats = {
        'dictionaryLoaded': dictionary_loaded,
        'totalWords': sum(len(words) for words in word_cache.values()),
        'wordsByLength': {length: len(words) for length, words in word_cache.items()}
    }
    
    return jsonify(stats)

@app.route('/register', methods=['POST'])
def register_user():
    """
    Register a new user with email and password.
    Sends verification email before user can log in.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        verification_expires = datetime.now(timezone.utc) + timedelta(hours=48)
        print(f"Generated verification token: {verification_token} with expiry: {verification_expires}")
        password_hash = generate_password_hash(password)
        cursor.execute('''INSERT INTO Users 
                         (email, password_hash, email_verified, verification_token, verification_expires) 
                         VALUES (?, ?, ?, ?, ?)''', 
                      (email, password_hash, False, verification_token, verification_expires))
        db.commit()
        
        # Send verification email
        if send_verification_email(email, verification_token):
            return jsonify({'message': 'User registered successfully. Please check your email to verify your account.'}), 201
        else:
            return jsonify({'error': 'User registered but failed to send verification email. Please contact support.'}), 202
            
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/login', methods=['POST'])    
def login_user():
    """
    Authenticate a user and return a JWT token.
    Requires email to be verified.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT password_hash, email_verified FROM Users WHERE email = ?', (email,))
    user = cursor.fetchone()
    
    if not user:
        return jsonify({'error': 'Invalid credentials.'}), 401
    
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials.'}), 401
    
    if not user['email_verified']:
        return jsonify({'error': 'Please verify your email before logging in.'}), 403
    
    # User is verified, create tokens
    access_token = create_access_token(identity=email)
    refresh_token = create_refresh_token(identity=email)

    # storing refresh token in database
    refresh_token_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + app.config['JWT_REFRESH_TOKEN_EXPIRES']
    cursor.execute('''
                   INSERT INTO RefreshTokens (id, user_email, token_hash, expires_at) 
                   VALUES (?, ?, ?, ?)''', (refresh_token_id, email, generate_password_hash(refresh_token), expires_at))
    db.commit()
    return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200
    
@app.route('/verify-email', methods=['GET'])
def verify_email():
    """
    Verify user's email address using the token from the email link.
    """
    token = request.args.get('token')
    print(f"Verification token received: {token}")
    if not token:
        return jsonify({'error': 'Verification token is required.'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # first check if user with this token exists
        cursor.execute('''SELECT email, verification_expires, email_verified 
                         FROM Users 
                         WHERE verification_token = ?''', (token,))
        user = cursor.fetchone()
        
        if not user:
            # Token not found - check if this token was recently used
            # Look for recently verified users (within last 5 minutes) 
            # This handles the React StrictMode double-request issue
            cursor.execute('''SELECT email, email_verified 
                             FROM Users 
                             WHERE email_verified = TRUE 
                             AND verification_token IS NULL
                             AND created_at > ?''', 
                          (datetime.now(timezone.utc) - timedelta(minutes=5),))
            recent_user = cursor.fetchone()
            
            if recent_user:
                print("Token already used but email recently verified.")
                return jsonify({'message': 'Email already verified. You can now log in.'}), 200
            else:
                print("No user found with this token.")
                return jsonify({'error': 'Invalid verification token.'}), 400
        
        # if already verified, return success (idempotent behavior)
        if user['email_verified']:
            print("Email already verified, returning success.")
            return jsonify({'message': 'Email already verified. You can now log in.'}), 200
        
        # checking if token has expired
        try:
            expires_at = datetime.fromisoformat(user['verification_expires'].replace('Z', '+00:00')) if isinstance(user['verification_expires'], str) else user['verification_expires']
            
            if datetime.now(timezone.utc) > expires_at:
                print("Verification token has expired.")
                return jsonify({'error': 'Verification token has expired.'}), 400
        except ValueError:
            print("Error parsing verification timestamp.")
            return jsonify({'error': 'Invalid verification timestamp.'}), 500
        
        # marking email as verified and clear verification token
        cursor.execute('''UPDATE Users 
                         SET email_verified = TRUE, verification_token = NULL, verification_expires = NULL 
                         WHERE verification_token = ? AND email_verified = FALSE''', (token,))
        db.commit()
        
        return jsonify({'message': 'Email verified successfully. You can now log in.'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    """
    Resend verification email for unverified users.
    """
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required.'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # checking if user exists and is not verified
        cursor.execute('SELECT email_verified FROM Users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found.'}), 404
        
        if user['email_verified']:
            return jsonify({'error': 'Email is already verified.'}), 400
        
        # generating new verification token
        verification_token = secrets.token_urlsafe(32)
        verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        
        cursor.execute('''UPDATE Users 
                         SET verification_token = ?, verification_expires = ? 
                         WHERE email = ?''', (verification_token, verification_expires, email))
        db.commit()
        
        # sending new verification email
        if send_verification_email(email, verification_token):
            return jsonify({'message': 'Verification email sent successfully.'}), 200
        else:
            return jsonify({'error': 'Failed to send verification email.'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token(): 
    """
    Generate a new access token using a valid refresh token.
    """
    current_user = get_jwt_identity()

    # verify refresh token exists in database
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
                    SELECT id FROM RefreshTokens
                    WHERE user_email = ? AND expires_at > ?
                    ORDER BY expires_at DESC LIMIT 1
                    ''', (current_user, datetime.now(timezone.utc)))
    if not cursor.fetchone():
        return jsonify({'error': 'Invalid refresh token'}), 401
    new_access_token = create_access_token(identity=current_user)
    return jsonify({'access_token': new_access_token}), 200
    
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout_user():
    """
    Logout and revoke tokens
    """
    current_user = get_jwt_identity()
    jti = get_jwt()['jti']

    try:
        db = get_db()
        cursor = db.cursor()
        
        # adding current token to blacklist table
        cursor.execute('INSERT INTO BlacklistedTokens (id, token) VALUES (?, ?)', (jti, jti))
        
        # removing refresh tokens from database
        cursor.execute('DELETE FROM RefreshTokens WHERE user_email = ?', (current_user,))
        db.commit()

        return jsonify({'message': 'Successfully logged out'}), 200
    except Exception as e:
        app.logger.error(f"Error during logout: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

def init_database():
    """
    Initialize the database and create tables if they do not exist.
    This endpoint is for development purposes only.
    """
    try:
        init_db()
        return jsonify({'message': 'Database initialized successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    # loading dictionary at startup
    load_dictionary()
    app.run(debug=True)