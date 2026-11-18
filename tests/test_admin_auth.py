import asyncio
import json
import os
import sys
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import unquote, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import app, activities


class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        self.original_participants = activities["Chess Club"]["participants"][:]
        activities["Chess Club"]["participants"] = self.original_participants[:]
        self.environment = patch.dict(
            os.environ,
            {
                "TEACHER_USERNAME": "teacher",
                "TEACHER_PASSWORD": "correct horse battery staple",
                "SESSION_SECRET": "test-session-secret-with-at-least-32-chars",
                "SESSION_COOKIE_SECURE": "false",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self._restore_participants)

    def _restore_participants(self):
        activities["Chess Club"]["participants"] = self.original_participants

    def request(self, method, url, body=None, cookie=None):
        return asyncio.run(self._request(method, url, body, cookie))

    async def _request(self, method, url, body, cookie):
        parsed_url = urlsplit(url)
        request_body = (
            json.dumps(body).encode("utf-8") if body is not None else b""
        )
        headers = [(b"host", b"testserver")]
        if body is not None:
            headers.append((b"content-type", b"application/json"))
        if cookie is not None:
            headers.append((b"cookie", cookie.encode("latin-1")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": unquote(parsed_url.path),
            "raw_path": parsed_url.path.encode("ascii"),
            "query_string": parsed_url.query.encode("ascii"),
            "root_path": "",
            "headers": headers,
            "client": ("testclient", 123),
            "server": ("testserver", 80),
        }
        request_sent = False
        response_messages = []

        async def receive():
            nonlocal request_sent
            if request_sent:
                return {"type": "http.disconnect"}
            request_sent = True
            return {
                "type": "http.request",
                "body": request_body,
                "more_body": False,
            }

        async def send(message):
            response_messages.append(message)

        await app(scope, receive, send)
        response_start = next(
            message
            for message in response_messages
            if message["type"] == "http.response.start"
        )
        response_body = b"".join(
            message.get("body", b"")
            for message in response_messages
            if message["type"] == "http.response.body"
        )
        return (
            response_start["status"],
            dict(response_start["headers"]),
            json.loads(response_body),
        )

    def test_students_cannot_register_or_unregister(self):
        email = "michael@mergington.edu"

        signup_status, _, _ = self.request(
            "POST",
            "/activities/Chess%20Club/signup?email=new%40mergington.edu",
        )
        unregister_status, _, _ = self.request(
            "DELETE",
            f"/activities/Chess%20Club/unregister?email={email}",
        )

        self.assertEqual(signup_status, 401)
        self.assertEqual(unregister_status, 401)
        self.assertIn(email, activities["Chess Club"]["participants"])
        self.assertNotIn(
            "new@mergington.edu", activities["Chess Club"]["participants"]
        )

    def test_teacher_login_allows_registration_management(self):
        email = "michael@mergington.edu"
        login_status, login_headers, _ = self.request(
            "POST",
            "/auth/login",
            {
                "username": "teacher",
                "password": "correct horse battery staple",
            },
        )
        cookie = SimpleCookie()
        cookie.load(login_headers[b"set-cookie"].decode("latin-1"))
        session_cookie = cookie["teacher_session"].OutputString().split(";", 1)[0]

        signup_status, _, _ = self.request(
            "POST",
            "/activities/Chess%20Club/signup?email=new%40mergington.edu",
            cookie=session_cookie,
        )
        unregister_status, _, _ = self.request(
            "DELETE",
            f"/activities/Chess%20Club/unregister?email={email}",
            cookie=session_cookie,
        )

        self.assertEqual(login_status, 200)
        self.assertTrue(cookie["teacher_session"]["httponly"])
        self.assertEqual(signup_status, 200)
        self.assertEqual(unregister_status, 200)
        self.assertIn(
            "new@mergington.edu", activities["Chess Club"]["participants"]
        )
        self.assertNotIn(email, activities["Chess Club"]["participants"])

    def test_invalid_login_is_rejected_but_activities_remain_public(self):
        login_status, _, _ = self.request(
            "POST",
            "/auth/login",
            {"username": "student", "password": "wrong"},
        )
        activities_status, _, result = self.request("GET", "/activities")

        self.assertEqual(login_status, 401)
        self.assertEqual(activities_status, 200)
        self.assertIn("Chess Club", result)
