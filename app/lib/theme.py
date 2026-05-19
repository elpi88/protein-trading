"""CSS custom per dare un look 'banking premium' all'app."""
import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        /* Tipografia */
        html, body, [class*="css"] {
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
        }

        /* Header pagina */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b3d91 0%, #08306b 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #f1f5f9 !important;
        }
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stSelectbox label {
            color: #f1f5f9 !important;
        }

        /* Card KPI */
        .kpi-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06),
                        0 4px 12px rgba(15, 23, 42, 0.04);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(15, 23, 42, 0.08),
                        0 12px 24px rgba(15, 23, 42, 0.08);
        }
        .kpi-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
            margin-bottom: 6px;
            font-weight: 600;
        }
        .kpi-value {
            font-size: 2.0rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.1;
        }
        .kpi-sub {
            font-size: 0.85rem;
            color: #64748b;
            margin-top: 4px;
        }
        .kpi-accent {
            display: inline-block;
            width: 36px;
            height: 3px;
            background: #0b3d91;
            border-radius: 2px;
            margin-bottom: 12px;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background: #f1f5f9;
            border-radius: 10px 10px 0 0;
            padding: 10px 18px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: #0b3d91 !important;
            color: white !important;
        }

        /* Pulsanti */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid #cbd5e1;
            padding: 0.5rem 1.1rem;
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            border-color: #0b3d91;
            color: #0b3d91;
        }
        .stButton > button[kind="primary"] {
            background: #0b3d91;
            color: white;
            border: none;
        }
        .stButton > button[kind="primary"]:hover {
            background: #08306b;
            color: white;
        }

        /* DataFrame */
        [data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }

        /* Hero header pagina */
        .page-title {
            color: #0f172a;
            font-size: 1.9rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
            letter-spacing: -0.015em;
        }
        .page-sub {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }

        /* Badge categoria */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: white;
        }

        /* Hide hamburger e footer Streamlit (look pulito) */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* ============================================================
           MOBILE / TABLET — schermi <= 768px
           ============================================================ */
        @media (max-width: 768px) {
            /* Riduci padding generale per usare più spazio */
            .main .block-container {
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
            }

            /* Titolo pagina più compatto */
            .page-title {
                font-size: 1.35rem !important;
                line-height: 1.2 !important;
            }
            .page-sub {
                font-size: 0.85rem !important;
                margin-bottom: 1rem !important;
            }

            /* COLONNE: forza impilamento verticale su mobile.
               Streamlit di base le tiene affiancate, su mobile diventano illeggibili. */
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
                margin-bottom: 0.5rem;
            }

            /* Card KPI più compatte */
            .kpi-card {
                padding: 14px 16px;
            }
            .kpi-value {
                font-size: 1.6rem !important;
            }
            .kpi-label {
                font-size: 0.7rem !important;
            }

            /* PULSANTI: aumenta touch target (regola Apple/Google: min 44px) */
            .stButton > button,
            .stDownloadButton > button {
                min-height: 44px !important;
                padding: 0.7rem 1rem !important;
                font-size: 0.95rem !important;
            }

            /* Input più alti, più facili da toccare */
            .stTextInput input,
            .stNumberInput input,
            .stDateInput input,
            .stSelectbox > div > div {
                min-height: 44px !important;
                font-size: 16px !important;  /* 16px evita zoom Safari iOS */
            }

            /* Tabelle: scroll orizzontale e altezza ragionevole */
            [data-testid="stDataFrame"] {
                font-size: 0.82rem !important;
            }

            /* Sidebar: occupa tutto schermo quando aperta */
            section[data-testid="stSidebar"] {
                width: 85vw !important;
            }

            /* Tabs più piccoli */
            .stTabs [data-baseweb="tab"] {
                padding: 8px 12px !important;
                font-size: 0.85rem !important;
            }

            /* Riduci spazio sopra dataframe */
            .stDataFrame {
                margin-top: 0.5rem !important;
            }

            /* Plotly: ridimensiona */
            .js-plotly-plot, .plot-container {
                width: 100% !important;
            }
        }

        /* ============================================================
           SCHERMI MOLTO PICCOLI — phone in verticale (<= 480px)
           ============================================================ */
        @media (max-width: 480px) {
            .page-title { font-size: 1.2rem !important; }
            .kpi-value  { font-size: 1.4rem !important; }
            .main .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Colore per categoria proteina (coerente con macro VBA)
PROTEIN_COLORS = {
    "FISH":         "#4472C4",
    "PORK":         "#C65911",
    "BEEF":         "#C00000",
    "POULTRY":      "#BF8F00",
    "LAMB":         "#70AD47",
    "TRADER":       "#7030A0",
    "POTATOES":     "#DAA520",
    "POTATO":       "#DAA520",
    "OTHER":        "#808080",
    "UNCLASSIFIED": "#94A3B8",
}


def protein_badge(value: str) -> str:
    """Ritorna HTML di un badge colorato per la categoria proteina."""
    if not value:
        return ""
    color = PROTEIN_COLORS.get(str(value).strip().upper(), "#94A3B8")
    return f'<span class="badge" style="background:{color}">{value}</span>'


def kpi_card(label: str, value: str, sub: str = "") -> str:
    """Ritorna HTML di una card KPI per la dashboard."""
    return f"""
    <div class="kpi-card">
        <div class="kpi-accent"></div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """
