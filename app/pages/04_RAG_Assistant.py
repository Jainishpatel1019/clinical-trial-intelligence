"""RAG Assistant page for retrieval-augmented clinical trial Q&A."""

import hashlib
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _REPO_ROOT / ".env"
_DOTENV_LOADED = False
try:
    from dotenv import load_dotenv

    if _ENV_FILE.is_file():
        _DOTENV_LOADED = bool(load_dotenv(_ENV_FILE, override=True))
    _cwd_env = Path.cwd() / ".env"
    if _cwd_env.is_file() and _cwd_env.resolve() != _ENV_FILE.resolve():
        load_dotenv(_cwd_env, override=True)
except ImportError:
    pass

from src.data.schema import get_connection
from src.rag.indexer import TrialIndexer
from src.rag.qa_chain import TrialQAChain
from app.theme import inject_theme

st.set_page_config(page_title="RAG Assistant", page_icon="🤖", layout="wide")
inject_theme(chat_layout=True)


def _merge_llm_keys_from_streamlit_secrets() -> None:
    """Pick up keys from .streamlit/secrets.toml when env vars are empty (e.g. Cursor preview)."""
    try:
        sec = st.secrets
        for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
            if (os.environ.get(key) or "").strip():
                continue
            try:
                val = sec[key]
            except Exception:
                continue
            if val is not None and str(val).strip():
                os.environ[key] = str(val).strip()
    except Exception:
        pass


_merge_llm_keys_from_streamlit_secrets()

# Same placeholder strings as src.rag.qa_chain (non-secret).
_GEMINI_PLACEHOLDERS = frozenset({"your_gemini_api_key_here", "your_google_api_key_here"})
_ANTHROPIC_PLACEHOLDER = "your_anthropic_api_key_here"


def _env_llm_key(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _llm_env_fingerprint() -> str:
    """Hash of LLM-related env so cache invalidates when keys change (value not logged)."""
    blob = "|".join(
        [
            os.getenv("GEMINI_API_KEY") or "",
            os.getenv("GOOGLE_API_KEY") or "",
            os.getenv("ANTHROPIC_API_KEY") or "",
        ]
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:20]


@st.cache_resource
def get_indexer() -> TrialIndexer:
    return TrialIndexer()


@st.cache_resource
def get_qa_chain(_indexer: TrialIndexer, _llm_fp: str) -> TrialQAChain:
    return TrialQAChain(_indexer)


def build_index_if_needed(indexer: TrialIndexer, conn) -> None:
    if not indexer.index_exists():
        df = conn.execute("SELECT * FROM trials").df()
        indexer.build_index(df)
        return
    if not indexer.load_index():
        df = conn.execute("SELECT * FROM trials").df()
        indexer.build_index(df)


st.markdown(
    """
    <div class="cti-chat-shell">
      <div class="cti-chat-brand">
        <div class="cti-chat-brand-mark" aria-hidden="true">🧬</div>
        <h1 class="cti-chat-title">Ask Anything</h1>
      </div>
      <p class="cti-chat-sub">Ask questions about clinical trials in plain English.
      Every answer is backed by <strong>real trial data</strong> with sources you can verify.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

indexer = get_indexer()
conn = get_connection()
try:
    with st.spinner("Loading trial index..."):
        build_index_if_needed(indexer, conn)
except Exception as exc:
    st.error(
        "Could not load or build the trial index. "
        "Run `python scripts/generate_demo_data.py` (or ingest data) first."
    )
    st.caption(str(exc))
    st.stop()
finally:
    conn.close()

qa_chain = get_qa_chain(indexer, _llm_env_fingerprint())

with st.sidebar:
    st.header("Assistant Settings")

    k_results = st.slider("Trials to retrieve", 3, 10, 5)

    st.divider()
    if qa_chain.llm_backend == "gemini":
        st.success("✅ Powered by Google Gemini")
    elif qa_chain.llm_backend == "anthropic":
        st.success("✅ Powered by Claude")
    else:
        st.warning("⚠️ Demo mode — add GEMINI_API_KEY to .env for real answers")

    st.divider()
    st.markdown("**Try these questions:**")

    example_questions = [
        "Which condition has the highest average enrollment?",
        "Compare completion rates between Phase 2 and Phase 3 trials",
        "Which trials had more than 1000 participants and completed successfully?",
        "What is the average trial duration for randomized trials?",
        "Which conditions have the most trials in recruiting status?",
    ]

    for i, q in enumerate(example_questions):
        if st.button(q, use_container_width=True, key=f"eq_{i}"):
            st.session_state.pending_question = q

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        qa_chain.clear_history()
        st.rerun()

    if qa_chain._demo_mode:
        gk = _env_llm_key("GEMINI_API_KEY")
        gok = _env_llm_key("GOOGLE_API_KEY")
        ak = _env_llm_key("ANTHROPIC_API_KEY")
        gemini_is_placeholder = gk in _GEMINI_PLACEHOLDERS or gok in _GEMINI_PLACEHOLDERS
        anthropic_is_placeholder = ak == _ANTHROPIC_PLACEHOLDER
        if gemini_is_placeholder or anthropic_is_placeholder:
            st.warning(
                "⚠️ **Demo mode:** your `.env` still contains the **example placeholder** text "
                "from `.env.example` (e.g. `your_gemini_api_key_here`), not a real key. "
                "Replace it with a key from [Google AI Studio](https://aistudio.google.com/apikey) "
                "(Gemini keys usually start with `AIza` and are ~39 characters)."
            )
        else:
            st.warning(
                "⚠️ Demo mode: set **GEMINI_API_KEY** (or **GOOGLE_API_KEY**) or "
                "**ANTHROPIC_API_KEY** in `.env`, **`.streamlit/secrets.toml`**, or Space secrets."
            )
    elif qa_chain.llm_backend == "gemini":
        st.success("✅ Gemini API connected")
    else:
        st.success("✅ Claude API connected")

    with st.expander("LLM connection (troubleshooting)", expanded=False):
        st.caption("No secret values are shown — only whether variables are non-empty.")
        st.text(f"Repo .env path:\n{_ENV_FILE}")
        st.text(f"Repo .env exists: {_ENV_FILE.is_file()}")
        st.text(f"dotenv loaded that file: {_DOTENV_LOADED}")
        st.text(f"CWD: {Path.cwd()}")
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
            raw = (os.environ.get(name) or "").strip()
            n = len(raw)
            st.text(f"{name} length: {n}")
            if name in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and raw in _GEMINI_PLACEHOLDERS:
                st.caption(f"→ `{name}` is still the **template placeholder**, not a real key.")
            if name == "ANTHROPIC_API_KEY" and raw == _ANTHROPIC_PLACEHOLDER:
                st.caption("→ `ANTHROPIC_API_KEY` is still the **template placeholder**.")
        st.text(f"Active backend: {qa_chain.llm_backend}")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if not st.session_state.messages:
    st.markdown(
        '<div class="cti-chat-welcome">Try asking something like <strong>"Which cancer trials had '
        'the most patients?"</strong> or <strong>"What is the average success rate for diabetes '
        'trials?"</strong> — or pick a question from the sidebar.</div>',
        unsafe_allow_html=True,
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander(f"📚 {len(msg['sources'])} source trials"):
                for i, (src, text, score) in enumerate(
                    zip(msg["sources"], msg["source_texts"], msg["scores"])
                ):
                    conf_color = (
                        "🟢" if score > 0.55 else "🟡" if score > 0.38 else "🔵"
                    )
                    st.markdown(
                        f"**{conf_color} {src.get('brief_title', 'Unknown')}** "
                        f"(NCT: {src.get('nct_id', 'N/A')}) — Score: {score:.2f}"
                    )
                    st.caption(text)
                    if i < len(msg["sources"]) - 1:
                        st.divider()

prompt = st.chat_input("Ask about the clinical trials...")

if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching trials and generating answer..."):
            result = qa_chain.ask(prompt, k=k_results)

        st.markdown(result["answer"])

        confidence_icon = (
            "🟢 High confidence"
            if result["confidence"] == "High"
            else "🟡 Good match"
            if result["confidence"] == "Medium"
            else "🔵 Partial match"
        )
        st.caption(
            f"Confidence: {confidence_icon} | "
            f"Retrieved {len(result['source_trials'])} trials"
        )

        with st.expander(f"📚 {len(result['source_trials'])} source trials"):
            for i, (src, text, score) in enumerate(
                zip(
                    result["source_trials"],
                    result["source_texts"],
                    result["scores"],
                )
            ):
                conf_icon = "🟢" if score > 0.55 else "🟡" if score > 0.38 else "🔵"
                st.markdown(
                    f"**{conf_icon} {src.get('brief_title', 'Unknown')}** "
                    f"(NCT: {src.get('nct_id', 'N/A')})"
                )
                st.caption(text)
                if i < len(result["source_trials"]) - 1:
                    st.divider()

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["source_trials"],
            "source_texts": result["source_texts"],
            "scores": result["scores"],
        }
    )

st.caption(
    "⚠️ Answers are grounded in ClinicalTrials.gov public data. "
    "Always verify with primary sources before clinical decisions."
)
