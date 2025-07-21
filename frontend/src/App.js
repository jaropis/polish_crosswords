import React, { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useSearchParams,
  useNavigate,
} from "react-router-dom";
import "./App.css";
import EmailVerification from "./EmailVerification";

const AuthForm = ({ setIsAuthenticated }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // authentication state
  const [showLogin, setShowLogin] = useState(true); // true for login, false for register
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);

  const resetForm = () => {
    setEmail("");
    setPassword("");
    setAuthError(null);
    setRegistrationSuccess(false);
  };

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
      localStorage.setItem("accessToken", data.access_token);
      localStorage.setItem("refreshToken", data.refresh_token);
      setIsAuthenticated(true);
    } catch (error) {
      setAuthError("Failed to log in: " + error.message);
      resetForm();
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);
    setRegistrationSuccess(false);

    try {
      const response = await fetch("http://localhost:5000/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Registration failed");
      }

      setRegistrationSuccess(true);
      setPassword(""); // clear password but keep email for resend functionality
      setAuthError(null);
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!email) {
      setAuthError(
        "Wprowadź adres email aby wysłać ponownie link weryfikacyjny.",
      );
      return;
    }

    setResendLoading(true);
    setAuthError(null);

    try {
      const response = await fetch(
        "http://localhost:5000/resend-verification",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to resend verification email");
      }

      setAuthError(null);
      // You might want to show a success message here
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setResendLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (showLogin) {
      await handleLogin(email, password);
    } else {
      await handleRegister(email, password);
    }
  };
  return (
    <div className="auth-container">
      <div className="auth-form">
        <h2>{showLogin ? "Zaloguj się" : "Zarejestruj się"}</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Hasło:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength="6"
            />
          </div>

          <button type="submit" disabled={authLoading}>
            {authLoading
              ? "Ładowanie..."
              : showLogin
              ? "Zaloguj"
              : "Zarejestruj"}
          </button>
        </form>

        {registrationSuccess && !showLogin && (
          <div className="registration-success">
            <p className="success">
              Rejestracja zakończona pomyślnie! Sprawdź swoją skrzynkę email i
              kliknij link weryfikacyjny.
            </p>
            <p>
              Nie otrzymałeś/aś wiadomości?{" "}
              <button
                type="button"
                onClick={handleResendVerification}
                disabled={resendLoading}
                className="link-button"
              >
                {resendLoading ? "Wysyłanie..." : "Wyślij ponownie"}
              </button>
            </p>
          </div>
        )}

        {authError && <p className="error">{authError}</p>}

        <p>
          {showLogin ? "Nie masz konta? " : "Masz już konto? "}
          <button
            type="button"
            onClick={() => {
              setShowLogin(!showLogin);
              resetForm();
            }}
            className="link-button"
          >
            {showLogin ? "Zarejestruj się" : "Zaloguj się"}
          </button>
        </p>
      </div>
    </div>
  );
};
function App() {
  const [wordLength, setWordLength] = useState("");
  const [letterInputs, setLetterInputs] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  // authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // this will be moved later

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

  const refreshToken = async () => {
    try {
      const refreshToken = localStorage.getItem("refreshToken");
      if (!refreshToken) {
        return false;
      }

      const response = await fetch("http://localhost:5000/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${refreshToken}`,
        },
      });
      if (!response.ok) {
        return false;
      }

      const data = await response.json();
      localStorage.setItem("accessToken", data.access_token);
      return true;
    } catch (error) {
      console.error("Token refresh failed:", error);
      return false;
    }
  };
  // checking authentication status
  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

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
      setError("Failed to fetch the results: " + error.message);
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
        {isAuthenticated && (
          <button onClick={handleLogout} className="logout-button">
            Wyloguj
          </button>
        )}
      </header>
      {!isAuthenticated ? (
        <AuthForm setIsAuthenticated={setIsAuthenticated} />
      ) : (
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
                      onChange={(e) =>
                        handleLetterChange(index, e.target.value)
                      }
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
      )}
    </div>
  );
}

const RouterApp = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/verify" element={<EmailVerification />} />
      </Routes>
    </Router>
  );
};

export default RouterApp;
