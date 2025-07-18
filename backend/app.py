from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
import time
from werkzeug.security import generate_password_hash, check_password_hash
from db import init_db, get_db, close_db
import sqlite3
import uuid
from datetime import datetime, timedelta
app = Flask(__name__)
CORS(app)  # enabling cross-origin requests for development
app.teardown_appcontext(close_db)
app.config['JWT_SECRET_KEY'] = "12345"
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)

# store for backend tokens (in production use Redis or database)
blacklisted_tokens = set()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """
    Check if the token is in the blacklist
    """
    return jwt_payload['jti'] in blacklisted_tokens

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

@app.route('/init_db', methods=['GET'])
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

@app.route('/register', methods=['POST'])
def register_user():
    """
    Register a new user with email and password.
    Passwords are stored as hashes for security.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO Users (email, password_hash) VALUES (?, ?)', (email, password_hash))
        db.commit()
        return jsonify({'message': 'User registered successfully.'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/login', methods=['POST'])    
def login_user():
    """
    Authenticate a user and return a JWT token.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT password_hash FROM Users WHERE email = ?', (email,))
    user = cursor.fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        access_token = create_access_token(identity=email)
        refresh_token = create_refresh_token(identity=email)

        # storing refresh token in database
        refresh_token_id= str(uuid.uuid4())
        expires_at = datetime.now(datetime.timezone.utc) + app.config['JWT_REFRESH_TOKEN_EXPIRES']
        cursor.execute('''
                       INSERT INTO RefreshTokens (id, user_email, token_hash, expires_at) 
                       VALUES (?, ?, ?, ?)''', (refresh_token_id, email, generate_password_hash(refresh_token), expires_at))
        db.commit()
        return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200
    else:
        return jsonify({'error': 'Invalid credentials.'}), 401
    
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
                    ''', (current_user, datetime.now(datetime.timezone.utc)))
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

    # adding current token to blacklist
    blacklisted_tokens.add(jti)

    # removing refresh tokens from database
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM RefreshTokens WHERE user_email = ?', (current_user,))
    db.commit()

    return jsonify({'message': 'Succesfully logged out'}), 200
if __name__ == '__main__':
    # loading dictionary at startup
    load_dictionary()
    app.run(debug=True)