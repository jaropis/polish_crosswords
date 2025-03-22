import React, { useState } from "react";
import "./App.css";

function App() {
  const [wordLength, setWordLength] = useState("");
  const [letterInputs, setLetterInputs] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // handling word length input change
  const handleWordLengthChange = (e) => {
    setWordLength(e.target.value);
  };

  // generating letter input fields based on word length
  const generateInputs = () => {
    const length = parseInt(wordLength);
    if (!isNaN(length) && length > 0) {
      setLetterInputs(Array(length).fill(""));
      setSearchResults([]);
    }
  };

  // updating letter inputs when user types
  const handleLetterChange = (index, value) => {
    const newInputs = [...letterInputs];
    newInputs[index] = value.toLowerCase();
    setLetterInputs(newInputs);
  };

  // searching for matching words
  const searchWords = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const query = letterInputs
        .map((letter, index) =>
          letter ? { position: index, letter: letter } : null,
        )
        .filter((item) => item !== null);

      const response = await fetch("http://localhost:5000/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          wordLength: letterInputs.length,
          knownLetters: query,
        }),
      });

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const data = await response.json();
      setSearchResults(data.results);
    } catch (error) {
      setError("Nie udało się pobrać wyników: " + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  // resetting the form
  const resetForm = () => {
    setWordLength("");
    setLetterInputs([]);
    setSearchResults([]);
    setError(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Polskie Krzyżówki</h1>
      </header>

      <div className="search-container">
        <div className="length-input">
          <label htmlFor="wordLength">Długość słowa:</label>
          <input
            type="number"
            id="wordLength"
            value={wordLength}
            onChange={handleWordLengthChange}
            min="1"
          />
          <button onClick={generateInputs}>Generuj</button>
          <button onClick={resetForm} className="reset-button">
            Resetuj
          </button>
        </div>

        {letterInputs.length > 0 && (
          <div className="letters-container">
            <p>Wprowadź znane litery (pozostaw puste dla nieznanych):</p>
            <div className="letter-inputs">
              {letterInputs.map((letter, index) => (
                <div key={index} className="letter-position">
                  <div className="position-number">{index}</div>
                  <input
                    type="text"
                    maxLength="1"
                    value={letter}
                    onChange={(e) => handleLetterChange(index, e.target.value)}
                    className="letter-input"
                  />
                </div>
              ))}
            </div>
            <button onClick={searchWords}>Szukaj</button>
          </div>
        )}

        {isLoading && <p>Wyszukiwanie...</p>}

        {error && <p className="error">{error}</p>}

        {searchResults.length > 0 && (
          <div className="results-container">
            <h2>Znalezione słowa:</h2>
            <ul className="results-list">
              {searchResults.map((word, index) => (
                <li key={index}>{word}</li>
              ))}
            </ul>
          </div>
        )}

        {searchResults.length === 0 &&
          !isLoading &&
          letterInputs.length > 0 && (
            <p>Nie znaleziono słów pasujących do Twoich kryteriów.</p>
          )}
      </div>
    </div>
  );
}

export default App;
