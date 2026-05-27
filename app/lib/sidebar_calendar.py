"""
Mini calendario mensile per la sidebar — versione senza st.columns().
Navigazione mese tramite query params per evitare problemi con Streamlit sidebar.
"""
from __future__ import annotations
import calendar
from datetime import date
import streamlit as st


def _iso_week(d: date) -> int:
    return d.isocalendar()[1]


def render_sidebar_calendar(events_dates: set = None):
    """
    Renderizza il mini calendario nella sidebar.
    Chiamare dentro `with st.sidebar:`.
    Nessun st.columns() — solo st.markdown() e st.button().
    """
    if events_dates is None:
        events_dates = set()

    today = date.today()

    if "cal_year"  not in st.session_state:
        st.session_state["cal_year"]  = today.year
    if "cal_month" not in st.session_state:
        st.session_state["cal_month"] = today.month

    year  = st.session_state["cal_year"]
    month = st.session_state["cal_month"]

    # ── Navigazione ──────────────────────────────────────────────────────
    month_label = date(year, month, 1).strftime("%B %Y")
    st.markdown(
        f"<div style='text-align:center;font-weight:700;font-size:.8rem;"
        f"color:#ccc;margin:4px 0'>{month_label}</div>",
        unsafe_allow_html=True,
    )
    b_prev = st.button("← Mese prec.", key="cal_prev", use_container_width=True)
    b_next = st.button("Mese succ. →", key="cal_next", use_container_width=True)

    if b_prev:
        if month == 1:
            st.session_state["cal_month"] = 12
            st.session_state["cal_year"]  = year - 1
        else:
            st.session_state["cal_month"] = month - 1
        st.rerun()

    if b_next:
        if month == 12:
            st.session_state["cal_month"] = 1
            st.session_state["cal_year"]  = year + 1
        else:
            st.session_state["cal_month"] = month + 1
        st.rerun()

    # ── Griglia calendario ───────────────────────────────────────────────
    cal   = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    iso_today = _iso_week(today)

    rows_html = ""
    for week in weeks:
        wn = _iso_week(week[3])
        cells = f'<td style="color:#555;font-size:.62rem;text-align:right;padding-right:3px">W{wn}</td>'
        for d in week:
            if d.month != month:
                cells += f'<td style="color:#333">{d.day}</td>'
            elif d == today:
                cells += (f'<td style="background:#e84e0f;color:#fff;font-weight:700;'
                          f'border-radius:50%;width:20px">{d.day}</td>')
            elif str(d) in events_dates:
                cells += f'<td style="color:#f0a500;font-weight:600">{d.day}</td>'
            else:
                cells += f'<td style="color:#ccc">{d.day}</td>'
        rows_html += f"<tr>{cells}</tr>"

    html = f"""
<div style="font-family:sans-serif;width:100%;margin-bottom:4px">
  <div style="text-align:center;font-size:.68rem;color:#aaa;margin-bottom:4px">
    Week <b style="color:#e84e0f">{iso_today}</b>
    &nbsp;·&nbsp; {today.strftime("%a %d %b %Y")}
  </div>
  <table style="border-collapse:collapse;width:100%;font-size:.70rem">
    <thead>
      <tr>
        <th style="color:#555;font-size:.6rem"></th>
        <th style="color:#777;text-align:center;padding:2px">Mo</th>
        <th style="color:#777;text-align:center;padding:2px">Tu</th>
        <th style="color:#777;text-align:center;padding:2px">We</th>
        <th style="color:#777;text-align:center;padding:2px">Th</th>
        <th style="color:#777;text-align:center;padding:2px">Fr</th>
        <th style="color:#c44;text-align:center;padding:2px">Sa</th>
        <th style="color:#c44;text-align:center;padding:2px">Su</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("---")
