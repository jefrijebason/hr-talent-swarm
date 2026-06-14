"""
agents/aria_interviewer/face_tracker.py

Backend handler for face/eye-gaze flags.

The HEAVY work runs in the browser (MediaPipe Face Landmarker — free, client-side).
This module just receives raw events and aggregates them into anti-cheat flags.

Event types from frontend (POST to /api/interview/{cid}/face-flag):
  - "no_face"            : no face detected
  - "multiple_faces"     : 2+ faces detected (someone helping in the room)
  - "looking_off_screen" : eyes consistently away from screen
  - "looking_down"       : consistently looking down (phone / notes)
  - "tab_switch"         : page visibility change

We don't store every single frame's event — we aggregate INTO flags:
  - "no_face" for >20 seconds  → 1 flag
  - any "multiple_faces" event → 1 high-severity flag
  - "looking_off_screen" >20% of session → 1 flag
  - >2 tab switches             → 1 flag
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Thresholds
NO_FACE_THRESHOLD_SEC          = 20
OFF_SCREEN_RATIO_THRESHOLD     = 0.20
LOOKING_DOWN_RATIO_THRESHOLD   = 0.30
TAB_SWITCH_THRESHOLD           = 2


def aggregate_events(events: List[Dict[str, Any]], session_duration_sec: float) -> List[Dict[str, Any]]:
    """
    Reduce a list of raw frontend events into a small list of anti-cheat flags.

    events: list of {type, timestamp, duration_sec?, count?}
    """
    if not events:
        return []

    flags: List[Dict[str, Any]] = []

    # Buckets
    no_face_total       = 0.0
    off_screen_total    = 0.0
    looking_down_total  = 0.0
    multi_face_events   = 0
    tab_switches        = 0

    for e in events:
        t = e.get("type", "")
        dur = float(e.get("duration_sec", 0))
        cnt = int(e.get("count", 1))
        if t == "no_face":
            no_face_total += dur
        elif t == "multiple_faces":
            multi_face_events += cnt
        elif t == "looking_off_screen":
            off_screen_total += dur
        elif t == "looking_down":
            looking_down_total += dur
        elif t == "tab_switch":
            tab_switches += cnt

    # Translate aggregates → flags

    if no_face_total >= NO_FACE_THRESHOLD_SEC:
        flags.append({
            "type":     "candidate_absent",
            "severity": "medium",
            "detail":   f"No face detected for ~{int(no_face_total)}s total",
            "source":   "face_tracker",
        })

    if multi_face_events > 0:
        flags.append({
            "type":     "multiple_faces_detected",
            "severity": "high",
            "detail":   f"Additional person(s) detected in webcam {multi_face_events} time(s)",
            "source":   "face_tracker",
        })

    if session_duration_sec > 0:
        off_ratio = off_screen_total / session_duration_sec
        down_ratio = looking_down_total / session_duration_sec
        if off_ratio >= OFF_SCREEN_RATIO_THRESHOLD:
            flags.append({
                "type":     "frequent_off_screen_gaze",
                "severity": "medium",
                "detail":   f"Looking off-screen ~{int(off_ratio*100)}% of session — possible second monitor",
                "source":   "face_tracker",
            })
        if down_ratio >= LOOKING_DOWN_RATIO_THRESHOLD:
            flags.append({
                "type":     "frequent_looking_down",
                "severity": "medium",
                "detail":   f"Looking down ~{int(down_ratio*100)}% of session — possible notes/phone",
                "source":   "face_tracker",
            })

    if tab_switches >= TAB_SWITCH_THRESHOLD:
        flags.append({
            "type":     "frequent_tab_switching",
            "severity": "medium" if tab_switches <= 4 else "high",
            "detail":   f"Tab/window switched {tab_switches} times during interview",
            "source":   "face_tracker",
        })

    return flags


def event_to_immediate_flag(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    For events that should fire an IMMEDIATE flag (not aggregated).
    Currently: multiple_faces fires immediately, others are aggregated at end.
    """
    t = event.get("type")
    if t == "multiple_faces":
        return {
            "type":     "multiple_faces_detected",
            "severity": "high",
            "detail":   "Additional person detected on webcam",
            "source":   "face_tracker",
            "timestamp": event.get("timestamp", datetime.utcnow().isoformat()),
        }
    return {}
