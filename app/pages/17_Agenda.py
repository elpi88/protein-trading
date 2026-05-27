"""
Agenda - Gestione appuntamenti e impegni.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from lib.auth import require_login, get_current_user
from lib.db import (
    add_agenda_event, get_agenda_events,
    delete_agenda_event, update_agenda_event,
    init_db,
)

require_login()
init_db()

st.markdown(
    '<div class="page-title">📅 Agenda</div>'
    '<div class="page-sub">Gestione appuntamenti e impegni</div>',
    unsafe_allow_html=True,
)

current_user = get_current_user()
username = current_user["username"] if current_user else "system"

CATEGORIES = {
    "meeting":   ("🤝", "Meeting"),
    "call":      ("📞", "Call"),
    "travel":    ("✈️", "Travel"),
    "deadline":  ("⏰", "Deadline"),
    "delivery":  ("🚢", "Delivery"),
    "other":     ("📌", "Other"),
}

# -----------------------------------------------------------------------
# Layout: colonna sinistra = lista eventi, destra = form aggiunta
# -----------------------------------------------------------------------
col_list, col_form = st.columns([3, 2], gap="large")

# -----------------------------------------------------------------------
# FORM AGGIUNTA / MODIFICA
# -----------------------------------------------------------------------
with col_form:
    edit_id = st.session_state.get("agenda_edit_id")

    if edit_id:
        st.subheader("✏️ Edit event")
        edf = get_agenda_events()
        row = edf[edf["id"] == edit_id]
        if row.empty:
            st.session_state.pop("agenda_edit_id", None)
            st.rerun()
        row = row.iloc[0]
        default_title = row["title"]
        default_date  = datetime.strptime(row["event_date"], "%Y-%m-%d").date()
        default_ts    = row.get("time_start", "") or ""
        default_te    = row.get("time_end", "") or ""
        default_loc   = row.get("location", "") or ""
        default_desc  = row.get("description", "") or ""
        default_cat   = row.get("category", "meeting") or "meeting"
        btn_label     = "💾 Save changes"
    else:
        st.subheader("➕ New event")
        default_title = ""
        default_date  = date.today()
        default_ts    = ""
        default_te    = ""
        default_loc   = ""
        default_desc  = ""
        default_cat   = "meeting"
        btn_label     = "✅ Add event"

    with st.form("agenda_form", clear_on_submit=not bool(edit_id)):
        title = st.text_input("Title *", value=default_title, placeholder="e.g. Call with supplier")
        ev_date = st.date_input("Date *", value=default_date)

        c1, c2 = st.columns(2)
        with c1:
            time_start = st.text_input("Start time", value=default_ts, placeholder="09:00")
        with c2:
            time_end = st.text_input("End time", value=default_te, placeholder="10:00")

        location = st.text_input("Location", value=default_loc, placeholder="e.g. Zoom / Milano")

        cat_options = list(CATEGORIES.keys())
        cat_labels  = [f"{CATEGORIES[k][0]} {CATEGORIES[k][1]}" for k in cat_options]
        cat_idx     = cat_options.index(default_cat) if default_cat in cat_options else 0
        cat_sel     = st.selectbox("Category", options=cat_options, index=cat_idx,
                                   format_func=lambda k: f"{CATEGORIES[k][0]} {CATEGORIES[k][1]}")

        description = st.text_area("Notes", value=default_desc, height=80,
                                   placeholder="Additional notes...")

        submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Title is required.")
        else:
            if edit_id:
                ok = update_agenda_event(
                    edit_id, title.strip(), str(ev_date),
                    time_start, time_end, location, description, cat_sel
                )
                if ok:
                    st.success("Event updated!")
                    st.session_state.pop("agenda_edit_id", None)
                    st.rerun()
            else:
                add_agenda_event(
                    title.strip(), str(ev_date),
                    time_start, time_end, location, description, cat_sel,
                    user=username
                )
                st.success("Event added!")
                st.rerun()

    if edit_id:
        if st.button("✖ Cancel edit", use_container_width=True):
            st.session_state.pop("agenda_edit_id", None)
            st.rerun()

# -----------------------------------------------------------------------
# LISTA EVENTI
# -----------------------------------------------------------------------
with col_list:
    # Filtri
    fc1, fc2 = st.columns([2, 2])
    with fc1:
        view = st.radio("Show", ["Upcoming", "This week", "This month", "All"],
                        horizontal=True, label_visibility="collapsed")
    with fc2:
        search = st.text_input("🔍 Search", placeholder="Title or location...",
                               label_visibility="collapsed")

    today = date.today()
    if view == "Upcoming":
        df = get_agenda_events(date_from=str(today))
    elif view == "This week":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        df = get_agenda_events(str(monday), str(sunday))
    elif view == "This month":
        first = today.replace(day=1)
        import calendar as _cal
        last_day = _cal.monthrange(today.year, today.month)[1]
        last = today.replace(day=last_day)
        df = get_agenda_events(str(first), str(last))
    else:
        df = get_agenda_events()

    if search:
        mask = (
            df["title"].str.contains(search, case=False, na=False) |
            df["location"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if df.empty:
        st.info("No events found.")
    else:
        # Raggruppa per data
        df["event_date"] = pd.to_datetime(df["event_date"])
        df = df.sort_values(["event_date", "time_start"])

        current_date = None
        for _, row in df.iterrows():
            row_date = row["event_date"].date()
            if row_date != current_date:
                current_date = row_date
                iso_week = row_date.isocalendar()[1]
                day_label = row_date.strftime("%A, %d %B %Y")
                is_today = row_date == today
                badge = " 🔴 TODAY" if is_today else f" · W{iso_week}"
                st.markdown(
                    f"<div style='font-size:0.8rem; font-weight:700; color:#aaa; "
                    f"margin-top:12px; margin-bottom:4px; border-bottom:1px solid #333; "
                    f"padding-bottom:3px'>{day_label}{badge}</div>",
                    unsafe_allow_html=True
                )

            cat = row.get("category", "other") or "other"
            icon, cat_label = CATEGORIES.get(cat, ("📌", "Other"))
            t_start = row.get("time_start", "") or ""
            t_end   = row.get("time_end", "") or ""
            time_str = f"{t_start}–{t_end}" if t_start and t_end else (t_start or "")
            loc = row.get("location", "") or ""
            loc_str = f" · 📍 {loc}" if loc else ""

            with st.container():
                ca, cb = st.columns([6, 1])
                with ca:
                    st.markdown(
                        f"<div style='background:#1a1a2e; border-left:3px solid #e84e0f; "
                        f"border-radius:6px; padding:8px 12px; margin-bottom:4px;'>"
                        f"<div style='font-weight:600; font-size:0.9rem; color:#eee'>"
                        f"{icon} {row['title']}</div>"
                        f"<div style='font-size:0.75rem; color:#aaa; margin-top:2px'>"
                        f"{time_str}{loc_str} "
                        f"<span style='opacity:0.5'>{cat_label}</span></div>"
                        + (f"<div style='font-size:0.75rem; color:#888; margin-top:3px'>"
                           f"{row['description']}</div>" if row.get("description") else "")
                        + "</div>",
                        unsafe_allow_html=True
                    )
                with cb:
                    if st.button("✏️", key=f"edit_{row['id']}", help="Edit"):
                        st.session_state["agenda_edit_id"] = int(row["id"])
                        st.rerun()
                    if st.button("🗑️", key=f"del_{row['id']}", help="Delete"):
                        delete_agenda_event(int(row["id"]))
                        st.rerun()
