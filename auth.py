import streamlit as st

from config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USER
import database


def authenticate(username: str, password: str) -> bool:
    if username == DEFAULT_ADMIN_USER and password == DEFAULT_ADMIN_PASSWORD:
        return True
    user = database.get_user(username)
    return bool(user and user["password"] == password)


def ensure_authenticated() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.current_user = None

    if not st.session_state.authenticated:
        st.warning("Please sign in to access PingMonitor Pro.")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
            if submitted:
                if authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.stop()


def ensure_admin() -> bool:
    return st.session_state.get("current_user") == DEFAULT_ADMIN_USER
