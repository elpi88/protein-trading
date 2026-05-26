"""
PROTEIN TRADING - Entry point dell'app Streamlit.
Le pagine effettive sono in pages/.
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


# --- Setup primo admin ---
if not auth.has_users():
    setup_first_admin()
    st.stop()

# --- Login ---
if not st.session_state.get("logged_in"):
    login_form()
    st.stop()

# --- Navigazione esplicita (Streamlit >= 1.36) ---
pages = [
    st.Page("pages/0_Home.py",             title="Home",            icon="🏠", default=True),
    st.Page("pages/1_Dashboard.py",        title="Dashboard",       icon="📊"),
    st.Page("pages/2_Fornitori.py",        title="Fornitori",       icon="🏭"),
    st.Page("pages/3_Clienti.py",          title="Clienti",         icon="👥"),
    st.Page("pages/4_Offerte.py",          title="Offerte",         icon="📋"),
    st.Page("pages/5_Bid.py",              title="Bid",             icon="🎯"),
    st.Page("pages/7_Matching.py",         title="Matching",        icon="🔗"),
    st.Page("pages/8_Margini.py",          title="Margini",         icon="💰"),
    st.Page("pages/11_Spedizioni.py",      title="Spedizioni",      icon="🚢"),
    st.Page("pages/12_Ordini.py",          title="Ordini",          icon="📦"),
    st.Page("pages/13_Storico.py",         title="Storico",         icon="📜"),
    st.Page("pages/10_Merge_Duplicati.py", title="Merge Duplicati", icon="🔀"),
    st.Page("pages/14_Ordini_Fresco.py",   title="Ordini Fresco",   icon="🥩"),
    st.Page("pages/15_Carico_Camion.py",   title="Carico Camion",   icon="🚛"),
    st.Page("pages/16_Trasportatori.py",   title="Trasportatori",   icon="🚚"),
    st.Page("pages/6_Impostazioni.py",     title="Impostazioni",    icon="⚙️"),
]

pg = st.navigation(pages)
sidebar_user()
pg.run()
