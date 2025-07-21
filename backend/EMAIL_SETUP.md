# Email Setup Guide

## Gmail Configuration for Email Verification

### 1. Set up Gmail App Password

1. **Enable 2-Factor Authentication** on your Gmail account
2. Go to [Google Account Settings](https://myaccount.google.com/)
3. Navigate to **Security** → **2-Step Verification**
4. Scroll down to **App passwords**
5. Generate a new app password for "Mail"
6. Copy the 16-character password (remove spaces)

### 2. Environment Variables

Create a `.env` file in your project root with the following content:

```bash
# Copy from .env.example and fill in your actual values
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-char-app-password
FRONTEND_URL=http://localhost:3000
JWT_SECRET_KEY=your-secret-key-here-make-it-long-and-random
```

**Steps:**

1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Edit `.env` with your actual Gmail credentials
3. The `.env` file is already in `.gitignore` so it won't be committed

**Alternative:** You can still use environment variables:

```bash
export MAIL_USERNAME="your-email@gmail.com"
export MAIL_PASSWORD="your-16-char-app-password"
export FRONTEND_URL="http://localhost:3000"
export JWT_SECRET_KEY="your-secret-key-here"
```

### 3. Test Email Configuration

You can test the email functionality by:

1. Register a new user via `/register` endpoint
2. Check the terminal output for "Verification email sent to..."
3. Check your email for the verification link

### 4. API Endpoints

**Registration workflow:**

1. **POST /register**

   ```json
   {
     "email": "user@example.com",
     "password": "password123"
   }
   ```

   Response: User registered, verification email sent

2. **GET /verify-email?token=xyz**

   - User clicks link from email
   - Marks email as verified

3. **POST /login**

   ```json
   {
     "email": "user@example.com",
     "password": "password123"
   }
   ```

   Response: JWT tokens (only if email verified)

4. **POST /resend-verification** (optional)
   ```json
   {
     "email": "user@example.com"
   }
   ```
   Response: Sends new verification email

### 5. Frontend Integration

Your React frontend should:

1. Handle the `/verify?token=xyz` route
2. Call the backend `/verify-email?token=xyz` endpoint
3. Show success/error messages
4. Redirect to login page after successful verification

### 6. Error Handling

- Login attempts on unverified accounts return 403 with message "Please verify your email"
- Expired tokens return appropriate error messages
- Invalid tokens are rejected
