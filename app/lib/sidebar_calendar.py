"""
Mini calendario mensile per la sidebar.
Mostra il mese corrente con settimane ISO numerate e oggi evidenziato.
Navigazione mese precedente/successivo tramite session_state.
"""
from __future__ import annotations
import calendar
from datetime import date, datetime
import streamlit as st


def _iso_week(d: date) -> int:
    return d.isocalendar()[1]


def _build_calendar_html(year: int, month: int, events_dates: set = None) -> str:
    """Genera HTML del mini calendario."""
    if events_dates is None:
        events_dates = set()

    today = date.today()
    cal = calendar.Calendar(firstweekday=0)  # 0 = Monday
    month_days = cal.monthdatescalendar(year, month)
    month_name = date(year, month, 1).strftime("%B %Y")

    rows = ""
    last_week = None
    for week in month_days:
        week_num = _iso_week(week[0])
        if week_num == last_week:
            week_num = _iso_week(week[-1])
        last_week = week_num

        cells = f'<td class="wk-num">W{week_num}</td>'
        for d in week:
            cls = "other-month" if d.month != month else ""
            if d == today:
                cls += " today"
            if d.month == month and str(d) in events_dates:
                cls += " has-event"
            cells += f'<td class="{cls.strip()}">{d.day}</td>'
        rows += f"<tr>{cells}</tr>"

    html = f"""
    <style>
    .mini-cal {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.72rem;
        font-family: sans-serif;
        margin-bottom: 4px;
    }}
    .mini-cal th {{
        text-align: center;
        padding: 3px 1px;
        color: #888;
        font-weight: 600;
    }}
    .mini-cal .wk-num {{
        color: #aaa;
        font-size: 0.65rem;
        padding-right: 4px;
        text-align: right;
        min-width: 22px;
    }}
    .mini-cal td {{
        text-align: center;
        padding: 3px 2px;
        border-radius: 50%;
        cursor: default;
        color: #ddd;
    }}
    .mini-cal td.other-month {{
        color: #444;
    }}
    .mini-cal td.today {{
        background: #e84e0f;
        color: #fff !important;
        font-weight: 700;
        border-radius: 50%;
    }}
    .mini-cal td.has-event::after {{
        content: "•";
        color: #f0a500;
        font-size: 0.55rem;
        vertical-align: super;
    }}
    .cal-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        font-weight: 700;
        color: #ccc;
        margin-bottom: 4px;
        padding: 0 2px;
    }}
    .week-badge {{
        text-align: center;
        font-size: 0.7rem;
        color: #aaa;
        margin-bottom: 6px;
    }}
    </style>
    <div class="week-badge">
        Week <b style="color:#e84e0f">{_iso_week(today)}</b> &nbsp;|&nbsp; {today.strftime("%a, %d %b %Y")}
    </div>
    <table class="mini-cal">
      <thead>
        <tr>
          <th></th>
          <th>Mo</th><th>Tu</th><th>We</th>
          <th>Th</th><th>Fr</th>
          <th style="color:#c44">Sa</th>
          <th style="color:#c44">Su</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return html


def render_sidebar_calendar(events_dates: set = None):
    """
    Renderizza il mini calendario nella sidebar con navigazione mese.
    Chiama questa funzione all'interno di `with st.sidebar:`.
    """
    today = date.today()

    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year
    if "cal_month" not in st.session_state:
        st.session_state["cal_month"] = today.month

    year = st.session_state["cal_year"]
    month = st.session_state["cal_month"]
    month_label = date(year, month, 1).strftime("%B %Y")

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("‹", key="cal_prev", help="Mese precedente"):
            if month == 1:
                st.session_state["cal_month"] = 12
                st.session_state["cal_year"] = year - 1
            else:
                st.session_state["cal_month"] = month - 1
            st.rerun()
    with col2:
        st.markdown(
            f"<div style='text-align:center; font-weight:700; font-size:0.8rem; "
            f"color:#ccc; padding-top:6px'>{month_label}</div>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("›", key="cal_next", help="Mese successivo"):
            if month == 12:
                st.session_state["cal_month"] = 1
                st.session_state["cal_year"] = year + 1
            else:
                st.session_state["cal_month"] = month + 1
            st.rerun()

    html = _build_calendar_html(year, month, events_dates or set())
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("---")
