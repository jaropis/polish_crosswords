from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import time
from werkzeug.security import generate_password_hash, check_password_hash
from db import init_db, get_db, close_db
import sqlite3

app = Flask(__name__)
CORS(app)  # enabling cross-origin requests for development
app.teardown_appcontext(close_db)
app.config['JWT_SECRET_KEY'] = "12345"
jwt = JWTManager(app)

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
        return jsonify({'access_token': access_token}), 200
    else:
        return jsonify({'error': 'Invalid credentials.'}), 401
if __name__ == '__main__':
    # loading dictionary at startup
    load_dictionary()
    app.run(debug=True)