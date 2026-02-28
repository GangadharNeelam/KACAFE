"""Login page layout — KA Food Caterers branded, no role pre-selection."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html, dcc

# Users shown as quick-select tiles to pre-fill the username field.
# Tuple: (username, bootstrap-icon-class, role-label, accent-colour)
_USER_TILES: list[tuple[str, str, str, str]] = [
    ("Dorababu", "bi-briefcase-fill",    "Owner", "#3B82F6"),
    ("ramana",   "bi-person-badge-fill", "Staff", "#10B981"),
    ("seller",   "bi-person-badge-fill", "Staff", "#10B981"),
    ("ravi",     "bi-person-badge-fill", "Staff", "#10B981"),
]


def _user_tile(username: str, icon: str, role_label: str, color: str) -> html.Div:
    """Clickable tile — clicking pre-fills the username input."""
    return html.Div(
        [
            html.I(className=f"bi {icon} persona-icon", style={"color": color}),
            html.Div(username, className="persona-label"),
            html.Div(role_label, className="persona-desc"),
        ],
        id={"type": "user-tile", "username": username},
        className="persona-card",
        n_clicks=0,
        role="button",
        tabIndex=0,
        **{"aria-label": f"Sign in as {username}"},
    )


def get_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    # ── KA Branding ──────────────────────────────────────────
                    html.Div(
                        [
                            html.Div(
                                html.Div("KA", className="ka-logo-initials"),
                                className="ka-logo-circle",
                            ),
                            html.H1("KA Food Caterers", className="login-title"),
                            html.P(
                                "Made with love, delivered with care",
                                className="login-subtitle ka-motto",
                            ),
                        ],
                        className="login-logo",
                    ),

                    html.Hr(style={"borderColor": "var(--border-light)", "margin": "0 0 24px"}),

                    # ── User quick-select ─────────────────────────────────────
                    html.Div("Select your account", className="login-section-label"),
                    html.Div(
                        [_user_tile(*t) for t in _USER_TILES],
                        className="persona-row user-tiles-row",
                    ),

                    html.Div(
                        "— or type credentials directly —",
                        className="login-divider-text",
                    ),

                    # ── Username ──────────────────────────────────────────────
                    html.Div(
                        [
                            dbc.Label(
                                "Username",
                                className="login-label",
                                html_for="login-username",
                            ),
                            html.Div(
                                [
                                    html.I(className="bi bi-person login-field-icon"),
                                    dbc.Input(
                                        id="login-username",
                                        type="text",
                                        placeholder="Enter your username",
                                        className="login-input",
                                        autoComplete="username",
                                        n_submit=0,
                                    ),
                                ],
                                className="login-field-wrap",
                            ),
                        ],
                        className="mb-4",
                    ),

                    # ── Password ──────────────────────────────────────────────
                    html.Div(
                        [
                            dbc.Label(
                                "Password",
                                className="login-label",
                                html_for="login-password",
                            ),
                            html.Div(
                                [
                                    html.I(className="bi bi-lock login-field-icon"),
                                    dbc.Input(
                                        id="login-password",
                                        type="password",
                                        placeholder="Enter your password",
                                        className="login-input",
                                        autoComplete="current-password",
                                        n_submit=0,
                                    ),
                                ],
                                className="login-field-wrap",
                            ),
                        ],
                        className="mb-3",
                    ),

                    # ── Error / info banner ───────────────────────────────────
                    html.Div(id="login-error"),

                    # ── Submit ────────────────────────────────────────────────
                    dbc.Button(
                        [html.I(className="bi bi-box-arrow-in-right me-2"), "Sign In"],
                        id="login-btn",
                        className="login-btn",
                        n_clicks=0,
                    ),

                    # ── Footer ────────────────────────────────────────────────
                    html.Div(
                        "KA Food Caterers · Operations Platform v2.0.0",
                        className="login-footer-note",
                    ),
                ],
                className="login-card",
            ),
        ],
        className="login-page",
    )
