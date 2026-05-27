"""
Generatore PDF professionale per offerte e ordini.
Produce documenti pronti da inviare via email.
"""
from __future__ import annotations
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# ── Colori brand ─────────────────────────────────────────────────────────
BRAND      = colors.HexColor("#0b3d91")
BRAND_LITE = colors.HexColor("#dbe7ff")
ACCENT     = colors.HexColor("#e84e0f")
GREY       = colors.HexColor("#64748b")
LGREY      = colors.HexColor("#f1f5f9")
WHITE      = colors.white
BLACK      = colors.HexColor("#1e293b")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("H1",   parent=s["Normal"], fontSize=20, textColor=BRAND,
                          fontName="Helvetica-Bold", spaceAfter=2))
    s.add(ParagraphStyle("H2",   parent=s["Normal"], fontSize=12, textColor=BRAND,
                          fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4))
    s.add(ParagraphStyle("Sub",  parent=s["Normal"], fontSize=9,  textColor=GREY, spaceAfter=12))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=9,  textColor=BLACK, spaceAfter=4))
    s.add(ParagraphStyle("Bold", parent=s["Normal"], fontSize=9,  textColor=BLACK,
                          fontName="Helvetica-Bold", spaceAfter=4))
    s.add(ParagraphStyle("Small", parent=s["Normal"], fontSize=8, textColor=GREY))
    s.add(ParagraphStyle("Footer", parent=s["Normal"], fontSize=7.5, textColor=GREY,
                          alignment=1))
    return s


def _header_table(doc_type: str, doc_id: str, doc_date: str, s) -> Table:
    """Riga di intestazione con nome documento e ID."""
    data = [[
        Paragraph(f"<b>PROTEIN TRADING</b>", s["H1"]),
        Paragraph(
            f"<b>{doc_type}</b><br/>"
            f"<font color='#64748b' size='9'>{doc_id} · {doc_date}</font>",
            s["H2"]
        ),
    ]]
    t = Table(data, colWidths=[PAGE_W - 2 * MARGIN - 6 * cm, 6 * cm])
    t.setStyle(TableStyle([
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",     (1, 0), (1, 0),  "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    return t


def _section_table(label: str, rows: list[tuple], s) -> list:
    """Blocco info con etichetta sezione + righe label/valore."""
    elements = [Paragraph(label, s["H2"])]
    table_data = [[Paragraph(k, s["Bold"]), Paragraph(str(v) if v else "—", s["Body"])]
                  for k, v in rows if v is not None]
    if table_data:
        t = Table(table_data, colWidths=[4 * cm, PAGE_W - 2 * MARGIN - 4 * cm])
        t.setStyle(TableStyle([
            ("VALIGN",    (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LGREY, WHITE]),
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
    return elements


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    canvas.drawString(MARGIN, 1.2 * cm, f"Generated: {ts}")
    canvas.drawRightString(PAGE_W - MARGIN, 1.2 * cm,
                           f"Page {doc.page}")
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════
# PDF OFFERTA
# ══════════════════════════════════════════════════════════════════════════
def generate_offer_pdf(row: dict) -> bytes:
    """
    Genera PDF professionale per una singola offerta.
    row: dizionario con le colonne della tabella OFFERS.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=2 * cm,
    )
    s = _styles()
    story = []

    # Intestazione
    offer_id   = str(row.get("Offer ID", "—"))
    offer_date = str(row.get("Offer Date", datetime.now().strftime("%Y-%m-%d")))
    story.append(_header_table("OFFER", offer_id, offer_date, s))
    story.append(Spacer(1, 0.4 * cm))

    # Fornitore
    story += _section_table("Supplier", [
        ("Company",   row.get("Supplier")),
        ("Source",    row.get("Source")),
        ("Notes",     row.get("Notes")),
    ], s)
    story.append(Spacer(1, 0.3 * cm))

    # Prodotto
    story += _section_table("Product Details", [
        ("Product",       row.get("Product")),
        ("Subproduct",    row.get("Subproduct")),
        ("Specifics",     row.get("Specifics")),
        ("Packaging",     row.get("Packaging")),
        ("Match Key",     row.get("Match Key")),
    ], s)
    story.append(Spacer(1, 0.3 * cm))

    # Prezzo e condizioni
    price_rows = [
        ("Price",          str(row.get("Price", "—")) + " " + str(row.get("Currency", ""))),
        ("Unit",           row.get("Unit")),
        ("Price USD/kg",   f"$ {row.get('Price USD/kg', '—')}"),
        ("Incoterm",       row.get("Incoterm")),
        ("Destination",    row.get("Country Destination")),
        ("Load Ready",     row.get("Load Ready Date")),
    ]
    story += _section_table("Price & Terms", price_rows, s)
    story.append(Spacer(1, 0.5 * cm))

    # Box prezzo evidenziato
    price_usd = row.get("Price USD/kg", "")
    if price_usd:
        highlight = Table(
            [[Paragraph(f"<b>Price: USD {price_usd} / kg</b>", s["H2"])]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        highlight.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BRAND_LITE),
            ("TEXTCOLOR",     (0, 0), (-1, -1), BRAND),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("ROUNDEDCORNERS", [4]),
        ]))
        story.append(highlight)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# PDF ORDINE / BID
# ══════════════════════════════════════════════════════════════════════════
def generate_bid_pdf(row: dict) -> bytes:
    """
    Genera PDF professionale per un bid/ordine cliente.
    row: dizionario con le colonne della tabella BIDS.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=2 * cm,
    )
    s = _styles()
    story = []

    bid_id   = str(row.get("Bid ID", "—"))
    bid_date = str(row.get("Bid Date", datetime.now().strftime("%Y-%m-%d")))
    story.append(_header_table("BID / ORDER", bid_id, bid_date, s))
    story.append(Spacer(1, 0.4 * cm))

    # Cliente
    story += _section_table("Client", [
        ("Company",  row.get("Client")),
        ("Status",   row.get("Status")),
        ("Notes",    row.get("Notes")),
    ], s)
    story.append(Spacer(1, 0.3 * cm))

    # Prodotto richiesto
    story += _section_table("Product Request", [
        ("Product",    row.get("Product")),
        ("Subproduct", row.get("Subproduct")),
        ("Specifics",  row.get("Specifics")),
        ("Packaging",  row.get("Packaging")),
        ("Volume",     f"{row.get('Volume (kg)', '—')} kg"),
    ], s)
    story.append(Spacer(1, 0.3 * cm))

    # Target price e condizioni
    story += _section_table("Target Price & Terms", [
        ("Target Price",    str(row.get("Target Price", "—")) + " " + str(row.get("Currency", ""))),
        ("Unit",            row.get("Unit")),
        ("Target USD/kg",   f"$ {row.get('Target USD/kg', '—')}"),
        ("Incoterm",        row.get("Incoterm")),
        ("Origin Country",  row.get("Origin Country")),
        ("Need By Date",    row.get("Need By Date")),
    ], s)
    story.append(Spacer(1, 0.5 * cm))

    # Box prezzo target evidenziato
    target = row.get("Target USD/kg", "")
    if target:
        highlight = Table(
            [[Paragraph(f"<b>Target: USD {target} / kg · Volume: {row.get('Volume (kg)', '—')} kg</b>", s["H2"])]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        highlight.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BRAND_LITE),
            ("TEXTCOLOR",     (0, 0), (-1, -1), BRAND),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ]))
        story.append(highlight)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
