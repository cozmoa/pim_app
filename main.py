import json
import uuid
from typing import Optional
from database_pim_final import NoteDatabase

class NoteDatabaseSystem:
    """
    Business logic layer for the Personal Information Manager (PIM) system.
    
    Coordinates database operations, user authentication,
    session management, and API response formatting.
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """Initialize database connection and session store."""
        try:
            self.db = NoteDatabase(db_path)
            self.active_sessions = {}  # session_id -> username
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def register_user(self, username: str, password: str) -> str:
        """Register a new user account with input validation."""
        try:
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is required"})
            if not password or not password.strip():
                return json.dumps({"success": False, "message": "Password is required"})
            if len(password.strip()) < 3:
                return json.dumps({"success": False, "message": "Password must be at least 3 characters"})
            
            clean_username = username.strip()
            clean_password = password.strip()
            
            if self.db.create_user(clean_username, clean_password):
                return json.dumps({"success": True, "message": "User registered successfully"})
            return json.dumps({"success": False, "message": "User registration failed"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Registration failed: {str(e)}"})

    def login_user(self, username: str, password: str) -> str:
        """Authenticate user and create secure session."""
        try:
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is required"})
            if not password or not password.strip():
                return json.dumps({"success": False, "message": "Password is required"})
            
            clean_username = username.strip()
            clean_password = password.strip()
            
            if self.db.verify_user(clean_username, clean_password):
                session_id = str(uuid.uuid4())
                self.active_sessions[session_id] = clean_username
                return json.dumps({"success": True, "message": "Login successful", "session_id": session_id})
            return json.dumps({"success": False, "message": "Invalid username or password"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Login failed: {str(e)}"})

    def logout_user(self, session_id: str) -> str:
        """Logout user by invalidating session."""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                return json.dumps({"success": True, "message": "Logout successful"})
            return json.dumps({"success": False, "message": "Invalid session"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Logout failed: {str(e)}"})

    def _get_username_from_session(self, session_id: str) -> Optional[str]:
        """Internal: Retrieve username for a given session_id."""
        return self.active_sessions.get(session_id)

    def _validate_session(self, session_id: str) -> Optional[int]:
        """Internal: Validate session and return user ID from DB."""
        try:
            username = self._get_username_from_session(session_id)
            if not username:
                return None
            return self.db.get_user_id(username)
        except Exception:
            return None
