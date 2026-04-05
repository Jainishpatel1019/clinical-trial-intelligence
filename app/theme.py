"""Light clinical design system with warm cream tones and clinical blue accents."""

from __future__ import annotations

import streamlit as st

_BASE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Reset & base */
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    color: #1C1C1C;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.stApp {
    background: #FAFAF7 !important;
}

section.main > div.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #F3F2EE !important;
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
    color: #8C8C8C !important;
    margin-bottom: 0.5rem !important;
}

/* Sidebar nav capitalization */
section[data-testid="stSidebar"] a span,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    text-transform: capitalize !important;
}

/* Typography */
h1 {
    font-family: "Inter", sans-serif !important;
    font-weight: 700 !important;
    color: #1C1C1C !important;
    letter-spacing: -0.03em;
    font-size: 2rem !important;
    line-height: 1.15 !important;
}
h2 {
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    color: #1C1C1C !important;
    font-size: 1.15rem !important;
    letter-spacing: -0.01em;
}
h3 {
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    color: #2D2D2D !important;
    font-size: 0.95rem !important;
}
p, li, span, label {
    line-height: 1.6 !important;
    color: #4A4A4A;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: 999px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.01em;
    background: #1A5276 !important;
    border: none !important;
    color: #FFFFFF !important;
    box-shadow: 0 2px 8px rgba(26, 82, 118, 0.2) !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #154360 !important;
    box-shadow: 0 4px 16px rgba(26, 82, 118, 0.25) !important;
    transform: translateY(-1px) !important;
    color: #FFFFFF !important;
}
.stButton > button p,
.stDownloadButton > button p,
.stFormSubmitButton > button p,
.stButton > button span,
.stDownloadButton > button span,
.stFormSubmitButton > button span {
    color: #FFFFFF !important;
}

/* Metric cards */
div[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 16px !important;
    padding: 18px 20px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: all 0.2s ease !important;
}
div[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.06) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: #8C8C8C !important;
}
[data-testid="stMetricValue"] {
    color: #1C1C1C !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
}

/* Inputs & selects */
.stTextInput input, .stTextArea textarea {
    border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    background-color: #FFFFFF !important;
    color: #1C1C1C !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    font-size: 0.9rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #1A5276 !important;
    box-shadow: 0 0 0 3px rgba(26, 82, 118, 0.1) !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    border-radius: 12px !important;
    border-color: rgba(0,0,0,0.1) !important;
    background-color: #FFFFFF !important;
}
.stSlider [data-baseweb="slider"] [role="slider"] {
    background-color: #1A5276 !important;
}
.stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] > div {
    background: rgba(26, 82, 118, 0.25) !important;
}

/* Checkbox / multiselect */
.stMultiSelect [data-baseweb="tag"] {
    background-color: #EBF5FB !important;
    border-color: rgba(26, 82, 118, 0.2) !important;
    color: #1A5276 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: #F3F2EE !important;
    border-radius: 12px !important;
    padding: 3px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 0.45rem 1rem !important;
    color: #8C8C8C !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #FFFFFF !important;
    color: #1C1C1C !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* Expanders */
details[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
}
details[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    color: #1C1C1C !important;
}

/* Alerts */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
    font-size: 0.9rem !important;
}

/* Dataframes */
div[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* Plotly charts */
.js-plotly-plot .plotly .modebar {
    opacity: 0;
    transition: opacity 0.2s ease !important;
}
.js-plotly-plot:hover .plotly .modebar {
    opacity: 1;
}

/* Dividers */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, rgba(0,0,0,0.06) 20%, rgba(0,0,0,0.06) 80%, transparent 100%) !important;
    margin: 1.5rem 0 !important;
}

/* Page-enter transition */
.main .block-container {
    animation: pageIn 0.3s ease;
}
@keyframes pageIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Shimmer progress bar */
.cti-progress-bar {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 3px;
    z-index: 9999;
    background: linear-gradient(90deg, #1A5276, #5DADE2, #1A5276);
    background-size: 200% 100%;
    animation: shimmer 1.5s linear infinite;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Floating hero particles */
.cti-hero-wrap {
    position: relative;
    overflow: hidden;
}
.cti-hero-content { position: relative; z-index: 1; }
.float-dot {
    position: absolute;
    border-radius: 50%;
    background: rgba(26, 82, 118, 0.08);
    animation: floatUp linear infinite;
    z-index: 0;
    pointer-events: none;
}
@keyframes floatUp {
    0%   { transform: translateY(0) scale(1);   opacity: 0.3; }
    50%  { opacity: 0.15; }
    100% { transform: translateY(-70px) scale(0.6); opacity: 0; }
}

/* Card scroll-reveal */
.cti-step-card {
    opacity: 0;
    transform: translateY(20px);
    animation: cardReveal 0.5s ease forwards;
}
@keyframes cardReveal {
    to { opacity: 1; transform: translateY(0); }
}
.cti-step-col:nth-child(1) .cti-step-card { animation-delay: 0.08s; }
.cti-step-col:nth-child(2) .cti-step-card { animation-delay: 0.16s; }
.cti-step-col:nth-child(3) .cti-step-card { animation-delay: 0.24s; }
.cti-step-col:nth-child(4) .cti-step-card { animation-delay: 0.32s; }
.cti-step-col:nth-child(5) .cti-step-card { animation-delay: 0.40s; }

/* How it works timeline */
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
    left: calc(16.5%);
    right: calc(16.5%);
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(26, 82, 118, 0.2), rgba(26, 82, 118, 0.2), transparent);
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
    font-family: "Inter", sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #1A5276;
    line-height: 1;
    margin-bottom: 0.5rem;
}
.cti-how-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #1C1C1C;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.35rem;
}
.cti-how-desc {
    font-size: 0.82rem;
    color: #8C8C8C;
    line-height: 1.5;
}

/* Key Finding box */
.cti-finding {
    background: #EBF5FB;
    border: 1px solid rgba(26, 82, 118, 0.2);
    border-radius: 16px;
    padding: 20px 24px;
    margin-top: 20px;
}
.cti-finding-label {
    font-size: 11px;
    font-weight: 700;
    color: #1A5276;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.cti-finding-text {
    font-size: 16px;
    color: #1C1C1C;
    line-height: 1.6;
}

/* Spinners */
.stSpinner > div { border-top-color: #1A5276 !important; }

/* Hide chrome */
footer { visibility: hidden !important; height: 0 !important; }
#MainMenu { visibility: hidden !important; }

/* Home page hero */
.cti-hero {
    padding: 2.5rem 0 1.5rem 0;
}
.cti-hero-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #1A5276;
    margin-bottom: 0.6rem;
}
.cti-hero-title {
    font-family: "Inter", sans-serif !important;
    font-size: clamp(2.2rem, 5vw, 3.2rem);
    font-weight: 800;
    color: #1C1C1C;
    margin: 0;
    line-height: 1.1;
    letter-spacing: -0.03em;
}
.cti-hero-title .cti-accent {
    color: #1A5276;
}
.cti-hero-sub {
    font-size: 1.1rem;
    color: #6B6B6B;
    max-width: 44rem;
    line-height: 1.65;
    margin: 0.75rem 0 1.5rem 0;
    font-weight: 400;
}

/* Step cards */
.cti-step-card {
    background: #FFFFFF;
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 20px;
    padding: 1.4rem 1.25rem;
    height: 100%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}
.cti-step-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: #1A5276;
    opacity: 0;
    transition: opacity 0.25s ease;
}
.cti-step-card:hover {
    box-shadow: 0 8px 28px rgba(0,0,0,0.06);
    transform: translateY(-4px);
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
    color: #1C1C1C !important;
}
.cti-step-card p {
    color: #6B6B6B;
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
    font-family: "Inter", sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #1C1C1C;
    line-height: 1;
}
.cti-stat-label {
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8C8C8C;
    margin-top: 0.3rem;
}

/* Section header */
.cti-section-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #1A5276;
    margin-bottom: 0.6rem;
}

/* Glass card for special sections */
.cti-glass-card {
    background: rgba(255,255,255,0.8);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 20px;
    padding: 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* Geo map page */
.cti-map-container {
    background: #1C1C1C;
    border-radius: 20px;
    padding: 8px 4px 4px 4px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    margin-bottom: 1.5rem;
    overflow: hidden;
}
.cti-geo-kpi {
    background: #FFFFFF;
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 16px;
    padding: 1.25rem;
    text-align: center;
    transition: all 0.2s ease;
}
.cti-geo-kpi:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.cti-geo-kpi .kpi-value {
    font-family: "Inter", sans-serif;
    font-size: 1.75rem;
    font-weight: 800;
    color: #1C1C1C;
    line-height: 1;
}
.cti-geo-kpi .kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8C8C8C;
    margin-top: 0.4rem;
}
.cti-geo-kpi .kpi-sub {
    font-size: 0.78rem;
    color: #ABABAB;
    margin-top: 0.15rem;
}

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #8C8C8C !important;
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
    background: #1A5276;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 2px 10px rgba(26, 82, 118, 0.25);
}
.cti-chat-title {
    font-family: "Inter", sans-serif !important;
    font-size: 1.85rem;
    font-weight: 700;
    color: #1C1C1C;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.cti-chat-sub {
    color: #6B6B6B;
    font-size: 0.95rem;
    margin: 0.25rem 0 0 56px;
    line-height: 1.55;
    max-width: 36rem;
}

[data-testid="stChatMessage"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: 16px !important;
    padding: 0.65rem 1rem !important;
    margin-bottom: 0.85rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03) !important;
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
    line-height: 1.6;
    color: #4A4A4A;
}

[data-testid="stChatInput"] {
    border-radius: 999px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    background-color: #FFFFFF !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
}
[data-testid="stChatInput"] textarea {
    border-radius: 999px !important;
    color: #1C1C1C !important;
}

.cti-chat-welcome {
    background: #EBF5FB;
    border: 1px solid rgba(26, 82, 118, 0.12);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0 1.5rem 0;
    color: #4A4A4A;
    line-height: 1.6;
}
.cti-chat-welcome strong { color: #1A5276; }
"""


def inject_theme(*, chat_layout: bool = False) -> None:
    """Inject global CSS. Use ``chat_layout=True`` on the RAG Assistant page."""
    css = _BASE + (_CHAT if chat_layout else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
