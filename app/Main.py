"""Streamlit entrypoint - landing page."""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

from app.theme import inject_theme
from src.data.schema import get_connection, get_table_stats

st.set_page_config(
    page_title="Clinical Trial Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

for key, val in {"messages": [], "pending_question": None}.items():
    if key not in st.session_state:
        st.session_state[key] = val

_DOT_SPECS = [
    (10,  5,  4, 9,  0.0), (18, 20,  6, 11, 1.2), (30, 45,  8, 13, 0.4),
    (45, 70,  4, 10, 2.1), (60, 88,  6, 12, 0.8), (75, 15,  8, 14, 1.5),
    (85, 35,  4,  9, 0.3), (12, 60,  6, 11, 1.9), (50, 80, 10, 13, 0.6),
    (22, 92,  4, 10, 2.4), (68, 50,  6, 12, 1.1), (38, 10,  8,  8, 0.2),
    (80, 75,  4, 14, 1.7), (55, 28,  6,  9, 2.8), (25, 48, 10, 11, 0.9),
    (42, 90,  4, 13, 1.4), (72, 62,  8, 10, 2.2), (15, 82,  6, 12, 0.5),
    (90, 22,  4,  9, 1.8), (35, 72,  6, 14, 3.0),
]

_dot_divs = "\n".join(
    f'<div class="float-dot" style="top:{t}%;left:{l}%;'
    f'width:{s}px;height:{s}px;'
    f'animation-duration:{d}s;animation-delay:{delay}s;"></div>'
    for t, l, s, d, delay in _DOT_SPECS
)

st.markdown(
    f"""
    <div class="cti-hero-wrap">
        {_dot_divs}
        <div class="cti-hero-content cti-hero">
            <div class="cti-hero-eyebrow">Clinical Trial Intelligence</div>
            <div class="cti-hero-title">
                Find out which treatments<br>
                <span class="cti-accent">actually work, and for whom</span>
            </div>
            <p class="cti-hero-sub">
                Every year, thousands of clinical trials test new treatments for
                diseases like cancer, diabetes, and heart failure.
                This platform helps you explore that data, discover which patient
                groups benefit most, and get instant answers in plain English.
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

conn = None
try:
    conn = get_connection()
    stats = get_table_stats(conn)
    total = stats["total_trials"]
    n_cond = len(stats["conditions"])

    cols = st.columns(3)
    cols[0].metric("Trials in Database", f"{total:,}")
    cols[1].metric("Diseases Covered", str(n_cond))
    cols[2].metric("Data Source", "ClinicalTrials.gov")
except Exception:
    st.info("No data loaded yet. Visit **Data Explorer** in the sidebar to get started.")
finally:
    if conn is not None:
        conn.close()

st.markdown(
    """
    <div class="cti-how">
        <div class="cti-how-step">
            <div class="cti-how-num">01</div>
            <div class="cti-how-title">Explore</div>
            <div class="cti-how-desc">Browse thousands of clinical trials filtered by disease, phase, and size</div>
        </div>
        <div class="cti-how-step">
            <div class="cti-how-num">02</div>
            <div class="cti-how-title">Discover</div>
            <div class="cti-how-desc">See which patient groups benefit most from each treatment</div>
        </div>
        <div class="cti-how-step">
            <div class="cti-how-num">03</div>
            <div class="cti-how-title">Act</div>
            <div class="cti-how-desc">Download a PDF report with findings ready to share with your team</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="cti-section-label">What you can do</div>', unsafe_allow_html=True)

steps = [
    (
        "📊", "Explore Trials",
        "Browse thousands of real clinical trials. Filter by disease, "
        "trial phase, or status. See how big they are and how long they take."
    ),
    (
        "🔬", "Who Benefits Most?",
        "Find out which patient groups, by age, disease, or trial size, "
        "get the biggest benefit from a treatment. Not averages. Specifics."
    ),
    (
        "🎲", "Smarter Trial Design",
        "See what happens when you stop giving patients the losing treatment "
        "early. The simulator shows how many more people get the better option."
    ),
    (
        "💬", "Ask Anything",
        'Type a question like "Which cancer trials had the best results?" '
        "and get an answer backed by real data, with sources cited."
    ),
    (
        "🗺️", "Global View",
        "See where trials happen around the world on an interactive 3D globe. "
        "Zoom, rotate, and explore by disease or region."
    ),
]

cols = st.columns(5)
for col, (icon, title, desc) in zip(cols, steps):
    col.markdown(
        f'<div class="cti-step-col"><div class="cti-step-card">'
        f'<span class="step-icon">{icon}</span>'
        f'<h3>{title}</h3>'
        f'<p>{desc}</p>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.markdown(
        '<div style="font-family: Inter, sans-serif; font-size: 1.3rem; '
        'font-weight: 700; color: #1C1C1C; margin-bottom: 0.25rem;">🧬 Trial Intelligence</div>',
        unsafe_allow_html=True,
    )
    st.caption("Select a page above to get started.")
