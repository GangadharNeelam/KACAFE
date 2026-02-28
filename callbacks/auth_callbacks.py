"""Authentication callbacks: login, logout, and user-tile username pre-fill.

Rate limiting:
  Max 5 failed attempts per username in a 5-minute rolling window.
  Stored in-process (resets on server restart), which is appropriate for a
  single-worker deployment.  Swap for Redis if you scale to multiple workers.
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict

import flask
from dash import Input, Output, State, ALL, callback_context, no_update
from dash.exceptions import PreventUpdate

from server import app
import auth as auth_module
from services.auth_service import authenticate

logger = logging.getLogger(__name__)

# ── In-process rate limiter ───────────────────────────────────────────────────
_MAX_ATTEMPTS = 5
_WINDOW_SECS  = 300   # 5-minute rolling window

# Maps normalised username → list of failure timestamps (monotonic)
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def _is_rate_limited(username: str) -> bool:
    """Return True when *username* has exhausted its allowed attempts."""
    now = time.monotonic()
    key = username.lower().strip()
    _failed_attempts[key] = [
        t for t in _failed_attempts[key] if now - t < _WINDOW_SECS
    ]
    return len(_failed_attempts[key]) >= _MAX_ATTEMPTS


def _record_failure(username: str) -> None:
    _failed_attempts[username.lower().strip()].append(time.monotonic())


# ── Callback registration ─────────────────────────────────────────────────────

def register_callbacks() -> None:

    # ── User-tile click → pre-fill username ───────────────────────────────
    @app.callback(
        Output("login-username", "value"),
        Input({"type": "user-tile", "username": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def prefill_username_from_tile(n_clicks_list):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        # Extract username from the triggered pattern-matched component ID
        triggered_id_str = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            id_dict = json.loads(triggered_id_str)
            return id_dict.get("username", no_update)
        except (json.JSONDecodeError, KeyError):
            raise PreventUpdate

    # ── Login ─────────────────────────────────────────────────────────────
    @app.callback(
        [
            Output("login-error", "children"),
            Output("auth-store",  "data"),
        ],
        [
            Input("login-btn",      "n_clicks"),
            Input("login-username", "n_submit"),
            Input("login-password", "n_submit"),
        ],
        [
            State("login-username", "value"),
            State("login-password", "value"),
        ],
        prevent_initial_call=True,
    )
    def handle_login(
        _btn_clicks: int,
        _user_submit: int,
        _pass_submit: int,
        username: str | None,
        password: str | None,
    ):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        if not username or not password:
            return "Please enter both username and password.", no_update

        if _is_rate_limited(username):
            logger.warning("Rate-limit reached for username=%r", username)
            return (
                "Too many failed attempts. Please wait 5 minutes before trying again.",
                no_update,
            )

        user = authenticate(username, password)
        if not user:
            _record_failure(username)
            logger.warning("Failed login attempt for username=%r", username)
            return "Invalid username or password. Please try again.", no_update

        auth_module.login_user(user["id"], user["username"], user["role"])
        logger.info(
            "User %r (role=%s) logged in successfully.",
            user["username"],
            user["role"],
        )
        return "", {"logged_in": True, "role": user["role"], "ts": time.time()}

    # ── Logout ────────────────────────────────────────────────────────────
    @app.callback(
        Output("auth-store", "data", allow_duplicate=True),
        Input("logout-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def handle_logout(n_clicks: int):
        if n_clicks:
            username = flask.session.get("username", "unknown")
            auth_module.logout_user()
            logger.info("User %r logged out.", username)
            return {"logged_in": False, "ts": time.time()}
        raise PreventUpdate
