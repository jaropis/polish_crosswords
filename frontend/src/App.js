import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [wordLength, setWordLength] = useState("");
  const [letterInputs, setLetterInputs] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showLogin, setShowLogin] = useState(true); // true for login, false for register
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState(null);

  // checking authentication status
  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);
  // AUTHENTICATION LOGIC

  const handleLogin = async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);

    try {
      const response = await fetch("http://localhost:5000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Login failed");
      }

      const data = await response.json();

      // storing tokens in local storage
      localStorage.setItem("accessToken", data.accessToken);
      localStorage.setItem("refreshToken", data.refreshToken);
      setIsAuthenticated(true);
    } catch (error) {
      setAuthError("Nie udało się zalogować: " + error.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);

    try {
      const response = await fetch("http://localhost:5000/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Registration failed");
      }

      setShowLogin(true);
      setAuthError(null);
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("accessToken");
      if (token) {
        await fetch("http://localhost:5000/logout", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
      }
    } catch (error) {
      console.log("Logout error:", error);
    } finally {
      // clearing tokens regardless of API call success
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      setIsAuthenticated(false);
      resetForm();
    }
  };
  // BUSINESS LOGIC
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
      const token = localStorage.getItem("accessToken");
      if (!token) {
        throw new Error("No authentication token found");
      }
      const query = letterInputs
        .map((letter, index) =>
          letter ? { position: index, letter: letter } : null,
        )
        .filter((item) => item !== null);

      const response = await fetch("http://localhost:5000/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          wordLength: letterInputs.length,
          knownLetters: query,
        }),
      });

      if (!response.ok) {
        // handling token expiration
        if (response.status === 401) {
          // token might be expired, trying to refresh
          const refreshSuccess = await refreshToken();
          if (refreshSuccess) {
            return searchWords();
          } else {
            // refresh failed, user needs to login again
            setIsAuthenticated(false);
            throw new Error("Session expired. Please login again.");
          }
        }
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
                  <div className="position-number">{index + 1}</div>
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
