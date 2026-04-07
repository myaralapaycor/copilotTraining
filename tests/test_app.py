import copy
import pytest
from fastapi.testclient import TestClient

from src.app import app, activities

_original_activities = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities database before each test."""
    activities.clear()
    activities.update(copy.deepcopy(_original_activities))


@pytest.fixture
def client():
    return TestClient(app)


# -- GET / -----------------------------------------------------------------


class TestRoot:
    def test_root_redirects_to_index(self, client):
        # Arrange — nothing extra needed

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


# -- GET /activities -------------------------------------------------------


class TestGetActivities:
    def test_returns_all_activities(self, client):
        # Arrange
        expected_count = 9

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        assert response.status_code == 200
        assert len(data) == expected_count
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_activity_has_expected_fields(self, client):
        # Arrange
        required_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for name, details in data.items():
            assert required_fields.issubset(details.keys()), f"{name} missing fields"
            assert isinstance(details["participants"], list)

    def test_activity_contains_correct_data(self, client):
        # Arrange
        expected_description = "Learn strategies and compete in chess tournaments"

        # Act
        response = client.get("/activities")
        chess_club = response.json()["Chess Club"]

        # Assert
        assert chess_club["description"] == expected_description
        assert chess_club["max_participants"] == 12


# -- POST /activities/{name}/signup ----------------------------------------


class TestSignup:
    def test_signup_success(self, client):
        # Arrange
        email = "newstudent@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]
        participants = client.get("/activities").json()[activity]["participants"]
        assert email in participants

    def test_signup_activity_not_found(self, client):
        # Arrange
        email = "someone@mergington.edu"
        activity = "Nonexistent Club"

        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_participant(self, client):
        # Arrange — michael is already in Chess Club
        email = "michael@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()


# -- DELETE /activities/{name}/signup --------------------------------------


class TestUnregister:
    def test_unregister_success(self, client):
        # Arrange — michael is in Chess Club
        email = "michael@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]
        participants = client.get("/activities").json()[activity]["participants"]
        assert email not in participants

    def test_unregister_activity_not_found(self, client):
        # Arrange
        email = "someone@mergington.edu"
        activity = "Nonexistent Club"

        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_signed_up(self, client):
        # Arrange
        email = "nothere@mergington.edu"
        activity = "Chess Club"

        # Act
        response = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()


# -- Round-trip ------------------------------------------------------------


class TestRoundTrip:
    def test_signup_then_unregister(self, client):
        # Arrange
        email = "roundtrip@mergington.edu"
        activity = "Robotics Club"

        # Act — signup
        signup_resp = client.post(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert — signup succeeded and participant is present
        assert signup_resp.status_code == 200
        participants_after_signup = client.get("/activities").json()[activity]["participants"]
        assert email in participants_after_signup

        # Act — unregister
        unregister_resp = client.delete(
            f"/activities/{activity}/signup",
            params={"email": email},
        )

        # Assert — unregister succeeded and participant is removed
        assert unregister_resp.status_code == 200
        participants_after_unregister = client.get("/activities").json()[activity]["participants"]
        assert email not in participants_after_unregister
