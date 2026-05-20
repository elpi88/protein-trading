"""
PROTEIN TRADING - Piattaforma di gestione fornitori, clienti, offerte e bid.
Entry point dell'app Streamlit. Le pagine effettive sono in pages/.
"""
import streamlit as st

from lib.theme import apply_theme
from lib import auth

st.set_page_config(
    page_title="Protein Trading - Piattaforma",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()


def setup_first_admin():
    st.markdown(
        '<div class="page-title">Configurazione iniziale</div>'
        '<div class="page-sub">Crea il primo amministratore dell\'applicazione.</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "Nessun utente presente nel database. "
        "Crea ora l\'account amministratore: avra\' tutti i privilegi e "
        "potra\' creare altri utenti dalla pagina **Impostazioni**."
    )
    with st.form("first_admin", clear_on_submit=False):
        u = st.text_input("Username admin", value="nicolas")
        p1 = st.text_input("Password", type="password")
        p2 = st.text_input("Ripeti password", type="password")
        submit = st.form_submit_button("Crea amministratore", type="primary")
    if submit:
        if not u or not p1:
            st.error("Username e password sono obbligatori.")
            return
        if len(p1) < 8:
            st.error("La password deve essere lunga almeno 8 caratteri.")
            return
        if p1 != p2:
            st.error("Le due password non coincidono.")
            return
        ok = auth.create_user(u, p1, role="admin")
        if ok:
            st.success(f"Admin '{u}' creato. Ora effettua il login.")
            st.rerun()
        else:
            st.error("Username gia\' esistente o invalido.")


def login_form():
    st.markdown(
        '<div class="page-title">Accedi</div>'
        '<div class="page-sub">Inserisci le tue credenziali per accedere.</div>',
        unsafe_allow_html=True,
    )
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        with st.form("login", clear_on_submit=False):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submit = st.form_submit_button("Accedi", type="primary",
                                            use_container_width=True)
        if submit:
            user = auth.authenticate(u, p)
            if user:
                auth.login_session(user["username"], user["role"])
                st.rerun()
            else:
                st.error("Credenziali non valide.")


def sidebar_user():
    u = auth.get_current_user()
    if not u:
        return
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center; padding: 8px 0 16px 0;'>"
            "<div style='font-size: 1.4rem; font-weight: 800;'>PROTEIN TRADING</div>"
            "<div style='font-size: 0.78rem; opacity: 0.75; letter-spacing: 0.08em; "
            "text-transform: uppercase;'>Piattaforma di gestione</div></div>"
            f"<div style='text-align:center; padding-bottom: 8px; "
            f"font-size: 0.85rem; opacity: 0.85;'>Connesso come<br>"
            f"<b>{u['username']}</b> <span style='opacity:0.7;'>({u['role']})</span></div>",
            unsafe_allow_html=True,
        )
        if st.button("Esci", use_container_width=True):
            auth.logout()
            st.rerun()
        st.markdown("---")


# Routing principale
if not auth.has_users():
    setup_first_admin()
    st.stop()

if not st.session_state.get("logged_in"):
    login_form()
    st.stop()

sidebar_user()

u = auth.get_current_user()
st.markdown(
    f'<div class="page-title">Benvenuto, {u["username"].capitalize()}</div>'
    '<div class="page-sub">Piattaforma di trading proteine - fornitori, clienti, '
    'offerte e bid in un unico posto.</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("### Come iniziare")
    st.markdown(
        """
        Usa il **menu a sinistra** per navigare tra le sezioni:

        - **Dashboard** \u2014 numeri chiave e grafici in tempo reale
        - **Fornitori** \u2014 anagrafica completa, ricerca e modifica
        - **Clienti** \u2014 anagrafica clienti
        - **Offerte** \u2014 offerte ricevute dai fornitori
        - **Bid** \u2014 richieste dei clienti
        - **Impostazioni** \u2014 backup, gestione utenti (solo admin), refresh dati

        I dati ora sono su database SQLite (`protein_trading.db`),
        veloce e multi-utente.
        """
    )

with col2:
    st.info(
        "**Suggerimento**\n\n"
        "Puoi esportare i dati in Excel quando vuoi dalla pagina "
        "Impostazioni: utile per inviare report via email."
    )

st.markdown("---")

try:
    from lib.data import get_kpis
    from lib.theme import kpi_card
    kpis = get_kpis()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Fornitori",
                              f"{kpis['n_suppliers']:,}".replace(",", "'"),
                              "in anagrafica"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Clienti",
                              f"{kpis['n_clients']:,}".replace(",", "'"),
                              "in anagrafica"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Offerte",
                              f"{kpis['n_offers']:,}".replace(",", "'"),
                              "ricevute"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Bid aperti",
                              f"{kpis['n_bids_open']:,}".replace(",", "'"),
                              f"su {kpis['n_bids']} totali"),
                     unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Non riesco a leggere i dati: {e}")

st.markdown(
    "<div style='text-align:center; color:#94a3b8; font-size:0.8rem; "
    "margin-top:60px;'>v2.0 - Build per Nicolas Colombo - Maggio 2026</div>",
    unsafe_allow_html=True,
)
