from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List
import json
from datetime import datetime
from database_pim_final import NoteDatabase

# Import your existing system class
from main_pim_final import NoteDatabaseSystem

app = FastAPI(title="Notes & Todos API", version="1.0.0")

# Add CORS middleware - ESSENTIAL for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],  # React/Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Initialize your existing system
notes_system = NoteDatabaseSystem()

# Helper function for session management
def get_session_id(username: str) -> Optional[str]:
    """
    Get session_id for username from active sessions.
    
    Args:
        username (str): Username to lookup session for
        
    Returns:
        Optional[str]: Session ID if found, None otherwise
    """
    for sid, uname in notes_system.active_sessions.items():
        if uname == username:
            return sid
    return None

# Standardized response helper
def create_response(success: bool, data: any = None, message: str = ""):
    """
    Create standardized API response format for consistent frontend integration.
    
    Args:
        success (bool): Whether the operation was successful
        data (any): Response data payload (optional)
        message (str): Human-readable message (optional)
        
    Returns:
        dict: Standardized response dictionary
    """
    return {
        "success": success,
        "data": data,
        "message": message
    }

# Pydantic models for request/response validation
class UserRegister(BaseModel):
    """
    User registration request model with comprehensive validation.
    
    Validates username and password requirements to ensure data quality
    and security standards before account creation.
    """
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v):
        """Validate username meets requirements."""
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        if len(v.strip()) < 3 or len(v.strip()) > 50:
            raise ValueError('Username must be 3-50 characters')
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def password_must_be_strong(cls, v):
        """Validate password meets security requirements."""
        if not v:
            raise ValueError('Password cannot be empty')
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserLogin(BaseModel):
    """
    User login request model with input validation.
    
    Ensures login credentials are properly formatted before
    attempting authentication.
    """
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v):
        """Ensure username is provided."""
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def password_not_empty(cls, v):
        """Ensure password is provided."""
        if not v:
            raise ValueError('Password cannot be empty')
        return v

# Helper function to get username from session
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extract and validate current user from session token.
    
    Used as FastAPI dependency to protect authenticated endpoints.
    
    Args:
        credentials: HTTPBearer token containing session ID
        
    Returns:
        str: Username of authenticated user
        
    Raises:
        HTTPException: If session is invalid or expired
    """
    session_id = credentials.credentials
    username = notes_system._get_username_from_session(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    return username

# Test endpoint
@app.get("/test")
async def test_endpoint():
    """
    Test endpoint to verify API is working and accessible.
    
    Returns basic system information and timestamp for debugging
    and monitoring purposes.
    """
    return create_response(
        success=True,
        data={"timestamp": datetime.now().isoformat(), "version": "1.0.0"},
        message="API is working!"
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancer integration.
    
    Provides quick status check without heavy database operations.
    """
    return create_response(
        success=True,
        data={"status": "healthy"},
        message="Notes & Todos API is running"
    )

# Authentication endpoints
@app.post("/register")
async def register_user(user: UserRegister):
    """
    Register a new user account with comprehensive validation.
    
    Creates new user account with secure password hashing and
    proper error handling for duplicate usernames.
    
    Args:
        user: UserRegister model with username and password
        
    Returns:
        Standardized response with success status and message
    """
    try:
        result = json.loads(notes_system.register_user(user.username, user.password))
        return create_response(
            success=result["success"],
            data={"username": user.username} if result["success"] else None,
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login")
async def login_user(user: UserLogin):
    """
    Authenticate user and return session token for API access.
    
    Validates credentials and creates secure session for authenticated
    API operations.
    
    Args:
        user: UserLogin model with username and password
        
    Returns:
        Session token and user info on success, error on failure
    """
    try:
        result = json.loads(notes_system.login_user(user.username, user.password))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "session_id": result["session_id"],
                    "username": user.username
                },
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=401, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/logout")
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user and invalidate session token.
    
    Properly cleans up user session to prevent unauthorized access
    after logout.
    
    Args:
        credentials: HTTPBearer token to invalidate
        
    Returns:
        Confirmation of logout operation
    """
    try:
        session_id = credentials.credentials
        result = json.loads(notes_system.logout_user(session_id))
        return create_response(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

# Root endpoint with API information
@app.get("/")
async def root():
    """
    API information and available endpoints overview.
    
    Provides comprehensive API documentation links and endpoint summary
    for developers integrating with the system.
    """
    return create_response(
        success=True,
        data={
            "version": "1.0.0",
            "endpoints": {
                "auth": ["/register", "/login", "/logout"],
                "notes": ["Coming in next update"],
                "todos": ["Coming in next update"],
                "other": ["/stats", "/health", "/test"]
            },
            "docs": "/docs"
        },
        message="Welcome to Notes & Todos API"
    )

if __name__ == "__main__":
    import uvicorn
    print("Starting Notes & Todos API Server...")
    print("Visit http://localhost:8000/docs for interactive API documentation")
    print("Visit http://localhost:8000/test to verify the API is working")
    uvicorn.run(app, host="0.0.0.0", port=8000)
