"""Document Vault — archivio documenti per spedizioni e ordini."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from lib.auth import require_login
from lib.theme import apply_theme
from lib.db import (
    read_sheet,
    DOC_TYPES, REQUIRED_DOCS,
    save_document, list_documents,
    get_document_bytes, delete_document, get_missing_docs,
)

require_login()

st.set_page_config(page_title="Document Vault - Protein Trading", page_icon="🗄️", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="page-title">🗄️ Document Vault</div>
    <div class="page-sub">Archivio sicuro: Bill of Lading, Health Certificates, Customs & più.</div>
    """,
    unsafe_allow_html=True,
)

# ── Dati di supporto ────────────────────────────────────────────────────────
df_ship = read_sheet("SHIPMENTS")
df_inv  = read_sheet("INVOICES")

ship_ids = sorted(df_ship["Shipment ID"].dropna().tolist()) if not df_ship.empty else []
inv_ids  = sorted(df_inv["Invoice ID"].dropna().tolist())   if not df_inv.empty else []

ENTITY_LABELS = {
    "SHIPMENTS": "Spedizione",
    "INVOICES":  "Ordine / Fattura",
}

# ── Tab principali ──────────────────────────────────────────────────────────
tab_upload, tab_browse, tab_checklist = st.tabs([
    "📤 Carica Documento",
    "📂 Sfoglia Archivio",
    "✅ Checklist Mancanti",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD
# ════════════════════════════════════════════════════════════════════════════
with tab_upload:
    st.markdown("### Carica un nuovo documento")

    col1, col2 = st.columns(2)
    with col1:
        entity_type_label = st.selectbox(
            "Tipo documento collegato a",
            options=list(ENTITY_LABELS.values()),
            key="up_entity_label",
        )
        entity_type = [k for k, v in ENTITY_LABELS.items() if v == entity_type_label][0]

    with col2:
        id_list = ship_ids if entity_type == "SHIPMENTS" else inv_ids
        entity_id = st.selectbox(
            f"ID {entity_type_label}",
            options=id_list if id_list else ["— nessun record —"],
            key="up_entity_id",
        )

    col3, col4 = st.columns(2)
    with col3:
        doc_type = st.selectbox("Tipo di documento", options=DOC_TYPES, key="up_doc_type")
    with col4:
        notes = st.text_input("Note (opzionale)", key="up_notes")

    uploaded_file = st.file_uploader(
        "Seleziona file (PDF, JPG, PNG, DOCX…)",
        type=["pdf", "jpg", "jpeg", "png", "docx", "xlsx", "msg", "eml"],
        key="up_file",
    )

    if st.button("💾 Salva documento", type="primary", disabled=(not uploaded_file or entity_id == "— nessun record —")):
        user = st.session_state.get("username", "")
        content_bytes = uploaded_file.read()
        doc_id = save_document(
            entity_type=entity_type,
            entity_id=entity_id,
            doc_type=doc_type,
            filename=uploaded_file.name,
            content_bytes=content_bytes,
            notes=notes,
            uploaded_by=user,
        )
        if doc_id and doc_id > 0:
            st.success(f"✅ Documento salvato (ID: {doc_id}) — {uploaded_file.name}")
            st.rerun()
        else:
            st.error("❌ Errore nel salvataggio. Riprova.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — BROWSE
# ════════════════════════════════════════════════════════════════════════════
with tab_browse:
    st.markdown("### Tutti i documenti archiviati")

    # Filtri
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        f_entity = st.selectbox(
            "Filtra per tipo",
            options=["Tutti"] + list(ENTITY_LABELS.values()),
            key="br_entity",
        )
    with fcol2:
        f_id = st.text_input("Filtra per ID (es. SHP-00001)", key="br_id")
    with fcol3:
        f_doc = st.selectbox(
            "Filtra per tipo doc",
            options=["Tutti"] + DOC_TYPES,
            key="br_doc",
        )

    entity_type_filter = None
    if f_entity != "Tutti":
        entity_type_filter = [k for k, v in ENTITY_LABELS.items() if v == f_entity][0]

    df_docs = list_documents(
        entity_type=entity_type_filter or None,
        entity_id=f_id.strip() or None,
        doc_type=f_doc if f_doc != "Tutti" else None,
    )

    if df_docs.empty:
        st.info("Nessun documento trovato con i filtri selezionati.")
    else:
        st.markdown(f"**{len(df_docs)} documento/i trovati**")

        for _, row in df_docs.iterrows():
            label = ENTITY_LABELS.get(row["entity_type"], row["entity_type"])
            with st.expander(
                f"📄 {row['doc_type']}  ·  {label} {row['entity_id']}  ·  {row['uploaded_at'][:10] if row['uploaded_at'] else ''}",
                expanded=False,
            ):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**File:** {row['filename']}")
                    st.markdown(f"**Tipo:** {row['doc_type']}")
                    st.markdown(f"**Collegato a:** {label} — `{row['entity_id']}`")
                    if row.get("notes"):
                        st.markdown(f"**Note:** {row['notes']}")
                    if row.get("uploaded_by"):
                        st.markdown(f"**Caricato da:** {row['uploaded_by']}  ·  {row.get('uploaded_at', '')}")
                with c2:
                    # Download
                    file_bytes = get_document_bytes(int(row["id"]))
                    if file_bytes:
                        st.download_button(
                            label="⬇️ Scarica",
                            data=file_bytes,
                            file_name=row["filename"],
                            key=f"dl_{row['id']}",
                        )
                    else:
                        st.warning("File non trovato su disco")

                    # Elimina (solo admin)
                    from lib.auth import is_admin
                    if is_admin():
                        if st.button("🗑️ Elimina", key=f"del_{row['id']}"):
                            if delete_document(int(row["id"])):
                                st.success("Documento eliminato.")
                                st.rerun()
                            else:
                                st.error("Errore nell'eliminazione.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — CHECKLIST DOCUMENTI MANCANTI
# ════════════════════════════════════════════════════════════════════════════
with tab_checklist:
    st.markdown("### Documenti obbligatori mancanti")
    st.caption("Controlla quali spedizioni e ordini non hanno ancora tutti i documenti richiesti.")

    check_type_label = st.radio(
        "Verifica per",
        options=list(ENTITY_LABELS.values()),
        horizontal=True,
        key="chk_type",
    )
    check_type = [k for k, v in ENTITY_LABELS.items() if v == check_type_label][0]
    id_list_check = ship_ids if check_type == "SHIPMENTS" else inv_ids
    required = REQUIRED_DOCS.get(check_type, [])

    if not id_list_check:
        st.info(f"Nessun record trovato in {check_type_label}.")
    else:
        results = []
        for eid in id_list_check:
            missing = get_missing_docs(check_type, eid)
            results.append({
                "ID": eid,
                "Documenti mancanti": ", ".join(missing) if missing else "—",
                "Stato": "⚠️ Incompleto" if missing else "✅ Completo",
                "N. mancanti": len(missing),
            })

        df_check = pd.DataFrame(results)
        incomplete = df_check[df_check["N. mancanti"] > 0]
        complete   = df_check[df_check["N. mancanti"] == 0]

        kc1, kc2, kc3 = st.columns(3)
        kc1.metric("Totale", len(df_check))
        kc2.metric("✅ Completi", len(complete))
        kc3.metric("⚠️ Incompleti", len(incomplete))

        st.markdown(f"**Documenti obbligatori per {check_type_label}:** {', '.join(required)}")
        st.markdown("---")

        if not incomplete.empty:
            st.markdown("#### ⚠️ Record incompleti")
            st.dataframe(
                incomplete[["ID", "Documenti mancanti", "Stato"]],
                use_container_width=True,
                hide_index=True,
            )

        if not complete.empty:
            with st.expander(f"✅ Record completi ({len(complete)})", expanded=False):
                st.dataframe(
                    complete[["ID", "Stato"]],
                    use_container_width=True,
                    hide_index=True,
                )
