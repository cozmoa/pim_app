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
    title: str
    content: str
    
    @field_validator('title')
    @classmethod
    def title_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        if len(v.strip()) > 200:
            raise ValueError('Title must be less than 200 characters')
        return v.strip()
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()

class NoteUpdate(BaseModel):
    content: str
    title: Optional[str] = None  # Allow title change
    tags: Optional[str] = None  # Allow tags change
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def title_must_be_valid(cls, v):
        if v is not None and (not v.strip() or len(v.strip()) > 200):
            raise ValueError('Title must be 1-200 characters')
        return v.strip() if v else None

class TodoCreate(BaseModel):
    """
    Todo creation request model with comprehensive validation and optional features.
    
    Supports all todo features including priority levels, due dates, descriptions,
    tagging, and note linking for complete task management.
    """
    title: str
    description: str = ""
    due_date: Optional[str] = None
    priority: str = "normal"
    tags: Optional[List[str]] = []
    note_title: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_must_be_valid(cls, v):
        """Validate todo title requirements."""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        if len(v.strip()) > 200:
            raise ValueError('Title must be less than 200 characters')
        return v.strip()
    
    @field_validator('priority')
    @classmethod
    def priority_must_be_valid(cls, v):
        """Ensure priority is valid option."""
        if v not in {"low", "normal", "high"}:
            raise ValueError('Priority must be low, normal, or high')
        return v
    
    @field_validator('description')
    @classmethod
    def clean_description(cls, v):
        """Clean and normalize description."""
        return v.strip() if v else ""

class TagsAdd(BaseModel):
    """
    Batch tag addition request model with validation.
    
    Supports adding multiple tags to notes or todos with proper
    validation and normalization.
    """
    tags: List[str]
    
    @field_validator('tags')
    @classmethod
    def tags_must_be_valid(cls, v):
        """Validate tag list and normalize entries."""
        if not v:
            raise ValueError('Tags list cannot be empty')
        clean_tags = [tag.strip() for tag in v if tag.strip()]
        if not clean_tags:
            raise ValueError('No valid tags provided')
        return clean_tags

# Helper function to get username from session
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
    """Get all notes for the logged-in user"""
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
    """Create a new note"""
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
    """Get a specific note by title"""
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
    """Update note content and optionally title"""
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
    """Delete a note"""
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
    """Search notes by keyword"""
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

@app.post("/notes/{title}/tags")
async def add_tags_to_note(title: str, tags: TagsAdd, username: str = Depends(get_current_user)):
    """
    Add multiple tags to a note for organization and categorization.
    
    Uses normalized tag storage allowing tags to be shared across notes
    and todos for consistent organization.
    
    Args:
        title: Title of the note to tag
        tags: TagsAdd model with list of tags to add
        username: Current authenticated user (from session)
        
    Returns:
        Complete list of all tags on the note after addition
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.add_tags(session_id, title, tags.tags))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "title": title,
                    "all_tags": result["tags"]
                },
                message=f"Tags added to note '{title}'"
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add tags: {str(e)}")

@app.get("/stats")
async def get_user_stats(username: str = Depends(get_current_user)):
    """
    Get comprehensive user statistics for dashboard and analytics.
    
    Provides overview metrics including note counts, tag usage, todo statistics,
    and recent activity for user engagement insights.
    
    Args:
        username: Current authenticated user (from session)
        
    Returns:
        Complete user statistics and activity metrics
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.get_stats(session_id))
        if result["success"]:
            return create_response(
                success=True,
                data={"stats": result["stats"]},
                message="Statistics retrieved successfully"
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# Todo endpoints
@app.get("/todos")
async def get_todos(
    status: Optional[str] = None,
    tag: Optional[str] = None,
    priority: Optional[str] = None,
    username: str = Depends(get_current_user)
):
    """
    Get todos with advanced filtering for productivity workflows.
    
    Supports multiple filter criteria to help users organize and manage
    their tasks effectively. Filters can be combined for precise results.
    
    Args:
        status: Filter by "open" or "done" completion status
        tag: Filter by specific tag name
        priority: Filter by priority level (low/normal/high)
        username: Current authenticated user (from session)
        
    Returns:
        Filtered list of todos with complete metadata and tags
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.list_todos(session_id, status, tag, priority))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "todos": result["results"],
                    "count": len(result["results"]),
                    "filters": {
                        "status": status,
                        "tag": tag,
                        "priority": priority
                    }
                },
                message=f"Found {len(result['results'])} todos"
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get todos: {str(e)}")

@app.post("/todos")
async def create_new_todo(todo: TodoCreate, username: str = Depends(get_current_user)):
    """
    Create a new todo with comprehensive feature support.
    
    Supports priority levels, due dates, note linking, and tagging for
    complete task management and organization.
    
    Args:
        todo: TodoCreate model with title, optional fields, and metadata
        username: Current authenticated user (from session)
        
    Returns:
        Todo creation confirmation with assigned ID
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.create_todo(
            session_id, 
            todo.title, 
            todo.description, 
            todo.due_date, 
            todo.priority, 
            todo.tags, 
            todo.note_title
        ))
        if result["success"]:
            return create_response(
                success=True,
                data={
                    "todo_id": result.get("id"),
                    "title": todo.title
                },
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create todo: {str(e)}")

@app.patch("/todos/{todo_id}/toggle")
async def toggle_todo_completion(todo_id: int, username: str = Depends(get_current_user)):
    """
    Toggle todo completion status for task management.
    
    Switches between completed and incomplete states, enabling users
    to track task progress and maintain productivity workflows.
    
    Args:
        todo_id: ID of the todo to toggle
        username: Current authenticated user (from session)
        
    Returns:
        Status change confirmation or error if todo not found
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.toggle_todo(session_id, todo_id))
        if result["success"]:
            return create_response(
                success=True,
                data={"todo_id": todo_id},
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle todo: {str(e)}")

@app.delete("/todos/{todo_id}")
async def delete_todo_item(todo_id: int, username: str = Depends(get_current_user)):
    """
    Delete a todo item with proper authorization checking.
    
    Permanently removes todo and associated relationships while ensuring
    only the owner can delete their todos.
    
    Args:
        todo_id: ID of the todo to delete
        username: Current authenticated user (from session)
        
    Returns:
        Deletion confirmation or error if todo not found
    """
    try:
        session_id = get_session_id(username)
        if not session_id:
            raise HTTPException(status_code=401, detail="Session not found")
        
        result = json.loads(notes_system.delete_todo(session_id, todo_id))
        if result["success"]:
            return create_response(
                success=True,
                data={"deleted_todo_id": todo_id},
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete todo: {str(e)}")

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
                "todos": ["/todos", "/todos/{todo_id}"],
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
