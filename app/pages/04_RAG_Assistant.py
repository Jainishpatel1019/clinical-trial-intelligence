"""RAG Assistant page for retrieval-augmented clinical trial Q&A."""

import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import get_connection
from src.rag.indexer import TrialIndexer
from src.rag.qa_chain import TrialQAChain

st.set_page_config(page_title="RAG Assistant", page_icon="🤖", layout="wide")


@st.cache_resource
def get_indexer() -> TrialIndexer:
    return TrialIndexer()


@st.cache_resource
def get_qa_chain(_indexer: TrialIndexer) -> TrialQAChain:
    return TrialQAChain(_indexer)


def build_index_if_needed(indexer: TrialIndexer, conn) -> None:
    if not indexer.index_exists():
        df = conn.execute("SELECT * FROM trials").df()
        indexer.build_index(df)
        return
    if not indexer.load_index():
        df = conn.execute("SELECT * FROM trials").df()
        indexer.build_index(df)


st.title("🤖 Trial Intelligence Assistant")
st.markdown(
    "Ask questions about clinical trials in plain English. Answers are **grounded in real trial data** "
    "— no hallucinations."
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

qa_chain = get_qa_chain(indexer)

with st.sidebar:
    st.header("Assistant Settings")

    k_results = st.slider("Trials to retrieve", 3, 10, 5)

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
        st.warning(
            "⚠️ Demo mode: Add ANTHROPIC_API_KEY to .env for real AI answers"
        )
    else:
        st.success("✅ Claude API connected")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander(f"📚 {len(msg['sources'])} source trials"):
                for i, (src, text, score) in enumerate(
                    zip(msg["sources"], msg["source_texts"], msg["scores"])
                ):
                    conf_color = (
                        "🟢" if score > 0.75 else "🟡" if score > 0.5 else "🔴"
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
            "🟢 High"
            if result["confidence"] == "High"
            else "🟡 Medium"
            if result["confidence"] == "Medium"
            else "🔴 Low"
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
                conf_icon = "🟢" if score > 0.75 else "🟡" if score > 0.5 else "🔴"
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
