import os
from typing import Dict, Any

from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI


EFFECT_DOCS = {
    "lofi": "Lo‑Fi should feel warm, soft, and slightly degraded (like an old tape). Avoid crushing the highs too much for vocal‑led tracks, and be careful with extreme bass boosts.",
    "jazz": "Jazz should sound mid‑forward, smooth, and roomy. Reverb should add space without drowning vocals. Compression can be gentle; clarity matters more than loudness.",
    "dubstep": "Dubstep is about big, controlled low‑end and rhythmic movement. Too much high‑frequency harshness or over‑compression will make it fatiguing.",
    "vaporwave": "Vaporwave is slow, dreamy, and nostalgic. Small pitch‑down and tempo reduction are good, but extreme values or very bright echoes can make it unpleasant.",
    "rock": "Rock benefits from presence and punch. Midrange and upper‑mid boosts help guitars and vocals cut through, but heavy compression and treble boosts can become harsh fast.",
}


def _build_chain() -> LLMChain:
    tmpl = PromptTemplate(
        input_variables=["effect", "params", "question", "effect_docs"],
        template=(
            "You are an audio mixing assistant.\n\n"
            "Effect context:\n"
            "{effect_docs}\n\n"
            "Current style: {effect}\n"
            "Current parameters (0–1-ish where applicable): {params}\n\n"
            "User question or goal:\n"
            "{question}\n\n"
            "Give:\n"
            "1) A 2–3 sentence explanation in simple language.\n"
            "2) 3–5 concrete slider tweaks (bass/treble/reverb/tempo/pitch/volume/lowpass/compression) as bullet points.\n"
            "3) Values should stay in safe ranges and avoid making the track harsh or unlistenable.\n"
        ),
    )

    llm = ChatOpenAI(
        temperature=0.4,
        model_name=os.environ.get("LANGCHAIN_MODEL", "gpt-4o-mini"),
    )
    return LLMChain(prompt=tmpl, llm=llm)


_CHAIN: LLMChain | None = None


def suggest_parameters(question: str, effect: str, params: Dict[str, Any]) -> str:
    """
    Use LangChain + an LLM to explain the current settings and suggest tweaks.

    Requires OPENAI_API_KEY (or compatible) to be set in the environment.
    """
    global _CHAIN
    if _CHAIN is None:
        _CHAIN = _build_chain()

    eff_key = (effect or "lofi").lower()
    docs = EFFECT_DOCS.get(eff_key, "")
    result = _CHAIN.run(
        effect=eff_key,
        params=params,
        question=question or "Help me make this sound better.",
        effect_docs=docs,
    )
    return result.strip()

