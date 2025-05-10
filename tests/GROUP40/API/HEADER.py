# Create admin user data for the test token
from datetime import timedelta

from core.security import create_access_token

admin_test_data = {
    "sub": "johnsmith",
    "user_id": "0beefc90-5b7d-4e56-9df9-251b65672c2f",
    "role": "admin",  # Make sure this matches exactly what your middleware expects
    "username": "johnsmith"
}

# Create access token with long expiry for tests
BEARER_TOKEN = create_access_token(
    data=admin_test_data,
    expires_delta=timedelta(days=1)  # Set token to expire in 1 day for testing
)
