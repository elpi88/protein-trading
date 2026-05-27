"""
Modulo di autenticazione utenti.

Password cifrate con bcrypt (mai memorizzate in chiaro).
Tabella `users` in protein_trading.db (creata da db.init_db).

Funzioni principali:
    create_user, authenticate, list_users, update_user, delete_user,
    require_login, get_current_user, logout, has_users
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import bcrypt
import streamlit as st

from lib.db import get_conn, DATABASE_URL


def _sql(query: str) -> str:
    """Converte placeholder ? → %s per PostgreSQL."""
    if DATABASE_URL:
        return query.replace("?", "%s")
    return query


# ----------------------------------------------------------------------
# Hash / verifica password
# ----------------------------------------------------------------------
def hash_password(plain: str) -> str:
    """Hash bcrypt della password. Ritorna stringa utf-8."""
    return bcrypt.hashpw(plain.encode("utf-8"),
                          bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """True se la password corrisponde all'hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ----------------------------------------------------------------------
# CRUD utenti
# ----------------------------------------------------------------------
def has_users() -> bool:
    """True se nel DB esiste almeno un utente attivo."""
    with get_conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM users WHERE active = 1"
        ).fetchone()[0]
    return n > 0


def get_user(username: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            _sql("SELECT username, password_hash, role, created_at, last_login, active "
            "FROM users WHERE username = ?"),
            (username.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, role, created_at, last_login, active "
            "FROM users ORDER BY username"
        ).fetchall()
    return [dict(r) for r in rows]


def create_user(username: str, password: str, role: str = "user") -> bool:
    """Crea un nuovo utente. Ritorna False se username esiste gia'."""
    username = username.strip().lower()
    if not username or not password:
        return False
    if get_user(username):
        return False
    with get_conn() as conn:
        conn.execute(
            _sql("INSERT INTO users (username, password_hash, role, created_at, active) "
            "VALUES (?, ?, ?, ?, 1)"),
            (username, hash_password(password), role,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
    return True


def update_user(username: str,
                password: Optional[str] = None,
                role: Optional[str] = None,
                active: Optional[bool] = None) -> bool:
    username = username.strip().lower()
    if not get_user(username):
        return False
    fields, params = [], []
    ph = "%s" if DATABASE_URL else "?"
    if password is not None:
        fields.append(f"password_hash = {ph}")
        params.append(hash_password(password))
    if role is not None:
        fields.append(f"role = {ph}")
        params.append(role)
    if active is not None:
        fields.append(f"active = {ph}")
        params.append(1 if active else 0)
    if not fields:
        return False
    params.append(username)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE username = {ph}",
            params
        )
    return True


def delete_user(username: str) -> bool:
    """Cancella fisicamente un utente. Meglio update_user(active=False)."""
    username = username.strip().lower()
    with get_conn() as conn:
        cur = conn.execute(_sql("DELETE FROM users WHERE username = ?"), (username,))
        return cur.rowcount > 0


# ----------------------------------------------------------------------
# Autenticazione / session
# ----------------------------------------------------------------------
def authenticate(username: str, password: str) -> Optional[dict]:
    """Verifica credenziali. Ritorna dict utente se ok, None altrimenti."""
    user = get_user(username)
    if not user:
        return None
    if not user.get("active"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    # aggiorna last_login
    with get_conn() as conn:
        conn.execute(
            _sql("UPDATE users SET last_login = ? WHERE username = ?"),
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             user["username"])
        )
    return {"username": user["username"], "role": user["role"]}


def login_session(username: str, role: str) -> None:
    """Imposta la session di Streamlit come loggato."""
    st.session_state["user"] = username
    st.session_state["role"] = role
    st.session_state["logged_in"] = True


def logout() -> None:
    for k in ("user", "role", "logged_in"):
        if k in st.session_state:
            del st.session_state[k]


def get_current_user() -> Optional[dict]:
    if st.session_state.get("logged_in"):
        return {"username": st.session_state.get("user"),
                "role": st.session_state.get("role", "user")}
    return None


def is_admin() -> bool:
    u = get_current_user()
    return bool(u and u.get("role") == "admin")


# ----------------------------------------------------------------------
# Guard per le pagine
# ----------------------------------------------------------------------
def require_login() -> None:
    """Da chiamare a inizio pagina. Se non loggato, blocca con messaggio."""
    if not st.session_state.get("logged_in"):
        st.error("Devi effettuare il login per accedere a questa pagina.")
        st.info("Vai alla pagina **Home** dal menu a sinistra per fare il login.")
        st.stop()


def require_admin() -> None:
    """Blocca la pagina se l'utente non e' admin."""
    require_login()
    if not is_admin():
        st.error("Sezione riservata agli amministratori.")
        st.stop()
