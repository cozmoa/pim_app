import json
import uuid
from typing import Optional, List, Dict, Any
from database import NoteDatabase

class NoteDatabaseSystem:
    """
    Complete business logic layer for Personal Information Manager (PIM).
    
    Provides comprehensive note management, todo system, search functionality,
    tagging, analytics, and secure session-based operations with full validation
    and error handling.
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """Initialize the system with database and session management."""
        try:
            self.db = NoteDatabase(db_path)
            self.active_sessions = {}  # session_id -> username mapping
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def register_user(self, username: str, password: str) -> str:
        """Register a new user account."""
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
        """Authenticate user and create session."""
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
        """Logout user."""
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
        """Create a new note."""
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
        """List all notes for the user."""
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
        """Update note title."""
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
        """Search notes by keyword."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not query.strip():
                return json.dumps({"success": False, "message": "Search query is required"})

            results = self.db.search_user_notes(user_id, query.strip())

            # Create preview for each result
            for result in results:
                result["preview"] = result["content"][:150] + ("..." if len(result["content"]) > 150 else "")
                # Remove full content from search results
                del result["content"]

            return json.dumps({"success": True, "results": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Search failed: {str(e)}"})

    def add_tags(self, session_id: str, title: str, tags: List[str]) -> str:
        """Add tags to a note."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            if not tags or not any(tag.strip() for tag in tags):
                return json.dumps({"success": False, "message": "At least one valid tag is required"})

            clean_tags = [tag.strip() for tag in tags if tag.strip()]
            all_tags = self.db.add_note_tags(user_id, title.strip(), clean_tags)
            if all_tags is not None:
                return json.dumps({"success": True, "tags": all_tags})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to add tags: {str(e)}"})

    def get_stats(self, session_id: str) -> str:
        """Get user statistics."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            stats = self.db.get_user_stats(user_id)
            return json.dumps({"success": True, "stats": stats})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get stats: {str(e)}"})

    # Todo methods using database
    def create_todo(self, session_id: str, title: str, description: str = "", 
                   due_date: str = None, priority: str = "normal", 
                   tags: List[str] = None, note_title: str = None) -> str:
        """
        Create a new todo item with comprehensive feature support.
        
        Supports priority levels for task organization, optional due dates for
        scheduling, note linking for context, and tag integration for categorization.
        
        Args:
            session_id (str): Valid session ID for authorization
            title (str): Title/summary of the todo item  
            description (str): Detailed description. Defaults to empty string
            due_date (str): Due date in flexible format. Defaults to None
            priority (str): Priority level (low/normal/high). Defaults to "normal"
            tags (List[str]): Optional list of tags to apply. Defaults to None
            note_title (str): Title of note to link to. Defaults to None
            
        Returns:
            str: JSON response with todo_id on success or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})
            
            # Validate and normalize priority
            if priority not in {"low", "normal", "high"}:
                priority = "normal"  # Default to normal if invalid
            
            todo_id = self.db.create_todo(user_id, title.strip(), description.strip() if description else "", 
                                        due_date, priority, note_title.strip() if note_title else None)
            
            # Add tags to the todo if provided
            if todo_id and tags:
                clean_tags = [tag.strip() for tag in tags if tag.strip()]
                if clean_tags:
                    self.db.add_todo_tags(user_id, todo_id, clean_tags)
            
            return json.dumps({"success": True, "id": todo_id, "message": "Todo created"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create todo: {str(e)}"})

    def list_todos(self, session_id: str, status: str = None, tag: str = None,
                  priority: str = None, linked_to_note: str = None) -> str:
        """
        List todos with advanced filtering for productivity workflows.
        
        Supports multiple filter criteria to help users organize and manage
        their tasks effectively. Filters can be combined for precise results.
        
        Args:
            session_id (str): Valid session ID for authorization
            status (str): Filter by "open" or "done". None for all todos
            tag (str): Filter by specific tag name. None for all tags  
            priority (str): Filter by priority level. None for all priorities
            linked_to_note (str): Filter by linked note title. None for all
            
        Returns:
            str: JSON response with filtered todo list or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            todos = self.db.get_user_todos(user_id, status, tag, priority, linked_to_note)
            
            # Format response for API consistency
            results = [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "due_date": t["due_date"],
                    "priority": t["priority"],
                    "completed": t["completed"],
                    "tags": t["tags"],
                    "note_title": t["note_title"]
                }
                for t in todos
            ]
            
            return json.dumps({"success": True, "results": results})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to list todos: {str(e)}"})

    def toggle_todo(self, session_id: str, todo_id: int) -> str:
        """
        Toggle todo completion status for task management.
        
        Switches between completed and incomplete states, enabling users
        to track task progress and maintain productivity workflows.
        
        Args:
            session_id (str): Valid session ID for authorization
            todo_id (int): ID of the todo to toggle
            
        Returns:
            str: JSON response confirming status change or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if self.db.toggle_todo(user_id, todo_id):
                return json.dumps({"success": True, "message": "Todo updated"})
            else:
                return json.dumps({"success": False, "message": "Todo not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to toggle todo: {str(e)}"})

    def delete_todo(self, session_id: str, todo_id: int) -> str:
        """
        Delete a todo item with proper authorization checking.
        
        Permanently removes todo and associated relationships while ensuring
        only the owner can delete their todos.
        
        Args:
            session_id (str): Valid session ID for authorization
            todo_id (int): ID of the todo to delete
            
        Returns:
            str: JSON response confirming deletion or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if self.db.delete_todo(user_id, todo_id):
                return json.dumps({"success": True, "message": "Todo deleted"})
            else:
                return json.dumps({"success": False, "message": "Todo not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to delete todo: {str(e)}"})
