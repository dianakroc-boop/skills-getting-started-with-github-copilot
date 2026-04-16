"""
Tests for the Mergington High School API FastAPI application.

Tests cover:
- Activity listing endpoint
- Student signup for activities
- Student unregistration from activities
- Error handling for invalid activities and duplicate signups
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


client = TestClient(app)


class TestActivitiesEndpoint:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self):
        """Test that GET /activities returns the complete activities list"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) > 0

    def test_activities_have_required_fields(self):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_root_redirects_to_static(self):
        """Test that GET / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_student(self):
        """Test that a new student can successfully sign up for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newemail@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newemail@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_student_to_participants(self):
        """Test that signup actually adds the student to the activity"""
        email = "testuser@mergington.edu"
        client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Programming Class"]["participants"]

    def test_signup_duplicate_student_returns_error(self):
        """Test that signing up an already registered student returns 400 error"""
        # First signup
        client.post(
            "/activities/Robotics Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        
        # Duplicate signup
        response = client.post(
            "/activities/Robotics Club/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity_returns_404(self):
        """Test that signing up for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_signed_up_student(self):
        """Test that a signed-up student can unregister from an activity"""
        email = "unregister_test@mergington.edu"
        
        # First sign up
        client.post(
            "/activities/Theater Club/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Theater Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]

    def test_unregister_removes_student_from_participants(self):
        """Test that unregister actually removes the student from the activity"""
        email = "removal_test@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Swimming Team/signup",
            params={"email": email}
        )
        
        # Verify signed up
        response = client.get("/activities")
        assert email in response.json()["Swimming Team"]["participants"]
        
        # Unregister
        client.delete(
            "/activities/Swimming Team/unregister",
            params={"email": email}
        )
        
        # Verify unregistered
        response = client.get("/activities")
        assert email not in response.json()["Swimming Team"]["participants"]

    def test_unregister_not_signed_up_student_returns_error(self):
        """Test that unregistering a non-signed-up student returns 400 error"""
        response = client.delete(
            "/activities/Math Olympiad/unregister",
            params={"email": "notsignedup@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_nonexistent_activity_returns_404(self):
        """Test that unregistering from a non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]


class TestActivityCapacity:
    """Tests for activity capacity constraints"""

    def test_signup_respects_max_participants(self):
        """Test that activities enforce max participant limits"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert len(activity_data["participants"]) <= activity_data["max_participants"]


class TestDataIntegrity:
    """Tests for data integrity across operations"""

    def test_multiple_signups_succeed(self):
        """Test that multiple sequential signups work correctly"""
        emails = [
            "multi1@mergington.edu",
            "multi2@mergington.edu",
            "multi3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                "/activities/Soccer Team/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        participants = response.json()["Soccer Team"]["participants"]
        for email in emails:
            assert email in participants

    def test_signup_and_unregister_cycle(self):
        """Test signup followed by unregister works correctly"""
        email = "cycle_test@mergington.edu"
        activity = "Photography Club"
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Unregister
        client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
