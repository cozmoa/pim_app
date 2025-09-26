import sqlite3
import bcrypt
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

class NoteDatabase:
    """
    Database access layer for the Personal Information Manager (PIM) system.
    
    Provides comprehensive data persistence for users, notes, and tags with
    full CRUD operations, search functionality, and tagging system. Uses SQLite
    with proper normalization and security best practices.
    """
    
    def __init__(self, db_path: str = "notes.db"):
        """
        Initialize database connection and create required tables.
        
        Args:
            db_path (str): Path to SQLite database file. Defaults to "notes.db"
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """
        Initialize the complete database schema with all tables and relationships.
        
        Creates users, notes, tags, and junction tables with proper constraints,
        foreign keys, and indexes. Implements normalized design for efficient
        tag storage and retrieval.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Notes table
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

        # Tags table (normalized - one entry per unique tag)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')

        # Note-Tags junction table (many-to-many relationship)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with salt for secure storage.
        
        Args:
            password (str): Plain text password to hash
            
        Returns:
            str: Bcrypt hashed password with salt
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hash: str) -> bool:
        """
        Verify password against bcrypt hash.
        
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

            # Prevent duplicate titles for the same user
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
            bool: True if note deleted successfully, False if note not found
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
        
        Uses SQL LIKE pattern matching for flexible search across both
        note titles and content. Results ordered by modification date.
        
        Args:
            user_id (int): ID of the user whose notes to search
            query (str): Search term to match against title and content
            
        Returns:
            List[Dict[str, Any]]: List of matching notes with metadata
                Each contains: id, title, content, created_at, modified_at
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
        Add multiple tags to a note using normalized tag storage.
        
        Creates new tag entries if they don't exist, then links them to the note
        through the junction table. Prevents duplicate tag assignments.
        
        Args:
            user_id (int): ID of the user who owns the note
            title (str): Title of the note to tag
            tags (List[str]): List of tag names to add
            
        Returns:
            Optional[List[str]]: Complete list of all tags on the note if successful,
                               None if note not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get note ID and verify ownership
        cursor.execute('SELECT id FROM notes WHERE user_id = ? AND title = ?', (user_id, title))
        note_result = cursor.fetchone()
        if not note_result:
            conn.close()
            return None
        
        note_id = note_result[0]
        
        try:
            for tag_name in tags:
                # Insert tag if it doesn't exist (normalized storage)
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                
                # Get tag ID
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                tag_id = cursor.fetchone()[0]
                
                # Link note and tag (prevent duplicates with INSERT OR IGNORE)
                cursor.execute('INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)', 
                             (note_id, tag_id))
            
            # Return complete list of all tags for this note
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
        Generate comprehensive user statistics for dashboard display.
        
        Provides metrics including total counts, most recent activity,
        and other analytics useful for user overview.
        
        Args:
            user_id (int): ID of the user to generate stats for
            
        Returns:
            Dict[str, Any]: Statistics dictionary containing:
                - total_notes: Number of notes created by user
                - total_tags: Number of unique tags used by user
                - recent_note: Info about most recently modified note
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count total notes for user
        cursor.execute('SELECT COUNT(*) FROM notes WHERE user_id = ?', (user_id,))
        note_count = cursor.fetchone()[0]
        
        # Count unique tags used by this user
        cursor.execute('''
            SELECT COUNT(DISTINCT t.id)
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            JOIN notes n ON nt.note_id = n.id
            WHERE n.user_id = ?
        ''', (user_id,))
        tag_count = cursor.fetchone()[0]
        
        # Get most recently modified note info
        cursor.execute('''
            SELECT title, modified_at
            FROM notes
            WHERE user_id = ?
            ORDER BY modified_at DESC
            LIMIT 1
        ''', (user_id,))
        recent_note = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_notes": note_count,
            "total_tags": tag_count,
            "recent_note": {
                "title": recent_note[0] if recent_note else None,
                "modified_at": recent_note[1] if recent_note else None
            }
        }
