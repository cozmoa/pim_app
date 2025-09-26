import json
import uuid
from typing import Optional, List, Dict, Any
from database.py import NoteDatabase

class NoteDatabaseSystem:
    """
    Business logic layer for the Personal Information Manager (PIM) system.
    
    Provides secure, session-based access to note management functionality
    with comprehensive validation, error handling, and user-friendly responses.
    Coordinates between database operations and API endpoints.
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """
        Initialize the system with database connection and session storage.
        
        Args:
            db_path (str): Path to SQLite database file. Defaults to "notes.db"
            
        Raises:
            Exception: If database initialization fails
        """
        try:
            self.db = NoteDatabase(db_path)
            self.active_sessions = {}  # session_id -> username mapping
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def register_user(self, username: str, password: str) -> str:
        """
        Register a new user account with comprehensive input validation.
        
        Args:
            username (str): Desired username for the account
            password (str): Plain text password (will be hashed securely)
            
        Returns:
            str: JSON response with success status and descriptive message
        """
        try:
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is required and cannot be empty"})
            
            if not password:
                return json.dumps({"success": False, "message": "Password is required and cannot be empty"})
            if not password.strip():
                return json.dumps({"success": False, "message": "Password cannot be only whitespace"})
            
            if len(password.strip()) < 3:
                return json.dumps({"success": False, "message": "Password must be at least 3 characters long"})
            
            clean_username = username.strip()
            clean_password = password.strip()
            if self.db.create_user(clean_username, clean_password):
                return json.dumps({"success": True, "message": "User registered successfully"})
            else:
                return json.dumps({"success": False, "message": "User registration failed"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Registration failed: {str(e)}"})

    def login_user(self, username: str, password: str) -> str:
        """
        Authenticate user and create secure session with UUID-based session ID.
        
        Args:
            username (str): Username to authenticate
            password (str): Plain text password to verify
            
        Returns:
            str: JSON response with session_id on success, error message on failure
        """
        try:
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is required and cannot be empty"})
            
            if not password:
                return json.dumps({"success": False, "message": "Password is required and cannot be empty"})

            if not password.strip():
                return json.dumps({"success": False, "message": "Password cannot be only whitespace"})
            
            clean_username = username.strip()
            clean_password = password.strip()
            
            if self.db.verify_user(clean_username, clean_password):
                session_id = str(uuid.uuid4())
                self.active_sessions[session_id] = clean_username
                return json.dumps({
                    "success": True,
                    "message": "Login successful",
                    "session_id": session_id
                })
            else:
                return json.dumps({"success": False, "message": "Invalid username or password"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Login failed: {str(e)}"})

    def logout_user(self, session_id: str) -> str:
        """
        Logout user by invalidating their session.
        
        Args:
            session_id (str): Session ID to invalidate
            
        Returns:
            str: JSON response confirming logout status
        """
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                return json.dumps({"success": True, "message": "Logout successful"})
            return json.dumps({"success": False, "message": "Invalid session"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Logout failed: {str(e)}"})

    def _get_username_from_session(self, session_id: str) -> Optional[str]:
        """
        Retrieve username associated with a session ID for internal operations.
        
        Args:
            session_id (str): Session ID to lookup
            
        Returns:
            Optional[str]: Username if session valid, None if invalid
        """
        return self.active_sessions.get(session_id)

    def _validate_session(self, session_id: str) -> Optional[int]:
        """
        Validate session and return user ID for database operations.
        
        Args:
            session_id (str): Session ID to validate
            
        Returns:
            Optional[int]: User ID if session valid, None if invalid
        """
        try:
            username = self._get_username_from_session(session_id)
            if not username:
                return None
            return self.db.get_user_id(username)
        except Exception:
            return None

    def create_note(self, session_id: str, title: str, content: str) -> str:
        """
        Create a new note with session validation and duplicate prevention.
        
        Validates user session, checks for duplicate titles, and creates note
        with proper error handling and user feedback.
        
        Args:
            session_id (str): Valid session ID for authorization
            title (str): Unique title for the note (per user)
            content (str): Note content/body text
            
        Returns:
            str: JSON response with note_id on success, error message on failure
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip() or not content.strip():
                return json.dumps({"success": False, "message": "Title and content are required"})

            note_id = self.db.create_note(user_id, title.strip(), content.strip())
            if note_id:
                return json.dumps({
                    "success": True,
                    "message": "Note created successfully",
                    "note_id": note_id
                })
            else:
                return json.dumps({"success": False, "message": "Note title already exists"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create note: {str(e)}"})

    def get_note(self, session_id: str, title: str) -> str:
        """
        Retrieve a specific note by title with complete metadata.
        
        Args:
            session_id (str): Valid session ID for authorization
            title (str): Title of the note to retrieve
            
        Returns:
            str: JSON response with note data on success, error message on failure
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            note = self.db.get_note_by_title(user_id, title.strip())
            if note:
                return json.dumps({"success": True, "note": note})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get note: {str(e)}"})

    def list_notes(self, session_id: str, limit: int = 50) -> str:
        """
        List all notes for the user with content previews for performance.
        
        Generates content previews (100 characters + "...") to prevent sending
        large amounts of data for list views while providing enough context.
        
        Args:
            session_id (str): Valid session ID for authorization
            limit (int): Maximum number of notes to return. Defaults to 50
            
        Returns:
            str: JSON response with notes list and count, or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            notes = self.db.get_user_notes(user_id, limit)

            # Create content previews for efficient list display
            for note in notes:
                note["preview"] = note["content"][:100] + ("..." if len(note["content"]) > 100 else "")
                # Remove full content from list view to improve performance
                del note["content"]

            return json.dumps({"success": True, "notes": notes, "count": len(notes)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to list notes: {str(e)}"})

    def edit_note(self, session_id: str, title: str, new_content: str) -> str:
        """
        Edit note content with automatic timestamp updates.
        
        Updates note content and refreshes modification timestamp for tracking
        recent changes and activity.
        
        Args:
            session_id (str): Valid session ID for authorization
            title (str): Title of the note to edit
            new_content (str): New content to replace existing content
            
        Returns:
            str: JSON response confirming update success or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip() or not new_content.strip():
                return json.dumps({"success": False, "message": "Title and content are required"})

            if self.db.update_note_content(user_id, title.strip(), new_content.strip()):
                return json.dumps({"success": True, "message": "Note updated successfully"})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to edit note: {str(e)}"})
        
    def update_note_title(self, session_id: str, old_title: str, new_title: str) -> str:
        """
        Update note title with duplicate prevention and validation.
        
        Checks for title conflicts before updating to prevent duplicate titles
        within a user's note collection.
        
        Args:
            session_id (str): Valid session ID for authorization
            old_title (str): Current title of the note
            new_title (str): New title to set (must be unique for this user)
            
        Returns:
            str: JSON response confirming title update or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not old_title.strip() or not new_title.strip():
                return json.dumps({"success": False, "message": "Both titles are required"})
            
            # Check if new title would create a conflict
            existing_note = self.db.get_note_by_title(user_id, new_title.strip())
            if existing_note:
                return json.dumps({"success": False, "message": "A note with that title already exists"})
    
            if self.db.update_note_title(user_id, old_title.strip(), new_title.strip()):
                return json.dumps({"success": True, "message": "Note title updated successfully"})
            else:
                return json.dumps({"success": False, "message": "Original note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to update note title: {str(e)}"})       
                   
    def delete_note(self, session_id: str, title: str) -> str:
        """
        Delete a note with proper authorization and confirmation.
        
        Permanently removes note and all associated data including tags
        and folder relationships through cascade operations.
        
        Args:
            session_id (str): Valid session ID for authorization
            title (str): Title of the note to delete
            
        Returns:
            str: JSON response confirming deletion or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            if self.db.delete_note(user_id, title.strip()):
                return json.dumps({"success": True, "message": "Note deleted successfully"})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to delete note: {str(e)}"})
