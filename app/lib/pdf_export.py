"""Generazione PDF (schede fornitore/cliente, report margini)."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

# Colori marca
BRAND_DARK = colors.HexColor("#0b3d91")
BRAND_LIGHT = colors.HexColor("#dbe7ff")
GREY = colors.HexColor("#64748b")


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle("BrandH1", parent=base["Heading1"],
                              textColor=BRAND_DARK, fontSize=18, spaceAfter=4))
    base.add(ParagraphStyle("BrandSub", parent=base["Normal"],
                              textColor=GREY, fontSize=10, spaceAfter=14))
    base.add(ParagraphStyle("Section", parent=base["Heading2"],
                              textColor=BRAND_DARK, fontSize=12, spaceBefore=8, spaceAfter=4))
    base.add(ParagraphStyle("Label", parent=base["Normal"],
                              textColor=GREY, fontSize=8))
    base.add(ParagraphStyle("Value", parent=base["Normal"], fontSize=10))
    return base


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, A4[1] - 1.4 * cm, A4[0], 1.4 * cm, fill=True, stroke=False)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(2 * cm, A4[1] - 0.95 * cm, "PROTEIN TRADING")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 0.95 * cm,
                             datetime.now().strftime("%d/%m/%Y %H:%M"))
    # footer
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(2 * cm, 1 * cm, "Documento generato dalla Piattaforma Protein Trading")
    canvas.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def _kv_table(items: list[tuple[str, str]]) -> Table:
    """Tabella chiave-valore a 2 colonne."""
    rows = [[k, v if v not in (None, "") else "-"] for k, v in items]
    tbl = Table(rows, colWidths=[5 * cm, 11 * cm])
    tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GREY),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    return tbl


def supplier_card(row: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=2*cm, rightMargin=2*cm,
                              topMargin=2.2*cm, bottomMargin=2*cm)
    s = _styles()
    story = []
    name = str(row.get("Company Name", "") or "")
    story.append(Paragraph(name, s["BrandH1"]))
    story.append(Paragraph(f"Scheda fornitore - {row.get('Supplier ID', '')}", s["BrandSub"]))

    story.append(Paragraph("Anagrafica", s["Section"]))
    story.append(_kv_table([
        ("ID", str(row.get("Supplier ID", ""))),
        ("Nome azienda", str(row.get("Company Name", ""))),
        ("Categoria proteina", str(row.get("Protein Category", ""))),
        ("Paese", str(row.get("Country", ""))),
    ]))

    story.append(Paragraph("Contatti", s["Section"]))
    story.append(_kv_table([
        ("Contatto", str(row.get("Contact Person", ""))),
        ("Email", str(row.get("Email", ""))),
        ("Telefono", str(row.get("Phone", ""))),
        ("Sito web", str(row.get("Website", ""))),
        ("Indirizzo", str(row.get("Address", ""))),
    ]))

    story.append(Paragraph("Dettagli commerciali", s["Section"]))
    story.append(_kv_table([
        ("Prodotti", str(row.get("Products", ""))),
        ("Tax / VAT", str(row.get("Tax/VAT", ""))),
        ("Registration", str(row.get("Registration", ""))),
        ("Note", str(row.get("Notes", ""))),
    ]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


def client_card(row: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=2*cm, rightMargin=2*cm,
                              topMargin=2.2*cm, bottomMargin=2*cm)
    s = _styles()
    story = []
    name = str(row.get("Company Name", "") or "")
    story.append(Paragraph(name, s["BrandH1"]))
    story.append(Paragraph(f"Scheda cliente - {row.get('Client ID', '')}", s["BrandSub"]))

    story.append(Paragraph("Anagrafica", s["Section"]))
    story.append(_kv_table([
        ("ID", str(row.get("Client ID", ""))),
        ("Nome azienda", str(row.get("Company Name", ""))),
        ("Categoria proteina", str(row.get("PROTEIN CATEGORY", ""))),
        ("Paese", str(row.get("COUNTRY", ""))),
    ]))

    story.append(Paragraph("Contatti", s["Section"]))
    story.append(_kv_table([
        ("Contatto", str(row.get("CONTACT PERSON", ""))),
        ("Email", str(row.get("Email", ""))),
        ("Telefono", str(row.get("Phone", ""))),
    ]))

    story.append(Paragraph("Dettagli commerciali", s["Section"]))
    story.append(_kv_table([
        ("Items richiesti", str(row.get("ITEMS", ""))),
        ("Capacità mensile", str(row.get("Monthly Capacity", ""))),
        ("Note", str(row.get("Notes", ""))),
    ]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


def margins_report(df: pd.DataFrame, title: str = "Report Margini") -> bytes:
    """Report con top opportunità."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=1.5*cm, rightMargin=1.5*cm,
                              topMargin=2.2*cm, bottomMargin=2*cm)
    s = _styles()
    story = []
    story.append(Paragraph(title, s["BrandH1"]))
    story.append(Paragraph(f"Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}", s["BrandSub"]))

    if df.empty:
        story.append(Paragraph("Nessuna opportunità da mostrare.", s["Value"]))
        doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
        return buf.getvalue()

    # KPI in alto
    total = float(df["Margin USD"].sum()) if "Margin USD" in df.columns else 0
    n = len(df)
    avg_kg = float(df["Margin USD/kg"].mean()) if "Margin USD/kg" in df.columns else 0
    kpi = _kv_table([
        ("Opportunità trovate", str(n)),
        ("Margine totale potenziale", f"USD {total:,.0f}".replace(",", "'")),
        ("Margine medio USD/kg", f"{avg_kg:.4f}"),
    ])
    story.append(kpi)
    story.append(Spacer(1, 0.5*cm))

    # Tabella top
    cols = ["Bid ID", "Client", "Offer ID", "Supplier", "Product (bid)",
            "Margin USD/kg", "Volume (kg)", "Margin USD"]
    cols = [c for c in cols if c in df.columns]
    data = [cols]
    for _, r in df.head(25).iterrows():
        data.append([
            str(r.get(c, "")) if c not in ("Margin USD/kg", "Volume (kg)", "Margin USD")
            else (f"{r.get(c, 0):.4f}" if c == "Margin USD/kg" else
                  f"{r.get(c, 0):,.0f}".replace(",", "'"))
            for c in cols
        ])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("ALIGN", (-3, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(tbl)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()
