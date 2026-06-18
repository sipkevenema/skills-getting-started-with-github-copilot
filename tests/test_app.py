"""
Tests for the High School Management System API (FastAPI)

Uses pytest framework with AAA (Arrange-Act-Assert) pattern for clarity.
Each test is isolated with fixtures that provide fresh mock data.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """
    Fixture: Provides a TestClient for making HTTP requests to the app.
    Uses FastAPI's built-in TestClient which doesn't require the server running.
    """
    return TestClient(app)


@pytest.fixture
def mock_activities(monkeypatch):
    """
    Fixture: Provides clean, isolated mock activities data for each test.
    Uses monkeypatch to replace the app's global activities dictionary.
    This ensures tests don't interfere with each other's state.
    """
    mock_data = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 3,  # Smaller limit for testing capacity
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 2,  # Very small for testing full activity
            "participants": ["emma@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": []
        }
    }
    # Replace app's global activities with mock data
    import app as app_module
    monkeypatch.setattr(app_module, "activities", mock_data)
    return mock_data


# ============================================================================
# GET /activities Tests
# ============================================================================

class TestGetActivities:
    """Tests for the GET /activities endpoint (retrieve all activities)"""
    
    def test_get_activities_happy_path(self, client, mock_activities):
        """
        AAA Test: GET /activities returns all activities with correct structure
        
        Arrange: Client and mock activities with known state
        Act: Send GET request to /activities
        Assert: Verify 200 status and response contains all 3 mock activities
                with expected fields (description, schedule, max_participants, participants)
        """
        # Arrange
        expected_activity_count = 3
        
        # Act
        response = client.get("/activities")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == expected_activity_count
        
        # Verify each activity has required fields
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
        
        # Verify specific activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_returns_current_participants(self, client, mock_activities):
        """
        AAA Test: GET /activities returns current participant list for each activity
        
        Arrange: Mock activities with known participants
        Act: Send GET request to /activities
        Assert: Verify participant lists match expected state
        """
        # Arrange
        expected_chess_participants = ["michael@mergington.edu", "daniel@mergington.edu"]
        expected_prog_participants = ["emma@mergington.edu"]
        
        # Act
        response = client.get("/activities")
        
        # Assert
        data = response.json()
        assert data["Chess Club"]["participants"] == expected_chess_participants
        assert data["Programming Class"]["participants"] == expected_prog_participants
        assert data["Gym Class"]["participants"] == []


# ============================================================================
# POST /activities/{activity_name}/signup Tests
# ============================================================================

class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_happy_path(self, client, mock_activities):
        """
        AAA Test: Student successfully signs up for an activity
        
        Arrange: Empty activity (Gym Class) with no participants
        Act: Send POST request to signup new student
        Assert: Verify 200 status, response message, and participant was added
        """
        # Arrange
        activity_name = "Gym Class"
        new_email = "john@mergington.edu"
        initial_count = len(mock_activities[activity_name]["participants"])
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json() == {"message": f"Signed up {new_email} for {activity_name}"}
        assert new_email in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == initial_count + 1
    
    def test_signup_multiple_different_students(self, client, mock_activities):
        """
        AAA Test: Multiple different students can sign up to same activity
        
        Arrange: Empty activity with room for 2+ students
        Act: Sign up two different students
        Assert: Both students added successfully, count increased appropriately
        """
        # Arrange
        activity_name = "Gym Class"
        student1 = "alice@mergington.edu"
        student2 = "bob@mergington.edu"
        
        # Act
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": student1}
        )
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": student2}
        )
        
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert student1 in mock_activities[activity_name]["participants"]
        assert student2 in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == 2
    
    def test_signup_activity_not_found(self, client, mock_activities):
        """
        AAA Test: Signup fails with 404 when activity doesn't exist
        
        Arrange: No activity named "Nonexistent Club"
        Act: Try to signup to nonexistent activity
        Assert: Verify 404 status and error message
        """
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_email(self, client, mock_activities):
        """
        AAA Test: Signup fails with 400 when student already signed up
        
        Arrange: Chess Club has michael@mergington.edu as existing participant
        Act: Try to signup same email again
        Assert: Verify 400 status, error message, and participant count unchanged
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already in Chess Club
        initial_count = len(mock_activities[activity_name]["participants"])
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
        assert len(mock_activities[activity_name]["participants"]) == initial_count
    
    def test_signup_beyond_capacity(self, client, mock_activities):
        """
        AAA Test: App allows signup even when exceeding max_participants
        
        Note: The current app implementation doesn't enforce capacity limits.
        This test documents the current behavior where participants can exceed max_participants.
        
        Arrange: Programming Class has max_participants=2 with 1 current participant
        Act: Sign up two more students (exceeding max capacity)
        Assert: Both signups succeed, demonstrating no capacity enforcement
        """
        # Arrange
        activity_name = "Programming Class"
        new_email1 = "student1@mergington.edu"
        new_email2 = "student2@mergington.edu"
        max_participants = mock_activities[activity_name]["max_participants"]
        initial_count = len(mock_activities[activity_name]["participants"])
        
        # Act - First signup
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email1}
        )
        
        # Act - Second signup (exceeds max_participants)
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email2}
        )
        
        # Assert - Both succeed (no capacity enforcement)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert new_email1 in mock_activities[activity_name]["participants"]
        assert new_email2 in mock_activities[activity_name]["participants"]
        # Activity has exceeded max capacity (3 participants > 2 max_participants)
        assert len(mock_activities[activity_name]["participants"]) > max_participants


# ============================================================================
# DELETE /activities/{activity_name}/participants/{email} Tests
# ============================================================================

class TestRemoveParticipant:
    """Tests for the DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_happy_path(self, client, mock_activities):
        """
        AAA Test: Successfully remove a participant from an activity
        
        Arrange: Chess Club has michael@mergington.edu as participant
        Act: Send DELETE request to remove that participant
        Assert: Verify 200 status, response message, and participant was removed
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        initial_count = len(mock_activities[activity_name]["participants"])
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json() == {"message": f"Removed {email} from {activity_name}"}
        assert email not in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == initial_count - 1
    
    def test_remove_multiple_participants(self, client, mock_activities):
        """
        AAA Test: Can remove multiple participants from same activity
        
        Arrange: Chess Club has 2 participants
        Act: Remove first participant, then remove second
        Assert: Both removals succeed, activity eventually empty
        """
        # Arrange
        activity_name = "Chess Club"
        email1 = "michael@mergington.edu"
        email2 = "daniel@mergington.edu"
        
        # Act
        response1 = client.delete(
            f"/activities/{activity_name}/participants/{email1}"
        )
        response2 = client.delete(
            f"/activities/{activity_name}/participants/{email2}"
        )
        
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert email1 not in mock_activities[activity_name]["participants"]
        assert email2 not in mock_activities[activity_name]["participants"]
        assert len(mock_activities[activity_name]["participants"]) == 0
    
    def test_remove_participant_activity_not_found(self, client, mock_activities):
        """
        AAA Test: Remove fails with 404 when activity doesn't exist
        
        Arrange: No activity named "Nonexistent Club"
        Act: Try to remove participant from nonexistent activity
        Assert: Verify 404 status and error message
        """
        # Arrange
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_remove_participant_not_in_activity(self, client, mock_activities):
        """
        AAA Test: Remove fails with 404 when participant not signed up
        
        Arrange: Chess Club doesn't have alice@mergington.edu
        Act: Try to remove email not in the activity
        Assert: Verify 404 status, error message, and participants unchanged
        """
        # Arrange
        activity_name = "Chess Club"
        email = "alice@mergington.edu"  # Not in Chess Club
        initial_participants = list(mock_activities[activity_name]["participants"])
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Participant not found" in response.json()["detail"]
        assert mock_activities[activity_name]["participants"] == initial_participants
    
    def test_remove_from_empty_activity(self, client, mock_activities):
        """
        AAA Test: Remove fails with 404 when trying to remove from empty activity
        
        Arrange: Gym Class is empty
        Act: Try to remove any email from empty activity
        Assert: Verify 404 status and activity remains empty
        """
        # Arrange
        activity_name = "Gym Class"
        email = "student@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert len(mock_activities[activity_name]["participants"]) == 0


# ============================================================================
# GET / (Root/Redirect) Tests
# ============================================================================

class TestRootRedirect:
    """Tests for the GET / endpoint (root redirect)"""
    
    def test_root_redirect_to_static_html(self, client):
        """
        AAA Test: Root endpoint redirects to static HTML page
        
        Arrange: Client ready
        Act: Send GET request to /
        Assert: Verify redirect response (307) pointing to /static/index.html
        """
        # Arrange - client is ready from fixture
        
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
