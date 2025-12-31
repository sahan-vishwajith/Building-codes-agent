import re
import json
from typing import Optional, Tuple, List, Dict, Any

from .schemas import BuildingContext
from .llm_groq import GroqLLM

# ----------------------------
# Groq model/config selection
# ----------------------------
GROQ_CONFIG = {
    "models": {
        "extract": "llama-3.1-8b-instant",      # fast extraction / routing
        "reason":  "llama-3.3-70b-versatile",   # final answer
    },
    "params": {
        "extract": {"temperature": 0.0, "max_tokens": 500},
        "reason":  {"temperature": 0.1, "max_tokens": 1000},
    }
}

_llm_extract = GroqLLM(model=GROQ_CONFIG["models"]["extract"], **GROQ_CONFIG["params"]["extract"])
_llm_reason  = GroqLLM(model=GROQ_CONFIG["models"]["reason"],  **GROQ_CONFIG["params"]["reason"])

# ----------------------------
# Robust regex extractors
# ----------------------------
AREA_RE = re.compile(r'(?P<val>\d+(?:\.\d+)?)\s*(m²|m2|sqm|sq\s*m|square\s*meters?)', re.I)
KVA_RE  = re.compile(r'(?P<val>\d+(?:\.\d+)?)\s*kva\b', re.I)
COOL_RE = re.compile(r'(?P<val>\d+(?:\.\d+)?)\s*(kwth|kWth)\b', re.I)  # simplistic; user may say "cooling 400 kWth"
WWR_RE  = re.compile(r'\bwwr\b[^0-9]{0,20}(?P<val>\d+(?:\.\d+)?)\s*%', re.I)

def _regex_fill(ctx: BuildingContext, message: str) -> BuildingContext:
    if ctx.floor_area_m2 is None:
        m = AREA_RE.search(message)
        if m: ctx.floor_area_m2 = float(m.group("val"))

    if ctx.electrical_demand_kva is None:
        m = KVA_RE.search(message)
        if m: ctx.electrical_demand_kva = float(m.group("val"))

    if ctx.wwr_percent is None:
        m = WWR_RE.search(message)
        if m: ctx.wwr_percent = float(m.group("val"))

    low = message.lower()
    if ctx.district is None:
        if "colombo" in low: ctx.district = "Colombo"
    if ctx.is_new_building is None:
        if "new" in low or "brand new" in low: ctx.is_new_building = True

    return ctx

# ----------------------------
# Agent 1: Intake (LLM -> JSON) + regex patch
# ----------------------------
def intake(message: str, ctx: Optional[BuildingContext]) -> BuildingContext:
    ctx = ctx or BuildingContext()

    sys = "Extract building context fields as strict JSON only. No extra text."
    user = f"""
Return JSON for these fields (use null if unknown):
district, building_type, is_new_building, floor_area_m2, electrical_demand_kva,
cooling_capacity_kwth, heating_capacity_kwth, wwr_percent, skylight_percent,
glazing_vlt, hvac_type, operating_hours

User text:
{message}
"""
    try:
        raw = _llm_extract.chat(sys, user)
        jtxt = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(jtxt)
        merged = ctx.model_dump()
        for k, v in data.items():
            if v is not None:
                merged[k] = v
        ctx = BuildingContext(**merged)
    except Exception:
        # ignore and rely on regex + whatever ctx had
        pass

    # Always patch numeric fields with regex (super important)
    return _regex_fill(ctx, message)

# ----------------------------
# Agent 2: Applicability (area OR kVA OR HVAC thresholds)
# ----------------------------
def applicability(ctx: BuildingContext) -> Tuple[str, str]:
    known_any = False
    applies = False
    reasons = []

    # EEBC thresholds (keep as constants)
    # area >= 1000 m², electrical >= 500 kVA, cooling > 350 kWth, heating > 250 kWth
    if ctx.floor_area_m2 is not None:
        known_any = True
        if ctx.floor_area_m2 >= 1000:
            applies = True
        else:
            reasons.append(f"Floor area {ctx.floor_area_m2:g} m² < 1000 m².")
    else:
        reasons.append("Floor area missing (m²).")

    if ctx.electrical_demand_kva is not None:
        known_any = True
        if ctx.electrical_demand_kva >= 500:
            applies = True
        else:
            reasons.append(f"Electrical demand {ctx.electrical_demand_kva:g} kVA < 500 kVA.")
    else:
        reasons.append("Electrical demand missing (kVA).")

    if ctx.cooling_capacity_kwth is not None:
        known_any = True
        if ctx.cooling_capacity_kwth > 350:
            applies = True
        else:
            reasons.append(f"Cooling {ctx.cooling_capacity_kwth:g} kWth is not > 350 kWth.")
    else:
        reasons.append("Cooling capacity missing (kWth).")

    if ctx.heating_capacity_kwth is not None:
        known_any = True
        if ctx.heating_capacity_kwth > 250:
            applies = True
        else:
            reasons.append(f"Heating {ctx.heating_capacity_kwth:g} kWth is not > 250 kWth.")
    else:
        reasons.append("Heating capacity missing (kWth).")

    if not known_any:
        return "unknown", "Need at least floor area (m²) or electrical demand (kVA) or HVAC capacities (kWth)."

    if applies:
        return "yes", "EEBC likely applies because at least one threshold is met."
    return "no", "EEBC likely not mandatory based on provided values; you can still use it as best practice."

# ----------------------------
# Agent 3: Intent router (beginner vs compliance)
# ----------------------------
def _is_beginner_query(message: str) -> bool:
    low = message.lower()
    return any(k in low for k in ["what is", "explain", "i'm new", "im new", "beginner", "simple", "overview"])

# ----------------------------
# Agent 4: Multi-query retrieval agent
# store.search(query, top_k) must exist (your VectorStore)
# ----------------------------
def retrieval_multi(message: str, ctx: BuildingContext, store, top_k_each: int = 6) -> List[Dict[str, Any]]:
    # Generate 3 retrieval queries (LLM), then merge results
    sys = "Generate short search queries for retrieving the best EEBC clauses from a PDF. Output JSON only."
    user = f"""
Return JSON like: {{"queries": ["...", "...", "..."]}}
User question: {message}
Context: {ctx.model_dump()}
"""
    queries = [message]
    try:
        raw = _llm_extract.chat(sys, user)
        jtxt = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(jtxt)
        q = data.get("queries") or []
        q = [x for x in q if isinstance(x, str) and x.strip()]
        if q:
            queries = q[:3]
    except Exception:
        pass

    merged: Dict[str, Dict[str, Any]] = {}
    for q in queries:
        for r in store.search(q, top_k=top_k_each):
            cid = r.get("chunk_id") or f"{r.get('page')}-{hash(r.get('text','')[:80])}"
            if cid not in merged or r.get("score", 0) > merged[cid].get("score", 0):
                merged[cid] = r

    # Sort by score desc
    out = list(merged.values())
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out[:10]

# ----------------------------
# Agent 5: Answer agent (must cite pages)
# ----------------------------
def build_answer(message: str, ctx: BuildingContext, retrieved: List[Dict[str, Any]], applies: str, reason: str) -> Tuple[str, List[Dict[str, Any]]]:
    # Keep sources compact for UI
    sources = []
    for r in retrieved[:6]:
        sources.append({
            "page": r["page"],
            "chunk_id": r["chunk_id"],
            "score": r.get("score", 0.0),
            "excerpt": r["text"][:260].replace("\n", " ")
        })

    if _is_beginner_query(message):
        # No need to overwhelm; still cite
        sys = "You explain EEBC to a beginner in short bullet points using ONLY the provided sources. Include (p.X) citations."
    else:
        sys = "You are an EEBC compliance assistant. Answer clearly, step-by-step, using ONLY the provided sources. Every rule must have (p.X) citations."

    # Pack sources
    src_block = "\n".join([f"[S{i+1}] p.{s['page']} {s['chunk_id']}: {s['excerpt']}" for i, s in enumerate(sources)])

    user = f"""
User question:
{message}

Parsed context:
{ctx.model_dump()}

Applicability:
applies={applies}
reason={reason}

Sources (you must cite pages like (p.39)):
{src_block}

Write:
- 5–10 bullet points max
- If info is missing, ask 2–3 short questions
- Do NOT invent
"""
    answer = _llm_reason.chat(sys, user)
    return answer, sources

# ----------------------------
# Single entry point used by Flask
# ----------------------------
def run_pipeline(message: str, ctx: Optional[BuildingContext], store) -> Tuple[str, str, str, List[Dict[str, Any]]]:
    ctx2 = intake(message, ctx)
    applies, reason = applicability(ctx2)

    # Retrieval is still useful even in beginner mode (for citations),
    # but if no PDF indexed yet, handle gracefully
    retrieved = retrieval_multi(message, ctx2, store, top_k_each=6) if store else []

    answer, sources = build_answer(message, ctx2, retrieved, applies, reason)
    return answer, applies, reason, sources
