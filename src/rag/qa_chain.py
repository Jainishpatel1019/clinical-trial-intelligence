"""Direct RAG Q&A over indexed trials using Anthropic Claude (no LangChain)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.rag.indexer import TrialIndexer


class TrialQAChain:
    """Retrieve trial passages with ``TrialIndexer`` and answer with Claude or a demo stub."""

    def __init__(self, indexer: TrialIndexer, api_key: str | None = None) -> None:
        self.indexer = indexer
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.chat_history: list[dict[str, str]] = []
        self._demo_mode = not bool(self.api_key) or (
            self.api_key == "your_anthropic_api_key_here"
        )

    def _get_client(self) -> None:
        if self.client is None and not self._demo_mode:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)

    def _build_context(self, search_results: list[dict[str, Any]]) -> str:
        context = "RETRIEVED CLINICAL TRIAL DATA:\n\n"
        for i, result in enumerate(search_results, 1):
            context += f"[Trial {i} | Relevance: {result['score']:.2f}]\n"
            context += result["text"] + "\n\n"
        return context

    def ask(self, question: str, k: int = 5) -> dict[str, Any]:
        search_results = self.indexer.search(question, k=k)
        context = self._build_context(search_results)

        system_prompt = """You are a clinical trial intelligence analyst. 
Answer questions using ONLY the trial data provided in the context. 
Always mention the NCT ID when referencing a specific trial.
Be precise with numbers and statistics.
If the answer cannot be found in the provided context, say exactly: "The available trial data does not contain enough information to answer this question."
Keep answers concise — 2-4 sentences maximum unless a comparison or list is needed."""

        user_message = f"""Context:
{context}

Question: {question}"""

        if self._demo_mode:
            top_trial = search_results[0]["metadata"] if search_results else {}
            cr = top_trial.get("completion_rate")
            if cr is not None:
                cr_part = f"a {float(cr):.1%} completion rate"
            else:
                cr_part = "completion rate not available in metadata"
            answer = (
                "[DEMO MODE — Add ANTHROPIC_API_KEY to .env for real answers] "
                f"Based on the retrieved trials, the most relevant result is "
                f"{top_trial.get('brief_title', 'Unknown')} "
                f"(NCT ID: {top_trial.get('nct_id', 'N/A')}) with "
                f"{int(top_trial.get('enrollment_count', 0) or 0):,} participants and {cr_part}."
            )
        else:
            self._get_client()
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                block = response.content[0]
                answer = getattr(block, "text", str(block))
            except Exception as e:
                answer = (
                    f"Error calling Claude API: {e!s}. "
                    "Check your ANTHROPIC_API_KEY in .env"
                )

        confidence = (
            "High"
            if search_results and search_results[0]["score"] > 0.75
            else (
                "Medium"
                if search_results and search_results[0]["score"] > 0.5
                else "Low"
            )
        )

        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": answer})

        return {
            "answer": answer,
            "source_trials": [r["metadata"] for r in search_results],
            "source_texts": [r["text"][:300] + "..." for r in search_results],
            "scores": [r["score"] for r in search_results],
            "confidence": confidence,
        }

    def clear_history(self) -> None:
        self.chat_history = []
