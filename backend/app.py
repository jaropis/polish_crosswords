from flask import Flask, request, jsonify
from flask_cors import CORS
from db import init_db, get_db, close_db

app = Flask(__name__)
CORS(app)  # enabling cross-origin requests for development
app.teardown_appcontext(close_db)

@app.route('/search', methods=['POST'])
def search_words():
    try:
        data = request.json
        word_length = data.get('wordLength')
        known_letters = data.get('knownLetters', [])
        
        # validating input
        if not word_length or word_length <= 0:
            return jsonify({'error': 'Invalid word length'}), 400
        
        # creating a dictionary for looking up by position
        letter_dict = {item['position']: item['letter'] for item in known_letters}
        
        # opening the dictionary file with the correct encoding
        results = []
        with open("pl_PL.dic", encoding="iso-8859-2") as file:
            for line in file:
                # parsing the dictionary entry
                slash_pos = line.find('/')
                if slash_pos != -1:
                    word = line[:slash_pos]
                else:
                    word = line.strip()
                
                # checking if the word matches our criteria
                if len(word) == word_length:
                    match = True
                    for pos, letter in letter_dict.items():
                        if pos >= len(word) or word[pos].lower() != letter.lower():
                            match = False
                            break
                    
                    if match:
                        results.append(word)
        
        return jsonify({'results': results})
    
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)