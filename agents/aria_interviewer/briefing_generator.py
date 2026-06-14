"""
agents/aria_interviewer/briefing_generator.py

End-of-interview briefing generator.

Runs ONCE at interview completion. Single GPT-4o call (the only "big" model call in the
whole interview — everything else uses mini).

Outputs a structured briefing that gets:
  1. Stored on the candidate document (for dashboard display)
  2. Injected into the existing interviewer-assignment email
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from agents.aria_interviewer.answer_evaluator import (
    aggregate_dimension_scores,
    composite_score,
)

logger = logging.getLogger(__name__)

_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        )
    return _client


def _gpt4o() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O") or os.getenv("MODEL_GPT4O") or "gpt-4o"


# ════════════════════════════════════════════════════════════════════════
# Main entry
# ════════════════════════════════════════════════════════════════════════

def generate_briefing(
    *,
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    session: Dict[str, Any],
    weights: Dict[str, float],
    pass_threshold: int = 70,
) -> Dict[str, Any]:
    """
    Produce the complete AI-interview briefing.

    session must contain:
      - transcript           : list of {q, a, dimension, evaluation}
      - elapsed_seconds      : interview duration
      - anti_cheat_flags     : list of flag dicts from face/voice/cursor agents
      - screen_share_summary : optional dict from vision_analyzer
    """
    transcript = session.get("transcript", [])
    answer_evals = [
        {**(t.get("evaluation") or {}), "dimension": t.get("dimension")}
        for t in transcript if t.get("evaluation")
    ]

    # 1. Numeric aggregation
    dim_scores = aggregate_dimension_scores(answer_evals)
    comp_score = composite_score(dim_scores, weights)
    passed = comp_score >= pass_threshold

    # 2. Anti-cheat flag severity
    flags = session.get("anti_cheat_flags", []) or []
    flag_count = len(flags)
    if flag_count == 0:
        flag_severity = "none"
    elif flag_count <= 2:
        flag_severity = "minor"
    else:
        flag_severity = "significant"

    # 3. Qualitative narrative — ONE gpt-4o call, full context
    narrative = _generate_narrative(
        candidate=candidate, job=job, transcript=transcript,
        dim_scores=dim_scores, weights=weights, comp_score=comp_score,
        passed=passed, flags=flags,
    )

    briefing = {
        "version":         "1.0",
        "generated_at":    datetime.utcnow().isoformat(),
        "candidate_id":    candidate.get("id"),
        "candidate_name":  candidate.get("name"),
        "job_id":          job.get("id"),
        "role":            job.get("title"),
        "duration_minutes": round(session.get("elapsed_seconds", 0) / 60, 1),
        "questions_asked":  len(transcript),

        # Numeric
        "dimension_scores": dim_scores,
        "weights":          {k: round(v, 2) for k, v in weights.items()},
        "composite_score":  comp_score,
        "pass_threshold":   pass_threshold,
        "passed":           passed,

        # Anti-cheat
        "anti_cheat": {
            "severity":   flag_severity,
            "flag_count": flag_count,
            "flags":      flags,
        },

        # Qualitative
        "summary":             narrative.get("summary", ""),
        "strengths":           narrative.get("strengths", []),
        "concerns":            narrative.get("concerns", []),
        "red_flags":           narrative.get("red_flags", []),
        "resume_validation":   narrative.get("resume_validation", []),
        "focus_on":            narrative.get("focus_on_in_human_round", []),
        "do_not_test_again":   narrative.get("already_tested", []),
        "suggested_questions": narrative.get("suggested_questions", []),
        "verdict":             narrative.get("verdict", "PASS" if passed else "FAIL"),
        "verdict_reasoning":   narrative.get("verdict_reasoning", ""),

        # Reserve eligibility (failed but salvageable)
        "talent_reserve_eligible":
            (not passed) and comp_score >= 50,

        # Full transcript (for collapsible email section)
        "transcript": transcript,
    }
    return briefing


# ════════════════════════════════════════════════════════════════════════
# Narrative generation (single GPT-4o call)
# ════════════════════════════════════════════════════════════════════════

def _generate_narrative(
    *,
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    transcript: List[Dict[str, Any]],
    dim_scores: Dict[str, int],
    weights: Dict[str, float],
    comp_score: int,
    passed: bool,
    flags: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """One big call to GPT-4o — synthesizes everything into structured narrative."""

    # Compact the transcript so we stay in token budget
    compact_transcript = []
    for i, t in enumerate(transcript[:20], 1):
        compact_transcript.append({
            "q_num": i,
            "dimension": t.get("dimension"),
            "question": (t.get("q") or "")[:300],
            "answer":   (t.get("a") or "")[:800],
            "score":    (t.get("evaluation") or {}).get("dimension_score"),
            "signals":  (t.get("evaluation") or {}).get("key_signals", []),
        })

    ai_profile = candidate.get("ai_profile", {}) or {}
    resume_claims = ai_profile.get("claims", [])[:6]

    system = """You are ARIA's briefing writer. Synthesize the entire AI interview into a structured
briefing for the human technical interviewer who will see this candidate next.

Output JSON with this schema:
{
  "summary":              "<3-4 sentence overall summary>",
  "strengths":            ["<concrete strength tied to an answer>", ...],
  "concerns":             ["<concrete concern with evidence>", ...],
  "red_flags":            ["<serious issue if any>", ...],
  "resume_validation":    [{"claim": "...", "verdict": "supports|contradicts|unprobed", "evidence": "..."}],
  "focus_on_in_human_round": ["<area HR should dig into>", ...],
  "already_tested":       ["<skill already validated — don't re-ask>", ...],
  "suggested_questions":  ["<specific Q for the human interviewer>", ...],
  "verdict":              "STRONG_PASS|PASS|MARGINAL|FAIL",
  "verdict_reasoning":    "<one sentence>"
}

WRITING STYLE:
- Be CONCRETE. Reference actual answers ("Q3: said X but couldn't elaborate").
- No corporate fluff. No "demonstrated synergy" type phrases.
- If something was UNTESTED, say so honestly.
- Tie verdicts to evidence, not vibes.
- 3-6 items per list. Quality over quantity.
"""

    user = f"""
ROLE: {job.get('title')}
CANDIDATE: {candidate.get('name')} (seniority: {ai_profile.get('seniority','unknown')})
JD context: {(job.get('description') or '')[:600]}
HR's interview direction: {(job.get('interview_direction') or '(none)')[:400]}

RESUME CLAIMS:
{json.dumps(resume_claims, indent=2)}

DIMENSION SCORES (out of 100):
{json.dumps(dim_scores, indent=2)}
Weights applied: {json.dumps({k: round(v,2) for k,v in weights.items()})}
COMPOSITE: {comp_score}/100 ({'PASS' if passed else 'FAIL'})

ANTI-CHEAT FLAGS ({len(flags)} total):
{json.dumps(flags[:10], indent=2)}

INTERVIEW TRANSCRIPT:
{json.dumps(compact_transcript, indent=2)}

Write the briefing now.
"""

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_gpt4o(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=1600,
        )
        return json.loads(resp.choices[0].message.content or "{}")

    except Exception as e:
        logger.error(f"[ARIA] briefing narrative generation failed: {e}", exc_info=True)
        # Graceful fallback so the email still sends
        return {
            "summary": f"AI interview completed. Composite score: {comp_score}/100 ({'PASS' if passed else 'FAIL'}). Narrative generation failed — see transcript.",
            "strengths": [],
            "concerns": [f"Briefing generation error: {e}"],
            "red_flags": [],
            "resume_validation": [],
            "focus_on_in_human_round": ["Re-validate the strongest claims from the resume."],
            "already_tested": [],
            "suggested_questions": [],
            "verdict": "PASS" if passed else "FAIL",
            "verdict_reasoning": "Auto-fallback verdict (narrative generation failed).",
        }


# ════════════════════════════════════════════════════════════════════════
# Email-ready HTML formatter
# ════════════════════════════════════════════════════════════════════════

def format_briefing_for_email(briefing: Dict[str, Any]) -> str:
    """
    Render the briefing as inline HTML, designed to be embedded into the existing
    interviewer-assignment email body (NOT a standalone email).

    Inherits no styles from a wrapper — uses inline styles only.
    """
    if not briefing:
        return ""

    score = briefing.get("composite_score", 0)
    threshold = briefing.get("pass_threshold", 70)
    passed = briefing.get("passed", False)
    verdict = briefing.get("verdict", "PASS" if passed else "FAIL")

    # Color coding
    score_color = "#16a34a" if score >= threshold + 10 else ("#5b8def" if passed else "#dc2626")
    badge_bg    = "#dcfce7" if passed else "#fee2e2"
    badge_color = "#15803d" if passed else "#b91c1c"

    dims = briefing.get("dimension_scores", {})
    dim_html = "".join(
        f"""<tr>
          <td style="padding:6px 10px;font-size:12px;color:#475569;text-transform:capitalize">{k.replace('_',' ')}</td>
          <td style="padding:6px 10px;font-size:13px;font-weight:700;color:#0f172a;text-align:right">{v}/100</td>
        </tr>"""
        for k, v in dims.items()
    )

    def _list_block(title: str, items: List[str], emoji: str = "•", color: str = "#475569") -> str:
        if not items:
            return ""
        items_html = "".join(
            f'<li style="margin-bottom:6px;font-size:13px;color:{color};line-height:1.55">{emoji}&nbsp;{i}</li>'
            for i in items[:8]
        )
        return f"""
<div style="margin:14px 0">
  <div style="font-size:12px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">{title}</div>
  <ul style="margin:0;padding-left:4px;list-style:none">{items_html}</ul>
</div>"""

    strengths = _list_block("✨ Strengths",         briefing.get("strengths", []),         "✓", "#15803d")
    concerns  = _list_block("⚠ Concerns",          briefing.get("concerns", []),          "⚠", "#b45309")
    redflags  = _list_block("🚩 Red Flags",        briefing.get("red_flags", []),         "🚩", "#b91c1c")
    focus_on  = _list_block("🎯 Focus On in Your Round", briefing.get("focus_on", []),    "→", "#1e40af")
    avoid     = _list_block("✓ Already Tested by AI (skip)", briefing.get("do_not_test_again", []), "✓", "#475569")
    sugg      = _list_block("💡 Suggested Questions", briefing.get("suggested_questions", []),  "→", "#1e40af")

    # Resume validation table
    rv_html = ""
    rv = briefing.get("resume_validation", [])
    if rv:
        rows = ""
        for r in rv[:6]:
            verdict_color = {"supports": "#15803d", "contradicts": "#b91c1c", "unprobed": "#64748b"}.get(
                r.get("verdict", "unprobed"), "#64748b"
            )
            verdict_emoji = {"supports": "✓", "contradicts": "✗", "unprobed": "·"}.get(
                r.get("verdict", "unprobed"), "·"
            )
            rows += f"""<tr>
              <td style="padding:6px 8px;font-size:12px;color:#475569;border-bottom:1px solid #e2e8f0">{r.get('claim','')[:80]}</td>
              <td style="padding:6px 8px;font-size:12px;font-weight:700;color:{verdict_color};text-align:center;border-bottom:1px solid #e2e8f0">{verdict_emoji} {r.get('verdict','').upper()}</td>
            </tr>"""
        rv_html = f"""
<div style="margin:14px 0">
  <div style="font-size:12px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">📋 Resume Validation</div>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead><tr style="background:#f8fafc">
      <th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b">Claim</th>
      <th style="padding:6px 8px;text-align:center;font-size:11px;color:#64748b;width:120px">Verdict</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""

    # Anti-cheat note
    ac = briefing.get("anti_cheat", {})
    ac_html = ""
    if ac.get("severity") == "minor":
        ac_html = f"""
<div style="margin:14px 0;padding:10px 14px;background:#fef3c7;border-left:3px solid #d97706;border-radius:6px">
  <div style="font-size:11px;font-weight:700;color:#92400e;text-transform:uppercase;letter-spacing:0.06em">ℹ Minor flags worth noting ({ac.get('flag_count')})</div>
  <div style="font-size:12px;color:#78350f;margin-top:4px">Likely benign but visible to interviewer if curious. Full details in dashboard.</div>
</div>"""
    elif ac.get("severity") == "significant":
        ac_html = f"""
<div style="margin:14px 0;padding:10px 14px;background:#fee2e2;border-left:3px solid #b91c1c;border-radius:6px">
  <div style="font-size:11px;font-weight:700;color:#991b1b;text-transform:uppercase;letter-spacing:0.06em">🚩 Significant anti-cheat concerns ({ac.get('flag_count')} flags)</div>
  <div style="font-size:12px;color:#7f1d1d;margin-top:4px">Multiple suspicious signals during interview. Recommend probing authenticity in your round.</div>
</div>"""

    # Transcript collapsible (HTML <details>)
    transcript = briefing.get("transcript", [])
    transcript_html = ""
    if transcript:
        rows = ""
        for i, t in enumerate(transcript[:25], 1):
            rows += f"""
<div style="margin-bottom:14px;padding:10px 12px;background:#f8fafc;border-radius:8px;border-left:3px solid #5b8def">
  <div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">
    Q{i} · {t.get('dimension','').replace('_',' ').title()}
  </div>
  <div style="font-size:13px;color:#0f172a;font-weight:600;margin-bottom:6px">{(t.get('q') or '')}</div>
  <div style="font-size:13px;color:#475569;line-height:1.5;white-space:pre-wrap">{(t.get('a') or '')[:1500]}</div>
</div>"""
        transcript_html = f"""
<details style="margin:18px 0">
  <summary style="cursor:pointer;font-size:12px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.06em;padding:8px 0">
    📜 Full Interview Transcript ({len(transcript)} questions) — click to expand
  </summary>
  <div style="margin-top:10px">{rows}</div>
</details>"""

    return f"""
<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:24px;margin:18px 0;font-family:-apple-system,Segoe UI,sans-serif">

  <!-- Header -->
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #e2e8f0">
    <div>
      <div style="font-size:11px;color:#5b8def;font-weight:700;text-transform:uppercase;letter-spacing:0.08em">🤖 ARIA AI Interview Brief</div>
      <div style="font-size:18px;font-weight:800;color:#0f172a;margin-top:2px">{briefing.get('candidate_name','')}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:32px;font-weight:800;color:{score_color};line-height:1">{score}<span style="font-size:18px;color:#94a3b8">/100</span></div>
      <span style="display:inline-block;padding:3px 10px;background:{badge_bg};color:{badge_color};font-size:11px;font-weight:700;border-radius:100px;text-transform:uppercase;letter-spacing:0.06em;margin-top:4px">{verdict}</span>
    </div>
  </div>

  <!-- Summary -->
  <div style="font-size:14px;color:#0f172a;line-height:1.65;margin-bottom:16px">
    {briefing.get('summary','(No summary)')}
  </div>

  <!-- Dimension scores table -->
  <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;overflow:hidden;margin-bottom:14px">
    <tbody>{dim_html}</tbody>
  </table>

  <!-- Meta -->
  <div style="font-size:11px;color:#64748b;margin-bottom:12px">
    {briefing.get('duration_minutes',0)} min · {briefing.get('questions_asked',0)} questions · Threshold {threshold}/100
  </div>

  {ac_html}
  {strengths}
  {concerns}
  {redflags}
  {rv_html}
  {focus_on}
  {sugg}
  {avoid}
  {transcript_html}

</div>
"""