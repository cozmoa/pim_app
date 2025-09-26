import sqlite3
import bcrypt
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

class NoteDatabase:
    """
    Database access layer for the Personal Information Manager (PIM) system.
    
    Handles all database operations including user authentication, note management,
    and data persistence using SQLite. Implements secure password hashing and
    proper SQL injection prevention through parameterized queries.
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
        Initialize the database schema with all required tables.
        
        Creates users and notes tables with proper constraints, foreign keys,
        and indexes for optimal performance. Safe to run multiple times.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table with authentication data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Notes table with content and metadata
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
        Create a new user account with hashed password.
        
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
        Verify user credentials for authentication.
        
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
        Retrieve user ID by username.
        
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
        Create a new note for the specified user.
        
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
        Retrieve a specific note by its title for the given user.
        
        Args:
            user_id (int): ID of the user who owns the note
            title (str): Title of the note to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Note data with metadata if found, None otherwise
                Dictionary contains: id, title, content, created_at, modified_at, 
                reminder_date, tags (empty list for now)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.title, n.content, n.created_at, n.modified_at, n.reminder_date
            FROM notes n
            WHERE n.user_id = ? AND n.title = ?
        ''', (user_id, title))
        
        note_data = cursor.fetchone()
        if not note_data:
            conn.close()
            return None
        
        conn.close()
        
        return {
            "id": note_data[0],
            "title": note_data[1],
            "content": note_data[2],
            "created_at": note_data[3],
            "modified_at": note_data[4],
            "reminder_date": note_data[5],
            "tags": []  # Tags will be populated when tag system is implemented
        }
    
    def get_user_notes(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve all notes for a user, ordered by most recently modified.
        
        Args:
            user_id (int): ID of the user whose notes to retrieve
            limit (int): Maximum number of notes to return. Defaults to 50
            
        Returns:
            List[Dict[str, Any]]: List of note dictionaries with metadata
                Each dictionary contains: id, title, content, created_at, 
                modified_at, tags (empty list for now)
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
            notes.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "created_at": row[3],
                "modified_at": row[4],
                "tags": []  # Tags will be populated when tag system is implemented
            })
        
        conn.close()
        return notes
    
    def update_note_content(self, user_id: int, title: str, new_content: str) -> bool:
        """
        Update the content of an existing note and refresh modification timestamp.
        
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
        Update the title of an existing note with duplicate prevention.
        
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
        Delete a note permanently from the database.
        
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
