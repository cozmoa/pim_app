import sqlite3
import bcrypt
from typing import Optional, List, Dict, Any


class NoteDatabase:
    """
    Database layer for the Personal Information Manager (PIM).

    Handles:
    - User authentication and password security
    - Folder hierarchy with parent-child relationships
    - Notes management (CRUD, folder assignment, reminder support)
    - Tagging system for notes and todos
    - Todo management with priorities, due dates, and tags
    - Reminder scheduling
    - Full schema initialization with indexes and constraints
    """

    def __init__(self, db_path: str = "notes.db"):
        """
        Initialize the NoteDatabase and ensure schema exists.

        Args:
            db_path (str): Path to SQLite database file. Defaults to "notes.db".
        """
        self.db_path = db_path
        self._init_database()

    # ---------- helpers ----------
    def _connect(self):
        """
        Open a new SQLite connection with foreign keys enabled.

        Returns:
            sqlite3.Connection: Active database connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, decl: str):
        """
        Ensure a column exists in a table, adding it if missing.

        Args:
            conn (sqlite3.Connection): Database connection.
            table (str): Table name.
            column (str): Column name.
            decl (str): SQL declaration for the column.
        """
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            conn.commit()

    # ---------- schema ----------
    def _init_database(self):
        """
        Initialize schema: users, folders, notes, tags, todos, reminders, junction tables, and indexes.

        Creates all required tables if they do not exist, and sets up indexes for performance.
        """
        conn = self._connect()
        c = conn.cursor()

        # (schema creation code remains the same as you wrote it)
        # ...
        # Users, Folders, Notes, Tags, Note-Tags, Todos, Todo-Tags, Reminders, Indexes

        conn.commit()
        conn.close()

    # ---------- AUTH ----------
    def _hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with salt.

        Args:
            password (str): Plain-text password.

        Returns:
            str: Hashed password string.
        """
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, password: str, hash: str) -> bool:
        """
        Verify a password against a bcrypt hash.

        Args:
            password (str): Plain-text password.
            hash (str): Stored password hash.

        Returns:
            bool: True if valid, False otherwise.
        """
        return bcrypt.checkpw(password.encode("utf-8"), hash.encode("utf-8"))

    def create_user(self, username: str, password: str) -> bool:
        """
        Create a new user account.

        Args:
            username (str): Unique username.
            password (str): Plain-text password.

        Returns:
            bool: True if user created, False if username already exists.
        """
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, self._hash_password(password)),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def verify_user(self, username: str, password: str) -> bool:
        """
        Verify user login credentials.

        Args:
            username (str): Username.
            password (str): Plain-text password.

        Returns:
            bool: True if authentication succeeds, False otherwise.
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        return bool(row and self._verify_password(password, row[0]))

    def get_user_id(self, username: str) -> Optional[int]:
        """
        Get user ID by username.

        Args:
            username (str): Username.

        Returns:
            Optional[int]: User ID if found, None otherwise.
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    # ---------- FOLDERS ----------
    def create_folder(self, user_id: int, name: str, parent_id: Optional[int] = None) -> int:
        """
        Create a folder for a user.

        Args:
            user_id (int): Owner user ID.
            name (str): Folder name.
            parent_id (Optional[int]): Parent folder ID for hierarchy. Defaults to None.

        Returns:
            int: ID of the newly created folder.
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO folders (user_id, name, parent_id) VALUES (?, ?, ?)",
            (user_id, name, parent_id),
        )
        folder_id = cur.lastrowid
        conn.commit()
        conn.close()
        return folder_id

    def list_folders_tree(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve a user's folder hierarchy as a tree.

        Args:
            user_id (int): User ID.

        Returns:
            List[Dict[str, Any]]: Tree of folders with children arrays.
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, name, parent_id FROM folders WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        conn.close()
        nodes = {r[0]: {"id": r[0], "name": r[1], "parent_id": r[2], "children": []} for r in rows}
        roots = []
        for node in nodes.values():
            if node["parent_id"] and node["parent_id"] in nodes:
                nodes[node["parent_id"]]["children"].append(node)
            else:
                roots.append(node)
        return roots

    # ---------- NOTES ----------
    def create_note(self, user_id: int, title: str, content: str, folder_id: Optional[int] = None) -> Optional[int]:
        """
        Create a new note for a user.

        Args:
            user_id (int): Owner user ID.
            title (str): Note title (must be unique per user).
            content (str): Note body.
            folder_id (Optional[int]): Folder ID to assign. Defaults to None.

        Returns:
            Optional[int]: Note ID if created successfully, None if title exists.
        """
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notes (user_id, title, content, folder_id) VALUES (?, ?, ?, ?)",
                (user_id, title, content, folder_id),
            )
            note_id = cur.lastrowid
            conn.commit()
            return note_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_user_notes(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all notes for a user.

        Args:
            user_id (int): User ID.

        Returns:
            List[Dict[str, Any]]: List of notes with id, title, content, and folder_id.
        """
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, folder_id FROM notes WHERE user_id = ?", (user_id,))
        notes = [{"id": r[0], "title": r[1], "content": r[2], "folder_id": r[3]} for r in cur.fetchall()]
        conn.close()
        return notes
