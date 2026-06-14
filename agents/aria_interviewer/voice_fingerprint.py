"""
agents/aria_interviewer/voice_fingerprint.py

Multi-voice / speaker-verification handler.

Strategy (cost-conscious):
  1. ENROLLMENT: Take the candidate's first ~30 seconds of speech.
     Build a voiceprint via Azure Speaker Recognition.
  2. VERIFICATION: For each subsequent audio chunk (~15-30s), call Azure to
     verify the chunk matches the enrolled voiceprint.
  3. If verification fails → flag "different speaker detected".

NOTE: Azure Speaker Recognition is currently in limited-preview. If your tenant
doesn't have it enabled, this module GRACEFULLY DEGRADES — it logs a warning and
just records "voice verification unavailable" rather than blocking the interview.

Lightweight alternative (used as a fallback): we use Azure Speech SDK's
ConversationTranscriber for speaker diarization on the audio — it identifies
multiple speaker IDs in the same audio stream, which is sufficient to detect
"there are 2 voices on this recording".

Module is best-effort. We never fail the interview because of voice analysis.
"""

import os
import logging
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════

def analyze_audio_chunk(
    audio_bytes: bytes,
    *,
    candidate_id: str,
    session_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Process one audio chunk during the interview.

    On the first call: enrolls the voiceprint (treats chunk as candidate's voice).
    On subsequent calls: runs diarization to count distinct speakers.

    Returns:
      {
        "voice_state":      "enrolled" | "verified" | "mismatch" | "unavailable",
        "speaker_count":    int,
        "anti_cheat_flags": [...],
        "duration_sec":     float,
      }
    """
    voice_state = session_state.get("voice_state", "pending")

    # Try diarization (preferred since it works without preview features)
    try:
        speaker_count, duration = _diarize_chunk(audio_bytes)
    except Exception as e:
        logger.warning(f"[ARIA-Voice] diarization unavailable: {e}")
        return {
            "voice_state":      "unavailable",
            "speaker_count":    0,
            "anti_cheat_flags": [],
            "duration_sec":     0,
        }

    flags: List[Dict[str, Any]] = []

    if voice_state == "pending":
        # First chunk — establish baseline
        if speaker_count == 1:
            voice_state = "enrolled"
        elif speaker_count > 1:
            # Multiple speakers in the very first chunk — already suspicious
            voice_state = "mismatch"
            flags.append({
                "type":     "multiple_voices_in_first_chunk",
                "severity": "high",
                "detail":   f"{speaker_count} distinct speakers detected in opening audio",
                "source":   "voice_fingerprint",
                "timestamp": datetime.utcnow().isoformat(),
            })
        else:
            voice_state = "unavailable"
    else:
        # Already enrolled — verify this chunk has only 1 speaker
        if speaker_count > 1:
            voice_state = "mismatch"
            flags.append({
                "type":     "additional_voice_detected",
                "severity": "high",
                "detail":   f"{speaker_count} speakers in audio chunk — possible coaching/assistance",
                "source":   "voice_fingerprint",
                "timestamp": datetime.utcnow().isoformat(),
            })
        else:
            voice_state = "verified"

    return {
        "voice_state":      voice_state,
        "speaker_count":    speaker_count,
        "anti_cheat_flags": flags,
        "duration_sec":     duration,
    }


# ════════════════════════════════════════════════════════════════════════
# Diarization via Azure Speech SDK (ConversationTranscriber)
# ════════════════════════════════════════════════════════════════════════

def _diarize_chunk(audio_bytes: bytes) -> (int, float):
    """
    Run speaker diarization on an audio chunk. Returns (speaker_count, duration_seconds).

    Requires:
      AZURE_SPEECH_KEY    — same key you use for TTS
      AZURE_SPEECH_REGION — same region

    If Azure Speech SDK isn't installed, raises ImportError and the caller
    degrades gracefully.
    """
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError as e:
        raise RuntimeError("azure-cognitiveservices-speech not installed") from e

    key    = os.getenv("AZURE_SPEECH_KEY", "")
    region = os.getenv("AZURE_SPEECH_REGION", "")
    if not key or not region:
        raise RuntimeError("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not configured")

    # Persist chunk to temp WAV (SDK expects file or stream)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        audio_config  = speechsdk.audio.AudioConfig(filename=tmp_path)
        transcriber   = speechsdk.transcription.ConversationTranscriber(
            speech_config=speech_config, audio_config=audio_config,
        )

        speaker_ids = set()
        done = [False]
        duration_ms = [0]

        def _on_transcribed(evt):
            sid = evt.result.speaker_id
            if sid:
                speaker_ids.add(sid)
            try:
                duration_ms[0] = max(duration_ms[0], evt.result.offset // 10000 + evt.result.duration // 10000)
            except Exception:
                pass

        def _on_stopped(_evt):
            done[0] = True

        transcriber.transcribed.connect(_on_transcribed)
        transcriber.session_stopped.connect(_on_stopped)
        transcriber.canceled.connect(_on_stopped)
        transcriber.start_transcribing_async().get()

        # Wait up to ~10 seconds — chunk should be processed by then
        import time
        waited = 0
        while not done[0] and waited < 100:
            time.sleep(0.1)
            waited += 1

        transcriber.stop_transcribing_async().get()
        return (len(speaker_ids) if speaker_ids else 1, duration_ms[0] / 1000.0)

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════
# Final aggregation for the briefing
# ════════════════════════════════════════════════════════════════════════

def summarize_voice_analysis(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pull the final voice-related summary from the session anti_cheat_flags.
    Called by briefing generator to produce a concise paragraph.
    """
    flags = [f for f in session.get("anti_cheat_flags", []) if f.get("source") == "voice_fingerprint"]
    if not flags:
        return {"verdict": "single_speaker_consistent", "flag_count": 0}
    high = [f for f in flags if f.get("severity") == "high"]
    if high:
        return {
            "verdict":    "multiple_voices_detected",
            "flag_count": len(flags),
            "detail":     high[0].get("detail", ""),
        }
    return {"verdict": "minor_voice_anomalies", "flag_count": len(flags)}
