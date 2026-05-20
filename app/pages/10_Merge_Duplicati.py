"""Merge duplicati: 1) Auto-merge fuzzy con concatenazione  2) Merge manuale campo per campo."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from lib.data import (
    read_sheet, merge_records, merge_records_concat,
    find_potential_duplicates, find_fuzzy_duplicates, SCHEMAS,
)
from lib.theme import apply_theme

from lib.auth import require_login
require_login()


st.set_page_config(page_title="Merge duplicati - Protein Trading", page_icon="🔀", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">Merge duplicati</div>
    <div class="page-sub">Trova fornitori/clienti duplicati e unisci email, telefoni, contatti automaticamente.</div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Scelta entità
# -------------------------------------------------------------------
entity = st.radio("Cosa vuoi unire?",
                    ["Fornitori (SUPPLIERS_CLEAN)", "Clienti (CLIENTS)"],
                    horizontal=True)
sheet = "SUPPLIERS_CLEAN" if entity.startswith("Fornitori") else "CLIENTS"
df = read_sheet(sheet)
id_col = df.columns[0]

st.markdown("---")

# ===================================================================
# SEZIONE 1 — Auto-merge fuzzy (concatenazione automatica)
# ===================================================================
st.markdown("### 🔎 1. Trova duplicati automaticamente (fuzzy)")
st.caption(
    "Cerca aziende con nome **simile** (es. \"ACME SRL\" e \"Acme S.r.l. Trading\"). "
    "L'app ignora maiuscole, punteggiatura, spazi e suffissi legali (SRL, SPA, LTD, GMBH, SA, AG, …). "
    "Quando unisci, **email, telefoni e contatti vengono concatenati** con \"; \" — non perdi nulla."
)

cfg1, cfg2, _ = st.columns([2, 1, 3])
with cfg1:
    threshold = st.slider(
        "Soglia di similarità", min_value=50, max_value=100, value=85, step=5,
        help="100% = solo nomi identici (ignorando suffissi). "
             "85% = molto simili (consigliato). "
             "70% = generico, più falsi positivi."
    ) / 100.0
with cfg2:
    if st.button("🔍 Trova duplicati", type="primary", use_container_width=True):
        st.session_state["dedup_pairs"] = find_fuzzy_duplicates(sheet, threshold=threshold)
        st.session_state["dedup_sheet"] = sheet
        st.session_state["dedup_threshold"] = int(threshold * 100)

pairs = st.session_state.get("dedup_pairs", None)

if pairs is None:
    st.info("Clicca **Trova duplicati** per iniziare. Puoi cambiare la soglia se trovi troppi o troppo pochi risultati.")
elif pairs.empty:
    st.success(f"Nessun duplicato trovato con soglia {st.session_state.get('dedup_threshold', 85)}% su **{sheet}**. "
                 "Prova ad abbassare la soglia se vuoi una ricerca più ampia.")
else:
    st.markdown(f"Trovate **{len(pairs)} coppie** con soglia ≥ {st.session_state.get('dedup_threshold', 85)}%.")

    # Mostra le coppie con checkbox di selezione
    view = pairs.copy()
    view.insert(0, "✓ Unisci?", False)

    edited = st.data_editor(
        view,
        use_container_width=True,
        hide_index=True,
        height=380,
        disabled=["ID 1", "Nome 1", "ID 2", "Nome 2", "Similarità %"],
        column_config={
            "✓ Unisci?": st.column_config.CheckboxColumn(
                "Seleziona", help="Spunta le coppie che vuoi unire", width="small"
            ),
            "ID 1": st.column_config.TextColumn("ID 1 (tenuto)", width="small"),
            "Nome 1": st.column_config.TextColumn("Nome 1 (tenuto)", width="large"),
            "ID 2": st.column_config.TextColumn("ID 2 (eliminato)", width="small"),
            "Nome 2": st.column_config.TextColumn("Nome 2 (eliminato)", width="large"),
            "Similarità %": st.column_config.NumberColumn("Sim %", format="%.1f%%", width="small"),
        },
        key="dedup_editor",
    )

    sel = edited[edited["✓ Unisci?"] == True]
    st.caption(f"Selezionate: **{len(sel)}** coppie. "
                 "Per ogni coppia: il record **ID 1** rimane (con tutti i dati uniti), "
                 "il record **ID 2** viene eliminato. I riferimenti in OFFERS/BIDS/SHIPMENTS/INVOICES "
                 "vengono aggiornati al nome del record tenuto.")

    # Anteprima dettagliata della prima coppia selezionata
    if len(sel) > 0:
        first = sel.iloc[0]
        with st.expander(f"👁 Anteprima merge: **{first['ID 1']}** ← **{first['ID 2']}**", expanded=False):
            r1 = df[df[id_col].astype(str) == str(first["ID 1"])]
            r2 = df[df[id_col].astype(str) == str(first["ID 2"])]
            if not r1.empty and not r2.empty:
                d1 = r1.iloc[0].to_dict()
                d2 = r2.iloc[0].to_dict()
                rows = []
                for col in SCHEMAS[sheet][1:]:
                    v1 = d1.get(col)
                    v2 = d2.get(col)
                    v1s = "" if v1 is None or pd.isna(v1) else str(v1)
                    v2s = "" if v2 is None or pd.isna(v2) else str(v2)
                    # Anteprima del valore unito
                    if not v1s and not v2s:
                        merged = ""
                    elif not v1s:
                        merged = v2s
                    elif not v2s:
                        merged = v1s
                    elif v1s.strip().lower() == v2s.strip().lower():
                        merged = v1s
                    elif col == "Company Name":
                        merged = v1s  # non concatena il nome
                    else:
                        merged = f"{v1s}; {v2s}"
                    rows.append({
                        "Campo": col,
                        f"Valore in {first['ID 1']}": v1s,
                        f"Valore in {first['ID 2']}": v2s,
                        "Risultato dopo merge": merged,
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    btn1, btn2, _ = st.columns([2, 1, 3])
    with btn1:
        confirm_auto = st.button(
            f"✅ Unisci {len(sel)} coppie selezionate (concatenazione automatica)",
            type="primary", use_container_width=True, disabled=(len(sel) == 0)
        )
    with btn2:
        if st.button("✖ Pulisci ricerca", use_container_width=True):
            st.session_state.pop("dedup_pairs", None)
            st.rerun()

    if confirm_auto and len(sel) > 0:
        progress = st.progress(0.0, text="Inizio merge...")
        n_ok = 0
        n_fail = 0
        results = []
        # IMPORTANTE: se A→B e poi B→C, dopo il primo merge B non esiste più.
        # Filtriamo via le coppie che riferiscono ID già eliminati durante il batch.
        deleted_ids = set()
        for i, (_, row) in enumerate(sel.iterrows()):
            keep = str(row["ID 1"])
            drop = str(row["ID 2"])
            progress.progress((i + 1) / len(sel), text=f"Unisco {drop} → {keep} ({i+1}/{len(sel)})")
            if keep in deleted_ids or drop in deleted_ids:
                results.append({"ID tenuto": keep, "ID eliminato": drop,
                                 "Esito": "saltato (già unito in un'altra coppia)"})
                continue
            try:
                res = merge_records_concat(sheet, keep, drop)
                if res.get("ok"):
                    n_ok += 1
                    deleted_ids.add(drop)
                    results.append({
                        "ID tenuto": keep, "ID eliminato": drop,
                        "Esito": "OK",
                        "Campi uniti": ", ".join(res.get("fields_merged", [])) or "(nessun conflitto)",
                        "Riferimenti aggiornati": res.get("refs_updated", 0),
                    })
                else:
                    n_fail += 1
                    results.append({"ID tenuto": keep, "ID eliminato": drop,
                                     "Esito": f"errore: {res.get('error')}"})
            except Exception as e:
                n_fail += 1
                results.append({"ID tenuto": keep, "ID eliminato": drop,
                                 "Esito": f"errore: {e}"})

        progress.empty()
        if n_ok > 0:
            st.success(f"Merge completato: **{n_ok}** coppie unite con successo. "
                         f"Backup automatico salvato in `backups/`.")
            st.balloons()
        if n_fail > 0:
            st.error(f"{n_fail} merge falliti.")

        st.markdown("##### Riepilogo")
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

        # Reset
        st.session_state.pop("dedup_pairs", None)

st.markdown("---")

# ===================================================================
# SEZIONE 2 — Merge manuale (vecchia modalità, campo per campo)
# ===================================================================
with st.expander("⚙️ Merge manuale (avanzato) — scegli campo per campo quale valore tenere"):
    st.caption(
        "Usa questa modalità se vuoi controllo totale: per ogni campo decidi tu se tenere il valore del primo o del secondo record. "
        "Niente concatenazione."
    )

    # Suggerimenti rapidi: nomi identici (normalizzati)
    with st.expander("💡 Possibili duplicati con nome identico (normalizzato)"):
        dup_pairs = find_potential_duplicates(sheet)
        if dup_pairs.empty:
            st.success("Nessun duplicato palese rilevato.")
        else:
            st.dataframe(dup_pairs, use_container_width=True, hide_index=True)
            st.caption("Copia gli ID dalla tabella nei selettori sotto e clicca 'Confronta'.")

    st.markdown("##### Seleziona i due record da confrontare")
    options = [""] + df[id_col].astype(str).tolist()
    c1, c2, c3 = st.columns([3, 3, 1])
    with c1:
        keep_id = st.selectbox("ID da TENERE (rimane)", options=options, index=0, key="man_keep")
    with c2:
        drop_id = st.selectbox("ID da ELIMINARE (i dati vanno nel TENERE)", options=options, index=0, key="man_drop")
    with c3:
        do_compare = st.button("🔍 Confronta", use_container_width=True,
                                  disabled=not (keep_id and drop_id), key="man_compare")

    if keep_id and drop_id and keep_id != drop_id:
        keep_row = df[df[id_col].astype(str) == str(keep_id)]
        drop_row = df[df[id_col].astype(str) == str(drop_id)]
        if not keep_row.empty and not drop_row.empty:
            keep_data = keep_row.iloc[0].to_dict()
            drop_data = drop_row.iloc[0].to_dict()

            st.markdown(f"**Confronto: {keep_id} ⇄ {drop_id}**")

            chosen = {}
            columns = SCHEMAS[sheet][1:]
            header = st.columns([3, 3, 3, 2])
            header[0].markdown("**Campo**")
            header[1].markdown(f"**Valore in {keep_id}**")
            header[2].markdown(f"**Valore in {drop_id}**")
            header[3].markdown("**Quale tieni?**")

            prefill = {}
            for col in columns:
                kv = keep_data.get(col)
                dv = drop_data.get(col)
                if (pd.isna(kv) or kv is None or str(kv).strip() == "") and \
                   not (pd.isna(dv) or dv is None or str(dv).strip() == ""):
                    prefill[col] = "drop"
                else:
                    prefill[col] = "keep"

            for col in columns:
                cc1, cc2, cc3, cc4 = st.columns([3, 3, 3, 2])
                cc1.markdown(f"**{col}**")
                kv = keep_data.get(col); dv = drop_data.get(col)
                cc2.text(str(kv) if kv is not None and not pd.isna(kv) else "(vuoto)")
                cc3.text(str(dv) if dv is not None and not pd.isna(dv) else "(vuoto)")
                opts = ["keep", "drop"]
                labels = {"keep": f"Tieni {keep_id}", "drop": f"Tieni {drop_id}"}
                chosen[col] = cc4.radio(
                    f"man_choice_{col}", options=opts,
                    format_func=lambda x: labels[x],
                    index=opts.index(prefill[col]),
                    key=f"man_choice_{col}",
                    label_visibility="collapsed",
                )

            cf1, _ = st.columns([1, 5])
            with cf1:
                if st.button("✅ Esegui merge manuale", type="primary",
                              use_container_width=True, key="man_confirm"):
                    try:
                        ok = merge_records(sheet, keep_id, drop_id, chosen)
                        if ok:
                            st.success(f"Merge completato. {drop_id} fuso in {keep_id}.")
                            st.balloons()
                        else:
                            st.error("Errore: ID non trovato.")
                    except Exception as e:
                        st.error(f"Errore: {e}")
