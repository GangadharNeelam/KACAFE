"""RBAC role constants and page-permission registry.

Single source of truth for every role-based access-control decision in the
application.  Import these constants instead of hardcoding role strings.
"""
from __future__ import annotations

# ── Role identifiers (stored in the DB and Flask session) ────────────────────
ROLE_OWNER: str = "supervisor"
ROLE_STAFF: str = "seller"

ALL_ROLES: tuple[str, ...] = (ROLE_OWNER, ROLE_STAFF)

# ── Human-readable metadata per role ─────────────────────────────────────────
ROLE_DISPLAY: dict[str, str] = {
    ROLE_OWNER: "Owner",
    ROLE_STAFF: "Staff",
}

ROLE_DESCRIPTION: dict[str, str] = {
    ROLE_OWNER: "Full access — analytics, inventory, menu, vendors & procurement",
    ROLE_STAFF: "Sales POS, personal dashboard, inventory monitor & menu reference",
}

ROLE_ICON: dict[str, str] = {
    ROLE_OWNER: "bi-briefcase-fill",
    ROLE_STAFF: "bi-person-badge-fill",
}

# ── Page-level permission registry ───────────────────────────────────────────
# Maps URL hash → tuple of roles authorised to render that page.
PAGE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "#":                 (ROLE_OWNER,),
    "#sales":            (ROLE_OWNER, ROLE_STAFF),
    "#live-sales":       (ROLE_OWNER,),
    "#inventory":        (ROLE_OWNER,),
    "#menu":             (ROLE_OWNER,),
    "#vendors":          (ROLE_OWNER,),
    "#procurement":      (ROLE_OWNER,),
    "#seller-dashboard": (ROLE_STAFF,),
    "#seller-inventory": (ROLE_STAFF,),
    "#seller-menu":      (ROLE_STAFF,),
}


def has_permission(role: str, page_hash: str) -> bool:
    """Return True if *role* is authorised to access *page_hash*."""
    return role in PAGE_PERMISSIONS.get(page_hash, ())
