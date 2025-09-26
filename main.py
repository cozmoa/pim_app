import json
import uuid
from typing import Optional, List, Dict, Any
from database_pim_final import NoteDatabase

class NoteDatabaseSystem:
    """
    Comprehensive business logic layer for Personal Information Manager (PIM).
    
    Provides complete note management with search, tagging, analytics, and
    secure session-based operations. Handles validation, error management,
    and user experience optimization.
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """
        Initialize the system with database connection and session storage.
        
        Args:
            db_path (str): Path to SQLite database file
            
        Raises:
            Exception: If database initialization fails
        """
        try:
            self.db = NoteDatabase(db_path)
            self.active_sessions = {}  # session_id -> username mapping
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def register_user(self, username: str, password: str) -> str:
        """Register a new user account with comprehensive validation."""
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
        """Authenticate user and create secure session."""
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
        """Logout user by invalidating session."""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                return json.dumps({"success": True, "message": "Logout successful"})
            return json.dumps({"success": False, "message": "Invalid session"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Logout failed: {str(e)}"})

    def _get_username_from_session(self, session_id: str) -> Optional[str]:
        """Get username from session ID."""
        return self.active_sessions.get(session_id)

    def _validate_session(self, session_id: str) -> Optional[int]:
        """Validate session and return user_id."""
        try:
            username = self._get_username_from_session(session_id)
            if not username:
                return None
            return self.db.get_user_id(username)
        except Exception:
            return None

    def create_note(self, session_id: str, title: str, content: str) -> str:
        """Create a new note with validation."""
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
        """Get a specific note by title."""
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
        """List all notes with content previews."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            notes = self.db.get_user_notes(user_id, limit)

            # Create preview for each note
            for note in notes:
                note["preview"] = note["content"][:100] + ("..." if len(note["content"]) > 100 else "")
                # Remove full content from list view
                del note["content"]

            return json.dumps({"success": True, "notes": notes, "count": len(notes)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to list notes: {str(e)}"})

    def edit_note(self, session_id: str, title: str, new_content: str) -> str:
        """Edit note content."""
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
        """Update note title with conflict prevention."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not old_title.strip() or not new_title.strip():
                return json.dumps({"success": False, "message": "Both titles are required"})
            
            existing_note = self.db.get_note_by_title(user_id, new_title.strip())
            if existing_note:
                return json.dumps({"success": False, "message": "Original note not found"})
    
            if self.db.update_note_title(user_id, old_title.strip(), new_title.strip()):
                return json.dumps({"success": True, "message": "Note title updated successfully"})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to update note title: {str(e)}"})       
                   
    def delete_note(self, session_id: str, title: str) -> str:
        """Delete a note."""
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

    def search_notes(self, session_id: str, query: str) -> str:
        """
        Search notes by keyword with fuzzy matching across titles and content.
        
        Performs LIKE-pattern matching against note titles and content, returning
        results with extended previews (150 characters) for better context in
        search results display.
        
        Args:
            session_id (str): Valid session ID for authorization
            query (str): Search term to match against note content
            
        Returns:
            str: JSON response with search results and count, or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not query.strip():
                return json.dumps({"success": False, "message": "Search query is required"})

            results = self.db.search_user_notes(user_id, query.strip())

            # Create extended preview for search results (more context than list view)
            for result in results:
                result["preview"] = result["content"][:150] + ("..." if len(result["content"]) > 150 else "")
                # Remove full content from search results for performance
                del result["content"]

            return json.dumps({"success": True, "results": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Search failed: {str(e)}"})

    def add_tags(self, session_id: str, title: str, tags: List[str]) -> str:
        """
        Add multiple tags to a note for organization and categorization.
        
        Validates and normalizes tag input, prevents duplicates, and uses
        normalized tag storage for efficient tagging across the system.
        
        Args:
            session_id (str): Valid session ID for authorization
            title (str): Title of the note to tag
            tags (List[str]): List of tag names to add to the note
            
        Returns:
            str: JSON response with complete tag list or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            if not tags or not any(tag.strip() for tag in tags):
                return json.dumps({"success": False, "message": "At least one valid tag is required"})

            # Clean and normalize tags
            clean_tags = [tag.strip() for tag in tags if tag.strip()]
            all_tags = self.db.add_note_tags(user_id, title.strip(), clean_tags)
            if all_tags is not None:
                return json.dumps({"success": True, "tags": all_tags})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to add tags: {str(e)}"})

    def get_stats(self, session_id: str) -> str:
        """
        Generate comprehensive user statistics for dashboard and analytics.
        
        Provides overview metrics including note counts, tag usage, recent activity,
        and other analytics useful for user engagement and system insights.
        
        Args:
            session_id (str): Valid session ID for authorization
            
        Returns:
            str: JSON response with user statistics or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            stats = self.db.get_user_stats(user_id)
            return json.dumps({"success": True, "stats": stats})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get stats: {str(e)}"})
