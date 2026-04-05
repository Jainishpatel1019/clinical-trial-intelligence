"""Direct RAG Q&A over indexed trials using Gemini, Anthropic Claude, or a demo stub."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from src.rag.indexer import TrialIndexer

_LLMBackend = Literal["demo", "gemini", "anthropic"]

_GEMINI_PLACEHOLDERS = frozenset(
    {"", "your_gemini_api_key_here", "your_google_api_key_here"}
)
_ANTHROPIC_PLACEHOLDERS = frozenset({"", "your_anthropic_api_key_here"})


def _resolve_gemini_key(
    explicit: str | None,
) -> str | None:
    if explicit is not None:
        return explicit.strip() or None
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip() or None


def _resolve_anthropic_key(api_key: str | None, anthropic_api_key: str | None) -> str | None:
    if anthropic_api_key is not None:
        return anthropic_api_key.strip() or None
    if api_key is not None:
        return api_key.strip() or None
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip() or None


class TrialQAChain:
    """Retrieve trial passages with ``TrialIndexer`` and answer with Gemini, Claude, or a demo stub."""

    def __init__(
        self,
        indexer: TrialIndexer,
        api_key: str | None = None,
        *,
        anthropic_api_key: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        self.indexer = indexer
        self.gemini_key = _resolve_gemini_key(gemini_api_key)
        self.anthropic_key = _resolve_anthropic_key(api_key, anthropic_api_key)

        gk = self.gemini_key or ""
        ak = self.anthropic_key or ""

        if gk and gk not in _GEMINI_PLACEHOLDERS:
            self._backend: _LLMBackend = "gemini"
        elif ak and ak not in _ANTHROPIC_PLACEHOLDERS:
            self._backend = "anthropic"
        else:
            self._backend = "demo"

        self.client = None
        self.chat_history: list[dict[str, str]] = []

    @property
    def _demo_mode(self) -> bool:
        return self._backend == "demo"

    @property
    def llm_backend(self) -> _LLMBackend:
        """Active provider: ``demo``, ``gemini``, or ``anthropic``."""
        return self._backend

    def _get_anthropic_client(self) -> None:
        if self.client is None and self._backend == "anthropic":
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.anthropic_key)

    def _gemini_model_names_to_try(self) -> list[str]:
        """Prefer ``GEMINI_MODEL``; fall back when a name is retired (404) or rate-limited (429)."""
        preferred = (os.getenv("GEMINI_MODEL") or "").strip()
        fallbacks = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
        ]
        ordered: list[str] = []
        for m in ([preferred] if preferred else []) + fallbacks:
            if m and m not in ordered:
                ordered.append(m)
        return ordered

    def _generate_with_gemini(self, system_prompt: str, user_message: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.gemini_key)
        last_err: Exception | None = None
        for model_name in self._gemini_model_names_to_try():
            try:
                model = genai.GenerativeModel(
                    model_name,
                    system_instruction=system_prompt,
                )
                response = model.generate_content(
                    user_message,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=500,
                    ),
                )
                text = (response.text or "").strip()
                return text or (
                    "The model returned an empty response. Try rephrasing your question."
                )
            except Exception as e:
                last_err = e
                err_s = str(e).lower()
                if (
                    "404" in str(e)
                    or "not found" in err_s
                    or "429" in str(e)
                    or "quota" in err_s
                    or "resourceexhausted" in err_s
                ):
                    continue
                raise
        if last_err is not None:
            raise last_err
        raise RuntimeError("No Gemini model candidates configured")

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
Keep answers concise, 2-4 sentences maximum unless a comparison or list is needed."""

        user_message = f"""Context:
{context}

Question: {question}"""

        if self._backend == "demo":
            top_trial = search_results[0]["metadata"] if search_results else {}
            cr = top_trial.get("completion_rate")
            if cr is not None:
                cr_part = f"a {float(cr):.1%} completion rate"
            else:
                cr_part = "completion rate not available in metadata"
            answer = (
                "[DEMO MODE - Set GEMINI_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY in .env / Streamlit secrets] "
                f"Based on the retrieved trials, the most relevant result is "
                f"{top_trial.get('brief_title', 'Unknown')} "
                f"(NCT ID: {top_trial.get('nct_id', 'N/A')}) with "
                f"{int(top_trial.get('enrollment_count', 0) or 0):,} participants and {cr_part}."
            )
        elif self._backend == "gemini":
            try:
                answer = self._generate_with_gemini(system_prompt, user_message)
            except Exception as e:
                err = str(e)
                hint = (
                    "Check GEMINI_API_KEY / GOOGLE_API_KEY. Optional: set "
                    "`GEMINI_MODEL` (e.g. `gemini-2.5-flash`) in `.env`."
                )
                if "429" in err or "quota" in err.lower() or "ResourceExhausted" in err:
                    hint = (
                        "Quota exceeded for all tried models. Wait and retry, set "
                        "`GEMINI_MODEL=gemini-2.5-flash-lite`, or enable billing in Google AI Studio."
                    )
                if "404" in err or "not found" in err.lower():
                    hint = (
                        "Model id not available for your API version. Set "
                        "`GEMINI_MODEL=gemini-2.5-flash` (see https://ai.google.dev/gemini-api/docs/models )."
                    )
                answer = f"Error calling Gemini API: {e!s}. {hint}"
        else:
            self._get_anthropic_client()
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

        top_score = search_results[0]["score"] if search_results else 0.0
        if top_score > 0.55:
            confidence = "High"
        elif top_score > 0.38:
            confidence = "Medium"
        else:
            confidence = "Low"

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
