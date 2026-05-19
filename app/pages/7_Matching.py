"""Matching automatico offerte ↔ bid sullo stesso prodotto."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from lib.data import get_matches, read_sheet
from lib.theme import apply_theme, kpi_card

st.set_page_config(page_title="Matching - Protein Trading", page_icon="🔗", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Matching offerte ↔ bid</div>
    <div class="page-sub">Incrocio automatico tra offerte dei fornitori e richieste dei clienti sullo stesso prodotto.</div>
    """,
    unsafe_allow_html=True,
)

# Bottoni utility
ca, cb = st.columns([4, 1])
with cb:
    if st.button("🔄 Ricarica", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------------------------
# Filtri
# -------------------------------------------------------------------
col_a, col_b, col_c = st.columns([2, 2, 2])
with col_a:
    open_only = st.checkbox("Solo bid OPEN", value=True)
with col_b:
    positive_only = st.checkbox("Solo margine positivo", value=True)
with col_c:
    sort_by = st.selectbox("Ordina per",
                            ["Margin USD/kg", "Margin USD", "Volume (kg)"],
                            index=0)

# -------------------------------------------------------------------
# Calcolo match
# -------------------------------------------------------------------
df = get_matches(open_bids_only=open_only)

if df.empty:
    st.info("Nessun match trovato. Verifica di avere offerte e bid sullo stesso Product.")
    st.stop()

if positive_only:
    df = df[df["Margin USD/kg"] > 0]

df = df.sort_values(sort_by, ascending=False, na_position="last").reset_index(drop=True)

# -------------------------------------------------------------------
# KPI sintetici
# -------------------------------------------------------------------
n_match = len(df)
pos = df[df["Margin USD/kg"] > 0]
n_pos = len(pos)
total_margin = float(pos["Margin USD"].sum()) if not pos.empty else 0.0
avg_margin_pct = (
    100 * (pos["Margin USD/kg"] / pos["Target USD/kg"]).mean()
    if not pos.empty else 0.0
)

c1, c2, c3, c4 = st.columns(4)
fmt = lambda n: f"{int(n):,}".replace(",", "'")
with c1:
    st.markdown(kpi_card("Match trovati", fmt(n_match), "totali"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Profittevoli", fmt(n_pos),
                           f"{100*n_pos/n_match:.0f}% del totale" if n_match else ""),
                  unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Margine totale",
                           f"USD {total_margin/1000:,.0f}k".replace(",", "'"),
                           "match con margine > 0"),
                  unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Margine medio %",
                           f"{avg_margin_pct:.1f}%",
                           "sui match positivi"),
                  unsafe_allow_html=True)

st.markdown("")

# -------------------------------------------------------------------
# Tabella match
# -------------------------------------------------------------------
display_cols = [
    "Bid ID", "Client", "Product (bid)", "Subproduct (bid)",
    "Offer ID", "Supplier", "Subproduct (offer)",
    "Target USD/kg", "Price USD/kg", "Margin USD/kg",
    "Volume (kg)", "Margin USD", "Status", "Need By Date",
]
display_cols = [c for c in display_cols if c in df.columns]

st.dataframe(
    df[display_cols],
    use_container_width=True,
    hide_index=True,
    height=460,
    column_config={
        "Bid ID": st.column_config.TextColumn("Bid", width="small"),
        "Offer ID": st.column_config.TextColumn("Offerta", width="small"),
        "Product (bid)": st.column_config.TextColumn("Prodotto"),
        "Subproduct (bid)": st.column_config.TextColumn("Sub (bid)"),
        "Subproduct (offer)": st.column_config.TextColumn("Sub (offer)"),
        "Target USD/kg": st.column_config.NumberColumn("Target $/kg", format="%.4f"),
        "Price USD/kg": st.column_config.NumberColumn("Offer $/kg", format="%.4f"),
        "Margin USD/kg": st.column_config.NumberColumn("Margin $/kg", format="%.4f"),
        "Volume (kg)": st.column_config.NumberColumn("Volume kg", format="%.0f"),
        "Margin USD": st.column_config.NumberColumn("Margin USD", format="$%.0f"),
    },
)

st.caption(
    f"**{n_match:,}** match in totale".replace(",", "'") +
    f", di cui **{n_pos:,}** con margine positivo".replace(",", "'")
)

st.markdown("---")

# -------------------------------------------------------------------
# Dettaglio match selezionato
# -------------------------------------------------------------------
st.markdown("### Dettaglio match")
pair_options = [f"{r['Bid ID']} ⇄ {r['Offer ID']}  ({r.get('Product (bid)', '')})"
                for _, r in df.iterrows()]
sel_pair = st.selectbox("Seleziona un match per vedere il dettaglio",
                          options=[""] + pair_options,
                          index=0)

if sel_pair:
    idx = pair_options.index(sel_pair)
    row = df.iloc[idx]
    bid_id = row["Bid ID"]
    offer_id = row["Offer ID"]

    suppliers = read_sheet("SUPPLIERS_CLEAN")
    clients = read_sheet("CLIENTS")
    bids = read_sheet("BIDS")
    offers = read_sheet("OFFERS")

    bid_row = bids[bids["Bid ID"].astype(str) == str(bid_id)]
    off_row = offers[offers["Offer ID"].astype(str) == str(offer_id)]

    col_b, col_o = st.columns(2)

    with col_b:
        st.markdown("##### 🎯 BID (cliente)")
        if not bid_row.empty:
            b = bid_row.iloc[0]
            client_name = str(b.get("Client", ""))
            # cerca match nel db clienti
            cli_match = clients[clients["Company Name"].astype(str).str.upper()
                                  == client_name.upper()]
            st.markdown(f"**{bid_id}** — {client_name}")
            cdata = {
                "Product": b.get("Product"),
                "Subproduct": b.get("Subproduct"),
                "Specifics": b.get("Specifics"),
                "Target Price": f"{b.get('Target Price', '')} {b.get('Currency', '')} / {b.get('Unit', '')}",
                "Target USD/kg": b.get("Target USD/kg"),
                "Volume (kg)": b.get("Volume (kg)"),
                "Incoterm": b.get("Incoterm"),
                "Origin Country": b.get("Origin Country"),
                "Need By Date": b.get("Need By Date"),
                "Status": b.get("Status"),
            }
            st.dataframe(pd.DataFrame(list(cdata.items()), columns=["Campo", "Valore"]),
                          hide_index=True, use_container_width=True)
            if not cli_match.empty:
                cm = cli_match.iloc[0]
                with st.expander("Dati cliente"):
                    st.write(f"**{cm['Company Name']}** — {cm.get('COUNTRY', '')}")
                    if cm.get("CONTACT PERSON"): st.write(f"Contatto: {cm['CONTACT PERSON']}")
                    if cm.get("Email"): st.write(f"Email: {cm['Email']}")
                    if cm.get("Phone"): st.write(f"Phone: {cm['Phone']}")
            else:
                st.caption("Cliente non in anagrafica — aggiungilo dalla pagina Clienti.")

    with col_o:
        st.markdown("##### 📈 OFFERTA (fornitore)")
        if not off_row.empty:
            o = off_row.iloc[0]
            supplier_name = str(o.get("Supplier", ""))
            sup_match = suppliers[suppliers["Company Name"].astype(str).str.upper()
                                    == supplier_name.upper()]
            st.markdown(f"**{offer_id}** — {supplier_name}")
            odata = {
                "Product": o.get("Product"),
                "Subproduct": o.get("Subproduct"),
                "Specifics": o.get("Specifics"),
                "Packaging": o.get("Packaging"),
                "Price": f"{o.get('Price', '')} {o.get('Currency', '')} / {o.get('Unit', '')}",
                "Price USD/kg": o.get("Price USD/kg"),
                "Incoterm": o.get("Incoterm"),
                "Country Destination": o.get("Country Destination"),
                "Offer Date": o.get("Offer Date"),
                "Source": o.get("Source"),
            }
            st.dataframe(pd.DataFrame(list(odata.items()), columns=["Campo", "Valore"]),
                          hide_index=True, use_container_width=True)
            if not sup_match.empty:
                sm = sup_match.iloc[0]
                with st.expander("Dati fornitore"):
                    st.write(f"**{sm['Company Name']}** — {sm.get('Country', '')}")
                    if sm.get("Contact Person"): st.write(f"Contatto: {sm['Contact Person']}")
                    if sm.get("Email"): st.write(f"Email: {sm['Email']}")
                    if sm.get("Phone"): st.write(f"Phone: {sm['Phone']}")

    # Riepilogo del margine
    st.markdown("---")
    st.markdown("##### Margine atteso")
    margin_kg = row.get("Margin USD/kg") or 0
    vol = row.get("Volume (kg)") or 0
    target = row.get("Target USD/kg") or 0
    margin_pct = (100 * margin_kg / target) if target else 0

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Margine USD/kg", f"{margin_kg:.4f}",
                  delta=f"{margin_pct:+.1f}%" if target else None,
                  delta_color="normal" if margin_kg >= 0 else "inverse")
    mc2.metric("Volume", f"{vol:,.0f} kg".replace(",", "'"))
    mc3.metric("Margine totale", f"USD {(margin_kg * vol):,.0f}".replace(",", "'"),
                  delta_color="normal" if margin_kg >= 0 else "inverse")
