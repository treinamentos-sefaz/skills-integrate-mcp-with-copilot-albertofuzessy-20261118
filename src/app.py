"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


class TeacherLogin(BaseModel):
    username: str
    password: str


def _session_config() -> tuple[str, str, str]:
    username = os.getenv("TEACHER_USERNAME")
    password = os.getenv("TEACHER_PASSWORD")
    secret = os.getenv("SESSION_SECRET")
    if not username or not password or not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Teacher login is not configured",
        )
    if len(secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SESSION_SECRET must contain at least 32 bytes",
        )
    return username, password, secret


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _create_session_token(username: str, secret: str) -> str:
    payload = json.dumps(
        {"username": username, "expires_at": int(time.time()) + SESSION_TTL_SECONDS},
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return f"{_encode_segment(payload)}.{_encode_segment(signature)}"


def _is_valid_session(token: str, username: str, secret: str) -> bool:
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        payload = base64.b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4),
            altchars=b"-_",
            validate=True,
        )
        signature = base64.b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4),
            altchars=b"-_",
            validate=True,
        )
        expected_signature = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return False
        session = json.loads(payload)
        return (
            session.get("username") == username
            and type(session.get("expires_at")) is int
            and session["expires_at"] > time.time()
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return False


def _require_teacher(request: Request) -> None:
    username, _, secret = _session_config()
    token = request.cookies.get(SESSION_COOKIE)
    if token is None or not _is_valid_session(token, username, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Teacher login required",
        )


def _secure_cookie() -> bool:
    return os.getenv("SESSION_COOKIE_SECURE", "true").lower() != "false"


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/status")
def get_auth_status(request: Request):
    username = os.getenv("TEACHER_USERNAME")
    secret = os.getenv("SESSION_SECRET")
    token = request.cookies.get(SESSION_COOKIE)
    return {
        "authenticated": bool(
            username
            and secret
            and token
            and _is_valid_session(token, username, secret)
        )
    }


@app.post("/auth/login")
def login(teacher: TeacherLogin, response: Response):
    username, password, secret = _session_config()
    username_matches = hmac.compare_digest(
        teacher.username.encode("utf-8"), username.encode("utf-8")
    )
    password_matches = hmac.compare_digest(
        teacher.password.encode("utf-8"), password.encode("utf-8")
    )
    if not (username_matches and password_matches):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=_create_session_token(username, secret),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=_secure_cookie(),
        samesite="strict",
        path="/",
    )
    return {"message": "Logged in as a teacher"}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=_secure_cookie(),
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _teacher: None = Depends(_require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _teacher: None = Depends(_require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
