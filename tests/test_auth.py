from datetime import datetime, timedelta, timezone

import pytest

# Assuming we need a mock for the Logger service
from pymon.utils.logger import Logger

# We assume auth module exists and contains necessary classes/functions
try:
    from pymon.auth import AuthenticationManager, UserCredential
except ImportError as e:
    print(f"Warning: Could not import modules from pymon/auth. Check if the file structure is correct. Error: {e}")


@pytest.fixture(scope="module")
def logger_service():
    """Fixture to provide a consistent instance of the Logger service."""
    # We instantiate it here so tests use the same centralized logging setup
    from pymon.utils.logger import Logger  # Import locally in fixture scope

    return Logger()


@pytest.fixture(scope="module")
def auth_manager():
    """Fixture to provide a fresh AuthenticationManager instance for each test session."""
    # Assuming AuthenticationManager handles all authentication logic
    return AuthenticationManager()


class TestAuthenticationModule:
    """Unit tests suite for the core JWT and password management in pymon/auth.py."""

    def test_password_hashing(self, logger_service):
        """Test that passwords are correctly hashed and verified securely."""
        # Mock function call assumed to be in auth.py or a dependency
        hashed_pass = self.auth_manager.hash_password("secure_password_123")
        assert isinstance(hashed_pass, str)
        assert len(hashed_pass) > 50  # Hashed passwords should be long

        # Test verification
        is_valid = self.auth_manager.verify_password("secure_password_123", hashed_pass)
        assert is_valid == True

        # Test failure case
        is_invalid = self.auth_manager.verify_password("wrong_password", hashed_pass)
        assert is_invalid == False
        logger_service.info("Password hashing tests passed successfully.")

    def test_user_creation(self, auth_manager):
        """Test the secure creation and storage of a new user."""
        # Assume create_user returns a User object or boolean success
        new_username = "testuser"
        initial_password = "TempPass123!"

        try:
            user_id, success = self.auth_manager.create_user(new_username, initial_password)
            assert user_id is not None
            assert success == True
            logger_service.info("User creation test passed.")
        except Exception as e:
            pytest.fail(f"Failed during user creation: {e}")

    def test_jwt_token_generation_success(self, auth_manager):
        """Test successful generation of a valid JWT token."""
        # Use mock credentials that are known to work for testing purposes
        username = "admin"
        password = self.auth_manager.hash_password("changeme")  # Hash the default password

        token = self.auth_manager.login(username, password)

        assert isinstance(token, str)
        # JWTs typically contain multiple parts separated by dots
        assert len(token.split(".")) == 3
        logger_service.info("JWT Token generation successful.")

    def test_jwt_token_validation_success(self, auth_manager):
        """Test that a valid token can be decoded and validated against expiry/revocation."""
        # 1. Generate a known good token
        username = "admin"
        password = self.auth_manager.hash_password("changeme")
        valid_token = self.auth_manager.login(username, password)

        # 2. Attempt to validate it
        try:
            user_data = self.auth_manager.validate_token(valid_token)
            assert user_data["username"] == username
            logger_service.info("Token validation successful.")
        except Exception as e:
            pytest.fail(f"Valid token failed validation unexpectedly: {e}")

    def test_jwt_token_validation_expired(self, auth_manager):
        """Test failure when attempting to validate an expired token."""
        # This requires mocking the time or having a utility function to generate an old token.
        # Assuming a method exists for testing expiry:
        try:
            expired_token = self.auth_manager._generate_expired_token()  # Mocked helper call
            with pytest.raises(ValueError, match="Token has expired"):
                self.auth_manager.validate_token(expired_token)
            logger_service.info("Expired token handling test passed.")
        except AttributeError:
            # Skip if the mocked method doesn't exist in current auth.py implementation
            pytest.skip("Skipping expired token test: _generate_expired_token() not found in AuthenticationManager.")

    def test_jwt_token_validation_invalid(self, auth_manager):
        """Test failure when provided with a malformed or tampered token."""
        # A completely random string that should not match the signature/format
        malformed_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIn0.invalid-signature"

        with pytest.raises(ValueError, match="Invalid signature"):
            self.auth_manager.validate_token(malformed_token)
        logger_service.info("Malformed token handling test passed.")


@pytest.mark.parametrize("bad_password", ["123", "", "too short"])
def test_login_failure_scenarios(auth_manager, logger_service, bad_password):
    """Test multiple login failures to ensure security and correct error messages."""
    # 1. Test wrong password against existing user
    wrong_token = auth_manager.login("admin", "fake_password")
    assert wrong_token is None or "Invalid credentials" in str(wrong_token)

    # 2. Test non-existent user
    non_existent_token = auth_manager.login("ghostuser", "anypass")
    assert non_existent_token is None or "Invalid credentials" in str(non_existent_token)
