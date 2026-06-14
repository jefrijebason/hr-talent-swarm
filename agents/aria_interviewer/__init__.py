"""
ARIA Interviewer Agent

An adaptive AI interviewer that evaluates candidates on 5 dimensions:
  1. First-principles thinking
  2. AI tool fluency
  3. Problem decomposition
  4. Taste / Judgment
  5. Verification skill

Public API:
    from agents.aria_interviewer import (
        start_interview,
        submit_answer,            # returns next question + action ('probe'|'next'|'wrap_up')
        complete_interview,
        resume_interview,
        get_interview_state,
        record_anti_cheat_flag,
    )

NOTE: There is no separate get_next_question() — submit_answer() drives the
conversation forward and returns ARIA's next utterance in its response.

See agent.py for the high-level orchestrator.
"""

from agents.aria_interviewer.agent import (
    start_interview,
    submit_answer,
    complete_interview,
    resume_interview,
    get_interview_state,
    record_anti_cheat_flag,
)

from agents.aria_interviewer.resume_analyzer import (
    analyze_resume,
    get_or_create_ai_profile,
)

from agents.aria_interviewer.briefing_generator import (
    generate_briefing,
    format_briefing_for_email,
)

__all__ = [
    "start_interview",
    "submit_answer",
    "complete_interview",
    "resume_interview",
    "get_interview_state",
    "record_anti_cheat_flag",
    "analyze_resume",
    "get_or_create_ai_profile",
    "generate_briefing",
    "format_briefing_for_email",
]