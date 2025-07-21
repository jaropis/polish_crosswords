import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";

const EmailVerification = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [verificationStatus, setVerificationStatus] = useState("verifying"); // "verifying", "success", "error"
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");

    if (!token) {
      setVerificationStatus("error");
      setMessage("Token weryfikacyjny nie został znaleziony.");
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(
          `http://localhost:5000/verify-email?token=${token}`,
          {
            method: "GET",
          },
        );

        const data = await response.json();

        if (response.ok) {
          setVerificationStatus("success");
          setMessage(
            "Email został pomyślnie zweryfikowany! Możesz się teraz zalogować.",
          );
        } else {
          setVerificationStatus("error");
          setMessage(data.error || "Weryfikacja nie powiodła się.");
        }
      } catch (error) {
        setVerificationStatus("error");
        setMessage("Wystąpił błąd podczas weryfikacji: " + error.message);
      }
    };

    verifyEmail();
  }, [searchParams]);

  const handleBackToLogin = () => {
    navigate("/");
  };

  return (
    <div className="verification-container">
      <div className="verification-form">
        <h2>Weryfikacja Email</h2>

        {verificationStatus === "verifying" && (
          <div className="verification-loading">
            <p>Weryfikowanie Twojego adresu email...</p>
          </div>
        )}

        {verificationStatus === "success" && (
          <div className="verification-success">
            <p className="success">{message}</p>
            <button onClick={handleBackToLogin} className="back-button">
              Przejdź do logowania
            </button>
          </div>
        )}

        {verificationStatus === "error" && (
          <div className="verification-error">
            <p className="error">{message}</p>
            <button onClick={handleBackToLogin} className="back-button">
              Powrót do strony głównej
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailVerification;
