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
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture
def db(temp_db_path):
    """Fixture: Database instance with clean temporary database"""
    return NoteDatabase(temp_db_path)

@pytest.fixture  
def system(temp_db_path):
    """Fixture: Business logic system with clean temporary database"""
    return NoteDatabaseSystem(temp_db_path)

class TestHelpers:
    """
    Helper functions for common test operations.
    
    Purpose: Eliminate code duplication across test methods
    Pattern: Create once, use everywhere
    """
    
    @staticmethod
    def create_user(system, username="testuser", password="password123"):
        """
        Helper: Create and register a user.
        
        Returns: Username used (allows easy customization)
        Usage: TestHelpers.create_user(system) or TestHelpers.create_user(system, "custom_user")
        """
        result = json.loads(system.register_user(username, password))
        assert result["success"], f"User creation failed: {result['message']}"
        return username
    
    @staticmethod
    def login_user(system, username="testuser", password="password123"):
        """
        Helper: Login user and return session ID.
        
        Returns: Session ID string
        Combines: Login + extract session + assert success
        """
        result = json.loads(system.login_user(username, password))
        assert result["success"], f"Login failed: {result['message']}"
        return result["session_id"]
    
    @staticmethod
    def create_user_and_login(system, username="testuser", password="password123"):
        """
        Helper: Complete user setup (register + login).
        
        Returns: Tuple of (username, session_id)
        Most common pattern: Need logged-in user for testing
        """
        TestHelpers.create_user(system, username, password)
        session_id = TestHelpers.login_user(system, username, password)
        return username, session_id
    
    @staticmethod
    def create_sample_note(system, session_id, title="Sample Note", content="Sample content"):
        """
        Helper: Create a note for testing.
        
        Returns: Note title (for easy reference in tests)
        Usage: For tests that need existing notes
        """
        result = json.loads(system.create_note(session_id, title, content))
        assert result["success"], f"Note creation failed: {result['message']}"
        return title

class TestDatabase:
    """
    Unit tests for the database layer (NoteDatabase class).
    
    Purpose: Verify that SQL operations work correctly in isolation
    Why these tests matter: Database is the foundation - if data operations
    fail, everything fails. These tests ensure data integrity.
    """
    
    def test_user_creation_success(self, db):
        """
        Test successful user creation.
        
        Purpose: Verify that valid users can be created
        Expected: Function returns True, user appears in database
        Critical because: User creation is the entry point to the system
        """
        result = db.create_user("testuser", "password123")
        assert result == True, "User creation should succeed with valid data"
        
        # Verify user actually exists in database
        user_id = db.get_user_id("testuser")
        assert user_id is not None, "Created user should be retrievable"
    
    def test_user_creation_duplicate_username(self, db):
        """
        Test duplicate username rejection.
        
        Purpose: Verify system prevents duplicate usernames
        Expected: First creation succeeds, second fails
        Why important: Usernames must be unique for authentication to work
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
        
        Purpose: Verify security implementation - passwords must be properly hashed
        Method: Create user, verify password hash uses bcrypt format
        Security principle: Never store plain text passwords
        Bcrypt format: $2b$12$... (algorithm + cost + salt + hash)
        """
        db.create_user("testuser", "password123")
        
        # Check that stored password is hashed using bcrypt
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("testuser",))
        stored_hash = cursor.fetchone()[0]
        conn.close()
        
        assert stored_hash != "password123", "Password should be hashed, not stored as plain text"
        assert stored_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')), "Should use bcrypt format"
        assert len(stored_hash) == 60, f"Bcrypt hash should be 60 characters, got {len(stored_hash)}"
        
        # Verify bcrypt structure: $version$cost$salt+hash
        parts = stored_hash.split('$')
        assert len(parts) == 4, "Bcrypt should have 4 parts separated by $"
        assert parts[1] in ['2a', '2b', '2x', '2y'], "Should use valid bcrypt version"
    
    def test_note_creation_with_valid_user(self, db):
        """
        Test note creation for existing user.
        
        Purpose: Verify core functionality of note storage
        Prerequisites: User must exist before creating notes
        Tests foreign key relationship: notes.user_id -> users.id
        """
        # Setup: Create a user first
        db.create_user("testuser", "password123")
        user_id = db.get_user_id("testuser")
        
        # Test: Create a note
        note_id = db.create_note(user_id, "Test Note", "This is test content")
        assert note_id is not None, "Note creation should return a note ID"
        assert isinstance(note_id, int), "Note ID should be an integer"
    
    def test_note_title_uniqueness_per_user(self, db):
        """
        Test that note titles must be unique per user.
        
        Purpose: Verify business rule - users can't have duplicate note titles
        Why: Allows users to reference notes by title unambiguously
        Edge case: Different users CAN have same title (tested separately)
        """
        # Setup
        db.create_user("testuser", "password123")
        user_id = db.get_user_id("testuser")
        
        # First note should succeed
        note_id1 = db.create_note(user_id, "My Note", "Content 1")
        assert note_id1 is not None, "First note with title should succeed"
        
        # Duplicate title for same user should fail
        note_id2 = db.create_note(user_id, "My Note", "Content 2")
        assert note_id2 is None, "Duplicate note title for same user should fail"

class TestBusinessLogic:
    """
    Integration tests for business logic (NoteDatabaseSystem class).
    
    Purpose: Test that business rules and workflows work correctly.
    Difference from database tests: These test the logic layer that sits
    above the database, including session management and JSON responses.
    """
    
    def test_user_registration_workflow(self, system):
        """
        Test the complete user registration workflow.
        
        Purpose: Verify that registration returns proper JSON responses
        Tests: Input validation, success response format, error handling
        Why JSON: API endpoints expect structured responses
        """
        result = json.loads(system.register_user("testuser", "password123"))
        
        # Verify response structure
        assert "success" in result, "Response should include success field"
        assert "message" in result, "Response should include message field"
        assert result["success"] == True, "Registration should succeed"
        assert "registered successfully" in result["message"], "Should have success message"
    
    def test_input_validation_empty_fields(self, system):
        """
        Test input validation for empty and whitespace-only inputs.
        
        Purpose: Verify system handles bad input gracefully and securely
        Real-world scenario: Users often submit forms with missing or invalid data
        Security consideration: Prevent empty usernames/passwords and whitespace-only passwords
        """
        # Test cases that should all fail with stricter validation
        invalid_cases = [
            ("", "password123", "empty username"),
            ("   ", "password123", "whitespace-only username"), 
            ("testuser", "", "empty password"),
            ("testuser", "   ", "whitespace-only password"),
            ("testuser", "\t", "tab-only password")
        ]
        
        for username, password, description in invalid_cases:
            result = json.loads(system.register_user(username, password))
            assert result["success"] == False, f"Should reject {description}"
            
            # Verify error message is informative
            message = result["message"].lower()
            assert any(word in message for word in ["required", "empty", "whitespace"]), \
                f"Error message should explain the problem: {result['message']}"
    
    def test_session_management_workflow(self, system):
        """
        Test session creation and validation.
        
        Purpose: Verify that login creates sessions and sessions work
        Security aspect: Sessions prevent users from accessing others' data
        Workflow: Register -> Login -> Use session -> Verify access
        """
        # Register user
        TestHelpers.create_user(system, "testuser", "password123")
        
        # Login and get session
        session_id = TestHelpers.login_user(system, "testuser", "password123")
        
        # Verify session works for protected operations
        result = json.loads(system.create_note(session_id, "Test Note", "Content"))
        assert result["success"] == True, "Valid session should allow note creation"
    
    def test_invalid_session_protection(self, system):
        """
        Test that invalid sessions are rejected.
        
        Purpose: Verify security - fake sessions shouldn't work
        Attack scenario: Malicious user tries to guess session IDs
        Expected: System rejects invalid sessions with clear error
        """
        fake_session = "fake-session-id-12345"
        result = json.loads(system.create_note(fake_session, "Test", "Content"))
        
        assert result["success"] == False, "Invalid session should be rejected"
        assert "not logged in" in result["message"].lower(), "Should explain authentication failure"
    
    def test_note_listing_with_preview(self, system):
        """
        Test note listing includes preview but not full content.
        
        Purpose: Verify performance optimization - don't send full content in lists
        UI consideration: Users need previews to identify notes
        Performance: Full content would make lists slow for users with many notes
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create note with long content
        long_content = "This is a very long note content. " * 20  # 700+ characters
        TestHelpers.create_sample_note(system, session_id, "Long Note", long_content)
        
        # List notes
        result = json.loads(system.list_notes(session_id))
        assert result["success"] == True, "Listing should succeed"
        
        notes = result["notes"]
        assert len(notes) > 0, "Should return the created note"
        
        note = notes[0]
        assert "preview" in note, "Note should include preview"
        assert "content" not in note, "Full content should not be in list view"
        assert len(note["preview"]) <= 103, "Preview should be truncated (100 chars + '...')"
    
    def test_note_creation_and_retrieval_workflow(self, system):
        """
        Test complete note workflow from creation to retrieval.
        
        Purpose: Verify end-to-end note functionality works correctly
        Workflow: Create user -> Login -> Create note -> Retrieve note -> Verify data
        """
        # Setup user
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create note
        title = "Integration Test Note"
        content = "This is content for integration testing workflow."
        create_result = json.loads(system.create_note(session_id, title, content))
        
        assert create_result["success"], f"Note creation failed: {create_result['message']}"
        assert "note_id" in create_result, "Should return note ID"
        
        # Retrieve note
        get_result = json.loads(system.get_note(session_id, title))
        assert get_result["success"], f"Note retrieval failed: {get_result['message']}"
        
        # Verify note data
        note = get_result["note"]
        assert note["title"] == title, "Retrieved title should match"
        assert note["content"] == content, "Retrieved content should match"
        assert "created_at" in note, "Should include creation timestamp"
        assert "modified_at" in note, "Should include modification timestamp"
    
    def test_note_update_workflow(self, system):
        """
        Test note content update workflow.
        
        Purpose: Verify note editing functionality works correctly
        Workflow: Create note -> Update content -> Verify changes -> Check timestamp
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        title = TestHelpers.create_sample_note(system, session_id, "Update Test", "Original content")
        
        # Update note
        new_content = "Updated content with new information"
        update_result = json.loads(system.edit_note(session_id, title, new_content))
        assert update_result["success"], f"Note update failed: {update_result['message']}"
        
        # Verify update
        get_result = json.loads(system.get_note(session_id, title))
        updated_note = get_result["note"]
        assert updated_note["content"] == new_content, "Content should be updated"
        # Note: In real implementation, modified_at should be later than created_at
    
    def test_note_deletion_workflow(self, system):
        """
        Test note deletion workflow.
        
        Purpose: Verify note deletion works correctly and note becomes inaccessible
        Workflow: Create note -> Verify exists -> Delete -> Verify gone
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        title = TestHelpers.create_sample_note(system, session_id)
        
        # Verify note exists
        get_result = json.loads(system.get_note(session_id, title))
        assert get_result["success"], "Note should exist before deletion"
        
        # Delete note
        delete_result = json.loads(system.delete_note(session_id, title))
        assert delete_result["success"], f"Deletion failed: {delete_result['message']}"
        
        # Verify note is gone
        get_after_delete = json.loads(system.get_note(session_id, title))
        assert not get_after_delete["success"], "Note should not exist after deletion"
    
    def test_search_functionality_workflow(self, system):
        """
        Test search functionality across note titles and content.
        
        Purpose: Verify search works correctly and returns relevant results
        Workflow: Create multiple notes -> Search -> Verify results
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create test notes with different content
        TestHelpers.create_sample_note(system, session_id, "Python Tutorial", "Learn Python programming")
        TestHelpers.create_sample_note(system, session_id, "JavaScript Guide", "Web development with JS")
        TestHelpers.create_sample_note(system, session_id, "Database Design", "SQL and Python integration")
        
        # Search for "Python" should find 2 notes
        search_result = json.loads(system.search_notes(session_id, "Python"))
        assert search_result["success"], "Search should succeed"
        assert search_result["count"] == 2, "Should find 2 notes containing 'Python'"
        
        # Verify search results have previews
        for result in search_result["results"]:
            assert "preview" in result, "Search results should include previews"
            assert "content" not in result, "Search results should not include full content"
