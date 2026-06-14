"""
Vibe Engineering Challenge — AI-augmented coding test.

Public API:
    from agents.vibe_engineering import (
        start_challenge,
        ask_ai_assistant,
        submit_challenge,
        get_challenge_state,
        save_code_snapshot,
    )
"""
from agents.vibe_engineering.agent import (
    start_challenge,
    ask_ai_assistant,
    submit_challenge,
    get_challenge_state,
    save_code_snapshot,
)
from agents.vibe_engineering.problems import pick_problem, get_problem

__all__ = [
    "start_challenge",
    "ask_ai_assistant",
    "submit_challenge",
    "get_challenge_state",
    "save_code_snapshot",
    "pick_problem",
    "get_problem",
]
