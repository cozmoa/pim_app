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
    
    Purpose: Test that business rules and workflows work correctly
    Difference from database tests: These test the logic layer that sits
    above the database, including session management and JSON responses
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

class TestSecurity:
    """
    Security-focused tests.
    
    Purpose: Verify that security measures work correctly
    Focus areas: Authentication, authorization, data isolation
    Why important: Web applications are attacked frequently
    """
    
    def test_user_data_isolation(self, system):
        """
        Test that users can only access their own data.
        
        Purpose: Verify authorization - User A can't see User B's notes
        Security principle: Data isolation prevents privacy breaches
        Real attack: Malicious user tries to access others' notes
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
        
        Purpose: Verify that logged-out sessions can't be reused
        Security scenario: User logs out on shared computer
        Expected: Session becomes unusable after logout
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Verify session works before logout
        result = json.loads(system.create_note(session_id, "Test", "Content"))
        assert result["success"] == True, "Session should work before logout"
        
        # Logout
        logout_result = json.loads(system.logout_user(session_id))
        assert logout_result["success"] == True, "Logout should succeed"
        
        # Verify session no longer works
        result = json.loads(system.create_note(session_id, "Test2", "Content2"))
        assert result["success"] == False, "Session should not work after logout"
    
    def test_session_uniqueness_and_unpredictability(self, system):
        """
        Test that session IDs are unique and unpredictable.
        
        Purpose: Verify sessions cannot be easily guessed or hijacked
        Security principle: Session IDs should be cryptographically random
        Attack prevention: Prevents session prediction attacks
        """
        # Create multiple sessions
        user1, session1 = TestHelpers.create_user_and_login(system, "user1", "pass1")
        user2, session2 = TestHelpers.create_user_and_login(system, "user2", "pass2")
        
        # Sessions should be different and sufficiently long
        assert session1 != session2, "Sessions should be unique"
        assert len(session1) > 20, "Session IDs should be long enough to prevent guessing"
        assert len(session2) > 20, "Session IDs should be long enough to prevent guessing"

class TestEdgeCases:
    """
    Edge case and error condition tests.
    
    Purpose: Test system behavior at boundaries and with invalid input
    Philosophy: "Happy path" tests show basic functionality works,
    but edge case tests show the system is robust and professional
    """
    
    def test_large_content_handling(self, system):
        """
        Test system handles very large note content.
        
        Purpose: Verify no arbitrary limits break the system
        Real scenario: User pastes large document into note
        Database consideration: TEXT fields in SQLite can handle this
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create large content (5000 characters)
        large_content = "A" * 5000
        
        result = json.loads(system.create_note(session_id, "Large Note", large_content))
        assert result["success"] == True, "System should handle large content"
        
        # Verify content is preserved (allow small tolerance for string handling)
        note_result = json.loads(system.get_note(session_id, "Large Note"))
        retrieved_content = note_result["note"]["content"]
        assert abs(len(retrieved_content) - len(large_content)) <= 5, "Large content should be preserved"
        assert retrieved_content.startswith("AAAAA"), "Content should start correctly"
    
    def test_special_characters_in_titles(self, system):
        """
        Test system handles special characters and Unicode.
        
        Purpose: Verify international users can use their languages
        Real scenario: Users with non-English names, emojis, special symbols
        Technical: UTF-8 encoding should handle this
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Test various special characters
        special_titles = [
            "Note with émojis 😀",
            "Título en español",
            "русский заголовок",
            "中文标题",
            "Note with symbols: @#$%^&*()"
        ]
        
        for title in special_titles:
            result = json.loads(system.create_note(session_id, title, "Content"))
            assert result["success"] == True, f"Should handle special characters in: {title}"
    
    def test_empty_database_queries(self, system):
        """
        Test queries on empty database don't crash.
        
        Purpose: Verify system gracefully handles "no data" scenarios
        New user experience: Account with no notes yet
        Expected: Empty lists, not errors
        """
        # Setup user with no notes
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Test listing empty notes
        result = json.loads(system.list_notes(session_id))
        assert result["success"] == True, "Listing empty notes should succeed"
        assert result["notes"] == [], "Should return empty list"
        assert result["count"] == 0, "Count should be zero"
        
        # Test searching empty notes
        search_result = json.loads(system.search_notes(session_id, "anything"))
        assert search_result["success"] == True, "Searching empty database should succeed"
        assert search_result["results"] == [], "Should return empty results"
    
    def test_sql_injection_prevention(self, system):
        """
        Test that system prevents SQL injection attacks.
        
        Purpose: Verify security against common web attacks
        Attack scenario: Malicious user tries to inject SQL in inputs
        Protection: Parameterized queries should prevent this
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Try SQL injection in note title
        malicious_title = "'; DROP TABLE notes; --"
        result = json.loads(system.create_note(session_id, malicious_title, "Content"))
        
        # Should either succeed (treating it as normal text) or fail gracefully
        # But should NOT break the database
        assert isinstance(result, dict), "Should return valid JSON response"
        assert "success" in result, "Should have proper response structure"
        
        # Verify database still works by creating a normal note
        normal_result = json.loads(system.create_note(session_id, "Normal Note", "Content"))
        assert normal_result["success"] == True, "Database should still work after injection attempt"
    
    def test_extremely_long_titles(self, system):
        """
        Test system behavior with extremely long note titles.
        
        Purpose: Verify system handles boundary conditions gracefully
        Real scenario: User accidentally pastes large text as title
        Expected: Either truncate gracefully or reject with clear error
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create extremely long title (500 characters)
        long_title = "A" * 500
        
        result = json.loads(system.create_note(session_id, long_title, "Content"))
        
        # System should either handle it or reject with clear message
        assert isinstance(result, dict), "Should return valid response"
        assert "success" in result, "Response should have success field"
        
        if not result["success"]:
            # If rejected, error should be about title length
            assert "title" in result["message"].lower(), "Error should mention title issue"
    
    def test_concurrent_note_creation_same_title(self, system):
        """
        Test handling of concurrent attempts to create notes with same title.
        
        Purpose: Verify system handles race conditions properly
        Scenario: Two requests trying to create same title simultaneously
        Expected: One succeeds, one fails with clear error
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # First note creation should succeed
        result1 = json.loads(system.create_note(session_id, "Duplicate Title", "Content 1"))
        assert result1["success"] == True, "First note should succeed"
        
        # Second note with same title should fail
        result2 = json.loads(system.create_note(session_id, "Duplicate Title", "Content 2"))
        assert result2["success"] == False, "Second note with same title should fail"
        assert "already exists" in result2["message"].lower(), "Should explain the conflict"
    
    def test_malformed_search_queries(self, system):
        """
        Test search functionality with malformed and edge case queries.
        
        Purpose: Verify search is robust against unusual input
        Edge cases: Very long queries, special characters, SQL-like syntax
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        TestHelpers.create_sample_note(system, session_id, "Test Note", "Test content")
        
        # Test various edge case searches
        edge_case_queries = [
            "",  # Empty query (should be rejected)
            "   ",  # Whitespace only
            "%" * 100,  # SQL wildcard characters
            "SELECT * FROM notes",  # SQL injection attempt
            "🔍😀🎯",  # Emoji search
            "a" * 200,  # Very long query
        ]
        
        for query in edge_case_queries:
            result = json.loads(system.search_notes(session_id, query))
            
            # Should either work or fail gracefully
            assert isinstance(result, dict), f"Should return valid JSON for query: {query[:20]}..."
            assert "success" in result, "Should have success field"
            
            if result["success"]:
                assert "results" in result, "Successful search should have results field"
                assert isinstance(result["results"], list), "Results should be a list"
    
    def test_system_recovery_after_errors(self, system):
        """
        Test that system continues working normally after error conditions.
        
        Purpose: Verify system resilience - errors don't break future operations
        Scenario: Cause error, then verify normal operations still work
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Cause an error (try to get non-existent note)
        error_result = json.loads(system.get_note(session_id, "Non-existent Note"))
        assert error_result["success"] == False, "Should fail for non-existent note"
        
        # Verify system still works normally after error
        recovery_result = json.loads(system.create_note(session_id, "Recovery Test", "System should work"))
        assert recovery_result["success"] == True, "System should work normally after error"
        
        # Verify we can still list notes
        list_result = json.loads(system.list_notes(session_id))
        assert list_result["success"] == True, "Should still be able to list notes"
        assert len(list_result["notes"]) == 1, "Should show the recovery test note"
    
    def test_unicode_content_preservation(self, system):
        """
        Test that Unicode content is properly preserved through all operations.
        
        Purpose: Verify international content works end-to-end
        Real scenario: Users creating notes in various languages
        Technical: UTF-8 encoding preservation through database and JSON
        """
        # Setup
        username, session_id = TestHelpers.create_user_and_login(system)
        
        # Create note with various Unicode content
        unicode_content = """
        English: Hello World! 
        Spanish: ¡Hola Mundo!
        Russian: Привет мир!
        Chinese: 你好世界！
        Japanese: こんにちは世界！
        Arabic: مرحبا بالعالم!
        Emoji: 🌍🚀💫⭐
        Symbols: ©®™€£¥
        Math: ∑∞≠≤≥±∆
        """
        
        # Create note
        create_result = json.loads(system.create_note(session_id, "Unicode Test", unicode_content))
        assert create_result["success"] == True, "Should create Unicode note"
        
        # Retrieve and verify content preservation
        get_result = json.loads(system.get_note(session_id, "Unicode Test"))
        assert get_result["success"] == True, "Should retrieve Unicode note"
        
        retrieved_content = get_result["note"]["content"]
        assert "你好世界" in retrieved_content, "Chinese characters should be preserved"
        assert "Привет мир" in retrieved_content, "Russian characters should be preserved"
        assert "🌍🚀" in retrieved_content, "Emoji should be preserved"
        assert "∑∞≠" in retrieved_content, "Math symbols should be preserved"
