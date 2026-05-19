"""Ordini eseguiti / fatturati (INVOICES)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
import pandas as pd
import streamlit as st

from lib.data import read_sheet, add_row, update_row, delete_row, next_id, get_currencies
from lib.theme import apply_theme, kpi_card

st.set_page_config(page_title="Ordini - Protein Trading", page_icon="📦", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Ordini / Fatture</div>
    <div class="page-sub">Tutti gli ordini eseguiti, lo stato di pagamento, le scadenze.</div>
    """,
    unsafe_allow_html=True,
)

SHEET = "INVOICES"
df = read_sheet(SHEET)
PAYMENT_STATUS = ["PENDING", "PAID", "PARTIAL", "OVERDUE", "CANCELLED"]
today = date.today()

# Pre-calcolo overdue
if not df.empty and "Due Date" in df.columns and "Payment Status" in df.columns:
    df["_due_d"] = pd.to_datetime(df["Due Date"], errors="coerce").dt.date
    df["_overdue"] = df.apply(
        lambda r: (r["Payment Status"] not in ["PAID", "CANCELLED"])
                    and r["_due_d"] is not None
                    and (not pd.isna(r["_due_d"]))
                    and r["_due_d"] < today,
        axis=1
    )

# -------------------------------------------------------------------
# KPI
# -------------------------------------------------------------------
n_total = len(df)
n_paid = int((df.get("Payment Status", pd.Series()).astype(str).str.upper() == "PAID").sum()) if not df.empty else 0
n_pending = int((df.get("Payment Status", pd.Series()).astype(str).str.upper() == "PENDING").sum()) if not df.empty else 0
n_overdue = int(df["_overdue"].sum()) if "_overdue" in df.columns else 0

total_usd = 0.0
total_pending = 0.0
try:
    total_usd = float(pd.to_numeric(df["Total USD"], errors="coerce").sum())
    pending_mask = df["Payment Status"].astype(str).str.upper() != "PAID"
    total_pending = float(pd.to_numeric(df.loc[pending_mask, "Total USD"], errors="coerce").sum())
except Exception:
    pass

fmt = lambda n: f"{int(n):,}".replace(",", "'")
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_card("Ordini totali", fmt(n_total), f"{n_paid} pagati"), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("In sospeso", fmt(n_pending), "PENDING"), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("In ritardo", fmt(n_overdue), "scaduti non pagati"), unsafe_allow_html=True)
with c4:
    pending_str = f"USD {total_pending/1000:,.0f}k".replace(",", "'")
    st.markdown(kpi_card("Da incassare", pending_str, "valore non saldato"), unsafe_allow_html=True)

st.markdown("")

# -------------------------------------------------------------------
# Toolbar
# -------------------------------------------------------------------
left, mid, right = st.columns([3, 2, 1])
with left:
    q = st.text_input("Cerca", placeholder="Cerca cliente, prodotto, ID...",
                      label_visibility="collapsed")
with mid:
    st_sel = st.selectbox("Payment Status", ["Tutti"] + PAYMENT_STATUS, label_visibility="collapsed")
with right:
    if st.button("➕ Nuovo ordine", use_container_width=True, type="primary"):
        st.session_state["inv_mode"] = "add"
        st.session_state["inv_edit_id"] = None

view = df.copy()
if q:
    qq = q.lower()
    view = view[view.apply(lambda r: qq in " ".join(str(v) for v in r.values).lower(), axis=1)]
if st_sel != "Tutti" and "Payment Status" in view.columns:
    view = view[view["Payment Status"].astype(str).str.upper() == st_sel.upper()]

st.caption(f"**{len(view):,}** ordini".replace(",", "'") +
            (f" (filtrati su {len(df):,})".replace(",", "'") if len(view) != len(df) else ""))

# -------------------------------------------------------------------
# Alert ritardi
# -------------------------------------------------------------------
if n_overdue > 0:
    overdue_df = df[df.get("_overdue", False) == True]
    with st.expander(f"⚠️ {n_overdue} ordini scaduti non pagati", expanded=False):
        st.dataframe(overdue_df[["Invoice ID", "Client", "Product", "Total USD",
                                    "Due Date", "Payment Status"]],
                       use_container_width=True, hide_index=True,
                       column_config={
                           "Total USD": st.column_config.NumberColumn(format="$%.0f"),
                           "Due Date": st.column_config.DateColumn("Scadenza"),
                       })

# -------------------------------------------------------------------
# Tabella principale
# -------------------------------------------------------------------
display_cols = ["Invoice ID", "Date", "Bid ID", "Client", "Product",
                "Quantity", "Unit", "Unit Price", "Currency",
                "Total USD", "Payment Status", "Due Date"]
display_cols = [c for c in display_cols if c in view.columns]
st.dataframe(view[display_cols], use_container_width=True, hide_index=True, height=420,
               column_config={
                   "Invoice ID": st.column_config.TextColumn("ID", width="small"),
                   "Date": st.column_config.DateColumn("Data"),
                   "Quantity": st.column_config.NumberColumn(format="%.0f"),
                   "Unit Price": st.column_config.NumberColumn("$/unit", format="%.4f"),
                   "Total USD": st.column_config.NumberColumn(format="$%.0f"),
                   "Due Date": st.column_config.DateColumn("Scadenza"),
               })

# -------------------------------------------------------------------
# Azioni
# -------------------------------------------------------------------
st.markdown("##### Azioni su un ordine esistente")
col_id, col_b1, col_b2 = st.columns([3, 1, 1])
with col_id:
    sel_id = st.selectbox("ID ordine",
        options=[""] + view["Invoice ID"].astype(str).tolist() if not view.empty else [""],
        label_visibility="collapsed", placeholder="Seleziona un ordine...")
with col_b1:
    if st.button("✏️ Modifica", use_container_width=True, disabled=not sel_id):
        st.session_state["inv_mode"] = "edit"; st.session_state["inv_edit_id"] = sel_id
with col_b2:
    if st.button("🗑️ Cancella", use_container_width=True, disabled=not sel_id):
        st.session_state["inv_mode"] = "delete"; st.session_state["inv_edit_id"] = sel_id


mode = st.session_state.get("inv_mode")
edit_id = st.session_state.get("inv_edit_id")

if mode in ("add", "edit"):
    title = "Nuovo ordine" if mode == "add" else f"Modifica {edit_id}"
    new_id = next_id(SHEET) if mode == "add" else edit_id
    existing = {}
    if mode == "edit" and edit_id:
        row = df[df["Invoice ID"].astype(str) == str(edit_id)]
        if not row.empty:
            existing = row.iloc[0].to_dict()

    with st.expander(f"📝 {title}", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Invoice ID", value=new_id, disabled=True)
            bid_id_v = st.text_input("Bid ID di riferimento", value=str(existing.get("Bid ID", "") or ""))
            client = st.text_input("Client *", value=str(existing.get("Client", "") or ""))
            product = st.text_input("Product *", value=str(existing.get("Product", "") or ""))
            try:
                qty = st.number_input("Quantity", value=float(existing.get("Quantity") or 0),
                                         step=100.0, format="%.0f")
            except Exception:
                qty = st.number_input("Quantity", value=0.0, step=100.0, format="%.0f")
            unit = st.selectbox("Unit", ["KG", "LB", "MT"],
                                  index=["KG", "LB", "MT"].index(str(existing.get("Unit", "KG") or "KG"))
                                  if str(existing.get("Unit", "KG") or "KG") in ["KG", "LB", "MT"] else 0)
            try:
                up = st.number_input("Unit Price", value=float(existing.get("Unit Price") or 0),
                                        step=0.01, format="%.4f")
            except Exception:
                up = st.number_input("Unit Price", value=0.0, step=0.01, format="%.4f")
        with c2:
            currencies = get_currencies()
            cur_cur = str(existing.get("Currency", "USD") or "USD")
            if cur_cur and cur_cur not in currencies: currencies = [cur_cur] + currencies
            currency = st.selectbox("Currency", currencies,
                                      index=currencies.index(cur_cur) if cur_cur in currencies else 0)
            try:
                vat = st.number_input("VAT %", value=float(existing.get("VAT %") or 0),
                                         step=0.5, format="%.1f")
            except Exception:
                vat = st.number_input("VAT %", value=0.0, step=0.5, format="%.1f")
            try:
                total_inv = st.number_input("Total Invoice", value=float(existing.get("Total Invoice") or 0),
                                                step=10.0, format="%.2f")
            except Exception:
                total_inv = st.number_input("Total Invoice", value=0.0, step=10.0, format="%.2f")
            try:
                total_usd = st.number_input("Total USD", value=float(existing.get("Total USD") or 0),
                                                step=10.0, format="%.2f")
            except Exception:
                total_usd = st.number_input("Total USD", value=0.0, step=10.0, format="%.2f")
            cur_p = str(existing.get("Payment Status", "PENDING") or "PENDING")
            pay = st.selectbox("Payment Status", PAYMENT_STATUS,
                                 index=PAYMENT_STATUS.index(cur_p) if cur_p in PAYMENT_STATUS else 0)

        cd1, cd2, cd3 = st.columns(3)
        with cd1:
            d_def = existing.get("Date") if mode == "edit" else date.today()
            try:
                d = st.date_input("Data ordine", value=pd.to_datetime(d_def).date()
                                     if d_def and pd.notna(d_def) else date.today())
            except Exception:
                d = st.date_input("Data ordine", value=date.today())
        with cd2:
            dd_def = existing.get("Due Date") if mode == "edit" else None
            try:
                due = st.date_input("Due Date", value=pd.to_datetime(dd_def).date()
                                       if dd_def and pd.notna(dd_def) else None)
            except Exception:
                due = st.date_input("Due Date", value=None)
        with cd3:
            pd_def = existing.get("Paid Date") if mode == "edit" else None
            try:
                paid_d = st.date_input("Paid Date", value=pd.to_datetime(pd_def).date()
                                          if pd_def and pd.notna(pd_def) else None)
            except Exception:
                paid_d = st.date_input("Paid Date", value=None)

        notes = st.text_area("Notes", value=str(existing.get("Notes", "") or ""), height=70)

        cb1, cb2, _ = st.columns([1, 1, 4])
        with cb1: save_clicked = st.button("💾 Salva", type="primary", use_container_width=True)
        with cb2: cancel_clicked = st.button("✖ Annulla", use_container_width=True)

        if save_clicked:
            if not client.strip() or not product.strip():
                st.error("Client e Product sono obbligatori.")
            else:
                values = {
                    "Date": d if d else None,
                    "Bid ID": bid_id_v.strip() or None,
                    "Client": client.strip(),
                    "Product": product.strip(),
                    "Quantity": float(qty) if qty else None,
                    "Unit": unit,
                    "Unit Price": float(up) if up else None,
                    "Currency": currency,
                    "VAT %": float(vat) if vat else 0,
                    "Total Invoice": float(total_inv) if total_inv else None,
                    "Total USD": float(total_usd) if total_usd else None,
                    "Payment Status": pay,
                    "Due Date": due if due else None,
                    "Paid Date": paid_d if paid_d else None,
                    "Notes": notes.strip() or None,
                }
                try:
                    if mode == "add":
                        nid = add_row(SHEET, values)
                        st.success(f"Ordine aggiunto: {nid}")
                    else:
                        update_row(SHEET, edit_id, values)
                        st.success(f"Ordine {edit_id} aggiornato.")
                    st.session_state["inv_mode"] = None
                    st.session_state["inv_edit_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
        if cancel_clicked:
            st.session_state["inv_mode"] = None
            st.session_state["inv_edit_id"] = None
            st.rerun()

if mode == "delete" and edit_id:
    st.warning(f"Cancellare l'ordine **{edit_id}**?")
    cc1, cc2, _ = st.columns([1, 1, 4])
    with cc1:
        if st.button("🗑️ Sì, cancella", type="primary", use_container_width=True):
            delete_row(SHEET, edit_id)
            st.success(f"{edit_id} cancellato.")
            st.session_state["inv_mode"] = None
            st.session_state["inv_edit_id"] = None
            st.rerun()
    with cc2:
        if st.button("Annulla", use_container_width=True):
            st.session_state["inv_mode"] = None
            st.session_state["inv_edit_id"] = None
            st.rerun()
