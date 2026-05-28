"""Ordini Fresco - disponibilità fornitore + ordini clienti settimanali."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib import auth
from lib.theme import apply_theme
from lib.db import get_supplier_products, get_supplier_names_with_products
from lib.fresh_orders import (
    init_fresh_tables, list_weeks, create_week, delete_week,
    parse_prevision_excel, save_availability, get_availability,
    add_fresh_order, update_fresh_order, delete_fresh_order,
    get_fresh_orders, get_allocation_summary, export_orders_excel,
    DAYS, DAYS_LABEL,
)

auth.require_login()
apply_theme()

st.markdown(
    '<div class="page-title">🥩 Ordini Fresco</div>'
    '<div class="page-sub">Disponibilità fornitore · Allocazione clienti · Export</div>',
    unsafe_allow_html=True,
)

init_fresh_tables()

# -----------------------------------------------------------------------
# Selezione settimana (sidebar-like nella pagina)
# -----------------------------------------------------------------------
weeks_df = list_weeks()

col_sel, col_new = st.columns([3, 1])
with col_sel:
    if weeks_df.empty:
        st.info("Nessuna settimana caricata. Crea la prima settimana →")
        selected_week_id = None
        selected_week_label = ""
    else:
        options = {
            f"Sett. {int(r['week_number'])} - {int(r['year'])} ({r['supplier'] or 'fornitore'})": int(r["id"])
            for _, r in weeks_df.iterrows()
        }
        sel_label = st.selectbox("Settimana di lavoro", list(options.keys()))
        selected_week_id = options[sel_label]
        selected_week_label = sel_label

with col_new:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Nuova settimana", use_container_width=True):
        st.session_state["show_new_week"] = True

if st.session_state.get("show_new_week"):
    with st.form("new_week_form"):
        st.markdown("**Crea nuova settimana**")
        c1, c2, c3 = st.columns(3)
        wn = c1.number_input("N° settimana", min_value=1, max_value=53, value=1)
        yr = c2.number_input("Anno", min_value=2024, max_value=2030, value=2026)
        sup = c3.text_input("Fornitore", value="Lorfood")
        notes = st.text_input("Note (opzionale)")
        ok = st.form_submit_button("Crea", type="primary")
        cancel = st.form_submit_button("Annulla")
    if ok:
        new_id = create_week(int(wn), int(yr), sup, notes)
        st.success(f"Settimana {wn}/{yr} creata.")
        st.session_state["show_new_week"] = False
        st.rerun()
    if cancel:
        st.session_state["show_new_week"] = False
        st.rerun()

if selected_week_id is None:
    st.stop()

st.markdown("---")

# -----------------------------------------------------------------------
# Tab principali
# -----------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📦 Disponibilità Fornitore", "📋 Ordini Clienti", "📥 Esporta"])


# ═══════════════════════════════════════════════════════════════════════
# TAB 1 — DISPONIBILITÀ
# ═══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Carica file disponibilità fornitore")
    st.caption("Carica il file PREVISION settimanale (es. PREVISION ITALIA SM-17.xlsx)")

    uploaded = st.file_uploader("Seleziona file Excel fornitore", type=["xlsx", "xls"])
    if uploaded:
        try:
            with st.spinner("Lettura file..."):
                df_avail = parse_prevision_excel(uploaded.read())
            if df_avail.empty:
                st.error("Nessun prodotto trovato nel file. Verifica il formato.")
            else:
                st.success(f"Trovati {len(df_avail)} prodotti. Anteprima:")
                day_cols = [c for c in ["lun_qty","mar_qty","mer_qty","gio_qty","ven_qty","sab_qty","dom_qty"]]
                show_cols = ["product_code","product_name","category","format","um"] + day_cols
                st.dataframe(df_avail[show_cols].head(20), use_container_width=True, hide_index=True)
                if st.button("✅ Salva disponibilità per questa settimana", type="primary"):
                    n = save_availability(selected_week_id, df_avail)
                    st.success(f"Salvati {n} prodotti per {selected_week_label}.")
                    st.rerun()
        except Exception as e:
            st.error(f"Errore nella lettura del file: {e}")

    st.markdown("---")
    st.markdown("### Disponibilità corrente")
    avail_df = get_availability(selected_week_id)
    if avail_df.empty:
        st.info("Nessuna disponibilità caricata per questa settimana. Usa il caricatore qui sopra.")
    else:
        # Riepilogo per giorno
        st.markdown("**Totale disponibile per giorno:**")
        day_totals = {}
        for d, label in zip(DAYS, DAYS_LABEL):
            col = f"{d}_qty"
            tot = float(avail_df[col].sum()) if col in avail_df.columns else 0
            day_totals[label[:3]] = tot
        dc = st.columns(7)
        for i, (label, tot) in enumerate(day_totals.items()):
            dc[i].metric(label, f"{int(tot):,}".replace(",", "'"))

        # Tabella filtrata per categoria
        categories = ["Tutte"] + sorted(avail_df["category"].dropna().unique().tolist())
        cat_filter = st.selectbox("Filtra per categoria", categories)
        df_show = avail_df if cat_filter == "Tutte" else avail_df[avail_df["category"] == cat_filter]
        day_col_labels = {f"{d}_qty": l for d, l in zip(DAYS, DAYS_LABEL)}
        df_show = df_show.rename(columns={
            "product_code": "Codice", "product_name": "Prodotto",
            "category": "Categoria", "format": "Formato", "um": "UM",
            **day_col_labels
        })
        show = ["Codice","Prodotto","Categoria","Formato","UM"] + list(DAYS_LABEL)
        show = [c for c in show if c in df_show.columns]
        st.dataframe(df_show[show], use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════
# TAB 2 — ORDINI CLIENTI
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    # Riepilogo allocazioni
    summary = get_allocation_summary(selected_week_id)
    st.markdown("**Disponibile vs Allocato per giorno:**")
    cols7 = st.columns(7)
    for i, row in summary.iterrows():
        with cols7[i]:
            rimanente = row["Rimanente"]
            color = "normal" if rimanente >= 0 else "inverse"
            st.metric(
                row["Giorno"][:3],
                f"{int(row['Allocato']):,}".replace(",","'"),
                f"rimane {int(rimanente):,}".replace(",","'"),
                delta_color=color,
            )

    st.markdown("---")

    # Form aggiunta ordine
    with st.expander("➕ Aggiungi ordine cliente", expanded=False):
        avail_df2 = get_availability(selected_week_id)
        products_list = []
        if not avail_df2.empty:
            products_list = sorted(
                avail_df2["product_name"].dropna().unique().tolist()
            )

        # Lista clienti dalla piattaforma
        try:
            from lib.data import read_sheet
            cli_df = read_sheet("CLIENTS")
            cli_list = sorted(cli_df["Company Name"].dropna().unique().tolist()) if not cli_df.empty else []
        except Exception:
            cli_list = []

        with st.form("add_order_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            client = c1.selectbox("Cliente", cli_list) if cli_list else c1.text_input("Cliente")

            # Menu a tendina: catalogo fornitore oppure lista disponibilità settimana
            suppliers_with_products = get_supplier_names_with_products()
            if suppliers_with_products:
                sup_fresco = c2.selectbox(
                    "Fornitore (catalogo)",
                    ["— lista disponibilità settimana —"] + suppliers_with_products,
                    key="fresco_sup_sel",
                )
                if sup_fresco != "— lista disponibilità settimana —":
                    prod_df_f = get_supplier_products(sup_fresco)
                    prod_opts_f = [""] + [f"{r['product_code']} — {r['product_name']}" for _, r in prod_df_f.iterrows()]
                    prod_sel_f = c2.selectbox("Prodotto *", prod_opts_f, key="fresco_prod_sel")
                    if prod_sel_f and " — " in prod_sel_f:
                        product_code = prod_sel_f.split(" — ")[0]
                        product_name = " — ".join(prod_sel_f.split(" — ")[1:])
                    else:
                        product_code = ""
                        product_name = prod_sel_f or ""
                elif products_list:
                    product_name = c2.selectbox("Prodotto *", products_list, key="fresco_prod_avail")
                    product_code = ""
                else:
                    product_name = c2.text_input("Prodotto *", key="fresco_prod_text")
                    product_code = ""
            elif products_list:
                product_name = c2.selectbox("Prodotto", products_list)
                product_code = ""
            else:
                product_name = c2.text_input("Prodotto")
                product_code = ""

            c3, c4 = st.columns(2)
            product_type = c3.text_input("Tipo/Variante (es. mixto Tarancon)")
            um_options = ["UN", "KG", "CAJA", "CT"]
            um = c4.selectbox("Unità di misura", um_options)

            c5, c6, c7 = st.columns(3)
            load_day = c5.selectbox("Giorno carico", DAYS_LABEL)
            load_date = c6.text_input("Data carico (gg/mm/aaaa)")
            quantity = c7.number_input("Quantità", min_value=0.0, step=1.0)

            c8, c9 = st.columns(2)
            price = c8.number_input("Prezzo (opzionale)", min_value=0.0, step=0.01, format="%.2f")
            delivery_notes = c9.text_input("Note scarico (es. descarga miercoles con Esselunga)")

            # Trova codice prodotto dalla disponibilità settimana (se non già impostato dal catalogo)
            if not product_code and not avail_df2.empty and product_name:
                match = avail_df2[avail_df2["product_name"] == product_name]
                if not match.empty:
                    product_code = match.iloc[0]["product_code"]

            submit_order = st.form_submit_button("Aggiungi ordine", type="primary")

        if submit_order:
            if not client or not product_name or quantity <= 0:
                st.error("Cliente, prodotto e quantità sono obbligatori.")
            else:
                day_key = DAYS[DAYS_LABEL.index(load_day)]
                try:
                    user = auth.get_current_user()["username"]
                except Exception:
                    user = "system"
                add_fresh_order(selected_week_id, {
                    "client": client,
                    "product_code": product_code,
                    "product_name": product_name,
                    "product_type": product_type,
                    "load_day": day_key,
                    "load_date": load_date,
                    "quantity": quantity,
                    "um": um,
                    "price": price if price > 0 else None,
                    "delivery_notes": delivery_notes,
                    "status": "confermato",
                }, user)
                st.success(f"Ordine aggiunto: {client} — {product_name} — {quantity} {um}")
                st.rerun()

    # Tabella ordini esistenti
    st.markdown("### Ordini della settimana")
    orders_df = get_fresh_orders(selected_week_id)
    if orders_df.empty:
        st.info("Nessun ordine inserito per questa settimana.")
    else:
        # Raggruppa per giorno
        for day, label in zip(DAYS, DAYS_LABEL):
            day_orders = orders_df[orders_df["load_day"] == day]
            if day_orders.empty:
                continue
            total_day = day_orders["quantity"].sum()
            st.markdown(f"**{label}** — {int(total_day):,} pz/kg totali".replace(",","'"))
            show_cols = ["client", "product_name", "product_type", "quantity", "um", "price", "delivery_notes", "status"]
            show_cols = [c for c in show_cols if c in day_orders.columns]
            renamed = day_orders[show_cols].rename(columns={
                "client": "Cliente", "product_name": "Prodotto",
                "product_type": "Tipo", "quantity": "Quantità",
                "um": "UM", "price": "Prezzo", "delivery_notes": "Note scarico",
                "status": "Stato"
            })
            st.dataframe(renamed, use_container_width=True, hide_index=True)

            # Elimina ordine
            with st.expander(f"🗑️ Elimina un ordine di {label}"):
                id_to_del = st.selectbox(
                    "ID ordine da eliminare",
                    day_orders["id"].tolist(),
                    key=f"del_{day}",
                    format_func=lambda x: f"ID {x} — " + str(day_orders[day_orders["id"]==x]["client"].values[0]) + " — " + str(day_orders[day_orders["id"]==x]["product_name"].values[0])
                )
                if st.button(f"Elimina ID {id_to_del}", key=f"btn_del_{day}", type="secondary"):
                    delete_fresh_order(int(id_to_del))
                    st.success("Ordine eliminato.")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# TAB 3 — EXPORT
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Esporta ordini in Excel")
    orders_exp = get_fresh_orders(selected_week_id)

    if orders_exp.empty:
        st.info("Nessun ordine da esportare per questa settimana.")
    else:
        clients_exp = sorted(orders_exp["client"].dropna().unique().tolist())

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 Esporta TUTTI i clienti (un foglio ciascuno)", use_container_width=True, type="primary"):
                try:
                    xlsx_bytes = export_orders_excel(selected_week_id)
                    st.download_button(
                        "⬇ Scarica Excel completo",
                        data=xlsx_bytes,
                        file_name=f"ordini_fresco_{selected_week_label.replace(' ','_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Errore export: {e}")

        with c2:
            sel_client = st.selectbox("Oppure scegli un cliente specifico", clients_exp)
            if st.button(f"📥 Esporta solo {sel_client}", use_container_width=True):
                try:
                    xlsx_bytes = export_orders_excel(selected_week_id, client=sel_client)
                    st.download_button(
                        f"⬇ Scarica Excel {sel_client}",
                        data=xlsx_bytes,
                        file_name=f"ordine_{sel_client.replace(' ','_')}_{selected_week_label.replace(' ','_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Errore export: {e}")

        st.markdown("---")
        st.markdown("**Riepilogo per cliente:**")
        summary_cli = orders_exp.groupby("client").agg(
            Ordini=("id", "count"),
            Quantità_totale=("quantity", "sum")
        ).reset_index().rename(columns={"client": "Cliente"})
        st.dataframe(summary_cli, use_container_width=True, hide_index=True)
