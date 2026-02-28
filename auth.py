"""Session-based authentication helpers."""
from __future__ import annotations
import flask


def get_current_user() -> dict:
    return {
        "user_id":  flask.session.get("user_id"),
        "username": flask.session.get("username"),
        "role":     flask.session.get("role"),
    }


def is_authenticated() -> bool:
    return flask.session.get("user_id") is not None


def get_role() -> str | None:
    return flask.session.get("role")


def login_user(user_id: int, username: str, role: str) -> None:
    flask.session["user_id"]  = user_id
    flask.session["username"] = username
    flask.session["role"]     = role
    flask.session.permanent   = True


def logout_user() -> None:
    flask.session.clear()
