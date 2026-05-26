"""
Carico Camion Fresco
- Selezione clienti del viaggio
- Ordine di scarico impostabile dall'utente
- Ordine di carico = inverso dello scarico
- Link Google Maps con tutte le tappe
- Gestione indirizzi clienti
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import urllib.parse
import streamlit as st
import pandas as pd
from lib import auth
from lib.theme import apply_theme
from lib.db import get_conn, DATABASE_URL

auth.require_login()
apply_theme()

st.markdown(
    '<div class="page-title">🚛 Carico Camion Fresco</div>'
    '<div class="page-sub">Pianifica l\'ordine di carico · Genera route Google Maps</div>',
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------
def _pk():
    return "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"


def init_truck_tables():
    # Migrazione in transazione separata (se fallisce fa rollback pulito)
    try:
        with get_conn() as conn:
            conn.execute('ALTER TABLE clients ADD COLUMN "Indirizzo Scarico" TEXT')
    except Exception:
        pass  # Colonna già presente - va bene

    # Creazione tabelle in transazione separata
    with get_conn() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS client_delivery_addresses (
                id {_pk()},
                client_name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                country TEXT DEFAULT 'Italy',
                notes TEXT
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS truck_trips (
                id {_pk()},
                trip_date TEXT,
                week_number INTEGER,
                driver TEXT,
                notes TEXT,
                created_at TEXT
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS truck_trip_stops (
                id {_pk()},
                trip_id INTEGER,
                delivery_order INTEGER,
                client_name TEXT,
                address TEXT,
                quantity TEXT,
                product_notes TEXT
            )
        """)


def get_all_addresses() -> pd.DataFrame:
    """Legge gli indirizzi di scarico dalla tabella clienti."""
    init_truck_tables()
    with get_conn() as conn:
        raw = conn._conn if hasattr(conn, "_conn") else conn
        return pd.read_sql_query(
            'SELECT "Client ID", "Company Name", "Indirizzo Scarico", "COUNTRY" '
            'FROM clients WHERE "Indirizzo Scarico" IS NOT NULL AND "Indirizzo Scarico" != \'\' '
            'ORDER BY "Company Name"',
            raw
        )


def save_address(client_name: str, address: str, city: str = "", country: str = "", notes: str = ""):
    """Aggiorna 'Indirizzo Scarico' nella tabella clienti."""
    full_address = ", ".join(filter(None, [address, city, country]))
    with get_conn() as conn:
        conn.execute(
            'UPDATE clients SET "Indirizzo Scarico" = ? WHERE "Company Name" = ?',
            (full_address, client_name)
        )
    # Svuota cache
    try:
        from lib.db import clear_cache
        clear_cache()
    except Exception:
        pass


def save_trip(stops: list[dict], trip_date: str, week_number: int, driver: str, notes: str) -> int:
    """Salva un viaggio con le sue tappe. Ritorna l'id del viaggio."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        if DATABASE_URL:
            cur = conn.execute(
                "INSERT INTO truck_trips (trip_date, week_number, driver, notes, created_at) "
                "VALUES (?,?,?,?,?) RETURNING id",
                (trip_date, week_number, driver, notes, ts)
            )
            trip_id = cur.fetchone()[0]
        else:
            conn.execute(
                "INSERT INTO truck_trips (trip_date, week_number, driver, notes, created_at) VALUES (?,?,?,?,?)",
                (trip_date, week_number, driver, notes, ts)
            )
            trip_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for stop in stops:
            conn.execute(
                "INSERT INTO truck_trip_stops (trip_id, delivery_order, client_name, address, quantity, product_notes) "
                "VALUES (?,?,?,?,?,?)",
                (trip_id, stop["delivery_order"], stop["client_name"],
                 stop.get("address", ""), stop.get("quantity", ""), stop.get("product_notes", ""))
            )
    return trip_id


def get_trips() -> pd.DataFrame:
    init_truck_tables()
    with get_conn() as conn:
        raw = conn._conn if hasattr(conn, "_conn") else conn
        return pd.read_sql_query(
            "SELECT t.*, COUNT(s.id) as n_stops FROM truck_trips t "
            "LEFT JOIN truck_trip_stops s ON s.trip_id = t.id "
            "GROUP BY t.id ORDER BY t.id DESC LIMIT 20",
            raw
        )


def get_trip_stops(trip_id: int) -> pd.DataFrame:
    with get_conn() as conn:
        raw = conn._conn if hasattr(conn, "_conn") else conn
        return pd.read_sql_query(
            "SELECT * FROM truck_trip_stops WHERE trip_id=? ORDER BY delivery_order",
            raw, params=(trip_id,)
        )


# -----------------------------------------------------------------------
# Google Maps helpers
# -----------------------------------------------------------------------
def build_gmaps_url(addresses: list[str]) -> str:
    """
    Costruisce URL Google Maps con più tappe (senza API key).
    Apre direttamente Google Maps nel browser con il percorso.
    """
    addresses = [a.strip() for a in addresses if a and a.strip()]
    if len(addresses) < 2:
        return ""
    encoded = [urllib.parse.quote(a) for a in addresses]
    # Formato: https://www.google.com/maps/dir/Indirizzo1/Indirizzo2/...
    return "https://www.google.com/maps/dir/" + "/".join(encoded)


def build_gmaps_embed_url(addresses: list[str]) -> str:
    """URL per iframe Google Maps (senza API key - usa search su primo indirizzo)."""
    if not addresses:
        return ""
    q = urllib.parse.quote(addresses[0])
    return f"https://www.google.com/maps/search/?api=1&query={q}"


# -----------------------------------------------------------------------
# Init
# -----------------------------------------------------------------------
init_truck_tables()

tab1, tab2, tab3 = st.tabs(["🚛 Pianifica Viaggio", "📍 Gestisci Indirizzi", "🗂️ Storico Viaggi"])


# ═══════════════════════════════════════════════════════════════════════
# TAB 1 — PIANIFICA VIAGGIO
# ═══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Componi il viaggio")

    # Info viaggio
    c1, c2, c3, c4 = st.columns(4)
    trip_date = c1.text_input("Data viaggio (gg/mm/aaaa)")
    week_num  = c2.number_input("N° settimana", min_value=1, max_value=53, value=1)
    driver    = c3.text_input("Autista")
    trip_notes = c4.text_input("Note viaggio")

    st.markdown("---")
    st.markdown("### Tappe di scarico (ordine consegna)")
    st.caption("Aggiungi i clienti nell'ordine in cui vuoi **scaricare**. Il carico sarà l'inverso automaticamente.")

    # Carica lista indirizzi registrati
    addr_df = get_all_addresses()
    addr_map = {}
    if not addr_df.empty:
        for _, r in addr_df.iterrows():
            addr_map[str(r["Company Name"])] = str(r.get("Indirizzo Scarico") or "")

    # Lista clienti disponibili
    try:
        from lib.data import read_sheet
        cli_df = read_sheet("CLIENTS")
        all_clients = sorted(cli_df["Company Name"].dropna().unique().tolist()) if not cli_df.empty else []
    except Exception:
        all_clients = []

    # Aggiungi cliente con indirizzo registrato come priorità
    clients_with_addr = list(addr_map.keys())
    clients_choice = clients_with_addr + [c for c in all_clients if c not in clients_with_addr]

    # Gestione tappe in session state
    if "trip_stops" not in st.session_state:
        st.session_state.trip_stops = []

    # Form aggiungi tappa
    with st.form("add_stop_form", clear_on_submit=True):
        sc1, sc2, sc3 = st.columns([3, 3, 1])
        stop_client = sc1.selectbox("Cliente", clients_choice) if clients_choice else sc1.text_input("Cliente")
        stop_qty    = sc2.text_input("Merce / Quantità (es. 900 UN Jamones mixto)")
        stop_notes  = sc3.text_input("Note")
        add_stop = st.form_submit_button("➕ Aggiungi tappa", type="primary")

    if add_stop and stop_client:
        address = addr_map.get(stop_client, "")
        st.session_state.trip_stops.append({
            "client_name": stop_client,
            "address": address,
            "quantity": stop_qty,
            "product_notes": stop_notes,
        })

    # Mostra e riordina le tappe
    if not st.session_state.trip_stops:
        st.info("Nessuna tappa aggiunta. Usa il form qui sopra per aggiungere clienti al viaggio.")
    else:
        n = len(st.session_state.trip_stops)

        st.markdown(f"**{n} tappe di scarico:**")
        for i, stop in enumerate(st.session_state.trip_stops):
            addr_display = stop.get("address") or "⚠️ indirizzo mancante"
            cols = st.columns([0.4, 3, 3, 2, 0.5, 0.5, 0.5])
            cols[0].markdown(f"**{i+1}°**")
            cols[1].markdown(f"**{stop['client_name']}**")
            cols[2].caption(addr_display)
            cols[3].caption(stop.get("quantity",""))
            # Sposta su
            if i > 0 and cols[4].button("▲", key=f"up_{i}"):
                st.session_state.trip_stops[i], st.session_state.trip_stops[i-1] = \
                    st.session_state.trip_stops[i-1], st.session_state.trip_stops[i]
                st.rerun()
            # Sposta giù
            if i < n-1 and cols[5].button("▼", key=f"dn_{i}"):
                st.session_state.trip_stops[i], st.session_state.trip_stops[i+1] = \
                    st.session_state.trip_stops[i+1], st.session_state.trip_stops[i]
                st.rerun()
            # Rimuovi
            if cols[6].button("✕", key=f"rm_{i}"):
                st.session_state.trip_stops.pop(i)
                st.rerun()

        st.markdown("---")

        # Ordine di CARICO (inverso dello scarico)
        stops_reversed = list(reversed(st.session_state.trip_stops))
        st.markdown("### 📦 Ordine di carico sul camion")
        st.caption("Il primo cliente caricato è l'ultimo a essere scaricato (in fondo al camion). L'ultimo caricato è il primo a scaricare (vicino alla porta).")

        load_rows = []
        for i, stop in enumerate(stops_reversed):
            addr_display = stop.get("address") or "⚠️ indirizzo mancante"
            load_rows.append({
                "Pos. carico": f"{i+1}°",
                "Cliente": stop["client_name"],
                "Indirizzo": addr_display,
                "Merce": stop.get("quantity",""),
                "Pos. scarico": f"{n - i}°",
            })
        st.dataframe(pd.DataFrame(load_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # Google Maps
        st.markdown("### 🗺️ Route Google Maps")
        addresses_in_order = [s.get("address","") for s in st.session_state.trip_stops]
        addresses_ok = [a for a in addresses_in_order if a]

        if len(addresses_ok) < 2:
            st.warning("Aggiungi almeno 2 clienti con indirizzo registrato per generare il percorso. Vai su **Gestisci Indirizzi** per registrarli.")
        else:
            missing = [s["client_name"] for s in st.session_state.trip_stops if not s.get("address","")]
            if missing:
                st.warning(f"⚠️ Indirizzi mancanti per: {', '.join(missing)}. Saranno esclusi dal percorso.")

            gmaps_url = build_gmaps_url(addresses_ok)
            st.markdown(
                f'<a href="{gmaps_url}" target="_blank" style="display:inline-block; '
                f'background:#0b3d91; color:white; padding:12px 24px; border-radius:8px; '
                f'text-decoration:none; font-weight:bold; font-size:1rem;">'
                f'🗺️ Apri percorso in Google Maps ({len(addresses_ok)} tappe)</a>',
                unsafe_allow_html=True
            )
            st.caption(f"Percorso: {' → '.join([s['client_name'] for s in st.session_state.trip_stops if s.get('address','')])}")

        st.markdown("---")

        # Salva viaggio
        col_save, col_clear = st.columns(2)
        with col_save:
            if st.button("💾 Salva viaggio nello storico", type="primary", use_container_width=True):
                stops_to_save = [
                    {**s, "delivery_order": i+1}
                    for i, s in enumerate(st.session_state.trip_stops)
                ]
                save_trip(stops_to_save, trip_date, int(week_num), driver, trip_notes)
                st.success("Viaggio salvato!")
                st.session_state.trip_stops = []
                st.rerun()
        with col_clear:
            if st.button("🗑️ Svuota tappe", use_container_width=True):
                st.session_state.trip_stops = []
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB 2 — GESTISCI INDIRIZZI
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Indirizzi di consegna clienti")
    st.caption("Registra una volta l'indirizzo di ogni cliente — verrà usato automaticamente nella pianificazione del camion.")

    # Form aggiungi/modifica indirizzo
    try:
        from lib.data import read_sheet
        cli_df2 = read_sheet("CLIENTS")
        all_clients2 = sorted(cli_df2["Company Name"].dropna().unique().tolist()) if not cli_df2.empty else []
    except Exception:
        all_clients2 = []

    with st.form("add_address_form", clear_on_submit=True):
        st.markdown("**Aggiungi o aggiorna indirizzo cliente**")
        ac1, ac2 = st.columns(2)
        addr_client = ac1.selectbox("Cliente", all_clients2) if all_clients2 else ac1.text_input("Cliente")
        addr_street = ac2.text_input("Via / Indirizzo (es. Via Roma 1)")
        ac3, ac4, ac5 = st.columns(3)
        addr_city    = ac3.text_input("Città")
        addr_country = ac4.text_input("Paese", value="Italy")
        addr_notes   = ac5.text_input("Note (opzionale)")
        save_addr = st.form_submit_button("💾 Salva indirizzo", type="primary")

    if save_addr and addr_client:
        if not addr_street and not addr_city:
            st.error("Inserisci almeno via o città.")
        else:
            save_address(addr_client, addr_street, addr_city, addr_country, addr_notes)
            st.success(f"Indirizzo salvato per {addr_client}.")
            st.rerun()

    # Tabella indirizzi esistenti
    addr_df2 = get_all_addresses()
    if addr_df2.empty:
        st.info("Nessun indirizzo registrato. Usa il form qui sopra per aggiungerne.")
    else:
        st.markdown(f"**{len(addr_df2)} clienti con indirizzo scarico:**")
        show_addr = addr_df2.rename(columns={
            "Company Name": "Cliente",
            "Indirizzo Scarico": "Indirizzo",
            "COUNTRY": "Paese"
        })
        show_cols = [c for c in ["Cliente","Indirizzo","Paese"] if c in show_addr.columns]
        st.dataframe(show_addr[show_cols], use_container_width=True, hide_index=True)
        st.caption("Per modificare un indirizzo, usa il form qui sopra inserendo lo stesso nome cliente.")


# ═══════════════════════════════════════════════════════════════════════
# TAB 3 — STORICO VIAGGI
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Storico viaggi salvati")
    trips_df = get_trips()

    if trips_df.empty:
        st.info("Nessun viaggio salvato ancora.")
    else:
        for _, trip in trips_df.iterrows():
            trip_id = int(trip["id"])
            label = f"📅 {trip.get('trip_date','?')}  |  Sett. {trip.get('week_number','?')}  |  Autista: {trip.get('driver','—')}  |  {int(trip.get('n_stops',0))} tappe"
            with st.expander(label):
                stops = get_trip_stops(trip_id)
                if stops.empty:
                    st.caption("Nessuna tappa registrata.")
                else:
                    # Ordine scarico
                    st.markdown("**Ordine scarico:**")
                    for _, s in stops.iterrows():
                        st.markdown(f"{int(s['delivery_order'])}° — **{s['client_name']}** — {s.get('address','')} — {s.get('quantity','')}")

                    # Ordine carico (inverso)
                    st.markdown("**Ordine carico (inverso):**")
                    stops_rev = stops.sort_values("delivery_order", ascending=False).reset_index(drop=True)
                    for i, s in stops_rev.iterrows():
                        st.markdown(f"{i+1}° carico — **{s['client_name']}**")

                    # Google Maps link
                    addresses_hist = [s.get("address","") for _, s in stops.iterrows() if s.get("address","")]
                    if len(addresses_hist) >= 2:
                        gmaps_url_hist = build_gmaps_url(addresses_hist)
                        st.markdown(f'<a href="{gmaps_url_hist}" target="_blank">🗺️ Apri percorso in Google Maps</a>', unsafe_allow_html=True)

                if trip.get("notes"):
                    st.caption(f"Note: {trip['notes']}")
