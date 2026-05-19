"""
PROTEIN TRADING — Piattaforma di gestione fornitori, clienti, offerte e bid.
Entry point dell'app Streamlit. Le pagine effettive sono in pages/.
"""
import streamlit as st

from lib.theme import apply_theme

st.set_page_config(
    page_title="Protein Trading - Piattaforma",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ---------------------------------------------------------------------
# Sidebar: brand
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 8px 0 20px 0;">
            <div style="font-size: 1.4rem; font-weight: 800; letter-spacing: 0.02em;">
                PROTEIN TRADING
            </div>
            <div style="font-size: 0.78rem; opacity: 0.75; letter-spacing: 0.08em; text-transform: uppercase;">
                Piattaforma di gestione
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

# ---------------------------------------------------------------------
# Pagina principale (home)
# ---------------------------------------------------------------------
st.markdown(
    """
    <div class="page-title">Benvenuto, Nicolas</div>
    <div class="page-sub">Piattaforma di trading proteine - fornitori, clienti, offerte e bid in un unico posto.</div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### Come iniziare")
    st.markdown(
        """
        Usa il **menu a sinistra** per navigare tra le sezioni:

        - **Dashboard** — numeri chiave e grafici in tempo reale
        - **Fornitori** — anagrafica completa dei fornitori, ricerca e modifica
        - **Clienti** — anagrafica clienti
        - **Offerte** — offerte ricevute dai fornitori
        - **Bid** — richieste dei clienti
        - **Impostazioni** — backup, percorsi, refresh dati

        I dati sono letti e scritti sul file Excel `Protein_Trading_ERP_FULL.xlsm`.
        Ogni modifica fatta dall'app crea automaticamente un backup in `backups/`.
        """
    )

with col2:
    st.info(
        "**Suggerimento**\n\n"
        "Puoi continuare a usare Excel e le macro VBA in parallelo: "
        "questa app legge e scrive sullo stesso file."
    )

st.markdown("---")

# ---------------------------------------------------------------------
# Quick stats in home
# ---------------------------------------------------------------------
try:
    from lib.data import get_kpis
    from lib.theme import kpi_card

    kpis = get_kpis()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Fornitori", f"{kpis['n_suppliers']:,}".replace(",", "'"), "in anagrafica"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Clienti", f"{kpis['n_clients']:,}".replace(",", "'"), "in anagrafica"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Offerte", f"{kpis['n_offers']:,}".replace(",", "'"), "ricevute"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Bid aperti", f"{kpis['n_bids_open']:,}".replace(",", "'"),
                              f"su {kpis['n_bids']} totali"), unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Non riesco a leggere i dati: {e}")

st.markdown(
    """
    <div style="text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:60px;">
        v1.0 - Build per Nicolas Colombo - Maggio 2026
    </div>
    """,
    unsafe_allow_html=True,
)
