"""
Mini calendario mensile per la sidebar.
Mostra il mese corrente con settimane ISO numerate e oggi evidenziato.
Navigazione mese precedente/successivo tramite session_state.
"""
from __future__ import annotations
import calendar
from datetime import date
import streamlit as st


def _iso_week(d: date) -> int:
    return d.isocalendar()[1]


def _build_calendar_html(year: int, month: int, events_dates: set = None) -> str:
    """Genera HTML del mini calendario — tutto self-contained, nessun widget Streamlit."""
    if events_dates is None:
        events_dates = set()

    today = date.today()
    cal = calendar.Calendar(firstweekday=0)  # lunedì primo
    month_days = cal.monthdatescalendar(year, month)
    month_label = date(year, month, 1).strftime("%B %Y")
    iso_today = _iso_week(today)

    rows = ""
    seen_weeks = set()
    for week in month_days:
        wn = _iso_week(week[3])   # usa il giorno centrale per evitare ambiguità
        if wn in seen_weeks:
            wn = _iso_week(week[-1])
        seen_weeks.add(wn)

        cells = f'<td class="wk">{wn}</td>'
        for d in week:
            if d.month != month:
                cells += '<td class="out"> </td>'
            elif d == today:
                cells += f'<td class="tod">{d.day}</td>'
            elif str(d) in events_dates:
                cells += f'<td class="evt">{d.day}</td>'
            else:
                cells += f'<td>{d.day}</td>'
        rows += f"<tr>{cells}</tr>"

    return f"""
<style>
.sc-wrap {{ font-family: sans-serif; width:100%; margin-bottom:2px }}
.sc-head {{ text-align:center; font-size:.78rem; font-weight:700;
            color:#ccc; margin:0 0 4px 0; letter-spacing:.04em }}
.sc-week {{ text-align:center; font-size:.68rem; color:#aaa; margin-bottom:6px }}
.sc-week b {{ color:#e84e0f }}
.sc-cal {{ border-collapse:collapse; width:100%; font-size:.70rem }}
.sc-cal th {{ color:#777; text-align:center; padding:2px 0; font-weight:600 }}
.sc-cal td {{ text-align:center; padding:3px 1px; color:#ccc }}
.sc-cal td.wk  {{ color:#555; font-size:.62rem; text-align:right;
                  padding-right:4px; min-width:20px }}
.sc-cal td.out {{ color:#333 }}
.sc-cal td.tod {{ background:#e84e0f; color:#fff; font-weight:700;
                  border-radius:50%; width:20px }}
.sc-cal td.evt {{ color:#f0a500; font-weight:600 }}
</style>
<div class="sc-wrap">
  <div class="sc-week">
    Week <b>{iso_today}</b> &nbsp;·&nbsp; {today.strftime("%a %d %b %Y")}
  </div>
  <div class="sc-head">{month_label}</div>
  <table class="sc-cal">
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
</div>
"""


def render_sidebar_calendar(events_dates: set = None):
    """
    Renderizza il mini calendario nella sidebar.
    Deve essere chiamata DENTRO un blocco `with st.sidebar:`.
    """
    today = date.today()

    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year
    if "cal_month" not in st.session_state:
        st.session_state["cal_month"] = today.month

    year  = st.session_state["cal_year"]
    month = st.session_state["cal_month"]

    # HTML del calendario
    st.markdown(
        _build_calendar_html(year, month, events_dates or set()),
        unsafe_allow_html=True,
    )

    # Navigazione: due bottoni affiancati con HTML + pulsanti normali
    b1, b2 = st.columns(2)
    with b1:
        if st.button("◀ Prev", key="cal_prev", use_container_width=True):
            if month == 1:
                st.session_state["cal_month"] = 12
                st.session_state["cal_year"]  = year - 1
            else:
                st.session_state["cal_month"] = month - 1
            st.rerun()
    with b2:
        if st.button("Next ▶", key="cal_next", use_container_width=True):
            if month == 12:
                st.session_state["cal_month"] = 1
                st.session_state["cal_year"]  = year + 1
            else:
                st.session_state["cal_month"] = month + 1
            st.rerun()

    st.markdown("---")
