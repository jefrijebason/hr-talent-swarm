/**
 * InterviewPage.jsx — Meeting-style AI Interview
 *
 * Drop-in replacement for: frontend/apply-portal/src/interview/InterviewPage.js
 *
 * SETUP — one-time:
 *   1. cd frontend/apply-portal
 *      npm install microsoft-cognitiveservices-speech-sdk
 *
 *   2. Add to your .env (frontend/apply-portal/.env):
 *      REACT_APP_AZURE_SPEECH_KEY=<your-azure-speech-subscription-key>
 *      REACT_APP_AZURE_SPEECH_REGION=<your-region e.g. centralindia>
 *
 *   3. Restart: npm start
 *
 *   If Azure isn't configured, the page falls back to browser TTS automatically.
 *
 * BACKEND WIRING — search for "TODO: WIRE" in this file to find the 4 spots
 * where you'll connect your real ARIA backend (next-question, submit-answer, etc.)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';

// Azure Speech SDK — optional, falls back gracefully if not installed
let SpeechSDK = null;
try {
  // eslint-disable-next-line global-require
  SpeechSDK = require('microsoft-cognitiveservices-speech-sdk');
} catch (e) {
  console.warn('[ARIA] Azure Speech SDK not installed — will use browser TTS');
}

/* ════════════════════════════════════════════════════════════════════
   CONFIGURATION
════════════════════════════════════════════════════════════════════ */

// Best Azure Neural voices per language (Indian accents preferred)
const AZURE_VOICE = {
  en: 'en-IN-NeerjaNeural',       // Female, Indian English
  hi: 'hi-IN-SwaraNeural',         // Female, Hindi
  ta: 'ta-IN-PallaviNeural',       // Female, Tamil
  te: 'te-IN-ShrutiNeural',        // Female, Telugu
  kn: 'kn-IN-SapnaNeural',         // Female, Kannada
  ml: 'ml-IN-SobhanaNeural',       // Female, Malayalam
  mr: 'mr-IN-AarohiNeural',        // Female, Marathi
  bn: 'bn-IN-TanishaaNeural',      // Female, Bengali
};

const STT_LANG = {
  en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN',
  kn: 'kn-IN', ml: 'ml-IN', mr: 'mr-IN', bn: 'bn-IN',
};

// Real backend integration — no mock questions needed
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const SCREEN_CAPTURE_INTERVAL_MS = 15000;   // capture every 15s
const FACE_BATCH_INTERVAL_MS     = 30000;   // submit face flags every 30s
const VOICE_CHUNK_INTERVAL_MS    = 30000;   // upload voice chunk every 30s


/* ════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
════════════════════════════════════════════════════════════════════ */
export default function InterviewPage({
  candidateId,
  jobId,
  candidateName = 'there',
  roleName = 'this role',
  preferredLanguage = 'en',
}) {
  // ── Stage machine ──────────────────────────────────────────────
  // precall → intro → questions → closing → complete
  const [stage, setStage] = useState('precall');

  // ── Control toggles ────────────────────────────────────────────
  const [isMuted,     setIsMuted]     = useState(false);
  const [isCamOn,     setIsCamOn]     = useState(true);
  const [showText,    setShowText]    = useState(false);
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  // ── Conversation state ─────────────────────────────────────────
  const [isAriaSpeaking, setIsAriaSpeaking] = useState(false);
  const [isListening,    setIsListening]    = useState(false);
  const [caption,        setCaption]        = useState('');
  const [userTranscript, setUserTranscript] = useState('');
  const [questionIndex,  setQuestionIndex]  = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [textInput,      setTextInput]      = useState('');
  const [elapsedSec,     setElapsedSec]     = useState(0);
  const [networkStatus,  setNetworkStatus]  = useState('online'); // online | slow | offline
  const [permissionError, setPermissionError] = useState(null);
  const [tabHidden,      setTabHidden]      = useState(false);
  const [autoSubmitCountdown, setAutoSubmitCountdown] = useState(0);

  // ── Backend session ──
  const [sessionId,      setSessionId]      = useState(null);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [apiError,       setApiError]       = useState(null);

  // ── Screen share ──
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [showShareButton, setShowShareButton] = useState(false);
  const screenStreamRef   = useRef(null);
  const screenVideoRef    = useRef(null);
  const screenCaptureIntervalRef = useRef(null);

  // ── Anti-cheat batching ──
  const faceEventsBuffer  = useRef([]);
  const faceBatchTimerRef = useRef(null);
  const voiceRecorderRef  = useRef(null);
  const voiceChunksRef    = useRef([]);

  // ── Refs ───────────────────────────────────────────────────────
  const videoRef        = useRef(null);
  const cameraStream    = useRef(null);
  const synthRef        = useRef(null);  // Azure synthesizer
  const recognitionRef  = useRef(null);  // Web Speech recognition
  const timerRef        = useRef(null);
  const audioCtxRef     = useRef(null);
  const audioAnalyserRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const lastSpeechAtRef = useRef(0);
  const submitAnswerRef = useRef(null);  // set later to break circular ref

  /* ── Camera setup ─────────────────────────────────────────────── */
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240 },
        audio: true,
      });
      cameraStream.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch (err) {
      console.warn('[ARIA] Camera/mic permission denied:', err);
      setPermissionError(
        err.name === 'NotAllowedError'
          ? 'permission'
          : err.name === 'NotFoundError'
          ? 'no-device'
          : 'unknown'
      );
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (cameraStream.current) {
      cameraStream.current.getTracks().forEach(t => t.stop());
      cameraStream.current = null;
    }
  }, []);

  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, [startCamera, stopCamera]);

  /* ── Network monitoring ─────────────────────────────────────── */
  useEffect(() => {
    const handleOnline = () => setNetworkStatus('online');
    const handleOffline = () => setNetworkStatus('offline');
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Check connection speed via Network Information API
    const checkSpeed = () => {
      const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (!conn) return;
      if (!navigator.onLine) { setNetworkStatus('offline'); return; }
      if (conn.effectiveType === '2g' || conn.effectiveType === 'slow-2g' || conn.downlink < 1) {
        setNetworkStatus('slow');
      } else {
        setNetworkStatus('online');
      }
    };
    checkSpeed();
    const conn = navigator.connection;
    if (conn) conn.addEventListener('change', checkSpeed);
    const interval = setInterval(checkSpeed, 10000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (conn) conn.removeEventListener('change', checkSpeed);
      clearInterval(interval);
    };
  }, []);

  /* ── Tab visibility ─────────────────────────────────────────── */
  useEffect(() => {
    const handleVisibility = () => setTabHidden(document.hidden);
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);


  /* ── Azure Speech TTS setup ──────────────────────────────────── */
  useEffect(() => {
    const key    = process.env.REACT_APP_AZURE_SPEECH_KEY;
    const region = process.env.REACT_APP_AZURE_SPEECH_REGION;

    if (!SpeechSDK || !key || !region) {
      console.warn('[ARIA] Azure Speech not configured — using browser TTS fallback');
      return;
    }

    const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(key, region);
    speechConfig.speechSynthesisVoiceName = AZURE_VOICE[preferredLanguage] || AZURE_VOICE.en;
    const audioConfig = SpeechSDK.AudioConfig.fromDefaultSpeakerOutput();
    synthRef.current = new SpeechSDK.SpeechSynthesizer(speechConfig, audioConfig);

    return () => {
      if (synthRef.current) {
        try { synthRef.current.close(); } catch {}
        synthRef.current = null;
      }
    };
  }, [preferredLanguage]);

  /* ── Speak (TTS) ─────────────────────────────────────────────── */
  const speak = useCallback((text, onDone) => {
    if (!text) { onDone?.(); return; }

    setIsAriaSpeaking(true);
    setCaption(text);

    // Try Azure first
    if (synthRef.current) {
      synthRef.current.speakTextAsync(
        text,
        () => { setIsAriaSpeaking(false); onDone?.(); },
        err => {
          console.error('[ARIA] Azure TTS error:', err);
          setIsAriaSpeaking(false);
          onDone?.();
        }
      );
      return;
    }

    // Fallback: browser TTS
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = STT_LANG[preferredLanguage] || 'en-IN';
    utter.rate = 0.95;
    utter.pitch = 1.05;
    // Try to pick a female voice if available
    const voices = window.speechSynthesis.getVoices();
    const femaleVoice = voices.find(v =>
      v.lang.startsWith(utter.lang.slice(0, 2)) &&
      (v.name.toLowerCase().includes('female') || v.name.includes('Neerja') || v.name.includes('Heera'))
    );
    if (femaleVoice) utter.voice = femaleVoice;
    utter.onend = () => { setIsAriaSpeaking(false); onDone?.(); };
    utter.onerror = () => { setIsAriaSpeaking(false); onDone?.(); };
    window.speechSynthesis.speak(utter);
  }, [preferredLanguage]);

  /* ── Listen (STT) + silence-detection → auto-submit ──────────── */
  const startListening = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.warn('[ARIA] STT not supported in this browser');
      return;
    }
    const recog = new SR();
    recog.continuous = true;
    recog.interimResults = true;
    recog.lang = STT_LANG[preferredLanguage] || 'en-IN';

    recog.onresult = (e) => {
      const t = Array.from(e.results).map(r => r[0].transcript).join('');
      setUserTranscript(t);
      lastSpeechAtRef.current = Date.now();
    };
    recog.onend = () => setIsListening(false);
    recog.onerror = (err) => {
      console.warn('[ARIA] STT error:', err);
      setIsListening(false);
    };

    recog.start();
    recognitionRef.current = recog;
    setIsListening(true);

    // ── Silence detector: poll for 2.5s of silence after speech ──
    const SILENCE_THRESHOLD_MS = 2500;
    silenceTimerRef.current = setInterval(() => {
      if (lastSpeechAtRef.current === 0) return; // user hasn't started yet
      const sinceLastSpeech = Date.now() - lastSpeechAtRef.current;
      if (sinceLastSpeech >= SILENCE_THRESHOLD_MS) {
        // candidate paused long enough — auto-submit
        clearInterval(silenceTimerRef.current);
        silenceTimerRef.current = null;
        lastSpeechAtRef.current = 0;
        setAutoSubmitCountdown(0);
        if (submitAnswerRef.current) submitAnswerRef.current();
      } else {
        const remaining = Math.ceil((SILENCE_THRESHOLD_MS - sinceLastSpeech) / 1000);
        setAutoSubmitCountdown(remaining);
      }
    }, 250);
  }, [preferredLanguage]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      recognitionRef.current = null;
    }
    if (silenceTimerRef.current) {
      clearInterval(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    lastSpeechAtRef.current = 0;
    setAutoSubmitCountdown(0);
    setIsListening(false);
  }, []);

  /* ── Timer ───────────────────────────────────────────────────── */
  useEffect(() => {
    if (stage === 'questions' || stage === 'intro') {
      timerRef.current = setInterval(() => setElapsedSec(s => s + 1), 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [stage]);

  const formatTime = (s) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  /* ── Backend API helpers ─────────────────────────────────────── */
  const api = useCallback(async (path, opts = {}) => {
    const { silent, ...fetchOpts } = opts;
    try {
      const r = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...fetchOpts,
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      return await r.json();
    } catch (err) {
      console.error('[ARIA API]', path, err);
      if (!silent) setApiError(err.message);
      throw err;
    }
  }, []);

  /* ── Resume check on mount ───────────────────────────────────── */
  useEffect(() => {
    if (!candidateId) return;
    (async () => {
      try {
        const r = await api(`/api/interview/${candidateId}/resume`, { silent: true });
        if (r?.status === 'active' && r?.last_question) {
          // Active session found — skip pre-call, resume from where they left off
          console.log('[ARIA] Resuming session', r.session_id);
          setStage('questions');
          setCurrentQuestion(r.last_question);
          setQuestionNumber(r.question_number || 1);
          setTotalQuestions(r.total_questions || 10);
          setSessionId(r.session_id);
          setTimeout(() => {
            speak(r.last_question, () => {
              if (!isMuted) startListening();
            });
          }, 500);
        }
      } catch (e) {
        // No active session — normal pre-call flow (silently ignored)
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

  /* ── Interview flow ──────────────────────────────────────────── */
  const joinInterview = useCallback(async () => {
    if (!candidateId) {
      setApiError('Missing candidate ID');
      return;
    }

    // Auto-resolve jobId from candidate record if not provided as prop
    let resolvedJobId = jobId;
    if (!resolvedJobId) {
      try {
        const cand = await api(`/api/candidates/${candidateId}`);
        resolvedJobId = cand?.job_id;
      } catch (_) {}
      if (!resolvedJobId) {
        setApiError("Couldn't find this candidate's job. Please contact HR.");
        return;
      }
    }

    setStage('intro');
    try {
      const r = await api('/api/interview/start', {
        method: 'POST',
        body: JSON.stringify({ candidate_id: candidateId, job_id: resolvedJobId }),
      });
      setSessionId(r.session_id);
      setTotalQuestions(r.total_questions || 10);
      setQuestionNumber(1);
      setCurrentQuestion(r.first_question);

      // Speak greeting, then the first question
      speak(r.greeting, () => {
        setStage('questions');
        speak(r.first_question, () => {
          if (!isMuted) startListening();
        });
      });

      // Start background anti-cheat batching
      startFaceBatcher();
      startVoiceRecorder();
    } catch (e) {
      // api() already set apiError
      setStage('precall');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId, jobId, api, speak, startListening, isMuted]);

  /* ── submitAnswerAndContinue — drives the conversation via backend ── */
  const submitAnswerAndContinue = useCallback(async () => {
    stopListening();
    const answer = (showText ? textInput : userTranscript).trim();
    if (!answer) return;

    setUserTranscript('');
    setTextInput('');

    try {
      const r = await api('/api/interview/answer', {
        method: 'POST',
        body: JSON.stringify({
          candidate_id: candidateId,
          answer_text: answer,
        }),
      });

      // Action: 'probe' | 'next' | 'wrap_up'
      if (r.is_screen_share_request) {
        setShowShareButton(true);
      }

      if (r.action === 'wrap_up' || r.is_closing) {
        setStage('closing');
        setCurrentQuestion(r.next_question);
        speak(r.next_question, async () => {
          // Auto-complete interview
          try {
            await api(`/api/interview/${candidateId}/complete`, { method: 'POST' });
          } catch (_) {}
          stopAllAntiCheat();
          stopScreenShare();
          setStage('complete');
          confetti({
            particleCount: 100, spread: 80, origin: { y: 0.4 },
            colors: ['#5b8def', '#8f9bff', '#6db4f0', '#d8b878'],
          });
        });
        return;
      }

      // Regular next question (or probe)
      setCurrentQuestion(r.next_question);
      if (r.question_number) setQuestionNumber(r.question_number);

      speak(r.next_question, () => {
        if (!isMuted && !r.is_screen_share_request) startListening();
      });
    } catch (e) {
      // api() already set apiError. Keep the UI usable.
      console.error('[ARIA] submit answer failed', e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId, showText, textInput, userTranscript, api,
      speak, startListening, stopListening, isMuted]);

  // Keep ref in sync so the silence detector (set up earlier) can call it
  useEffect(() => {
    submitAnswerRef.current = submitAnswerAndContinue;
  }, [submitAnswerAndContinue]);

  const toggleMute = () => {
    if (cameraStream.current) {
      cameraStream.current.getAudioTracks().forEach(t => t.enabled = isMuted);
    }
    if (isMuted) {
      // Re-enable listening if we're mid-question
      if (stage === 'questions' && !isAriaSpeaking) startListening();
    } else {
      stopListening();
    }
    setIsMuted(!isMuted);
  };

  const toggleCam = () => {
    if (cameraStream.current) {
      cameraStream.current.getVideoTracks().forEach(t => t.enabled = !isCamOn);
    }
    setIsCamOn(!isCamOn);
  };

  const handleEndInterview = useCallback(async () => {
    stopListening();
    stopAllAntiCheat();
    stopScreenShare();
    stopCamera();
    try {
      await api(`/api/interview/${candidateId}/complete`, { method: 'POST' });
    } catch (_) {}
    setShowEndConfirm(false);
    setStage('complete');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId, api, stopListening, stopCamera]);

  /* ──────────────────────────────────────────────────────────── */
  /*  SCREEN SHARE                                                 */
  /* ──────────────────────────────────────────────────────────── */
  const startScreenShare = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' },
        audio: false,
      });
      screenStreamRef.current = stream;
      if (screenVideoRef.current) screenVideoRef.current.srcObject = stream;
      setIsScreenSharing(true);
      setShowShareButton(false);

      // User clicked browser's native "Stop sharing" → end share
      stream.getVideoTracks()[0].onended = () => stopScreenShare();

      // Resume listening once they share
      if (!isMuted) startListening();

      // Start periodic frame capture → backend vision analyzer
      screenCaptureIntervalRef.current = setInterval(captureScreenFrame, SCREEN_CAPTURE_INTERVAL_MS);
      // First capture after 3s (give them time to navigate)
      setTimeout(captureScreenFrame, 3000);
    } catch (err) {
      console.warn('[ARIA] Screen share declined:', err);
      setShowShareButton(false);
      if (!isMuted) startListening();  // proceed without screen share
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMuted, startListening]);

  const stopScreenShare = useCallback(() => {
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(t => t.stop());
      screenStreamRef.current = null;
    }
    if (screenCaptureIntervalRef.current) {
      clearInterval(screenCaptureIntervalRef.current);
      screenCaptureIntervalRef.current = null;
    }
    setIsScreenSharing(false);
  }, []);

  const captureScreenFrame = useCallback(async () => {
    const video = screenVideoRef.current;
    if (!video || !screenStreamRef.current) return;
    if (video.videoWidth === 0) return;

    // Downscale to reduce upload + vision cost
    const maxW = 1280;
    const scale = Math.min(1, maxW / video.videoWidth);
    const canvas = document.createElement('canvas');
    canvas.width  = video.videoWidth  * scale;
    canvas.height = video.videoHeight * scale;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const form = new FormData();
      form.append('frame', blob, 'frame.jpg');
      try {
        const r = await fetch(`${API_BASE}/api/interview/${candidateId}/screen-frame`, {
          method: 'POST',
          body: form,
        });
        const data = await r.json().catch(() => ({}));
        // If ARIA wants to ask a contextual follow-up about what she sees, speak it
        if (data.follow_up_question && !data.skipped) {
          stopListening();
          speak(data.follow_up_question, () => {
            if (!isMuted) startListening();
          });
        }
      } catch (e) {
        console.warn('[ARIA] screen-frame upload failed:', e);
      }
    }, 'image/jpeg', 0.75);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId, isMuted, speak, startListening, stopListening]);

  /* ──────────────────────────────────────────────────────────── */
  /*  ANTI-CHEAT: face/gaze batching + voice chunks                */
  /* ──────────────────────────────────────────────────────────── */
  const recordFaceEvent = useCallback((event) => {
    faceEventsBuffer.current.push({
      ...event,
      timestamp: new Date().toISOString(),
    });
    // Multiple-faces is high severity — fire immediately
    if (event.type === 'multiple_faces') {
      fetch(`${API_BASE}/api/interview/face-flag-immediate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_id: candidateId, event }),
      }).catch(() => {});
    }
  }, [candidateId]);

  const flushFaceBatch = useCallback(async () => {
    if (faceEventsBuffer.current.length === 0) return;
    const events = faceEventsBuffer.current;
    faceEventsBuffer.current = [];
    try {
      await fetch(`${API_BASE}/api/interview/face-flag-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          events,
          session_duration_sec: elapsedSec,
        }),
      });
    } catch (e) {
      console.warn('[ARIA] face batch flush failed:', e);
    }
  }, [candidateId, elapsedSec]);

  const startFaceBatcher = useCallback(() => {
    // Record tab-switch events
    const onVisibilityChange = () => {
      if (document.hidden) recordFaceEvent({ type: 'tab_switch', count: 1 });
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    faceBatchTimerRef.current = setInterval(flushFaceBatch, FACE_BATCH_INTERVAL_MS);
    // Try loading MediaPipe Face Landmarker for eye-gaze tracking (best-effort)
    initFaceLandmarker();
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [recordFaceEvent, flushFaceBatch]);

  const initFaceLandmarker = useCallback(async () => {
    // MediaPipe is heavy (~10MB). Loaded lazily, fails gracefully.
    try {
      const { FaceLandmarker, FilesetResolver } = await import('@mediapipe/tasks-vision');
      const fileset = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
      );
      const landmarker = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: {
          modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        outputFaceBlendshapes: true,
        numFaces: 2,  // detect if multiple faces present
      });
      runFaceDetectionLoop(landmarker);
    } catch (e) {
      console.warn('[ARIA] Face landmarker unavailable — falling back to tab-visibility only:', e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runFaceDetectionLoop = useCallback((landmarker) => {
    const video = videoRef.current;
    if (!video) return;

    let lastNoFaceAt = null;
    let lastOffScreenAt = null;

    const tick = () => {
      if (!video.videoWidth || stage !== 'questions') {
        requestAnimationFrame(tick);
        return;
      }
      try {
        const result = landmarker.detectForVideo(video, performance.now());
        const faceCount = (result.faceLandmarks || []).length;
        const now = Date.now();

        if (faceCount === 0) {
          if (lastNoFaceAt === null) lastNoFaceAt = now;
          else if (now - lastNoFaceAt > 5000) {
            recordFaceEvent({ type: 'no_face', duration_sec: (now - lastNoFaceAt) / 1000 });
            lastNoFaceAt = now;
          }
        } else {
          lastNoFaceAt = null;
        }

        if (faceCount > 1) {
          recordFaceEvent({ type: 'multiple_faces', count: faceCount });
        }

        // Rough gaze inference via blendshapes (eyeLookOutLeft / eyeLookOutRight strength)
        const blends = result.faceBlendshapes?.[0]?.categories || [];
        const lookOut = blends.find(b => b.categoryName === 'eyeLookOutLeft')?.score
                      + blends.find(b => b.categoryName === 'eyeLookOutRight')?.score;
        if (lookOut && lookOut > 0.6) {
          if (lastOffScreenAt === null) lastOffScreenAt = now;
          else if (now - lastOffScreenAt > 3000) {
            recordFaceEvent({ type: 'looking_off_screen', duration_sec: (now - lastOffScreenAt) / 1000 });
            lastOffScreenAt = now;
          }
        } else {
          lastOffScreenAt = null;
        }
      } catch (_) {}
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [stage, recordFaceEvent]);

  const startVoiceRecorder = useCallback(() => {
    if (!cameraStream.current) return;
    try {
      const audioTracks = cameraStream.current.getAudioTracks();
      if (audioTracks.length === 0) return;
      const audioStream = new MediaStream(audioTracks);
      const mr = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
      mr.ondataavailable = async (e) => {
        if (e.data.size === 0) return;
        const form = new FormData();
        form.append('audio', e.data, 'chunk.webm');
        try {
          await fetch(`${API_BASE}/api/interview/${candidateId}/voice-chunk`, {
            method: 'POST', body: form,
          });
        } catch (_) {}
      };
      mr.start(VOICE_CHUNK_INTERVAL_MS);   // emits a blob every 30s
      voiceRecorderRef.current = mr;
    } catch (e) {
      console.warn('[ARIA] Voice recorder unavailable:', e);
    }
  }, [candidateId]);

  const stopAllAntiCheat = useCallback(() => {
    if (faceBatchTimerRef.current) {
      clearInterval(faceBatchTimerRef.current);
      faceBatchTimerRef.current = null;
    }
    flushFaceBatch();
    if (voiceRecorderRef.current && voiceRecorderRef.current.state !== 'inactive') {
      try { voiceRecorderRef.current.stop(); } catch (_) {}
      voiceRecorderRef.current = null;
    }
  }, [flushFaceBatch]);

  /* ──────────────────────────────────────────────────────────── */
  /*  RENDER                                                       */
  /* ──────────────────────────────────────────────────────────── */
  return (
    <div className="iv-page">
      <style>{INTERVIEW_CSS}</style>

      {/* Ambient background */}
      <div className="iv-bg" />
      <div className="iv-grid-overlay" />

      {/* Hidden video element for screen capture (always mounted) */}
      <video ref={screenVideoRef} autoPlay muted playsInline
        style={{ position: 'absolute', width: 1, height: 1, opacity: 0, pointerEvents: 'none' }} />

      {/* ── API error banner ── */}
      {apiError && (
        <div className="iv-banner iv-banner-error" style={{ top: 80 }}>
          ⚠ {apiError}
          <button onClick={() => setApiError(null)}
            style={{ marginLeft: 12, background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: 16 }}>✕</button>
        </div>
      )}

      {/* ── Connection / permission / tab-hidden banners ── */}
      <AnimatePresence>
        {networkStatus !== 'online' && (
          <motion.div className={`iv-banner iv-banner-${networkStatus === 'offline' ? 'error' : 'warn'}`}
            initial={{ y: -50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -50, opacity: 0 }}>
            {networkStatus === 'offline'
              ? '⚠ You appear to be offline. Your interview will resume when connection returns.'
              : '⚠ Slow connection detected. Audio may stutter — please switch to better network if possible.'}
          </motion.div>
        )}
        {tabHidden && (stage === 'questions' || stage === 'intro') && (
          <motion.div className="iv-banner iv-banner-warn"
            initial={{ y: -50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -50, opacity: 0 }}>
            ⚠ Please stay on this tab during the interview. Switching tabs is logged.
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Permission denied overlay ── */}
      {permissionError && (
        <div className="iv-perm-overlay">
          <div className="iv-perm-card">
            <div className="iv-perm-icon">🎤</div>
            <h2>{permissionError === 'no-device' ? 'No camera/microphone found' : 'Camera & microphone access needed'}</h2>
            <p>{permissionError === 'no-device'
              ? "We couldn't detect a camera or microphone on your device. Please connect one and refresh."
              : "ARIA needs access to your camera and microphone to conduct the interview. Click the camera icon in your browser's address bar and allow access, then refresh this page."}</p>
            <button onClick={() => window.location.reload()}>↻ Refresh & Try Again</button>
          </div>
        </div>
      )}

      <AnimatePresence mode="wait">
        {stage === 'precall' && (
          <PreCallScreen
            key="precall"
            candidateName={candidateName}
            roleName={roleName}
            videoRef={videoRef}
            cameraStream={cameraStream}
            onJoin={joinInterview}
          />
        )}

        {(stage === 'intro' || stage === 'questions' || stage === 'closing') && (
          <motion.div key="stage" className="iv-stage"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>

            {/* ── Top bar ── */}
            <div className="iv-topbar">
              <div className="iv-topleft">
                <span className="iv-badge">ARIA · AI Interview</span>
                <span className="iv-rolename">{roleName}</span>
              </div>
              <div className="iv-topright">
                <span className="iv-rec">
                  <span className="iv-recdot" /> REC
                </span>
                <span className="iv-timer">{formatTime(elapsedSec)}</span>
                <span className="iv-round">
                  Q{questionNumber} of {totalQuestions}
                </span>
              </div>
            </div>

            {/* ── ARIA orb OR screen share view ── */}
            {!isScreenSharing && (
              <div className="iv-orb-wrap">
                <AriaOrb speaking={isAriaSpeaking} listening={isListening} />
                <div className="iv-aria-name">
                  ARIA {isAriaSpeaking ? '— speaking' : isListening ? '— listening to you' : '— thinking...'}
                </div>
              </div>
            )}

            {isScreenSharing && (
              <div className="iv-screen-share-stage">
                <div className="iv-screen-share-banner">
                  <span className="iv-share-dot" /> Screen sharing — ARIA is watching
                </div>
                <div className="iv-screen-share-view">
                  <video autoPlay muted playsInline
                    ref={(el) => { if (el && screenStreamRef.current) el.srcObject = screenStreamRef.current; }} />
                </div>
                {/* Mini orb stays visible in the corner */}
                <div className="iv-orb-mini">
                  <AriaOrb speaking={isAriaSpeaking} listening={isListening} size={80} />
                </div>
              </div>
            )}

            {/* ── Live caption / transcript ── */}
            <div className="iv-caption-area">
              {currentQuestion && stage === 'questions' && (
                <div className="iv-q-marker">Question {questionNumber}</div>
              )}
              {isAriaSpeaking && (
                <CaptionLine kind="aria" text={caption} />
              )}
              {(isListening || userTranscript) && !isAriaSpeaking && (
                <>
                  <CaptionLine kind="user" text={userTranscript || 'Listening...'} />
                  {autoSubmitCountdown > 0 && userTranscript && (
                    <div className="iv-autosubmit">
                      <span className="iv-autosubmit-dot" />
                      ARIA will continue in {autoSubmitCountdown}s — keep talking to add more
                    </div>
                  )}
                </>
              )}
            </div>

            {/* ── Webcam PiP ── */}
            <div className={`iv-webcam ${!isCamOn ? 'iv-cam-off' : ''}`}>
              {isCamOn ? (
                <video
                  ref={(el) => {
                    videoRef.current = el;
                    if (el && cameraStream.current && el.srcObject !== cameraStream.current) {
                      el.srcObject = cameraStream.current;
                    }
                  }}
                  autoPlay muted playsInline />
              ) : (
                <div className="iv-cam-placeholder">
                  <div className="iv-cam-avatar">
                    {candidateName.slice(0, 1).toUpperCase()}
                  </div>
                  <div className="iv-cam-label">Camera off</div>
                </div>
              )}
              <div className="iv-cam-name">You</div>
            </div>

            {/* ── Text fallback panel (toggled) ── */}
            <AnimatePresence>
              {showText && stage === 'questions' && (
                <motion.div className="iv-textpanel"
                  initial={{ y: 60, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: 60, opacity: 0 }}>
                  <textarea
                    value={textInput}
                    onChange={e => setTextInput(e.target.value)}
                    placeholder="Type your answer here if you prefer..."
                    rows={3}
                  />
                  <button
                    onClick={submitAnswerAndContinue}
                    disabled={!textInput.trim() || isAriaSpeaking}>
                    Submit Answer →
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Control bar ── */}
            <ControlBar
              isMuted={isMuted}
              isCamOn={isCamOn}
              showText={showText}
              showShareButton={showShareButton}
              isScreenSharing={isScreenSharing}
              onMute={toggleMute}
              onCam={toggleCam}
              onText={() => setShowText(!showText)}
              onShare={startScreenShare}
              onStopShare={stopScreenShare}
              onEnd={() => setShowEndConfirm(true)}
            />
          </motion.div>
        )}

        {stage === 'complete' && (
          <CompleteScreen
            key="complete"
            candidateName={candidateName}
            roleName={roleName}
            duration={formatTime(elapsedSec)}
          />
        )}
      </AnimatePresence>

      {/* ── End-interview confirmation modal ── */}
      <AnimatePresence>
        {showEndConfirm && (
          <motion.div className="iv-modal-overlay"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowEndConfirm(false)}>
            <motion.div className="iv-modal"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={e => e.stopPropagation()}>
              <div className="iv-modal-icon">⚠</div>
              <h2>End interview now?</h2>
              <p>You're on question {questionNumber} of {totalQuestions}.
                  If you end now, you won't be able to come back to finish.</p>
              <div className="iv-modal-actions">
                <button className="btn-ghost" onClick={() => setShowEndConfirm(false)}>
                  Continue Interview
                </button>
                <button className="btn-danger" onClick={handleEndInterview}>
                  End Interview
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PRE-CALL SCREEN
════════════════════════════════════════════════════════════════════ */
function PreCallScreen({ candidateName, roleName, videoRef, cameraStream, onJoin }) {
  const [micLevel, setMicLevel] = useState(0);
  const animRef = useRef(null);

  useEffect(() => {
    // Animate mic level meter
    let stream;
    let ctx;
    let analyser;
    const setup = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        const src = ctx.createMediaStreamSource(stream);
        analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        src.connect(analyser);
        const data = new Uint8Array(analyser.frequencyBinCount);

        const tick = () => {
          analyser.getByteFrequencyData(data);
          const avg = data.reduce((s, v) => s + v, 0) / data.length;
          setMicLevel(Math.min(100, (avg / 128) * 100));
          animRef.current = requestAnimationFrame(tick);
        };
        tick();
      } catch (e) {
        console.warn('[ARIA] Mic level setup failed:', e);
      }
    };
    setup();
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      if (stream) stream.getTracks().forEach(t => t.stop());
      if (ctx) ctx.close();
    };
  }, []);

  return (
    <motion.div className="iv-precall"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
      <div className="iv-precall-card">
        <div className="iv-precall-head">
          <div className="iv-precall-orb">
            <AriaOrb speaking={false} listening={false} size={120} />
          </div>
          <h1>Ready for your interview?</h1>
          <p>You're about to meet <strong>ARIA</strong>, your AI interviewer,
              for the <strong>{roleName}</strong> role. Take a moment to check
              your camera and microphone.</p>
        </div>

        <div className="iv-precall-tests">
          {/* Camera preview */}
          <div className="iv-pretest">
            <div className="iv-pretest-label">📹 Camera</div>
            <div className="iv-pretest-video">
              <video
                ref={(el) => {
                  if (videoRef) videoRef.current = el;
                  if (el && cameraStream?.current && el.srcObject !== cameraStream.current) {
                    el.srcObject = cameraStream.current;
                  }
                }}
                autoPlay muted playsInline />
            </div>
          </div>

          {/* Mic level meter */}
          <div className="iv-pretest">
            <div className="iv-pretest-label">🎤 Microphone</div>
            <div className="iv-mic-meter">
              <div className="iv-mic-fill" style={{ width: `${micLevel}%` }} />
            </div>
            <div className="iv-pretest-hint">
              {micLevel > 5 ? '✓ Mic working — say something to test' : 'Speak to test your mic'}
            </div>
          </div>


        </div>

        <button className="iv-join-btn" onClick={onJoin}>
          Join Interview →
        </button>
        <div className="iv-precall-note">
          Hi <strong>{candidateName}</strong> — when you're ready, click Join.
          The interview takes about 15–25 minutes.
        </div>
      </div>
    </motion.div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   ARIA ORB — animated glowing avatar
════════════════════════════════════════════════════════════════════ */
function AriaOrb({ speaking, listening, size = 220 }) {
  const cls = speaking ? 'speaking' : listening ? 'listening' : 'idle';
  return (
    <div className={`iv-orb ${cls}`} style={{ width: size, height: size }}>
      <div className="iv-orb-halo" />
      <div className="iv-orb-core" />
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   CAPTION LINE
════════════════════════════════════════════════════════════════════ */
function CaptionLine({ kind, text }) {
  return (
    <motion.div className={`iv-caption iv-caption-${kind}`}
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <span className="iv-caption-tag">{kind === 'aria' ? 'ARIA' : 'You'}</span>
      <span className="iv-caption-text">{text}</span>
    </motion.div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   CONTROL BAR
════════════════════════════════════════════════════════════════════ */
function ControlBar({ isMuted, isCamOn, showText, showShareButton, isScreenSharing,
                      onMute, onCam, onText, onShare, onStopShare, onEnd }) {
  return (
    <motion.div className="iv-controlbar"
      initial={{ y: 80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.4 }}>
      <CtrlBtn icon={isMuted ? '🔇' : '🎤'} label={isMuted ? 'Unmute' : 'Mute'}
        active={isMuted} onClick={onMute} />
      <CtrlBtn icon={isCamOn ? '📹' : '📷'} label={isCamOn ? 'Camera' : 'Cam off'}
        active={!isCamOn} onClick={onCam} />
      <CtrlBtn icon="💬" label="Type"
        active={showText} onClick={onText} />
      {showShareButton && !isScreenSharing && (
        <CtrlBtn icon="🖥" label="Share Screen" primary onClick={onShare} />
      )}
      {isScreenSharing && (
        <CtrlBtn icon="🛑" label="Stop Share" active onClick={onStopShare} />
      )}
      <CtrlBtn icon="📞" label="End"
        danger onClick={onEnd} />
    </motion.div>
  );
}

function CtrlBtn({ icon, label, active, primary, danger, disabled, onClick }) {
  const cls = [
    'iv-ctrl',
    active ? 'iv-ctrl-active' : '',
    primary ? 'iv-ctrl-primary' : '',
    danger ? 'iv-ctrl-danger' : '',
    disabled ? 'iv-ctrl-disabled' : '',
  ].filter(Boolean).join(' ');
  return (
    <button className={cls} onClick={onClick} disabled={disabled}>
      <span className="iv-ctrl-icon">{icon}</span>
      <span className="iv-ctrl-label">{label}</span>
    </button>
  );
}

/* ════════════════════════════════════════════════════════════════════
   COMPLETE SCREEN
════════════════════════════════════════════════════════════════════ */
function CompleteScreen({ candidateName, roleName, duration }) {
  return (
    <motion.div className="iv-complete"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}>
      <div className="iv-complete-card">
        <motion.div className="iv-complete-icon"
          initial={{ scale: 0, rotate: -90 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 200, damping: 14, delay: 0.2 }}>
          ✓
        </motion.div>
        <h1>Interview complete!</h1>
        <p>Thank you, <strong>{candidateName}</strong>.
          Your responses for the <strong>{roleName}</strong> role have been recorded.</p>

        <div className="iv-complete-stats">
          <div className="iv-stat">
            <div className="iv-stat-val">{duration}</div>
            <div className="iv-stat-lbl">Duration</div>
          </div>
          <div className="iv-stat">
            <div className="iv-stat-val">100%</div>
            <div className="iv-stat-lbl">Complete</div>
          </div>
        </div>

        <div className="iv-complete-next">
          <h3>What happens next</h3>
          <ul>
            <li>🤖 AI is analyzing your responses (takes ~3-5 min)</li>
            <li>🎯 You'll get a notification email with the outcome</li>
            <li>👤 If shortlisted, a human interviewer will reach out</li>
          </ul>
        </div>

        <button onClick={() => window.close()} className="iv-complete-btn">
          Close Window
        </button>
      </div>
    </motion.div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   CSS  (self-contained — injected into <style>)
════════════════════════════════════════════════════════════════════ */
const INTERVIEW_CSS = `
/* ── Reset & base ─────────────────────────────────── */
.iv-page * { box-sizing: border-box; margin: 0; padding: 0; }
.iv-page {
  position: fixed; inset: 0; z-index: 9999;
  background: #050811;
  color: #eaeef6;
  font-family: 'Sora', system-ui, -apple-system, sans-serif;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

/* ── Ambient background ───────────────────────────── */
.iv-bg {
  position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(1000px 600px at 20% 30%, rgba(91,141,239,0.15), transparent 60%),
    radial-gradient(800px 600px at 80% 70%, rgba(143,155,255,0.10), transparent 55%),
    radial-gradient(600px 500px at 50% 50%, rgba(109,180,240,0.08), transparent 60%);
  animation: bg-shift 20s ease-in-out infinite;
}
@keyframes bg-shift {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}
.iv-grid-overlay {
  position: absolute; inset: 0; pointer-events: none; opacity: 0.04;
  background-image:
    linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px);
  background-size: 64px 64px;
}

/* ════ PRE-CALL ════════════════════════════════════════ */
.iv-precall {
  position: absolute; inset: 0; z-index: 2;
  display: grid; place-items: center; padding: 24px;
}
.iv-precall-card {
  width: 560px; max-width: 96vw;
  background: linear-gradient(180deg, rgba(17,23,38,0.95), rgba(13,18,29,0.95));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 28px;
  padding: 36px 36px 30px;
  box-shadow: 0 40px 100px -20px rgba(0,0,0,0.7);
  backdrop-filter: blur(20px);
}
.iv-precall-head { text-align: center; margin-bottom: 28px; }
.iv-precall-orb {
  width: 120px; height: 120px; margin: 0 auto 18px;
  position: relative;
}
.iv-precall-head h1 {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 800; font-size: 28px; letter-spacing: -0.02em;
  margin-bottom: 10px;
}
.iv-precall-head p {
  color: #92a0ba; font-size: 14px; line-height: 1.65; max-width: 440px; margin: 0 auto;
}
.iv-precall-head strong { color: #eaeef6; font-weight: 600; }

.iv-precall-tests {
  display: grid; gap: 14px; margin-bottom: 26px;
}
.iv-pretest {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 14px 16px;
}
.iv-pretest-label {
  font-size: 12px; font-weight: 600; color: #92a0ba; margin-bottom: 10px;
}
.iv-pretest-video {
  width: 100%; height: 130px; border-radius: 10px; overflow: hidden;
  background: #000; display: grid; place-items: center;
}
.iv-pretest-video video {
  width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1);
}
.iv-mic-meter {
  height: 8px; background: rgba(255,255,255,0.06); border-radius: 100px;
  overflow: hidden;
}
.iv-mic-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #5b8def);
  transition: width 0.08s linear;
  border-radius: 100px;
}
.iv-pretest-hint {
  font-size: 11px; color: #5a667e; margin-top: 8px;
  font-family: 'JetBrains Mono', monospace;
}
.iv-test-voice {
  width: 100%; padding: 11px; border-radius: 10px;
  background: rgba(91,141,239,0.12);
  border: 1px solid rgba(91,141,239,0.3);
  color: #5b8def; font-family: inherit; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.iv-test-voice:hover:not(:disabled) {
  background: rgba(91,141,239,0.2); transform: translateY(-1px);
}
.iv-test-voice:disabled { opacity: 0.5; cursor: not-allowed; }

.iv-join-btn {
  width: 100%; padding: 16px; border-radius: 14px; border: none;
  background: linear-gradient(135deg, #5b8def, #3f6fd1);
  color: #fff; font-family: inherit; font-size: 16px; font-weight: 700;
  cursor: pointer; transition: all 0.2s;
  box-shadow: 0 12px 32px -8px rgba(91,141,239,0.6);
}
.iv-join-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px -8px rgba(91,141,239,0.75);
}
.iv-precall-note {
  text-align: center; font-size: 12px; color: #5a667e; margin-top: 14px;
}

/* ════ MAIN STAGE ════════════════════════════════════ */
.iv-stage {
  position: absolute; inset: 0; z-index: 2;
  display: flex; flex-direction: column;
  padding: 24px;
}
.iv-topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 22px;
  background: rgba(17,23,38,0.6);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  backdrop-filter: blur(20px);
}
.iv-topleft { display: flex; align-items: center; gap: 14px; }
.iv-topright { display: flex; align-items: center; gap: 16px; }
.iv-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  background: rgba(91,141,239,0.15); color: #5b8def;
  padding: 5px 10px; border-radius: 6px;
  letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700;
}
.iv-rolename { font-size: 13px; color: #92a0ba; font-weight: 500; }
.iv-rec {
  display: flex; align-items: center; gap: 6px;
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: #e0758a; font-weight: 700; letter-spacing: 0.08em;
}
.iv-recdot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #e0758a; animation: rec-blink 1.5s infinite;
}
@keyframes rec-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.iv-timer {
  font-family: 'JetBrains Mono', monospace; font-size: 14px;
  color: #eaeef6; font-weight: 600;
}
.iv-round {
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: #5b8def;
  padding: 5px 10px; background: rgba(91,141,239,0.1);
  border: 1px solid rgba(91,141,239,0.25); border-radius: 7px;
  font-weight: 700;
}

/* ── Center ── */
.iv-orb-wrap {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 18px;
  margin-top: -40px;
}
.iv-aria-name {
  font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: #92a0ba; letter-spacing: 0.05em;
}



/* ── Q-number marker ── */
.iv-q-marker {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: #5a667e;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 5px 10px; border-radius: 6px;
  margin-bottom: 10px;
}

/* ── Caption area ── */
.iv-caption-area {
  position: absolute; bottom: 130px; left: 50%; transform: translateX(-50%);
  max-width: 720px; width: calc(100% - 48px); padding: 0 24px;
}
.iv-caption {
  background: rgba(17,23,38,0.7);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 14px 18px;
  backdrop-filter: blur(12px);
  display: flex; align-items: flex-start; gap: 12px;
  margin-bottom: 8px;
}
.iv-caption-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  padding: 3px 8px; border-radius: 5px; flex-shrink: 0;
  letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700;
}
.iv-caption-aria .iv-caption-tag {
  background: rgba(91,141,239,0.18); color: #5b8def;
}
.iv-caption-user .iv-caption-tag {
  background: rgba(74,222,128,0.18); color: #4ade80;
}
.iv-caption-text {
  font-size: 14px; color: #eaeef6; line-height: 1.55; flex: 1;
}

/* ── Webcam PiP ── */
.iv-webcam {
  position: absolute; bottom: 110px; right: 24px;
  width: 180px; height: 135px; border-radius: 14px; overflow: hidden;
  background: #000;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 12px 36px -8px rgba(0,0,0,0.6);
}
.iv-webcam video {
  width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1);
}
.iv-cam-off { background: #1a1f2e; }
.iv-cam-placeholder {
  width: 100%; height: 100%;
  display: grid; place-items: center;
  background: linear-gradient(135deg, #1a1f2e, #0d121d);
}
.iv-cam-avatar {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #5b8def, #8f9bff);
  display: grid; place-items: center;
  font-size: 22px; font-weight: 700; color: #fff;
}
.iv-cam-label {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  font-size: 10px; color: #5a667e; font-family: 'JetBrains Mono', monospace;
}
.iv-cam-name {
  position: absolute; bottom: 6px; left: 8px;
  font-size: 10px; color: #fff;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(0,0,0,0.5); padding: 2px 8px; border-radius: 4px;
}

/* ── Text panel ── */
.iv-textpanel {
  position: absolute; bottom: 130px; left: 50%; transform: translateX(-50%);
  width: 90%; max-width: 720px;
  background: rgba(17,23,38,0.95);
  border: 1px solid rgba(91,141,239,0.3);
  border-radius: 16px;
  padding: 16px;
  display: flex; gap: 12px; align-items: flex-end;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 50px -10px rgba(0,0,0,0.5);
}
.iv-textpanel textarea {
  flex: 1; background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px; padding: 12px 14px;
  color: #eaeef6; font-family: inherit; font-size: 14px;
  resize: none; outline: none; line-height: 1.5;
}
.iv-textpanel textarea:focus {
  border-color: rgba(91,141,239,0.5);
}
.iv-textpanel button {
  padding: 12px 22px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, #5b8def, #3f6fd1);
  color: #fff; font-family: inherit; font-weight: 700; font-size: 13px;
  cursor: pointer; white-space: nowrap;
  box-shadow: 0 6px 18px -4px rgba(91,141,239,0.5);
}
.iv-textpanel button:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Control bar ── */
.iv-controlbar {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 8px;
  padding: 10px;
  background: rgba(17,23,38,0.85);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 50px -10px rgba(0,0,0,0.6);
}
.iv-ctrl {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: #eaeef6;
  padding: 10px 16px; border-radius: 12px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  cursor: pointer; transition: all 0.15s;
  font-family: inherit; min-width: 72px;
}
.iv-ctrl:hover:not(.iv-ctrl-disabled) {
  background: rgba(255,255,255,0.08); transform: translateY(-2px);
}
.iv-ctrl-active {
  background: rgba(216,184,120,0.18);
  border-color: rgba(216,184,120,0.4);
  color: #d8b878;
}
.iv-ctrl-primary {
  background: linear-gradient(135deg, #5b8def, #3f6fd1);
  border-color: transparent; color: #fff;
}
.iv-ctrl-primary:hover {
  background: linear-gradient(135deg, #6d99f0, #4a7be0);
}
.iv-ctrl-danger {
  background: rgba(224,117,138,0.15);
  border-color: rgba(224,117,138,0.35);
  color: #e0758a;
}
.iv-ctrl-danger:hover {
  background: rgba(224,117,138,0.25);
}
.iv-ctrl-disabled { opacity: 0.35; cursor: not-allowed; }
.iv-ctrl-icon { font-size: 18px; }
.iv-ctrl-label {
  font-size: 10px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}

/* ════ ARIA ORB — AURORA SPHERE (calm, no bouncing) ═════════════ */
.iv-orb {
  position: relative;
  display: grid; place-items: center;
}
.iv-orb-halo {
  position: absolute; inset: -8%; border-radius: 50%;
  background: radial-gradient(circle, rgba(91,141,239,0.22) 0%, rgba(143,155,255,0.08) 40%, transparent 70%);
  filter: blur(28px);
  opacity: 0.7;
  transition: opacity 0.6s ease, transform 0.8s ease;
}
.iv-orb-core {
  position: relative;
  width: 70%; height: 70%; border-radius: 50%;
  overflow: hidden;
  box-shadow:
    0 0 40px 2px rgba(91,141,239,0.3),
    inset 0 -20px 40px rgba(45,91,184,0.6),
    inset 0 -3px 0 rgba(0,0,0,0.2);
  transition: box-shadow 0.6s ease;
}
.iv-orb-core::before {
  content: '';
  position: absolute; inset: -25%;
  background: conic-gradient(from 0deg,
    #5b8def 0%, #8f9bff 20%, #6db4f0 40%,
    #5b8def 60%, #4a7be0 80%, #5b8def 100%);
  border-radius: 50%;
  animation: aurora-rotate 14s linear infinite;
  filter: blur(8px);
}
.iv-orb-core::after {
  content: '';
  position: absolute; inset: 0; border-radius: 50%;
  background:
    radial-gradient(ellipse at 30% 25%, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0.15) 25%, transparent 50%),
    radial-gradient(circle at 75% 80%, rgba(0,0,0,0.2), transparent 40%);
  pointer-events: none;
}

@keyframes aurora-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Idle: gentle slow rotation, no scale-bouncing */
.iv-orb.idle .iv-orb-halo {
  animation: halo-idle 6s ease-in-out infinite;
}
@keyframes halo-idle {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 0.75; transform: scale(1.04); }
}

/* Speaking: glow pulses gently, aurora slightly faster */
.iv-orb.speaking .iv-orb-core {
  box-shadow:
    0 0 70px 6px rgba(91,141,239,0.5),
    inset 0 -20px 40px rgba(45,91,184,0.6),
    inset 0 -3px 0 rgba(0,0,0,0.2);
}
.iv-orb.speaking .iv-orb-core::before { animation-duration: 6s; }
.iv-orb.speaking .iv-orb-halo {
  opacity: 1;
  animation: halo-speak 1.6s ease-in-out infinite;
}
@keyframes halo-speak {
  0%, 100% { opacity: 0.7; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.12); }
}

/* Listening: green aurora */
.iv-orb.listening .iv-orb-core {
  box-shadow:
    0 0 50px 4px rgba(74,222,128,0.35),
    inset 0 -20px 40px rgba(30,168,104,0.6),
    inset 0 -3px 0 rgba(0,0,0,0.2);
}
.iv-orb.listening .iv-orb-core::before {
  background: conic-gradient(from 0deg,
    #4ade80 0%, #6ee7b7 20%, #34d399 40%,
    #22c55e 60%, #16a34a 80%, #4ade80 100%);
  animation-duration: 10s;
}
.iv-orb.listening .iv-orb-halo {
  background: radial-gradient(circle, rgba(74,222,128,0.22) 0%, rgba(110,231,183,0.08) 40%, transparent 70%);
  opacity: 0.8;
  animation: halo-idle 4s ease-in-out infinite;
}

/* ════ SCREEN SHARE VIEW ══════════════════════════════════ */
.iv-screen-share-stage {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  padding: 60px 32px 24px;
}
.iv-screen-share-banner {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 18px; border-radius: 100px;
  background: rgba(91,141,239,0.15);
  border: 1px solid rgba(91,141,239,0.35);
  color: #5b8def; font-family: 'JetBrains Mono', monospace;
  font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase;
}
.iv-share-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #5b8def; animation: rec-blink 1.5s infinite;
}
.iv-screen-share-view {
  flex: 1; max-width: 90%; max-height: 70vh;
  border-radius: 16px; overflow: hidden;
  background: #000; border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 24px 64px -16px rgba(0,0,0,0.6);
}
.iv-screen-share-view video {
  width: 100%; height: 100%; object-fit: contain;
}
.iv-orb-mini {
  position: absolute; top: 100px; right: 32px;
  background: rgba(17,23,38,0.85); padding: 8px;
  border-radius: 50%; backdrop-filter: blur(12px);
  box-shadow: 0 8px 24px -8px rgba(0,0,0,0.5);
}

/* ════ BANNERS & ALERTS ══════════════════════════════════ */
.iv-banner {
  position: fixed; top: 24px; left: 50%; transform: translateX(-50%);
  z-index: 80; padding: 12px 22px; border-radius: 100px;
  font-size: 13px; font-weight: 600; font-family: 'Sora', sans-serif;
  backdrop-filter: blur(20px);
  box-shadow: 0 12px 40px -8px rgba(0,0,0,0.5);
  display: flex; align-items: center; gap: 8px;
}
.iv-banner-error {
  background: rgba(224,117,138,0.18);
  border: 1px solid rgba(224,117,138,0.4);
  color: #e0758a;
}
.iv-banner-warn {
  background: rgba(216,184,120,0.18);
  border: 1px solid rgba(216,184,120,0.4);
  color: #d8b878;
}

/* ════ AUTO-SUBMIT COUNTDOWN ═════════════════════════════ */
.iv-autosubmit {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 8px;
  font-size: 11px; color: #5a667e;
  font-family: 'JetBrains Mono', monospace;
  text-align: center;
}
.iv-autosubmit-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #d8b878;
  animation: pulse-dot 1s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(0.7); }
}

/* ════ PERMISSION OVERLAY ════════════════════════════════ */
.iv-perm-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(5,8,17,0.95); backdrop-filter: blur(12px);
  display: grid; place-items: center; padding: 24px;
}
.iv-perm-card {
  width: 500px; max-width: 92vw; text-align: center;
  background: linear-gradient(180deg, #111726, #0d121d);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 22px;
  padding: 36px 32px;
  box-shadow: 0 30px 80px -20px rgba(0,0,0,0.8);
}
.iv-perm-icon {
  width: 72px; height: 72px; border-radius: 50%;
  background: rgba(216,184,120,0.15);
  border: 2px solid rgba(216,184,120,0.4);
  display: grid; place-items: center;
  font-size: 32px; margin: 0 auto 20px;
}
.iv-perm-card h2 {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 800; font-size: 22px; letter-spacing: -0.02em;
  margin-bottom: 12px;
}
.iv-perm-card p {
  color: #92a0ba; font-size: 14px; line-height: 1.7; margin-bottom: 24px;
}
.iv-perm-card button {
  padding: 13px 32px; border-radius: 12px; border: none;
  background: linear-gradient(135deg, #5b8def, #3f6fd1);
  color: #fff; font-family: 'Sora', sans-serif;
  font-weight: 700; font-size: 14px; cursor: pointer;
  box-shadow: 0 8px 24px -6px rgba(91,141,239,0.6);
}
.iv-perm-card button:hover { transform: translateY(-2px); }

/* ════ MODAL ════════════════════════════════════════════ */
.iv-modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);
  display: grid; place-items: center; padding: 24px;
}
.iv-modal {
  width: 460px; max-width: 90vw;
  background: linear-gradient(180deg, #111726, #0d121d);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 22px;
  padding: 32px 30px;
  text-align: center;
  box-shadow: 0 30px 80px -20px rgba(0,0,0,0.8);
}
.iv-modal-icon {
  width: 64px; height: 64px; border-radius: 50%;
  background: rgba(224,117,138,0.15);
  border: 2px solid rgba(224,117,138,0.4);
  display: grid; place-items: center;
  font-size: 28px; margin: 0 auto 18px;
}
.iv-modal h2 {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 800; font-size: 22px; letter-spacing: -0.02em;
  margin-bottom: 10px;
}
.iv-modal p {
  color: #92a0ba; font-size: 14px; line-height: 1.65; margin-bottom: 24px;
}
.iv-modal-actions {
  display: flex; gap: 10px;
}
.iv-modal-actions button {
  flex: 1; padding: 13px 16px; border-radius: 11px;
  font-family: inherit; font-weight: 600; font-size: 13px;
  cursor: pointer; border: 1px solid;
}
.btn-ghost {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.1);
  color: #92a0ba;
}
.btn-ghost:hover { background: rgba(255,255,255,0.08); color: #eaeef6; }
.btn-danger {
  background: rgba(224,117,138,0.2);
  border-color: rgba(224,117,138,0.5);
  color: #e0758a; font-weight: 700;
}
.btn-danger:hover { background: rgba(224,117,138,0.3); }

/* ════ COMPLETE ════════════════════════════════════════ */
.iv-complete {
  position: absolute; inset: 0; z-index: 2;
  display: grid; place-items: center; padding: 24px;
}
.iv-complete-card {
  width: 580px; max-width: 96vw; text-align: center;
  background: linear-gradient(180deg, rgba(17,23,38,0.95), rgba(13,18,29,0.95));
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 28px;
  padding: 42px 40px 36px;
  backdrop-filter: blur(20px);
}
.iv-complete-icon {
  width: 80px; height: 80px; border-radius: 50%;
  background: linear-gradient(135deg, #4ade80, #22c55e);
  display: grid; place-items: center;
  margin: 0 auto 22px;
  color: #fff; font-size: 38px; font-weight: 800;
  box-shadow: 0 14px 40px -8px rgba(74,222,128,0.5);
}
.iv-complete-card h1 {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 800; font-size: 30px; letter-spacing: -0.02em;
  margin-bottom: 10px;
}
.iv-complete-card p {
  color: #92a0ba; font-size: 14px; line-height: 1.65; margin-bottom: 24px;
}
.iv-complete-card strong { color: #eaeef6; font-weight: 600; }
.iv-complete-stats {
  display: flex; justify-content: center; gap: 40px; margin: 24px 0 28px;
  padding: 18px 0; border-top: 1px solid rgba(255,255,255,0.08);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.iv-stat-val {
  font-family: 'JetBrains Mono', monospace; font-size: 24px;
  font-weight: 700; color: #5b8def;
}
.iv-stat-lbl {
  font-size: 11px; color: #5a667e; margin-top: 4px;
  letter-spacing: 0.06em; text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}
.iv-complete-next {
  text-align: left; background: rgba(91,141,239,0.06);
  border: 1px solid rgba(91,141,239,0.18);
  border-radius: 14px; padding: 18px 20px;
  margin-bottom: 22px;
}
.iv-complete-next h3 {
  font-size: 13px; color: #eaeef6; margin-bottom: 12px;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase; letter-spacing: 0.08em;
}
.iv-complete-next ul { list-style: none; }
.iv-complete-next li {
  font-size: 13px; color: #92a0ba; margin-bottom: 8px; line-height: 1.6;
}
.iv-complete-btn {
  padding: 13px 36px; border-radius: 12px; border: none;
  background: rgba(255,255,255,0.06);
  color: #eaeef6; font-family: inherit;
  font-weight: 600; font-size: 14px; cursor: pointer;
}
.iv-complete-btn:hover { background: rgba(255,255,255,0.1); }
`;