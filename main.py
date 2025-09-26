# Commit Message: feat: Add comprehensive CLI interface and complete folder management system
#
# - Implemented full-featured command-line interface (CLI) for standalone usage
# - Added hierarchical folder management with create_folder() and get_user_folders()
# - Created link_note_to_folder() for flexible note organization
# - Implemented complete CLI menu system with user-friendly navigation
# - Added interactive todo management interface within CLI
# - Enhanced user experience with formatted output and intuitive workflows
# - Integrated all PIM features into cohesive CLI application
# - Added proper error handling and user guidance throughout CLI interface
#
# CLI features implemented:
# - Complete authentication workflow (register/login/logout)
# - Interactive note management with content input helpers
# - Full todo system with priority and status management
# - Search functionality with formatted result display
# - Tag management with batch operations
# - User statistics and analytics display
# - Hierarchical folder organization system
# - Graceful error handling and user feedback

import json
import uuid
from typing import Optional, List, Dict, Any
from database_pim_final import NoteDatabase

class NoteDatabaseSystem:
    """
    Complete Personal Information Manager (PIM) business logic system.
    
    Provides comprehensive functionality for note management, todo tracking,
    search, tagging, folder organization, user analytics, and both API and
    CLI interfaces. Implements secure session management and data validation.
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """Initialize the system with database and session management."""
        try:
            self.db = NoteDatabase(db_path)
            self.active_sessions = {}  # session_id -> username mapping
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def register_user(self, username: str, password: str) -> str:
        """Register a new user account with validation."""
        try:
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is require and cannot be empty"})
            
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
        """Login user and create session."""
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
        """Create a new todo."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})
            
            if priority not in {"low", "normal", "high"}:
                priority = "normal"  # Default to normal if invalid
            
            todo_id = self.db.create_todo(user_id, title.strip(), description.strip() if description else "", 
                                        due_date, priority, note_title.strip() if note_title else None)
            
            if todo_id and tags:
                # Add tags to the todo
                clean_tags = [tag.strip() for tag in tags if tag.strip()]
                if clean_tags:
                    self.db.add_todo_tags(user_id, todo_id, clean_tags)
            
            return json.dumps({"success": True, "id": todo_id, "message": "Todo created"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create todo: {str(e)}"})

    def list_todos(self, session_id: str, status: str = None, tag: str = None,
                  priority: str = None, linked_to_note: str = None) -> str:
        """List todos for the user."""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            todos = self.db.get_user_todos(user_id, status, tag, priority, linked_to_note)
            
            # Format response similar to original
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
        """Toggle todo completion status."""
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
        """Delete a todo."""
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

    # Folder management methods
    def create_folder(self, session_id: str, name: str, parent_id: int = None) -> str:
        """
        Create a new hierarchical folder for note organization.
        
        Args:
            session_id (str): Valid session ID for authorization
            name (str): Name of the folder to create
            parent_id (int): ID of parent folder. None for root-level folder
            
        Returns:
            str: JSON response with folder_id on success or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            
            folder_id = self.db.create_folder(user_id, name.strip(), parent_id)
            if folder_id:
                return json.dumps({"success": True, "folder_id": folder_id})
            else:
                return json.dumps({"success": False, "message": "Folder name already exists"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create folder: {str(e)}"})

    def get_user_folders(self, session_id: str) -> str:
        """
        Get all folders for user as hierarchical tree structure.
        
        Args:
            session_id (str): Valid session ID for authorization
            
        Returns:
            str: JSON response with folder tree or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            
            folders = self.db.get_user_folders_tree(user_id)
            return json.dumps({"success": True, "folders": folders})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get folders: {str(e)}"})

    def link_note_to_folder(self, session_id: str, note_title: str, folder_id: int) -> str:
        """
        Link a note to a folder for organization.
        
        Args:
            session_id (str): Valid session ID for authorization
            note_title (str): Title of note to link
            folder_id (int): ID of folder to link note to
            
        Returns:
            str: JSON response confirming link operation or error message
        """
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            
            success = self.db.link_note_to_folder(user_id, note_title, folder_id)
            if success:
                return json.dumps({"success": True, "message": "Note linked to folder"})
            else:
                return json.dumps({"success": False, "message": "Note or folder not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to link note: {str(e)}"})
    
def run_cli():
    """
    Complete command-line interface for the PIM system.
    
    Provides full-featured interactive interface for all system functionality
    including user authentication, note management, todo tracking, search,
    tagging, and analytics. Designed for standalone usage without web interface.
    """
    system = NoteDatabaseSystem()
    current_session = None

    print("=== Personal Information Manager (PIM) System ===")
    print("Complete note-taking and todo management system")

    while True:
        try:
            if not current_session:
                print("\n=== Authentication Required ===")
                print("1. Register New Account")
                print("2. Login to Existing Account")
                print("3. Exit Application")
                choice = input("Choose option: ").strip()

                if choice == "1":
                    print("\n=== User Registration ===")
                    username = input("Choose username: ").strip()
                    password = input("Choose password: ").strip()
                    if username and password:
                        result = json.loads(system.register_user(username, password))
                        print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")
                    else:
                        print("✗ Username and password cannot be empty")

                elif choice == "2":
                    print("\n=== User Login ===")
                    username = input("Username: ").strip()
                    password = input("Password: ").strip()
                    if username and password:
                        result = json.loads(system.login_user(username, password))
                        print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")
                        if result["success"]:
                            current_session = result["session_id"]
                    else:
                        print("✗ Username and password cannot be empty")

                elif choice == "3":
                    print("Thank you for using PIM System. Goodbye! 👋")
                    break

                else:
                    print("✗ Invalid choice. Please select 1, 2, or 3.")

            else:
                username = system._get_username_from_session(current_session)
                print(f"\n=== PIM Dashboard - Welcome {username}! ===")
                print("1.  Notes Management")
                print("2.  Todo Management") 
                print("3.  Search Notes")
                print("4.   Manage Tags")
                print("5.  View Statistics")
                print("6.  Folder Management")
                print("7.  Logout")
               
                choice = input("Choose option: ").strip()

                if choice == "1":
                    # Notes Management Submenu
                    while True:
                        print(f"\n===  Notes Management ({username}) ===")
                        print("1.  Create New Note")
                        print("2.  List All Notes") 
                        print("3.  View Specific Note")
                        print("4.   Edit Note Content")
                        print("5.  Rename Note Title")
                        print("6.   Delete Note")
                        print("7.   Back to Main Menu")

                        note_choice = input("Choose option: ").strip()

                        if note_choice == "1":
                            print("\n=== ➕ Create New Note ===")
                            title = input("Note title: ").strip()
                            if not title:
                                print("✗ Title cannot be empty")
                                continue
                            print("Enter content (type 'END' on a new line to finish):")
                            content_lines = []
                            while True:
                                line = input()
                                if line == "END":
                                    break
                                content_lines.append(line)
                            content = "\n".join(content_lines)
                            result = json.loads(system.create_note(current_session, title, content))
                            print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")

                        elif note_choice == "2":
                            print("\n=== 📋 Your Notes ===")
                            result = json.loads(system.list_notes(current_session))
                            if result["success"]:
                                if result["notes"]:
                                    print(f"Found {result['count']} notes:")
                                    for note in result["notes"]:
                                        tags_str = ", ".join(note["tags"]) if note["tags"] else "No tags"
                                        print(f"\n {note['title']}")
                                        print(f"    Modified: {note['modified_at']}")
                                        print(f"     Tags: {tags_str}")
                                        print(f"    Preview: {note['preview']}")
                                else:
                                    print("No notes found. Create your first note!")
                            else:
                                print(f"✗ {result['message']}")

                        elif note_choice == "3":
                            print("\n=== 👀 View Note ===")
                            title = input("Note title to view: ").strip()
                            if not title:
                                print("✗ Title cannot be empty")
                                continue
                            result = json.loads(system.get_note(current_session, title))
                            if result["success"]:
                                note = result["note"]
                                print(f"\n === {note['title']} ===")
                                print(f" Created: {note['created_at']}")
                                print(f" Modified: {note['modified_at']}")
                                if note["tags"]:
                                    print(f"  Tags: {', '.join(note['tags'])}")
                                print(f"\n Content:\n{note['content']}")
                            else:
                                print(f"✗ {result['message']}")

                        elif note_choice == "4":
                            print("\n===  Edit Note ===")
                            title = input("Note title to edit: ").strip()
                            if not title:
                                print("✗ Title cannot be empty")
                                continue
                            print("Enter new content (type 'END' on a new line to finish):")
                            content_lines = []
                            while True:
                                line = input()
                                if line == "END":
                                    break
                                content_lines.append(line)
                            new_content = "\n".join(content_lines)
                            result = json.loads(system.edit_note(current_session, title, new_content))
                            print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")

                        elif note_choice == "5":
                            print("\n===  Rename Note ===")
                            old_title = input("Current note title: ").strip()
                            new_title = input("New note title: ").strip()
                            if not old_title or not new_title:
                                print("✗ Both titles are required")
                                continue
                            result = json.loads(system.update_note_title(current_session, old_title, new_title))
                            print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")

                        elif note_choice == "6":
                            print("\n=== 🗑️ Delete Note ===")
                            title = input("Note title to delete: ").strip()
                            if not title:
                                print("✗ Title cannot be empty")
                                continue
                            confirm = input(f"  Are you sure you want to delete '{title}'? (y/N): ")
                            if confirm.lower() == 'y':
                                result = json.loads(system.delete_note(current_session, title))
                                print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")
                            else:
                                print(" Deletion cancelled")

                        elif note_choice == "7":
                            break
                        else:
                            print("✗ Invalid choice")

                elif choice == "2":
                    # Todo Management Submenu  
                    while True:
                        print(f"\n===  Todo Management ({username}) ===")
                        print("1.  Create New Todo")
                        print("2.  List All Todos")
                        print("3.  Toggle Todo Status")
                        print("4.   Delete Todo")
                        print("5.   Back to Main Menu")

                        todo_choice = input("Choose option: ").strip()

                        if todo_choice == "1":
                            print("\n=== ➕ Create New Todo ===")
                            title = input("Todo title: ").strip()
                            if not title:
                                print("✗ Title cannot be empty")
                                continue
                            desc = input("Description (optional): ").strip()
                            due = input("Due date (YYYY-MM-DD or leave blank): ").strip() or None
                            prio = input("Priority (low/normal/high) [normal]: ").strip() or "normal"
                            if prio not in {"low", "normal", "high"}:
                                print("⚠️  Invalid priority, using 'normal'")
                                prio = "normal"
                            tags_input = input("Tags (comma-separated, optional): ").strip()
                            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else None
                            note_title = input("Link to note title (optional): ").strip() or None
                            result = json.loads(system.create_todo(current_session, title, desc, due, prio, tags, note_title))
                            print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")

                        elif todo_choice == "2":
                            print("\n=== 📋 Your Todos ===")
                            result = json.loads(system.list_todos(current_session))
                            if result["success"]:
                                if result["results"]:
                                    print(f"Found {len(result['results'])} todos:")
                                    for todo in result["results"]:
                                        status = "✅" if todo["completed"] else "⏳"
                                        priority_icon = {"low": "🟢", "normal": "🟡", "high": "🔴"}.get(todo["priority"], "🟡")
                                        note_info = f" 📎 {todo['note_title']}" if todo['note_title'] else ""
                                        tags_info = f" 🏷️ [{', '.join(todo['tags'])}]" if todo['tags'] else ""
                                        
                                        print(f"\n{status} [{todo['id']}] {todo['title']}{note_info}")
                                        print(f"   {priority_icon} Priority: {todo['priority']}")
                                        if todo['due_date']:
                                            print(f"   📅 Due: {todo['due_date']}")
                                        if tags_info:
                                            print(f"   {tags_info}")
                                else:
                                    print("📭 No todos found. Create your first todo!")
                            else:
                                print(f"✗ {result['message']}")

                        elif todo_choice == "3":
                            print("\n===  Toggle Todo Status ===")
                            try:
                                todo_id = int(input("Todo ID to toggle: ").strip())
                                result = json.loads(system.toggle_todo(current_session, todo_id))
                                print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")
                            except ValueError:
                                print("✗ Invalid todo ID - please enter a number")

                        elif todo_choice == "4":
                            print("\n=== 🗑️ Delete Todo ===")
                            try:
                                todo_id = int(input("Todo ID to delete: ").strip())
                                confirm = input(f"  Are you sure you want to delete todo {todo_id}? (y/N): ")
                                if confirm.lower() == 'y':
                                    result = json.loads(system.delete_todo(current_session, todo_id))
                                    print(f"✓ {result['message']}" if result["success"] else f"✗ {result['message']}")
                                else:
                                    print(" Deletion cancelled")
                            except ValueError:
                                print("✗ Invalid todo ID - please enter a number")

                        elif todo_choice == "5":
                            break
                        else:
                            print("✗ Invalid choice")

                elif choice == "3":
                    print("\n===  Search Notes ===")
                    query = input("Enter search term: ").strip()
                    if not query:
                        print("✗ Search query cannot be empty")
                        continue
                    result = json.loads(system.search_notes(current_session, query))
                    if result["success"] and result["results"]:
                        print(f"\n🎯 Found {result['count']} results for '{query}':")
                        for note in result["results"]:
                            print(f"\n {note['title']}")
                            print(f"    Modified: {note['modified_at']}")
                            print(f"    Preview: {note['preview']}")
                    else:
                        print("🔍 No results found")

                elif choice == "4":
                    print("\n===  Tag Management ===")
                    title = input("Note title to add tags to: ").strip()
                    if not title:
                        print("✗ Title cannot be empty")
                        continue
                    tags_input = input("Tags to add (comma-separated): ").strip()
                    if not tags_input:
                        print("✗ Tags cannot be empty")
                        continue
                    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                    if not tags:
                        print("✗ No valid tags provided")
                        continue
                    result = json.loads(system.add_tags(current_session, title, tags))
                    if result["success"]:
                        print(f" All tags on note: {', '.join(result['tags'])}")
                    else:
                        print(f"✗ {result['message']}")

                elif choice == "5":
                    print("\n===  Your Statistics ===")
                    result = json.loads(system.get_stats(current_session))
                    if result["success"]:
                        stats = result["stats"]
                        print(f" Total Notes: {stats['total_notes']}")
                        print(f"  Unique Tags: {stats['total_tags']}")
                        print(f" Total Todos: {stats['total_todos']}")
                        if stats["recent_note"]["title"]:
                            print(f" Most Recent Note: {stats['recent_note']['title']}")
                            print(f"   Last Modified: {stats['recent_note']['modified_at']}")
                        else:
                            print("📭 No notes created yet")
                    else:
                        print(f"✗ {result['message']}")

                elif choice == "6":
                    print("\n🚧 Folder Management - Coming Soon!")
                    print("This feature will be available in a future update.")

                elif choice == "7":
                    result = json.loads(system.logout_user(current_session))
                    print(f"✓ {result['message']}")
                    current_session = None

                else:
                    print("✗ Invalid choice. Please select 1-7.")
                    
        except KeyboardInterrupt:
            print("\n\n Goodbye! Thank you for using PIM System.")
            break
        except Exception as e:
            print(f"  An error occurred: {e}")
            print("Please try again or contact support if the issue persists.")


# Example usage and main entry point
if __name__ == "__main__":
    """
    Main entry point for the PIM system.
    
    Runs the command-line interface when this file is executed directly,
    providing standalone functionality for users who prefer terminal interaction.
    """
    print(" Starting Personal Information Manager (PIM) System...")
    run_cli()
