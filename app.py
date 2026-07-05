import base64
import io
import streamlit as st
import pandas as pd

import auth
import database

# Defensive reload: if the imported `database` module is missing expected
# attributes (due to a shadowed package or stale import), load the local
# `database.py` file directly and replace the module in sys.modules so
# subsequent imports use the correct implementation.
import importlib.util
import sys
from pathlib import Path

if not hasattr(database, "get_activity_logs"):
    db_path = Path(__file__).resolve().parent / "database.py"
    if db_path.exists():
        spec = importlib.util.spec_from_file_location("database", str(db_path))
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore
            sys.modules["database"] = module
            database = module
        except Exception:
            # If reload fails, leave the original module and continue; errors
            # will surface later in a clearer traceback.
            pass


def _safe_get_websites(search_value):
    """Call database.get_websites in a way that's compatible with older/new signatures.

    Tries positional and falls back to no-arg call.
    """
    try:
        return database.get_websites(search_value)
    except TypeError:
        try:
            return database.get_websites()
        except Exception:
            return []
from config import APP_TITLE, CSS_PATH
from monitor import run_monitor_cycle
from scheduler import MonitorScheduler

st.set_page_config(page_title=APP_TITLE, page_icon="📡", layout="wide")

if CSS_PATH.exists():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

auth.ensure_authenticated()

st.markdown(
    f"""
    <div class="header-bar">
        <div class="title-group">
            <img src="data:image/svg+xml;base64,{base64.b64encode(open('assets/logo.svg','rb').read()).decode()}" />
            <div>
                <div style="font-weight:700; color:#4338ca;">{APP_TITLE}</div>
                <div style="font-size:0.8rem; color:#7c3aed;">Website and server monitoring</div>
            </div>
        </div>
        <div style="font-size:0.9rem; color:#6b7280;">● Live</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-brand-icon">📡</div>
        <div>
            <div class="sidebar-brand-title">PingMonitor Pro</div>
            <div class="sidebar-brand-subtitle">Live uptime monitoring</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.success("System online · 24/7 monitoring")

st.session_state.dark_mode = st.sidebar.checkbox("🌙 Dark Mode", value=False)
if st.session_state.dark_mode:
    st.markdown("<style>.stApp{background:linear-gradient(135deg,#1f2937 0%,#111827 35%,#1e1b4b 100%); color:#f8fafc;} .header-bar, .hero, div[data-testid='stMetric'], .stDataFrame, .stForm, [data-testid='stSidebar'], [data-testid='stVerticalBlock'] > div{background:rgba(15,23,42,0.85)!important; color:#f8fafc!important;} .sidebar-brand-title, .hero h2, h1, h2, h3{color:#f8fafc!important;} .sidebar-brand-subtitle{color:#cbd5e1!important;} .stTextInput input, .stNumberInput input{background:#0f172a!important; color:#f8fafc!important;}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <h2>Monitor every website with clarity</h2>
        <p>Track uptime, response speed, and alerts from one polished control center.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "scheduler" not in st.session_state:
    st.session_state.scheduler = MonitorScheduler(interval_seconds=60)
    st.session_state.scheduler.start()

col1, col2, col3 = st.columns(3)
stats = database.get_dashboard_stats()
col1.metric("Monitored Sites", stats["sites"])
col2.metric("Total Checks", stats["checks"])
col3.metric("Availability", f"{stats['availability']}%")

st.subheader("Recently Monitored")
checks = database.get_recent_checks(limit=10)
if checks:
    st.dataframe(checks, use_container_width=True)
else:
    st.info("No monitoring results yet. Add a website to start monitoring.")

st.subheader("Managed Websites")
search = st.text_input("🔍 Search websites")
websites = _safe_get_websites(search)
if websites:
    for site in websites:
        col_a, col_b, col_c = st.columns([3, 1, 1])
        with col_a:
            st.write(f"**{site['name']}**\n{site['url']}")
        with col_b:
            if st.button("⭐", key=f"fav-{site['id']}"):
                database.toggle_favorite(site['id'])
                st.rerun()
        with col_c:
            if st.button("🔔", key=f"notify-{site['id']}"):
                database.log_activity(st.session_state.current_user or "admin", "notification", f"Alert requested for {site['name']}")
                st.success("Alert request recorded")
    st.caption("Tip: favorites are highlighted in the list and available in the reports page.")
else:
    st.info("No websites configured. Use the Add Website page to begin.")

st.subheader("📥 Export Reports")
buffer = io.StringIO()
pd.DataFrame(database.get_recent_checks(limit=20)).to_csv(buffer, index=False)
st.download_button("Download CSV", buffer.getvalue(), file_name="monitoring_reports.csv", mime="text/csv")

st.subheader("🔔 Real-Time Notifications")
for item in database.get_activity_logs(limit=5):
    st.write(f"- {item['created_at']} | {item['username']} | {item['action']} | {item['details']}")

if st.button("Run Check Now"):
    run_monitor_cycle()
    database.log_activity(st.session_state.current_user or "admin", "manual_check", "Executed monitoring cycle")
    st.success("Monitoring cycle executed.")
