# 🔐 Authentication Service - Complete Learning Guide

## 📖 What Is This Service?

Think of this service as the **security guard** of our medical platform. Just like a hospital checks your ID before letting you in, this service:

- **Checks who you are** (authentication)
- **Decides what you can do** (authorization) 
- **Keeps you logged in safely** (session management)
- **Protects against hackers** (security features)

### Real-World Example
Imagine you're a doctor trying to access patient records:
1. You enter your email and password → **Authentication**
2. System checks: "Are you really Dr. Smith?" → **Verification**
3. System says: "Yes, and Dr. Smith can access patient records" → **Authorization**
4. You get a special "badge" (token) to use the system → **Session**

## 🎯 What Problems Does This Solve?

### Before This Service (Problems):
- ❌ Anyone could access medical records
- ❌ Passwords stored in plain text (hackable)
- ❌ No way to control who sees what
- ❌ Users had to login every time
- ❌ No protection against password attacks

### After This Service (Solutions):
- ✅ Only verified users can access the system
- ✅ Passwords are encrypted and secure
- ✅ Different users have different permissions
- ✅ Users stay logged in safely
- ✅ Automatic protection against attacks

## 🏗️ How It Works (Simple Architecture)

```
👤 User → 🔐 Auth Service → 🏥 Medical Platform
```

### Step-by-Step Process:
1. **User Registration**: "I want to join as Dr. Smith"
2. **Password Security**: We encrypt your password (like putting it in a safe)
3. **Login**: "I'm Dr. Smith, here's my password"
4. **Token Creation**: "Here's your special badge (JWT token)"
5. **Access Control**: "Your badge says you can access patient records"

### The Technology Stack (What We Built With):
- **FastAPI**: The web framework (like the foundation of a house)
- **PostgreSQL**: Database to store user info (like a filing cabinet)
- **Redis**: Fast memory storage (like a notepad for quick access)
- **JWT Tokens**: Digital badges for users (like hospital ID cards)
- **bcrypt**: Password encryption (like a super-strong safe)

## 👥 User Roles Explained

Think of roles like job titles in a hospital:

| Role | Real-World Example | What They Can Do |
|------|-------------------|------------------|
| **Admin** | Hospital IT Manager | Everything - manage all users and system |
| **Doctor** | Medical Doctor | Access patient records, upload medical documents |
| **Researcher** | Medical Researcher | Access research papers, limited document upload |
| **Student** | Medical Student | Read educational materials only |
| **User** | General Public | Basic access to public health information |

### Example Scenario:
- Dr. Smith (Doctor) can upload and view patient X-rays
- Student John (Student) can only read textbooks, not patient data
- Admin Sarah (Admin) can add new doctors to the system

## 🚀 Getting Started (Step by Step)

### What You Need First:
1. **Docker** - Think of it as a container that holds our service
2. **Database** - PostgreSQL to store user information
3. **Redis** - For fast access to login sessions
4. **Basic Terminal Knowledge** - To run commands

### Quick Start (5 Minutes):

#### Step 1: Get the Code Running
```bash
# Go to the backend folder
cd backend

# Start the service (this downloads and starts everything)
docker-compose -f docker-compose.dev.yml up -d auth-service

# Wait 30 seconds for everything to start
sleep 30

# Check if it's working
curl http://localhost:8010/health
```

#### Step 2: Create Your First User
```bash
# Register a new doctor
curl -X POST http://localhost:8010/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@hospital.com",
    "username": "dr_smith",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Smith",
    "role": "doctor"
  }'
```

#### Step 3: Login and Get Your Token
```bash
# Login to get your access token
curl -X POST http://localhost:8010/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@hospital.com",
    "password": "SecurePass123!"
  }'
```

You'll get back something like:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "email": "doctor@hospital.com",
    "role": "doctor"
  }
}
```

🎉 **Congratulations!** You now have a working authentication system!

## 📚 API Guide (Learn by Examples)

### Understanding the API
An API is like a menu at a restaurant - it tells you what you can order (what requests you can make).

### 1. User Registration (Creating New Accounts)

**What it does**: Creates a new user account
**When to use**: When someone new wants to join the platform

```bash
POST /api/v1/auth/register
```

**Example Request**:
```json
{
  "email": "nurse@hospital.com",
  "username": "nurse_jane",
  "password": "StrongPass456!",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "user"
}
```

**What happens**:
1. System checks if email is already used
2. Password gets encrypted (never stored in plain text)
3. New user account is created
4. User information is saved to database

### 2. User Login (Getting Access)

**What it does**: Verifies user identity and gives access token
**When to use**: Every time someone wants to use the platform

```bash
POST /api/v1/auth/login
```

**Example Request**:
```json
{
  "email": "nurse@hospital.com",
  "password": "StrongPass456!"
}
```

**What happens**:
1. System finds user by email
2. Checks if password matches (compares encrypted versions)
3. Creates a JWT token (like a temporary ID badge)
4. Returns token for future requests

### 3. Using Your Token (Accessing Protected Features)

**What it does**: Proves you're logged in for protected actions
**When to use**: For any action that requires authentication

```bash
GET /api/v1/users/me
Authorization: Bearer YOUR_TOKEN_HERE
```

**What happens**:
1. System reads your token
2. Verifies it's valid and not expired
3. Identifies who you are
4. Returns your user information

### 4. Refreshing Your Session (Staying Logged In)

**What it does**: Gets a new access token without re-entering password
**When to use**: When your current token is about to expire

```bash
POST /api/v1/auth/refresh
```

**Example Request**:
```json
{
  "refresh_token": "your_refresh_token_here"
}
```

## 🔒 Security Features Explained

### 1. Password Security
**Problem**: Hackers can steal password databases
**Solution**: We use bcrypt encryption

```python
# What happens to your password:
"MyPassword123!" → bcrypt → "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBcQsu.Wrrvg4."
```
Even if hackers steal our database, they can't see real passwords!

### 2. JWT Tokens (Digital ID Badges)
**Problem**: How to prove you're logged in without sending password every time
**Solution**: JWT tokens work like temporary ID badges

**Token Structure**:
```json
{
  "user_id": "123",
  "email": "doctor@hospital.com", 
  "role": "doctor",
  "expires": "2024-01-01T12:00:00Z"
}
```

### 3. Rate Limiting (Preventing Attacks)
**Problem**: Hackers try thousands of passwords per second
**Solution**: We limit login attempts

- Maximum 60 requests per minute per IP address
- After 5 failed login attempts, account locks for 15 minutes
- Automatic detection of suspicious activity

### 4. Session Management
**Problem**: How to handle user sessions securely
**Solution**: Two-token system

- **Access Token**: Short-lived (30 minutes) for API requests
- **Refresh Token**: Long-lived (7 days) to get new access tokens
- When access token expires, use refresh token to get a new one

## 🔄 How Services Talk to Each Other

Our authentication service doesn't work alone - it talks to other services:

```
Document Service: "Is this user allowed to upload files?"
Auth Service: "Let me check their token... Yes, they're a doctor!"

Search Service: "Can this user search medical records?"  
Auth Service: "Checking... Yes, but only public records for their role."
```

### Event Publishing (Telling Others What Happened)
When important things happen, we tell other services:

```json
{
  "event_type": "user.registered",
  "user_id": "123",
  "email": "doctor@hospital.com",
  "role": "doctor",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

Other services can listen and react:
- Email service sends welcome email
- Analytics service tracks new registrations
- Audit service logs the event

## 🧪 Testing Your Understanding

### Exercise 1: Create Different User Types
Try creating users with different roles and see how they work:

```bash
# Create an admin
curl -X POST http://localhost:8010/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@hospital.com",
    "username": "admin",
    "password": "AdminPass123!",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin"
  }'

# Create a student  
curl -X POST http://localhost:8010/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@university.com",
    "username": "med_student",
    "password": "StudentPass123!",
    "first_name": "Medical",
    "last_name": "Student", 
    "role": "student"
  }'
```

### Exercise 2: Test Token Expiration
1. Login and get a token
2. Wait 31 minutes (or change the expiration time in settings)
3. Try to use the expired token
4. Use refresh token to get a new access token

### Exercise 3: Test Security Features
1. Try logging in with wrong password 6 times
2. See how the account gets locked
3. Wait 15 minutes and try again

## 🐛 Troubleshooting (When Things Go Wrong)

### Problem: "Service not responding"
**Symptoms**: Can't reach http://localhost:8010
**Solutions**:
```bash
# Check if service is running
docker-compose ps

# Check service logs
docker-compose logs auth-service

# Restart the service
docker-compose restart auth-service
```

### Problem: "Database connection failed"
**Symptoms**: Service starts but can't save users
**Solutions**:
```bash
# Check if database is running
docker-compose logs postgres

# Check database connection
docker-compose exec postgres psql -U postgres -c "SELECT 1;"

# Reset database
docker-compose down
docker-compose up -d postgres
# Wait 30 seconds then start auth service
```

### Problem: "Invalid JWT token"
**Symptoms**: "Token is invalid" errors
**Solutions**:
1. Check if token is expired (they last 30 minutes)
2. Make sure you're using the token correctly:
   ```bash
   # Correct way:
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8010/api/v1/users/me
   
   # Wrong way:
   curl -H "Authorization: YOUR_TOKEN" http://localhost:8010/api/v1/users/me
   ```
3. Get a new token by logging in again

### Problem: "Password too weak"
**Symptoms**: Registration fails with password error
**Requirements**:
- At least 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)  
- At least one number (0-9)
- At least one special character (!@#$%^&*)

**Good password**: `SecurePass123!`
**Bad password**: `password` (too simple)

## 📈 Performance and Scaling

### How Fast Is It?
- **User Registration**: ~100ms
- **Login**: ~50ms  
- **Token Validation**: ~10ms
- **Can handle**: 1000+ requests per second

### Making It Faster
1. **Redis Caching**: Stores frequently accessed data in memory
2. **Database Indexing**: Makes user lookups super fast
3. **Connection Pooling**: Reuses database connections efficiently

### Scaling for More Users
```
1 User    → 1 Service Instance
1,000 Users → 1 Service Instance  
10,000 Users → 2-3 Service Instances
100,000 Users → 5-10 Service Instances + Load Balancer
```

## 🔧 Configuration Options

### Environment Variables Explained
These settings control how the service behaves:

```bash
# How long tokens last
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Access tokens expire in 30 minutes
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7     # Refresh tokens expire in 7 days

# Password requirements  
PASSWORD_MIN_LENGTH=8               # Passwords must be at least 8 characters
PASSWORD_REQUIRE_UPPERCASE=true     # Must have uppercase letters
PASSWORD_REQUIRE_NUMBERS=true       # Must have numbers

# Security settings
MAX_LOGIN_ATTEMPTS=5                # Lock account after 5 failed attempts
ACCOUNT_LOCKOUT_DURATION_MINUTES=15 # Keep locked for 15 minutes
RATE_LIMIT_REQUESTS_PER_MINUTE=60   # Max 60 requests per minute per IP
```

### Customizing for Your Needs
```bash
# For development (less secure, more convenient)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8 hours
PASSWORD_MIN_LENGTH=4                # Shorter passwords
MAX_LOGIN_ATTEMPTS=10                # More attempts allowed

# For production (more secure)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15   # 15 minutes
PASSWORD_MIN_LENGTH=12               # Longer passwords  
MAX_LOGIN_ATTEMPTS=3                 # Fewer attempts allowed
```

## 🎓 Learning More

### Next Steps
1. **Try the Document Service**: Learn how authenticated users upload files
2. **Explore Search Service**: See how roles affect search results
3. **Study the Database**: Look at how user data is stored
4. **Read About JWT**: Understand how tokens work in detail

### Useful Resources
- [JWT.io](https://jwt.io/) - Decode and understand JWT tokens
- [FastAPI Docs](https://fastapi.tiangolo.com/) - Learn about our web framework
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/) - Database concepts
- [Redis Guide](https://redis.io/documentation) - Caching and sessions

### Common Questions

**Q: Why do tokens expire?**
A: Security! If someone steals your token, it only works for 30 minutes instead of forever.

**Q: What happens if I forget my password?**
A: We'll add password reset functionality that sends a secure link to your email.

**Q: Can I have multiple sessions?**
A: Yes! You can be logged in on your phone and computer at the same time.

**Q: How secure is this really?**
A: Very secure! We use industry-standard encryption and follow security best practices.

---

## 🎉 Congratulations!

You now understand how authentication works in our medical AI platform! You've learned:

- ✅ What authentication and authorization mean
- ✅ How to register users and login
- ✅ How JWT tokens work
- ✅ Security features that protect users
- ✅ How to test and troubleshoot the service
- ✅ How different user roles work

**Next Challenge**: Try integrating this service with the Document Management service to see how authenticated users can upload medical documents!

---

**📞 Need Help?**  
- Check the troubleshooting section above
- Look at the service logs: `docker-compose logs auth-service`
- Ask questions in our team chat

**Last Updated**: August 2025