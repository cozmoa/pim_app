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

# Add CORS middleware - ESSENTIAL for frontend
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
    """Get session_id for username"""
    for sid, uname in notes_system.active_sessions.items():
        if uname == username:
            return sid
    return None

# Standardized response helper
def create_response(success: bool, data: any = None, message: str = ""):
    """Create standardized API response"""
    return {
        "success": success,
        "data": data,
        "message": message
    }

# Pydantic models for request/response with validation (V2 style)
class UserRegister(BaseModel):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        if len(v.strip()) < 3 or len(v.strip()) > 50:
            raise ValueError('Username must be 3-50 characters')
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def password_must_be_strong(cls, v):
        if not v:
            raise ValueError('Password cannot be empty')
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserLogin(BaseModel):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def password_not_empty(cls, v):
        if not v:
            raise ValueError('Password cannot be empty')
        return v

class NoteCreate(BaseModel):
    """
    Note creation request model with comprehensive validation.
    
    Validates note title and content requirements to ensure data quality
    and proper note structure for the system.
    """
    title: str
    content: str
    
    @field_validator('title')
    @classmethod
    def title_must_be_valid(cls, v):
        """Validate note title meets requirements."""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        if len(v.strip()) > 200:
            raise ValueError('Title must be less than 200 characters')
        return v.strip()
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v):
        """Ensure note content is provided."""
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()

class NoteUpdate(BaseModel):
    """
    Note update request model supporting content and optional title changes.
    
    Allows updating note content and optionally changing the title while
    maintaining validation requirements.
    """
    content: str
    title: Optional[str] = None  # Allow title change
    tags: Optional[str] = None  # Allow tags change
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v):
        """Ensure updated content is valid."""
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def title_must_be_valid(cls, v):
        """Validate new title if provided."""
        if v is not None and (not v.strip() or len(v.strip()) > 200):
            raise ValueError('Title must be 1-200 characters')
        return v.strip() if v else None

# Helper function to get username from session
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate current user from session token."""
    session_id = credentials.credentials
    username = notes_system._get_username_from_session(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    return username

# Test endpoint
@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return create_response(
        success=True,
        data={"timestamp": datetime.now().isoformat(), "version": "1.0.0"},
        message="API is working!"
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return create_response(
        success=True,
        data={"status": "healthy"},
        message="Notes & Todos API is running"
    )

# Authentication endpoints
@app.post("/register")
async def register_user(user: UserRegister):
    """Register a new user"""
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
    """Login user and get session token"""
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
    """Logout user"""
    try:
        session_id = credentials.credentials
        result = json.loads(notes_system.logout_user(session_id))
        return create_response(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

# Notes endpoints
@app.get("/notes")
async def list_notes(limit: int = 50, username: str = Depends(get_current_user)):
    """
    Get all notes for the logged-in user with pagination support.
    
    Returns note list with content previews for efficient browsing.
    Full content is excluded from list view to optimize performance.
    
    Args:
        limit: Maximum number of notes to return (default 50)
        username: Current authenticated user (from session)
        
    Returns:
        List of notes with metadata and content previews
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.list_notes(session_id, limit))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "notes": result["notes"],
                    "count": result["count"]
                },
                message=f"Found {result['count']} notes"
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list notes: {str(e)}")

@app.post("/notes")
async def create_note(note: NoteCreate, username: str = Depends(get_current_user)):
    """
    Create a new note with title uniqueness validation.
    
    Creates new note ensuring title is unique within user's collection.
    Validates input using Pydantic models before processing.
    
    Args:
        note: NoteCreate model with title and content
        username: Current authenticated user (from session)
        
    Returns:
        Note creation confirmation with assigned note ID
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.create_note(session_id, note.title, note.content))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "note_id": result.get("note_id"),
                    "title": note.title
                },
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")

@app.get("/notes/{title}")
async def get_note(title: str, username: str = Depends(get_current_user)):
    """
    Get a specific note by title with complete content and metadata.
    
    Retrieves full note data including content, tags, and timestamps.
    Used for note viewing and editing operations.
    
    Args:
        title: Title of the note to retrieve
        username: Current authenticated user (from session)
        
    Returns:
        Complete note data or 404 if not found
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.get_note(session_id, title))
        if result["success"]:
            return create_response(
                success=True,
                data={"note": result["note"]},
                message="Note retrieved successfully"
            )
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get note: {str(e)}")

@app.put("/notes/{title}")
async def update_note(title: str, note_update: NoteUpdate, username: str = Depends(get_current_user)):
    """
    Update note content and optionally title with conflict prevention.
    
    Supports updating note content and changing title while preventing
    duplicate titles within user's collection.
    
    Args:
        title: Current title of the note to update
        note_update: NoteUpdate model with new content and optional title
        username: Current authenticated user (from session)
        
    Returns:
        Update confirmation with new title information
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        # If title is being changed, check for conflicts
        new_title = note_update.title if note_update.title else title
        if new_title != title:
            # Check if new title already exists
            existing = json.loads(notes_system.get_note(session_id, new_title))
            if existing["success"]:
                raise HTTPException(status_code=400, detail="Note with that title already exists")
        
        # Update content
        content_result = json.loads(notes_system.edit_note(session_id, title, note_update.content))
        if not content_result["success"]:
            raise HTTPException(status_code=400, detail=content_result["message"])
        
        # Update title if changed
        if new_title != title:
            title_result = json.loads(notes_system.update_note_title(session_id, title, new_title))
            if not title_result["success"]:
                raise HTTPException(status_code=400, detail=title_result["message"])
        
        return create_response(
            success=True,
            data={"title": new_title, "old_title": title},
            message="Note updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update note: {str(e)}")
    
@app.delete("/notes/{title}")
async def delete_note(title: str, username: str = Depends(get_current_user)):
    """
    Delete a note permanently with authorization checking.
    
    Removes note and all associated data (tags, folder links) through
    database cascade operations.
    
    Args:
        title: Title of the note to delete
        username: Current authenticated user (from session)
        
    Returns:
        Deletion confirmation or error if note not found
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.delete_note(session_id, title))
        if result["success"]:
            return create_response(
                success=True,
                data={"deleted_title": title},
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {str(e)}")

@app.get("/notes/search/{query}")
async def search_notes(query: str, username: str = Depends(get_current_user)):
    """
    Search notes by keyword with fuzzy matching.
    
    Performs LIKE-pattern matching across note titles and content,
    returning results with extended previews for context.
    
    Args:
        query: Search term to match against notes
        username: Current authenticated user (from session)
        
    Returns:
        List of matching notes with search previews
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.search_notes(session_id, query))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "results": result["results"],
                    "count": result["count"],
                    "query": query
                },
                message=f"Found {result['count']} results for '{query}'"
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Root endpoint with API info
@app.get("/")
async def root():
    """API information"""
    return create_response(
        success=True,
        data={
            "version": "1.0.0",
            "endpoints": {
                "auth": ["/register", "/login", "/logout"],
                "notes": ["/notes", "/notes/{title}", "/notes/search/{query}"],
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
