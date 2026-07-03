"""Simple Streamlit UI for enterprise agent Q&A."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from enterprise_okf_ai.agent import AgentOrchestrator
from enterprise_okf_ai.core.embeddings import deterministic_embedding
from enterprise_okf_ai.core.settings import Settings


@st.cache_resource(show_spinner=False)
def _load_orchestrator(okf_dir: str, vector_dir: str) -> AgentOrchestrator:
    settings = Settings()
    return AgentOrchestrator.from_okf(
        okf_dir=settings.resolve(Path(okf_dir)),
        vector_dir=settings.resolve(Path(vector_dir)),
        embedding_fn=deterministic_embedding,
        llm=None,
    )


def _render_tool_calls(tool_calls: list[Any]) -> None:
    if not tool_calls:
        st.info("No tool calls captured.")
        return

    for idx, call in enumerate(tool_calls, start=1):
        label = f"{idx}. {call.tool_name}"
        with st.expander(label):
            st.code(str(call.arguments), language="json")
            st.write(call.output_summary)
            if call.citations:
                st.write("Citations:")
                for citation in sorted(set(call.citations)):
                    st.markdown(f"- `{citation}`")


def main() -> None:
    """Render Streamlit application."""

    st.set_page_config(page_title="Enterprise OKF Agent", layout="wide")
    st.title("Enterprise OKF Agent")
    st.caption("Tool-calling Q&A over OKF knowledge bundles")

    settings = Settings()

    with st.sidebar:
        st.subheader("Runtime")
        okf_dir = st.text_input("OKF directory", value=str(settings.okf_dir))
        vector_dir = st.text_input("Vector directory", value=str(settings.vector_dir))
        top_k = st.slider("Top K retrieval", min_value=3, max_value=20, value=8, step=1)

    question = st.text_area(
        "Ask a question",
        value="Which API updates order status and what metric depends on it?",
        height=120,
    )

    run_clicked = st.button("Run Agent", type="primary")
    if not run_clicked:
        st.stop()

    try:
        orchestrator = _load_orchestrator(okf_dir=okf_dir, vector_dir=vector_dir)
        response = orchestrator.ask(question=question, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Agent execution failed: {exc}")
        st.stop()

    st.subheader("Answer")
    st.write(response.answer)

    col1, col2, col3 = st.columns(3)
    col1.metric("Supported", "Yes" if response.supported else "No")
    col2.metric("Confidence", f"{response.confidence:.2f}")
    col3.metric("Strategy", response.strategy)

    if response.unsupported_reason:
        st.warning(f"Unsupported reason: `{response.unsupported_reason}`")

    st.subheader("Evidence Summary")
    st.write(response.evidence_summary or "No evidence summary")

    st.subheader("Citations")
    if response.citations:
        for citation in response.citations:
            st.markdown(f"- `{citation}`")
    else:
        st.info("No citations returned.")

    st.subheader("Used Concepts")
    if response.used_concepts:
        for concept in response.used_concepts:
            st.markdown(f"- `{concept}`")
    else:
        st.info("No concepts used.")

    st.subheader("Tool Calls")
    _render_tool_calls(response.tool_calls)

    with st.expander("Tool Trace"):
        for item in response.tool_trace:
            st.markdown(f"- {item}")


if __name__ == "__main__":
    main()
