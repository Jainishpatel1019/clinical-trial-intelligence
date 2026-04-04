"""Premium warm-palette design system — every pixel intentional."""

from __future__ import annotations

import streamlit as st

_BASE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&display=swap');

/* ── Reset & base ─────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    color: #2D2A26;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.stApp {
    background: #F7F5F0 !important;
}

section.main > div.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #EFEDE7 !important;
    border-right: 1px solid rgba(0,0,0,0.06) !important;
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.25rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-size: 0.85rem !important;
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8A857D !important;
    margin-bottom: 0.5rem !important;
}

/* ── Typography ───────────────────────────────────────────── */
h1 {
    font-family: "Playfair Display", Georgia, serif !important;
    font-weight: 500 !important;
    color: #1A1816 !important;
    letter-spacing: -0.025em;
    font-size: 2rem !important;
    line-height: 1.15 !important;
}
h2 {
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    color: #2D2A26 !important;
    font-size: 1.15rem !important;
    letter-spacing: -0.01em;
}
h3 {
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    color: #3D3929 !important;
    font-size: 0.95rem !important;
}
p, li, span, label {
    line-height: 1.6 !important;
}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.1rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    letter-spacing: 0.01em;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #C66A3E 0%, #B35A30 100%) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 1px 3px rgba(198, 106, 62, 0.3), 0 1px 2px rgba(0,0,0,0.06) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #B35A30 0%, #9A4D28 100%) !important;
    box-shadow: 0 4px 12px rgba(198, 106, 62, 0.35), 0 2px 4px rgba(0,0,0,0.08) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"],
.stButton > button:not([kind]) {
    background: #FFFFFF !important;
    color: #3D3929 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind]):hover {
    background: #F7F5F0 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    transform: translateY(-1px) !important;
}

/* ── Metric cards ─────────────────────────────────────────── */
div[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03), 0 1px 2px rgba(0,0,0,0.02) !important;
    transition: box-shadow 0.2s ease, transform 0.2s ease !important;
}
div[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 12px rgba(198,106,62,0.12), 0 2px 6px rgba(0,0,0,0.04) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: #8A857D !important;
}
[data-testid="stMetricValue"] {
    color: #1A1816 !important;
    font-weight: 600 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
}

/* ── Inputs & selects ─────────────────────────────────────── */
.stTextInput input, .stTextArea textarea {
    border-radius: 8px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    background-color: #FFFFFF !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    font-size: 0.9rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #C66A3E !important;
    box-shadow: 0 0 0 3px rgba(198, 106, 62, 0.12) !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    border-radius: 8px !important;
    border-color: rgba(0,0,0,0.1) !important;
    background-color: #FFFFFF !important;
}
.stSlider [data-baseweb="slider"] [role="slider"] {
    background-color: #C66A3E !important;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: #EFEDE7 !important;
    border-radius: 10px !important;
    padding: 3px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 0.45rem 1rem !important;
    color: #6B6560 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #FFFFFF !important;
    color: #1A1816 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── Expanders ────────────────────────────────────────────── */
details[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
}
details[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    font-size: 0.9rem !important;
}

/* ── Alerts ───────────────────────────────────────────────── */
.stAlert {
    border-radius: 10px !important;
    border: none !important;
    font-size: 0.9rem !important;
}

/* ── Dataframes ───────────────────────────────────────────── */
div[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
}

/* ── Plotly charts ────────────────────────────────────────── */
.js-plotly-plot .plotly .modebar {
    opacity: 0;
    transition: opacity 0.2s ease !important;
}
.js-plotly-plot:hover .plotly .modebar {
    opacity: 1;
}

/* ── Dividers ─────────────────────────────────────────────── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, rgba(0,0,0,0.06) 20%, rgba(0,0,0,0.06) 80%, transparent 100%) !important;
    margin: 1.5rem 0 !important;
}

/* ── Page-enter transition ────────────────────────────────── */
.main .block-container {
    animation: pageIn 0.3s ease;
}
@keyframes pageIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Shimmer progress bar (shown during long runs) ────────── */
.cti-progress-bar {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 3px;
    z-index: 9999;
    background: linear-gradient(90deg, #C66A3E, #E8A07A, #C66A3E);
    background-size: 200% 100%;
    animation: shimmer 1.5s linear infinite;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ── Floating hero dots ───────────────────────────────────── */
.cti-hero-wrap {
    position: relative;
    overflow: hidden;
}
.cti-hero-content { position: relative; z-index: 1; }
.float-dot {
    position: absolute;
    border-radius: 50%;
    background: rgba(198, 106, 62, 0.15);
    animation: floatUp linear infinite;
    z-index: 0;
    pointer-events: none;
}
@keyframes floatUp {
    0%   { transform: translateY(0);     opacity: 0.35; }
    100% { transform: translateY(-70px); opacity: 0; }
}

/* ── Card scroll-reveal ───────────────────────────────────── */
.cti-step-card {
    opacity: 0;
    transform: translateY(20px);
    animation: cardReveal 0.5s ease forwards;
}
@keyframes cardReveal {
    to { opacity: 1; transform: translateY(0); }
}
.cti-step-col:nth-child(1) .cti-step-card { animation-delay: 0.10s; }
.cti-step-col:nth-child(2) .cti-step-card { animation-delay: 0.20s; }
.cti-step-col:nth-child(3) .cti-step-card { animation-delay: 0.30s; }
.cti-step-col:nth-child(4) .cti-step-card { animation-delay: 0.40s; }
.cti-step-col:nth-child(5) .cti-step-card { animation-delay: 0.50s; }

/* ── How it works timeline ────────────────────────────────── */
.cti-how {
    display: flex;
    align-items: flex-start;
    gap: 0;
    margin: 1.5rem 0 2rem 0;
    position: relative;
}
.cti-how::before {
    content: '';
    position: absolute;
    top: 22px;
    left: calc(16.5% + 0px);
    right: calc(16.5% + 0px);
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(198,106,62,0.25), rgba(198,106,62,0.25), transparent);
    z-index: 0;
}
.cti-how-step {
    flex: 1;
    text-align: center;
    padding: 0 1rem;
    position: relative;
    z-index: 1;
}
.cti-how-num {
    font-family: "Playfair Display", serif;
    font-size: 2rem;
    font-weight: 500;
    color: #C66A3E;
    line-height: 1;
    margin-bottom: 0.5rem;
}
.cti-how-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #1A1816;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.35rem;
}
.cti-how-desc {
    font-size: 0.82rem;
    color: #6B6560;
    line-height: 1.5;
}

/* ── Key Finding box ──────────────────────────────────────── */
.cti-finding {
    background: #FDF6F0;
    border: 2px solid #C66A3E;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 20px;
}
.cti-finding-label {
    font-size: 11px;
    font-weight: 600;
    color: #C66A3E;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.cti-finding-text {
    font-size: 16px;
    color: #2D2A26;
    line-height: 1.6;
}

/* ── Spinners ─────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #C66A3E !important; }

/* ── Hide chrome ──────────────────────────────────────────── */
footer { visibility: hidden !important; height: 0 !important; }
#MainMenu { visibility: hidden !important; }

/* ── Home page hero ───────────────────────────────────────── */
.cti-hero {
    padding: 2.5rem 0 1.5rem 0;
}
.cti-hero-eyebrow {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #C66A3E;
    margin-bottom: 0.6rem;
}
.cti-hero-title {
    font-family: "Playfair Display", Georgia, serif !important;
    font-size: clamp(2.2rem, 5vw, 3.2rem);
    font-weight: 500;
    color: #1A1816;
    margin: 0;
    line-height: 1.1;
    letter-spacing: -0.03em;
}
.cti-hero-title .cti-accent {
    color: #C66A3E;
}
.cti-hero-sub {
    font-size: 1.1rem;
    color: #6B6560;
    max-width: 44rem;
    line-height: 1.65;
    margin: 0.75rem 0 1.5rem 0;
    font-weight: 400;
}

/* Tech pills */
.cti-tech-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #FFFFFF;
    color: #5A554E;
    padding: 5px 14px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 3px 4px 3px 0;
    border: 1px solid rgba(0,0,0,0.07);
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    transition: all 0.15s ease;
}
.cti-tech-badge:hover {
    border-color: rgba(198, 106, 62, 0.3);
    box-shadow: 0 2px 8px rgba(198, 106, 62, 0.1);
    transform: translateY(-1px);
}

/* Step cards */
.cti-step-card {
    background: #FFFFFF;
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 14px;
    padding: 1.25rem 1.15rem;
    height: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.cti-step-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #C66A3E, #D4956E);
    opacity: 0;
    transition: opacity 0.25s ease;
}
.cti-step-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.03);
    transform: translateY(-3px);
}
.cti-step-card:hover::before {
    opacity: 1;
}
.cti-step-card .step-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    display: block;
}
.cti-step-card h3 {
    margin: 0 0 0.35rem 0 !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #1A1816 !important;
}
.cti-step-card p {
    color: #6B6560;
    font-size: 0.84rem;
    margin: 0;
    line-height: 1.5;
}

/* Stat highlight row on home */
.cti-stat-row {
    display: flex;
    gap: 2rem;
    padding: 1rem 0;
}
.cti-stat-item {
    text-align: center;
}
.cti-stat-value {
    font-family: "Playfair Display", Georgia, serif;
    font-size: 2rem;
    font-weight: 500;
    color: #1A1816;
    line-height: 1;
}
.cti-stat-label {
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8A857D;
    margin-top: 0.3rem;
}

/* Section header */
.cti-section-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #B3AD9F;
    margin-bottom: 0.6rem;
}

/* Glass card for special sections */
.cti-glass-card {
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.03);
}

/* Geo map page specific */
.cti-map-container {
    background: #1A1816;
    border-radius: 20px;
    padding: 8px 4px 4px 4px;
    box-shadow: 0 12px 48px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.1);
    margin-bottom: 1.5rem;
    overflow: hidden;
}
.cti-geo-kpi {
    background: linear-gradient(135deg, #FFFFFF 0%, #F7F5F0 100%);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 14px;
    padding: 1.25rem;
    text-align: center;
    transition: all 0.2s ease;
}
.cti-geo-kpi:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.cti-geo-kpi .kpi-value {
    font-family: "Playfair Display", Georgia, serif;
    font-size: 1.75rem;
    font-weight: 500;
    color: #1A1816;
    line-height: 1;
}
.cti-geo-kpi .kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8A857D;
    margin-top: 0.4rem;
}
.cti-geo-kpi .kpi-sub {
    font-size: 0.78rem;
    color: #B3AD9F;
    margin-top: 0.15rem;
}
"""

_CHAT = """
section.main > div.block-container {
    max-width: 880px !important;
}

.cti-chat-shell { margin-bottom: 1.5rem; }
.cti-chat-brand {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 0.4rem;
}
.cti-chat-brand-mark {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: linear-gradient(145deg, #C66A3E 0%, #9A4D28 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 2px 10px rgba(198, 106, 62, 0.3);
}
.cti-chat-title {
    font-family: "Playfair Display", Georgia, serif !important;
    font-size: 1.85rem;
    font-weight: 500;
    color: #1A1816;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.cti-chat-sub {
    color: #6B6560;
    font-size: 0.95rem;
    margin: 0.25rem 0 0 56px;
    line-height: 1.55;
    max-width: 36rem;
}

[data-testid="stChatMessage"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
    border-radius: 16px !important;
    padding: 0.65rem 1rem !important;
    margin-bottom: 0.85rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
    line-height: 1.6;
}

[data-testid="stChatInput"] {
    border-radius: 999px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
}
[data-testid="stChatInput"] textarea {
    border-radius: 999px !important;
}

.cti-chat-welcome {
    background: linear-gradient(135deg, rgba(198,106,62,0.06) 0%, rgba(255,255,255,0.9) 60%);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0 1.5rem 0;
    color: #4A453D;
    line-height: 1.6;
}
.cti-chat-welcome strong { color: #B35A30; }
"""


def inject_theme(*, chat_layout: bool = False) -> None:
    """Inject global CSS. Use ``chat_layout=True`` on the RAG Assistant page."""
    css = _BASE + (_CHAT if chat_layout else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
