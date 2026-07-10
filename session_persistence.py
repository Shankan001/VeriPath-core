"""
VeriPath — Login session persistence across page refresh, via signed cookie
+ a server-side session token table (so tokens can be revoked/expired).
"""

import secrets
from datetime import datetime, timedelta, timezone
import streamlit as st
import extra_streamlit_components as stx
from supabase_db import get_client

SESSION_DURATION_DAYS = 7


def get_cookie_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state["cookie_manager"] = stx.CookieManager(key="veripath_cookie_mgr")
    return st.session_state["cookie_manager"]


def create_session(username: str) -> str:
    """Creates a new session token, stores it in Supabase, returns the token."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)
    supabase = get_client()
    supabase.table("user_sessions").insert({
        "token": token,
        "username": username,
        "expires_at": expires_at.isoformat(),
    }).execute()
    return token


def set_session_cookie(token: str):
    cookie_manager = get_cookie_manager()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)
    cookie_manager.set("veripath_session", token, expires_at=expires_at)


def get_valid_username_from_cookie():
    """Returns the username if a valid, non-expired session cookie exists, else None."""
    cookie_manager = get_cookie_manager()

    # Force a full cookie sync from the browser before reading — on the very
    # first script run after a page load, .get() can return None even when
    # the cookie exists, because the component hasn't synced yet.
    all_cookies = cookie_manager.get_all()
    token = all_cookies.get("veripath_session") if all_cookies else None

    if not token and not st.session_state.get("_cookie_sync_retried"):
        # Give the component one rerun to finish syncing, but only once
        # to avoid an infinite loop if there's genuinely no cookie.
        st.session_state["_cookie_sync_retried"] = True
        st.rerun()

    if not token:
        return None

    supabase = get_client()
    try:
        result = supabase.table("user_sessions").select("username, expires_at").eq(
            "token", token
        ).execute().data
    except Exception:
        return None

    if not result:
        return None

    row = result[0]
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        return None

    return row["username"]


def clear_session(token: str = None):
    cookie_manager = get_cookie_manager()
    if token is None:
        token = cookie_manager.get("veripath_session")
    if token:
        try:
            supabase = get_client()
            supabase.table("user_sessions").delete().eq("token", token).execute()
        except Exception:
            pass
    cookie_manager.delete("veripath_session")
