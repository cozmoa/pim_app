import pytest
import tempfile
import os
import json
from database_pim_final import NoteDatabase
from main_pim_final import NoteDatabaseSystem
import sqlite3
import bcrypt

@pytest.fixture
def temp_db_path():
    """
    Fixture: Creates temporary database file for testing.
    
    Purpose: Ensures each test gets clean database without affecting others.
    Automatic cleanup: File is deleted after test completes.
    
    This fixture is critical for test isolation - each test gets its own
    database file, preventing tests from interfering with each other.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture
def db(temp_db_path):
    """
    Fixture: Database instance with clean temporary database.
    
    Returns a fresh NoteDatabase instance for each test, ensuring
    no data contamination between test cases.
    """
    return NoteDatabase(temp_db_path)

@pytest.fixture  
def system(temp_db_path):
    """
    Fixture: Business logic system with clean temporary database.
    
    Provides a fresh NoteDatabaseSystem instance for integration testing
    of the business logic layer.
    """
    return NoteDatabaseSystem(temp_db_path)

class TestHelpers:
    """
    Helper functions for common test operations.
    
    Purpose: Eliminate code duplication across test methods by providing
    reusable functions for common testing patterns like user creation,
    login, and note setup.
    
    Pattern: Create once, use everywhere - reduces boilerplate and improves
    test maintainability.
    """
    
    @staticmethod
    def create_user(system, username="testuser", password="password123"):
        """
        Helper: Create and register a user with validation.
        
        Args:
            system: NoteDatabaseSystem instance
            username: Username for the account (default: "testuser")
            password: Password for the account (default: "password123")
        
        Returns:
            str: Username used (allows easy customization in tests)
            
        Raises:
            AssertionError: If user creation fails
        """
        result = json.loads(system.register_user(username, password))
        assert result["success"], f"User creation failed: {result['message']}"
        return username
    
    @staticmethod
    def login_user(system, username="testuser", password="password123"):
        """
        Helper: Login user and return session ID.
        
        Args:
            system: NoteDatabaseSystem instance
            username: Username to login (default: "testuser")
            password: Password for authentication (default: "password123")
        
        Returns:
            str: Session ID string for authenticated requests
            
        Combines: Login + extract session + assert success in one call
        """
        result = json.loads(system.login_user(username, password))
        assert result["success"], f"Login failed: {result['message']}"
        return result["session_id"]
    
    @staticmethod
    def create_user_and_login(system, username="testuser", password="password123"):
        """
        Helper: Complete user setup (register + login).
        
        Args:
            system: NoteDatabaseSystem instance
            username: Username for the account (default: "testuser")
            password: Password for the account (default: "password123")
        
        Returns:
            tuple: (username, session_id) for immediate use in tests
            
        Most common pattern: Need logged-in user for testing protected operations
        """
        TestHelpers.create_user(system, username, password)
        session_id = TestHelpers.login_user(system, username, password)
        return username, session_id
    
    @staticmethod
    def create_sample_note(system, session_id, title="Sample Note", content="Sample content"):
        """
        Helper: Create a note for testing with default or custom content.
        
        Args:
            system: NoteDatabaseSystem instance
            session_id: Valid session ID for authorization
            title: Note title (default: "Sample Note")
            content: Note content (default: "Sample content")
        
        Returns:
            str: Note title (for easy reference in tests)
            
        Usage: For tests that need existing notes to work with
        """
        result = json.loads(system.create_note(session_id, title, content))
        assert result["success"], f"Note creation failed: {result['message']}"
        return title

class TestDatabase:
    """
    Unit tests for the database layer (NoteDatabase class).
    
    Purpose: Verify that SQL operations work correctly in isolation.
    
    Why these tests matter: Database is the foundation - if data operations
    fail, everything fails. These tests ensure data integrity, proper
    constraints, and correct SQL behavior.
    """
    
    def test_user_creation_success(self, db):
        """
        Test successful user creation with valid credentials.
        
        Purpose: Verify that valid users can be created and stored properly.
        Expected: Function returns True, user appears in database with hashed password.
        Critical because: User creation is the entry point to the system.
        """
        result = db.create_user("testuser", "password123")
        assert result == True, "User creation should succeed with valid data"
        
        # Verify user actually exists in database
        user_id = db.get_user_id("testuser")
        assert user_id is not None, "Created user should be retrievable by username"
        assert isinstance(user_id, int), "User ID should be an integer"
    
    def test_user_creation_duplicate_username(self, db):
        """
        Test duplicate username rejection to ensure uniqueness.
        
        Purpose: Verify system prevents duplicate usernames for data integrity.
        Expected: First creation succeeds, second fails gracefully.
        Why important: Usernames must be unique for authentication to work.
        """
        # First user should succeed
        result1 = db.create_user("testuser", "password123")
        assert result1 == True, "First user creation should succeed"
        
        # Duplicate username should fail
        result2 = db.create_user("testuser", "differentpassword")
        assert result2 == False, "Duplicate username should be rejected"
    
    def test_password_hashing_bcrypt(self, db):
        """
        Test that passwords are hashed using bcrypt, not stored in plain text.
        
        Purpose: Verify security implementation - passwords must be properly hashed.
        Method: Create user, examine stored password hash format and properties.
        Security principle: Never store plain text passwords.
        
        Bcrypt format validation:
        - Should start with $2a$, $2b$, $2x$, or $2y$ (bcrypt versions)
        - Should be exactly 60 characters long
        - Should have 4 parts separated by $ (version, cost, salt+hash)
        """
        db.create_user("testuser", "password123")
        
        # Check that stored password is hashed using bcrypt format
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("testuser",))
        stored_hash = cursor.fetchone()[0]
        conn.close()
        
        # Verify password is not stored as plain text
        assert stored_hash != "password123", "Password should be hashed, not stored as plain text"
        
        # Verify bcrypt format structure
        assert stored_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')), "Should use bcrypt format"
        assert len(stored_hash) == 60, f"Bcrypt hash should be 60 characters, got {len(stored_hash)}"
        
        # Verify bcrypt structure: $version$cost$salt+hash
        parts = stored_hash.split('$')
        assert len(parts) == 4, "Bcrypt should have 4 parts separated by $"
        assert parts[1] in ['2a', '2b', '2x', '2y'], "Should use valid bcrypt version"
        
        # Verify the hash can be used for verification
        assert bcrypt.checkpw("password123".encode('utf-8'), stored_hash.encode('utf-8')), "Hash should verify correct password"
        assert not bcrypt.checkpw("wrongpassword".encode('utf-8'), stored_hash.encode('utf-8')), "Hash should reject wrong password"
    
    def test_user_authentication_workflow(self, db):
        """
        Test complete user authentication workflow from creation to verification.
        
        Purpose: Verify that the entire authentication system works end-to-end.
        Workflow: Create user -> Verify correct password -> Reject wrong password
        """
        # Create user
        username = "testuser"
        password = "securepassword123"
        assert db.create_user(username, password), "User creation should succeed"
        
        # Verify correct password
        assert db.verify_user(username, password), "Should authenticate with correct password"
        
        # Verify wrong password is rejected
        assert not db.verify_user(username, "wrongpassword"), "Should reject wrong password"
        
        # Verify non-existent user is rejected
        assert not db.verify_user("nonexistent", password), "Should reject non-existent user"
    
    def test_note_creation_with_valid_user(self, db):
        """
        Test note creation for existing user with proper foreign key relationships.
        
        Purpose: Verify core functionality of note storage and data integrity.
        Prerequisites: User must exist before creating notes (foreign key constraint).
        Tests: Foreign key relationship between notes.user_id and users.id
        """
        # Setup: Create a user first
        db.create_user("testuser", "password123")
        user_id = db.get_user_id("testuser")
        assert user_id is not None, "User should exist for note creation"
        
        # Test: Create a note
        note_id = db.create_note(user_id, "Test Note", "This is test content")
        assert note_id is not None, "Note creation should return a note ID"
        assert isinstance(note_id, int), "Note ID should be an integer"
        assert note_id > 0, "Note ID should be positive"
    
    def test_note_title_uniqueness_per_user(self, db):
        """
        Test that note titles must be unique per user (business rule validation).
        
        Purpose: Verify business rule - users can't have duplicate note titles.
        Why: Allows users to reference notes by title unambiguously.
        Edge case: Different users CAN have same title (tested separately).
        """
        # Setup: Create user
        db.create_user("testuser", "password123")
        user_id = db.get_user_id("testuser")
        
        # First note should succeed
        note_id1 = db.create_note(user_id, "My Note", "Content 1")
        assert note_id1 is not None, "First note with title should succeed"
        
        # Duplicate title for same user should fail
        note_id2 = db.create_note(user_id, "My Note", "Content 2")
        assert note_id2 is None, "Duplicate note title for same user should fail"
    
    def test_note_retrieval_with_metadata(self, db):
        """
        Test note retrieval includes all expected metadata fields.
        
        Purpose: Verify that note retrieval returns complete data structure.
        Tests: All expected fields are present and have correct types.
        """
        # Setup
        db.create_user("testuser", "password123")
        user_id = db.get_user_id("testuser")
        
        # Create note
        title = "Test Note"
        content = "Test content for retrieval"
        note_id = db.create_note(user_id, title, content)
        assert note_id is not None, "Note creation should succeed"
        
        # Retrieve note
        note = db.get_note_by_title(user_id, title)
        assert note is not None, "Note should be retrievable"
        
        # Verify all expected fields are present
        expected_fields = ["id", "title", "content", "created_at", "modified_at", "reminder_date", "tags"]
        for field in expected_fields:
            assert field in note, f"Note should contain '{field}' field"
        
        # Verify field values
        assert note["id"] == note_id, "Note ID should match"
        assert note["title"] == title, "Title should match"
        assert note["content"] == content, "Content should match"
        assert note["tags"] == [], "Tags should default to empty list"
