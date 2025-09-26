import sqlite3
import bcrypt
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

class NoteDatabase:
    """
    Complete database access layer for Personal Information Manager (PIM) system.
    
    Provides comprehensive data persistence for users, notes with hierarchical folders,
    todos with advanced filtering, tagging system, and search functionality. 
    Implements secure authentication, proper normalization, performance optimization
    through indexing, and maintains data integrity with foreign key constraints.
    
    Features:
    - User authentication with bcrypt password hashing
    - Notes with content versioning and metadata tracking  
    - Hierarchical folder system for note organization
    - Todo management with priorities, due dates, and completion tracking
    - Normalized tagging system shared between notes and todos
    - Full-text search across note content and titles
    - User analytics and statistics for dashboard display
    - Performance-optimized with strategic database indexes
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """
        Initialize database connection and create optimized schema.
        
        Args:
            db_path (str): Path to SQLite database file. Defaults to "notes.db"
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """
        Initialize complete database schema with all tables, relationships, and indexes.
        
        Creates the full PIM database structure including users, notes, todos, tags,
        folders, and all junction tables. Implements proper foreign key constraints,
        unique constraints, and performance indexes for optimal query execution.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table - Authentication and user management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Notes table - Core content storage with metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reminder_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, title)
            )
        ''')

        # Tags table - Normalized tag storage shared across notes and todos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')

        # Note-Tags junction table - Many-to-many relationship for note tagging
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')

        # Todos table - Task management with priorities and linking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT,
                priority TEXT DEFAULT 'normal',
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (note_id) REFERENCES notes (id)
            )
        ''')

        # Todo-Tags junction table - Many-to-many relationship for todo tagging
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todo_tags (
                todo_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (todo_id, tag_id),
                FOREIGN KEY (todo_id) REFERENCES todos (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')

        # Folders table - Hierarchical folder structure for note organization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                parent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE,
                UNIQUE(user_id, name, parent_id)
            )
        ''')

        # Note-Folder junction table - Many-to-many for flexible note organization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS note_folders (
                note_id INTEGER,
                folder_id INTEGER,
                PRIMARY KEY (note_id, folder_id),
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE CASCADE
            )
        ''')

        # Performance indexes for frequently queried columns
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_folders_parent_id ON folders(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_tags_todo_id ON todo_tags(todo_id)')

        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with salt for secure storage.
        
        Uses bcrypt's adaptive hashing with automatic salt generation for
        maximum security against rainbow table and brute force attacks.
        
        Args:
            password (str): Plain text password to hash
            
        Returns:
            str: Bcrypt hashed password with embedded salt
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hash: str) -> bool:
        """
        Verify password against stored bcrypt hash.
        
        Args:
            password (str): Plain text password to verify
            hash (str): Stored bcrypt hash to check against
            
        Returns:
            bool: True if password matches hash, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))
    
    def create_user(self, username: str, password: str) -> bool:
        """
        Create a new user account with secure password hashing.
        
        Args:
            username (str): Unique username for the account
            password (str): Plain text password to be hashed and stored
            
        Returns:
            bool: True if user created successfully, False if username already exists
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self._hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def verify_user(self, username: str, password: str) -> bool:
        """
        Verify user credentials for authentication using bcrypt.
        
        Args:
            username (str): Username to authenticate
            password (str): Plain text password to verify
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT password_hash FROM users WHERE username = ?',
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        return self._verify_password(password, result[0])
    
    def get_user_id(self, username: str) -> Optional[int]:
        """
        Retrieve user ID by username for session management.
        
        Args:
            username (str): Username to lookup
            
        Returns:
            Optional[int]: User ID if found, None if user doesn't exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def create_note(self, user_id: int, title: str, content: str) -> Optional[int]:
        """
        Create a new note with unique title constraint per user.
        
        Args:
            user_id (int): ID of the user creating the note
            title (str): Unique title for the note (per user)
            content (str): Note content/body text
            
        Returns:
            Optional[int]: Note ID if created successfully, None if title already exists
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)',
                (user_id, title, content)
            )
            note_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return note_id
            
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def get_note_by_title(self, user_id: int, title: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific note with all metadata and associated tags.
        
        Args:
            user_id (int): ID of the user who owns the note
            title (str): Title of the note to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Complete note data if found, None otherwise
                Dictionary contains: id, title, content, created_at, modified_at, 
                reminder_date, tags (list of tag names)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get note with metadata
        cursor.execute('''
            SELECT n.id, n.title, n.content, n.created_at, n.modified_at, n.reminder_date
            FROM notes n
            WHERE n.user_id = ? AND n.title = ?
        ''', (user_id, title))
        
        note_data = cursor.fetchone()
        if not note_data:
            conn.close()
            return None
        
        # Get associated tags for this note
        cursor.execute('''
            SELECT t.name
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            WHERE nt.note_id = ?
        ''', (note_data[0],))
        
        tags = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return {
            "id": note_data[0],
            "title": note_data[1],
            "content": note_data[2],
            "created_at": note_data[3],
            "modified_at": note_data[4],
            "reminder_date": note_data[5],
            "tags": tags
        }
    
    def get_user_notes(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve all notes for a user with tags, ordered by modification date.
        
        Args:
            user_id (int): ID of the user whose notes to retrieve
            limit (int): Maximum number of notes to return. Defaults to 50
            
        Returns:
            List[Dict[str, Any]]: List of note dictionaries with complete metadata
                Each contains: id, title, content, created_at, modified_at, tags
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, content, created_at, modified_at
            FROM notes
            WHERE user_id = ?
            ORDER BY modified_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        notes = []
        for row in cursor.fetchall():
            # Get tags for each note
            cursor.execute('''
                SELECT t.name
                FROM tags t
                JOIN note_tags nt ON t.id = nt.tag_id
                WHERE nt.note_id = ?
            ''', (row[0],))
            
            tags = [tag_row[0] for tag_row in cursor.fetchall()]
            
            notes.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "created_at": row[3],
                "modified_at": row[4],
                "tags": tags
            })
        
        conn.close()
        return notes
    
    def update_note_content(self, user_id: int, title: str, new_content: str) -> bool:
        """
        Update note content with automatic timestamp refresh.
        
        Args:
            user_id (int): ID of the user who owns the note
            title (str): Title of the note to update
            new_content (str): New content to replace existing content
            
        Returns:
            bool: True if note was updated successfully, False if note not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notes 
            SET content = ?, modified_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND title = ?
        ''', (new_content, user_id, title))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_note_title(self, user_id: int, old_title: str, new_title: str) -> bool:
        """
        Update note title with duplicate prevention and ownership validation.
        
        Args:
            user_id (int): ID of the user who owns the note
            old_title (str): Current title of the note
            new_title (str): New title to set (must be unique for this user)
            
        Returns:
            bool: True if title updated successfully, False if note not found
                  or new title already exists for this user
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if new title already exists for this user
            cursor.execute('SELECT id FROM notes WHERE user_id = ? AND title = ?', (user_id, new_title))
            if cursor.fetchone():
                conn.close()
                return False  # Title already exists

            cursor.execute('''
                UPDATE notes
                SET title = ?, modified_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND title = ?
            ''', (new_title, user_id, old_title))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception:
            conn.close()
            return False
    
    def delete_note(self, user_id: int, title: str) -> bool:
        """
        Delete a note and all associated tag relationships.
        
        Args:
            user_id (int): ID of the user who owns the note
            title (str): Title of the note to delete
            
        Returns:
            bool: True if note was deleted successfully, False if note not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM notes WHERE user_id = ? AND title = ?', (user_id, title))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def search_user_notes(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """
        Search notes by keyword matching in title or content.
        
        Args:
            user_id (int): ID of the user whose notes to search
            query (str): Search term to match against title and content
            
        Returns:
            List[Dict[str, Any]]: List of matching notes with metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        search_pattern = f"%{query}%"
        cursor.execute('''
            SELECT id, title, content, created_at, modified_at
            FROM notes
            WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)
            ORDER BY modified_at DESC
        ''', (user_id, search_pattern, search_pattern))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "created_at": row[3],
                "modified_at": row[4]
            })
        
        conn.close()
        return results
    
    def add_note_tags(self, user_id: int, title: str, tags: List[str]) -> Optional[List[str]]:
        """
        Add tags to a note. Returns all tags if successful, None if note not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get note ID
        cursor.execute('SELECT id FROM notes WHERE user_id = ? AND title = ?', (user_id, title))
        note_result = cursor.fetchone()
        if not note_result:
            conn.close()
            return None
        
        note_id = note_result[0]
        
        try:
            for tag_name in tags:
                # Insert tag if it doesn't exist
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                
                # Get tag ID
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                tag_id = cursor.fetchone()[0]
                
                # Link note and tag
                cursor.execute('INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)', 
                             (note_id, tag_id))
            
            # Get all tags for this note
            cursor.execute('''
                SELECT t.name
                FROM tags t
                JOIN note_tags nt ON t.id = nt.tag_id
                WHERE nt.note_id = ?
            ''', (note_id,))
            
            all_tags = [row[0] for row in cursor.fetchall()]
            
            conn.commit()
            conn.close()
            return all_tags
            
        except Exception:
            conn.close()
            return None
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get user statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count notes
        cursor.execute('SELECT COUNT(*) FROM notes WHERE user_id = ?', (user_id,))
        note_count = cursor.fetchone()[0]
        
        # Count unique tags used by user
        cursor.execute('''
            SELECT COUNT(DISTINCT t.id)
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            JOIN notes n ON nt.note_id = n.id
            WHERE n.user_id = ?
        ''', (user_id,))
        tag_count = cursor.fetchone()[0]
        
        # Get most recent note
        cursor.execute('''
            SELECT title, modified_at
            FROM notes
            WHERE user_id = ?
            ORDER BY modified_at DESC
            LIMIT 1
        ''', (user_id,))
        recent_note = cursor.fetchone()
        
        # Count todos
        cursor.execute('SELECT COUNT(*) FROM todos WHERE user_id = ?', (user_id,))
        todo_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_notes": note_count,
            "total_tags": tag_count,
            "total_todos": todo_count,
            "recent_note": {
                "title": recent_note[0] if recent_note else None,
                "modified_at": recent_note[1] if recent_note else None
            }
        }
    
    # Todo database methods
    def create_todo(self, user_id: int, title: str, description: str = "", 
                   due_date: str = None, priority: str = "normal", 
                   note_title: str = None) -> Optional[int]:
        """Create a new todo. Returns todo_id if successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        note_id = None
        if note_title:
            # Get note_id if linking to a note
            cursor.execute('SELECT id FROM notes WHERE user_id = ? AND title = ?', 
                         (user_id, note_title))
            note_result = cursor.fetchone()
            if note_result:
                note_id = note_result[0]
        
        cursor.execute('''
            INSERT INTO todos (user_id, title, description, due_date, priority, note_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, title, description, due_date, priority, note_id))
        
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return todo_id
    
    def get_user_todos(self, user_id: int, status: str = None, tag: str = None,
                      priority: str = None, linked_to_note: str = None) -> List[Dict[str, Any]]:
        """Get todos for a user with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query with filters
        query = '''
            SELECT t.id, t.title, t.description, t.due_date, t.priority, 
                   t.completed, t.created_at, n.title as note_title
            FROM todos t
            LEFT JOIN notes n ON t.note_id = n.id
            WHERE t.user_id = ?
        '''
        params = [user_id]
        
        if status == "open":
            query += " AND t.completed = 0"
        elif status == "done":
            query += " AND t.completed = 1"
            
        if priority:
            query += " AND t.priority = ?"
            params.append(priority)
            
        if linked_to_note:
            query += " AND n.title = ?"
            params.append(linked_to_note)
        
        query += " ORDER BY t.created_at DESC"
        
        cursor.execute(query, params)
        todos = []
        
        for row in cursor.fetchall():
            todo_id = row[0]
            
            # Get tags for this todo
            cursor.execute('''
                SELECT t.name
                FROM tags t
                JOIN todo_tags tt ON t.id = tt.tag_id
                WHERE tt.todo_id = ?
            ''', (todo_id,))
            
            todo_tags = [tag_row[0] for tag_row in cursor.fetchall()]
            
            # Apply tag filter if specified
            if tag and tag not in todo_tags:
                continue
            
            todos.append({
                "id": todo_id,
                "title": row[1],
                "description": row[2],
                "due_date": row[3],
                "priority": row[4],
                "completed": bool(row[5]),
                "created_at": row[6],
                "note_title": row[7],
                "tags": todo_tags
            })
        
        conn.close()
        return todos
    
    def toggle_todo(self, user_id: int, todo_id: int) -> bool:
        """Toggle todo completion status. Returns True if successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First get current status
        cursor.execute('SELECT completed FROM todos WHERE id = ? AND user_id = ?', 
                      (todo_id, user_id))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        new_status = not bool(result[0])
        
        cursor.execute('UPDATE todos SET completed = ? WHERE id = ? AND user_id = ?',
                      (new_status, todo_id, user_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_todo(self, user_id: int, todo_id: int) -> bool:
        """Delete a todo. Returns True if successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM todos WHERE id = ? AND user_id = ?', 
                      (todo_id, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def add_todo_tags(self, user_id: int, todo_id: int, tags: List[str]) -> Optional[List[str]]:
        """Add tags to a todo. Returns all tags if successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verify todo belongs to user
        cursor.execute('SELECT id FROM todos WHERE id = ? AND user_id = ?', 
                      (todo_id, user_id))
        if not cursor.fetchone():
            conn.close()
            return None
        
        try:
            for tag_name in tags:
                # Insert tag if it doesn't exist
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                
                # Get tag ID
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                tag_id = cursor.fetchone()[0]
                
                # Link todo and tag
                cursor.execute('INSERT OR IGNORE INTO todo_tags (todo_id, tag_id) VALUES (?, ?)', 
                             (todo_id, tag_id))
            
            # Get all tags for this todo
            cursor.execute('''
                SELECT t.name
                FROM tags t
                JOIN todo_tags tt ON t.id = tt.tag_id
                WHERE tt.todo_id = ?
            ''', (todo_id,))
            
            all_tags = [row[0] for row in cursor.fetchall()]
            
            conn.commit()
            conn.close()
            return all_tags
            
        except Exception:
            conn.close()
            return None

    
    # Folder management methods
    def create_folder(self, user_id: int, name: str, parent_id: int = None) -> Optional[int]:
        """Create a new folder for user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO folders (user_id, name, parent_id)
                VALUES (?, ?, ?)
            ''', (user_id, name, parent_id))
            
            folder_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return folder_id
            
        except sqlite3.IntegrityError:
            conn.close()
            return None

    def get_user_folders_tree(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's folder tree structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, parent_id, created_at
            FROM folders
            WHERE user_id = ?
            ORDER BY parent_id, name
        ''', (user_id,))
        
        folders = []
        for row in cursor.fetchall():
            folders.append({
                "id": row[0],
                "name": row[1], 
                "parent_id": row[2],
                "created_at": row[3]
            })
        
        conn.close()
        return folders

    def link_note_to_folder(self, user_id: int, note_title: str, folder_id: int) -> bool:
        """Link a note to a folder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get note ID
        cursor.execute('SELECT id FROM notes WHERE user_id = ? AND title = ?', (user_id, note_title))
        note_result = cursor.fetchone()
        if not note_result:
            conn.close()
            return False
        
        note_id = note_result[0]
        
        try:
            cursor.execute('INSERT OR IGNORE INTO note_folders (note_id, folder_id) VALUES (?, ?)',
                          (note_id, folder_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False
