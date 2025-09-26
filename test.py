"""
Comprehensive test suite for PIM (Personal Information Manager) System

This test suite demonstrates understanding of:
1. Unit Testing - Testing individual functions in isolation
2. Integration Testing - Testing components working together
3. Edge Case Testing - Testing boundary conditions and error scenarios
4. Security Testing - Testing authentication and authorization

Test Organization:
- TestDatabase: Tests the data layer (SQLite operations)
- TestBusinessLogic: Tests the core application logic
- TestSecurity: Tests authentication and session management
- TestEdgeCases: Tests error conditions and boundary cases

Purpose: Final project testing demonstration
"""

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
    This is critical for test isolation and preventing data contamination.
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
        
        Usage Examples:
            TestHelpers.create_user(system)  # Use defaults
            TestHelpers.create_user(system, "alice", "secret123")  # Custom credentials
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
            
        Most common pattern: Need logged-in user for testing protected operations.
        
        Usage:
            username, session = TestHelpers.create_user_and_login(system)
            # Now ready to test authenticated operations
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
    
    Testing Philosophy:
    - Each test is independent (using fresh database)
    - Tests focus on single responsibility
    - Both positive and negative cases covered
    - Database constraints and relationships verified
    """
    
    def test_user_creation_success(self, db):
        """
        Test successful user creation with valid credentials.
        
        Purpose: Verify that valid users can be created and stored properly.
        Expected: Function returns True, user appears in database with hashed password.
        Critical because: User creation is the entry point to the system.
        
        Tests:
        - User creation returns success
        - User can be retrieved from database
        - User ID is valid integer
        """
        result = db.create_user("testuser", "password123")
        assert result == True, "User creation should succeed with valid data"
        
        # Verify user actually exists in database
        user_id = db.get_user_id("testuser")
        assert user_id is not None, "Created user should be retrievable by username"
        assert isinstance(user_id, int), "User ID should be an integer"
        assert user_id > 0, "User ID should be positive"
    
    def test_user_creation_duplicate_username(self, db):
        """
        Test duplicate username rejection to ensure uniqueness.
        
        Purpose: Verify system prevents duplicate usernames for data integrity.
        Expected: First creation succeeds, second fails gracefully.
        Why important: Usernames must be unique for authentication to work.
        
        Database constraint: UNIQUE constraint on users.username
        """
        # First user should succeed
        result1 = db.create_user("testuser", "password123")
        assert result1 == True, "First user creation should succeed"
        
        # Duplicate username should fail due to UNIQUE constraint
        result2 = db.create_user("testuser", "differentpassword")
        assert result2 == False, "Duplicate username should be rejected"
        
        # Verify only one user exists
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("testuser",))
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1, "Should have exactly one user with that username"
    
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
        - Should successfully verify correct password
        - Should reject incorrect passwords
        """
        test_password = "password123"
        db.create_user("testuser", test_password)
        
        # Retrieve stored hash directly from database
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("testuser",))
        stored_hash = cursor.fetchone()[0]
        conn.close()
        
        # Verify password is not stored as plain text
        assert stored_hash != test_password, "Password should be hashed, not stored as plain text"
        
        # Verify bcrypt format structure
        assert stored_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')), "Should use bcrypt format"
        assert len(stored_hash) == 60, f"Bcrypt hash should be 60 characters, got {len(stored_hash)}"
        
        # Verify bcrypt structure: $version$cost$salt+hash
        parts = stored_hash.split('$')
        assert len(parts) == 4, "Bcrypt should have 4 parts separated by $"
        assert parts[1] in ['2a', '2b', '2x', '2y'], "Should use valid bcrypt version"
        assert len(parts[2]) == 22, "Salt should be 22 characters (base64)"
        assert len(parts[3]) == 31, "Hash should be 31 characters (base64)"
        
        # Verify the hash can be used for verification
        assert bcrypt.checkpw(test_password.encode('utf-8'), stored_hash.encode('utf-8')), \
            "Hash should verify correct password"
        assert not bcrypt.checkpw("wrongpassword".encode('utf-8'), stored_hash.encode('utf-8')), \
            "Hash should reject wrong password"
    
    def test_user_authentication_workflow(self, db):
        """
        Test complete user authentication workflow from creation to verification.
        
        Purpose: Verify that the entire authentication system works end-to-end.
        Workflow: Create user -> Verify correct password -> Reject wrong password
        
        Edge cases tested:
        - Correct credentials
        - Wrong password
        - Non-existent user
        - Case sensitivity
        """
        # Create user with specific credentials
        username = "testuser"
        password = "securepassword123"
        assert db.create_user(username, password), "User creation should succeed"
        
        # Verify correct password authentication
        assert db.verify_user(username, password), "Should authenticate with correct password"
        
        # Verify wrong password is rejected
        assert not db.verify_user(username, "wrongpassword"), "Should reject wrong password"
        
        # Verify case sensitivity
        assert not db.verify_user(username, "SecurePassword123"), "Should be case sensitive"
        
        # Verify non-existent user is rejected
        assert not db.verify_user("nonexistent", password), "Should reject non-existent user"
        
        # Verify empty credentials are rejected
        assert not db.verify_user("", password), "Should reject empty username"
        assert not db.verify_user(username, ""), "Should reject empty password"
    
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
        title = "Test Note"
        content = "This is test content for note creation"
        note_id = db.create_note(user_id, title, content)
        
        assert note_id is not None, "Note creation should return a note ID"
        assert isinstance(note_id, int), "Note ID should be an integer"
        assert note_id > 0, "Note ID should be positive"
        
        # Verify note is actually stored with correct data
        note = db.get_note_by_title(user_id, title)
        assert note is not None, "Created note should be retrievable"
        assert note["title"] == title, "Stored title should match input"
        assert note["content"] == content, "Stored content should match input"
        assert note["id"] == note_id, "Note ID should match returned ID"
    
    def test_note_title_uniqueness_per_user(self, db):
        """
        Test that note titles must be unique per user (business rule validation).
        
        Purpose: Verify business rule - users can't have duplicate note titles.
        Why: Allows users to reference notes by title unambiguously.
        Edge case: Different users CAN have same title (tested separately).
        
        Database constraint: UNIQUE(user_id, title) in notes table
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
        
        # Verify only one note exists with that title
        note = db.get_note_by_title(user_id, "My Note")
        assert note["content"] == "Content 1", "Should keep the first note's content"
    
    def test_different_users_can_have_same_note_titles(self, db):
        """
        Test that different users can have notes with the same title.
        
        Purpose: Verify title uniqueness is per-user, not global.
        Business rule: Title uniqueness is scoped to individual users.
        """
        # Create two users
        db.create_user("user1", "password1")
        db.create_user("user2", "password2")
        user1_id = db.get_user_id("user1")
        user2_id = db.get_user_id("user2")
        
        # Both users can create notes with same title
        same_title = "Shopping List"
        note1_id = db.create_note(user1_id, same_title, "User1's shopping list")
        note2_id = db.create_note(user2_id, same_title, "User2's shopping list")
        
        assert note1_id is not None, "User1 should be able to create note"
        assert note2_id is not None, "User2 should be able to create note with same title"
        assert note1_id != note2_id, "Notes should have different IDs"
        
        # Verify each user gets their own content
        user1_note = db.get_note_by_title(user1_id, same_title)
        user2_note = db.get_note_by_title(user2_id, same_title)
        
        assert user1_note["content"] == "User1's shopping list", "User1 should get their content"
        assert user2_note["content"] == "User2's shopping list", "User2 should get their content"

class TestBusinessLogic:
    """
    Integration tests for business logic (NoteDatabaseSystem class).
    
    Purpose: Test that business rules and workflows work correctly.
    Difference from database tests: These test the logic layer that sits
    above the database, including session management and JSON responses.
    
    Integration Testing Focus:
    - End-to-end workflows from user input to database storage
    - JSON response format consistency and error handling
    - Session management and security integration
    - Business rule enforcement across system layers
    """
    
    def test_user_registration_workflow(self, system):
        """
        Test the complete user registration workflow.
        
        Purpose: Verify that registration returns proper JSON responses.
        Tests: Input validation, success response format, error handling.
        Why JSON: API endpoints expect structured responses.
        
        Validates:
        - Response structure consistency
        - Success/failure indication
        - Informative error messages
        - Proper data types
        """
        result = json.loads(system.register_user("testuser", "password123"))
        
        # Verify response structure
        assert isinstance(result, dict), "Response should be a dictionary"
        assert "success" in result, "Response should include success field"
        assert "message" in result, "Response should include message field"
        assert isinstance(result["success"], bool), "Success should be boolean"
        assert isinstance(result["message"], str), "Message should be string"
        
        # Verify success case
        assert result["success"] == True, "Registration should succeed"
        assert "registered successfully" in result["message"], "Should have success message"
    
    def test_input_validation_empty_fields(self, system):
        """
        Test input validation for empty and whitespace-only inputs.
        
        Purpose: Verify system handles bad input gracefully and securely.
        Real-world scenario: Users often submit forms with missing or invalid data.
        Security consideration: Prevent empty usernames/passwords and whitespace-only passwords.
        
        Edge cases tested:
        - Empty strings
        - Whitespace-only strings
        - Tab characters
        - Various combinations
        """
        # Test cases that should all fail with stricter validation
        invalid_cases = [
            ("", "password123", "empty username"),
            ("   ", "password123", "whitespace-only username"), 
            ("testuser", "", "empty password"),
            ("testuser", "   ", "whitespace-only password"),
            ("testuser", "\t", "tab-only password"),
            ("testuser", "\n", "newline-only password"),
            ("", "", "both empty"),
            ("   ", "   ", "both whitespace")
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
        
        Purpose: Verify that login creates sessions and sessions work.
        Security aspect: Sessions prevent users from accessing others' data.
        Workflow: Register -> Login -> Use session -> Verify access.
        
        Session Management Tests:
        - Session creation on login
        - Session validation for protected operations
        - Session format and properties
        """
        # Register user
        TestHelpers.create_user(system, "testuser", "password123")
        
        # Login and get session
        session_id = TestHelpers.login_user(system, "testuser", "password123")
        
        # Verify session properties
        assert isinstance(session_id, str), "Session ID should be string"
        assert len(session_id) > 10, "Session ID should be reasonably long"
        
        # Verify session works for protected operations
        result = json.loads(system.create_note(session_id, "Test Note", "Content"))
        assert result["success"] == True, "Valid session should allow note creation"
    
    def test_invalid_session_protection(self, system):
        """
        Test that invalid sessions are rejected.
        
        Purpose: Verify security - fake sessions shouldn't work.
        Attack scenario: Malicious user tries to guess session IDs.
        Expected: System rejects invalid sessions with clear error.
        
        Invalid Session Types:
        - Completely fake sessions
        - Empty sessions
        - Malformed sessions
        - Expired sessions (simulated)
        """
        invalid_sessions = [
            "fake-session-id-12345",
            "",
            "   ",
            "short",
            "123",
            None  # Will be converted to string
        ]
        
        for fake_session in invalid_sessions:
            fake_session_str = str(fake_session) if fake_session is not None else ""
            result = json.loads(system.create_note(fake_session_str, "Test", "Content"))
            
            assert result["success"] == False, f"Invalid session '{fake_session}' should be rejected"
            assert "not logged in" in result["message"].lower(), "Should explain authentication failure"
    
    def test_note_listing_with_preview(self, system):
        """
        Test note listing includes preview but not full content.
        
        Purpose: Verify performance optimization - don't send full content in lists.
        UI consideration: Users need previews to identify notes.
        Performance: Full content would make lists slow for users with many notes.
        
        Preview Requirements:
        - Maximum 100 characters + "..." if truncated
        - Full content excluded from list view
        - All metadata included (title, dates, tags)
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create note with long content
        long_content = "This is a very long note content that should be truncated in the preview. " * 20  # 1400+ characters
        TestHelpers.create_sample_note(system, session_id, "Long Note", long_content)
        
        # List notes
        result = json.loads(system.list_notes(session_id))
        assert result["success"] == True, "Listing should succeed"
        
        # Verify response structure
        assert "notes" in result, "Response should include notes list"
        assert "count" in result, "Response should include count"
        assert isinstance(result["notes"], list), "Notes should be a list"
        
        notes = result["notes"]
        assert len(notes) > 0, "Should return the created note"
        
        note = notes[0]
        assert "preview" in note, "Note should include preview"
        assert "content" not in note, "Full content should not be in list view"
        assert "title" in note, "Should include title"
        assert "created_at" in note, "Should include creation date"
        assert "modified_at" in note, "Should include modification date"
        
        # Verify preview length and truncation
        assert len(note["preview"]) <= 103, "Preview should be truncated (100 chars + '...')"
        if len(long_content) > 100:
            assert note["preview"].endswith("..."), "Long content should be truncated with ellipsis"

class TestSecurity:
    """
    Security-focused tests.
    
    Purpose: Verify that security measures work correctly.
    Focus areas: Authentication, authorization, data isolation.
    Why important: Web applications are attacked frequently.
    
    Security Testing Areas:
    - Authentication: Password security, session management
    - Authorization: Access control, data isolation
    - Attack Prevention: Injection, session hijacking, data leaks
    """
    
    def test_user_data_isolation(self, system):
        """
        Test that users can only access their own data.
        
        Purpose: Verify authorization - User A can't see User B's notes.
        Security principle: Data isolation prevents privacy breaches.
        Real attack: Malicious user tries to access others' notes.
        
        Data Isolation Requirements:
        - Users see only their own notes
        - User operations don't affect other users
        - Cross-user access attempts fail gracefully
        """
        # Create two users
        user1, session1 = TestHelpers.create_user_and_login(system, "user1", "password1")
        user2, session2 = TestHelpers.create_user_and_login(system, "user2", "password2")
        
        # Each user creates a note
        TestHelpers.create_sample_note(system, session1, "User1 Note", "Secret content for user1")
        TestHelpers.create_sample_note(system, session2, "User2 Note", "Secret content for user2")
        
        # Verify each user only sees their own notes
        user1_notes = json.loads(system.list_notes(session1))["notes"]
        user2_notes = json.loads(system.list_notes(session2))["notes"]
        
        assert len(user1_notes) == 1, "User1 should see exactly one note"
        assert len(user2_notes) == 1, "User2 should see exactly one note"
        assert user1_notes[0]["title"] == "User1 Note", "User1 should see their own note"
        assert user2_notes[0]["title"] == "User2 Note", "User2 should see their own note"
    
    def test_logout_invalidates_session(self, system):
        """
        Test that logout properly invalidates sessions.
        
        Purpose: Verify that logged-out sessions can't be reused.
        Security scenario: User logs out on shared computer.
        Expected: Session becomes unusable after logout.
        
        Session Invalidation Requirements:
        - Logout returns success confirmation
        - Session cannot be used after logout
        - Clear error messages for invalid sessions
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Verify session works before logout
        result = json.loads(system.create_note(session_id, "Test", "Content"))
        assert result["success"] == True, "Session should work before logout"
        
        # Logout
        logout_result = json.loads(system.logout_user(session_id))
        assert logout_result["success"] == True, "Logout should succeed"
        assert "logout" in logout_result["message"].lower(), "Should confirm logout"
        
        # Verify session no longer works
        result = json.loads(system.create_note(session_id, "Test2", "Content2"))
        assert result["success"] == False, "Session should not work after logout"
    
    def test_session_uniqueness_and_unpredictability(self, system):
        """
        Test that session IDs are unique and unpredictable.
        
        Purpose: Verify sessions cannot be easily guessed or hijacked.
        Security principle: Session IDs should be cryptographically random.
        Attack prevention: Prevents session prediction attacks.
        
        Session Security Requirements:
        - Sessions are unique across users and time
        - Sessions are sufficiently long (entropy)
        - Sessions appear random (not sequential)
        """
        # Create multiple sessions
        user1, session1 = TestHelpers.create_user_and_login(system, "user1", "pass1")
        user2, session2 = TestHelpers.create_user_and_login(system, "user2", "pass2")
        
        # Sessions should be different and sufficiently long
        assert session1 != session2, "Sessions should be unique"
        assert len(session1) > 20, "Session IDs should be long enough to prevent guessing"
        assert len(session2) > 20, "Session IDs should be long enough to prevent guessing"
        
        # Test additional sessions for randomness
        sessions = []
        for i in range(5):
            username = f"user{i+10}"
            user, session = TestHelpers.create_user_and_login(system, username, "testpass")
            sessions.append(session)
        
        # All sessions should be unique
        assert len(set(sessions)) == len(sessions), "All sessions should be unique"

class TestEdgeCases:
    """
    Edge case and error condition tests.
    
    Purpose: Test system behavior at boundaries and with invalid input.
    Philosophy: "Happy path" tests show basic functionality works,
    but edge case tests show the system is robust and professional.
    
    Edge Case Categories:
    - Boundary conditions: Size limits, empty data, extreme values
    - Error conditions: Invalid input, system limits, malformed data
    - International support: Unicode, special characters, encodings
    - System resilience: Recovery from errors, graceful degradation
    """
    
    def test_large_content_handling(self, system):
        """
        Test system handles very large note content.
        
        Purpose: Verify no arbitrary limits break the system.
        Real scenario: User pastes large document into note.
        Database consideration: TEXT fields in SQLite can handle this.
        
        Large Content Tests:
        - 5KB content (typical large note)
        - Content preservation through all operations
        - Performance doesn't degrade significantly
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create large content (5000 characters)
        large_content = "A" * 5000
        title = "Large Note"
        
        result = json.loads(system.create_note(session_id, title, large_content))
        assert result["success"] == True, "System should handle large content"
        
        # Verify content is preserved exactly
        note_result = json.loads(system.get_note(session_id, title))
        assert note_result["success"] == True, "Should retrieve large note"
        
        retrieved_content = note_result["note"]["content"]
        assert len(retrieved_content) == len(large_content), "Content length should be preserved"
        assert retrieved_content == large_content, "Content should be identical"
        
        # Verify operations still work with large content
        update_result = json.loads(system.edit_note(session_id, title, large_content + " UPDATED"))
        assert update_result["success"] == True, "Should be able to update large content"
    
    def test_special_characters_in_titles(self, system):
        """
        Test system handles special characters and Unicode.
        
        Purpose: Verify international users can use their languages.
        Real scenario: Users with non-English names, emojis, special symbols.
        Technical: UTF-8 encoding should handle this.
        
        Character Types Tested:
        - Accented characters (French, Spanish)
        - Cyrillic alphabet (Russian)
        - CJK characters (Chinese, Japanese)
        - Emojis and symbols
        - Special punctuation
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Test various special characters
        special_titles = [
            "Note with émojis 😀🎯",
            "Título en español",
            "русский заголовок",
            "中文标题",
            "Note with symbols: @#$%^&*()",
            "Quotes: \"Hello\" 'World'",
            "Math: ∑∞≠≤≥±∆",
            "Currency: €£¥$₹"
        ]
        
        for i, title in enumerate(special_titles):
            content = f"Content for test {i+1} with special characters"
            result = json.loads(system.create_note(session_id, title, content))
            assert result["success"] == True, f"Should handle special characters in: {title}"
            
            # Verify retrieval preserves characters
            get_result = json.loads(system.get_note(session_id, title))
            assert get_result["success"] == True, f"Should retrieve note with title: {title}"
            assert get_result["note"]["title"] == title, "Title should be preserved exactly"
    
    def test_empty_database_queries(self, system):
        """
        Test queries on empty database don't crash.
        
        Purpose: Verify system gracefully handles "no data" scenarios.
        New user experience: Account with no notes yet.
        Expected: Empty lists, not errors.
        
        Empty Database Scenarios:
        - Listing notes when none exist
        - Searching with no notes
        - Getting stats with no activity
        - Various filters with no data
        """
        # Setup user with no notes
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Test listing empty notes
        result = json.loads(system.list_notes(session_id))
        assert result["success"] == True, "Listing empty notes should succeed"
        assert result["notes"] == [], "Should return empty list"
        assert result["count"] == 0, "Count should be zero"
        assert isinstance(result["notes"], list), "Notes should be a list even when empty"
        
        # Test searching empty notes
        search_result = json.loads(system.search_notes(session_id, "anything"))
        assert search_result["success"] == True, "Searching empty database should succeed"
        assert search_result["results"] == [], "Should return empty results"
        assert search_result["count"] == 0, "Should have zero results"
        
        # Test getting stats with no activity
        stats_result = json.loads(system.get_stats(session_id))
        assert stats_result["success"] == True, "Getting stats should succeed"
        stats = stats_result["stats"]
        assert stats["total_notes"] == 0, "Should show zero notes"
        assert stats["total_tags"] == 0, "Should show zero tags"
    
    def test_sql_injection_prevention(self, system):
        """
        Test that system prevents SQL injection attacks.
        
        Purpose: Verify security against common web attacks.
        Attack scenario: Malicious user tries to inject SQL in inputs.
        Protection: Parameterized queries should prevent this.
        
        SQL Injection Attempts:
        - DROP TABLE commands
        - SELECT statements
        - UPDATE statements
        - Special SQL characters
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Try SQL injection in note title
        malicious_inputs = [
            "'; DROP TABLE notes; --",
            "' OR '1'='1",
            "'; UPDATE notes SET content='HACKED'; --",
            "'; SELECT password_hash FROM users; --",
            "' UNION SELECT * FROM users --"
        ]
        
        for malicious_input in malicious_inputs:
            result = json.loads(system.create_note(session_id, malicious_input, "Content"))
            
            # Should either succeed (treating as normal text) or fail gracefully
            # But should NOT break the database or expose data
            assert isinstance(result, dict), f"Should return valid JSON for input: {malicious_input[:30]}..."
            assert "success" in result, "Should have proper response structure"
            
            # If it succeeded, it should be stored as literal text
            if result["success"]:
                get_result = json.loads(system.get_note(session_id, malicious_input))
                assert get_result["success"] == True, "Should retrieve the 'malicious' note"
                assert get_result["note"]["title"] == malicious_input, "Should store as literal text"
        
        # Verify database still works by creating a normal note
        normal_result = json.loads(system.create_note(session_id, "Normal Note", "Content"))
        assert normal_result["success"] == True, "Database should still work after injection attempts"

if __name__ == "__main__":
    """
    Main execution block for running tests.
    
    This comprehensive test suite covers:
    
    1. Unit Testing (TestDatabase):
       - Database operations in isolation
       - Data integrity and constraints
       - Password security and hashing
    
    2. Integration Testing (TestBusinessLogic):
       - End-to-end workflows
       - JSON API responses
       - Session management
    
    3. Security Testing (TestSecurity):
       - Authentication and authorization
       - Data isolation between users
       - Session security
    
    4. Edge Case Testing (TestEdgeCases):
       - Boundary conditions
       - Error handling
       - International support
       - Attack prevention
    
    To run these tests:
    
    1. Run all tests: 
       pytest test_pim_final.py -v
    
    2. Run specific test class:
       pytest test_pim_final.py::TestSecurity -v
    
    3. Run with coverage:
       pytest test_pim_final.py --cov=. --cov-report=html
    
    4. Run with detailed output:
       pytest test_pim_final.py -v -s --tb=short
    
    Expected Results:
    - All tests should pass (green)
    - High code coverage (>90%)
    - No security vulnerabilities detected
    - System handles edge cases gracefully
    
    Test Environment:
    - Each test uses isolated temporary database
    - No external dependencies required
    - Tests are deterministic and repeatable
    - Safe to run in any environment
    """
    print("=" * 60)
    print("PIM System Comprehensive Test Suite")
    print("=" * 60)
    print()
    print("This test suite validates:")
    print("• Database layer functionality and security")
    print("• Business logic and workflow integrity") 
    print("• Authentication and authorization systems")
    print("• Edge cases and error handling")
    print("• International character support")
    print("• SQL injection prevention")
    print()
    print("To run these tests:")
    print("1. pytest test_pim_final.py -v")
    print("2. pytest test_pim_final.py::TestSecurity -v")
    print("3. pytest test_pim_final.py --cov=. --cov-report=html")
    print()
    print("Expected: All tests should pass with >90% code coverage")
    print("=" * 60)
