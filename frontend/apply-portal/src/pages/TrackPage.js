import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { theme, fonts } from '../theme';
import { GlassCard, AuroraButton, GradientText, GlassInput } from '../components';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// ── Build dynamic stages from job config + candidate status ──────
function buildStages(candidate, job) {
  const status = candidate?.status || 'applied';
  const mode   = job?.interview_mode || 'standard';
  const stages = [];

  // Treat either flag as Vibe Engineering enabled (Option B unified flow)
  const vibeEnabled = job?.coding_assessment_enabled || job?.coding_round_enabled
    || ['vibe_engineering_sent','vibe_engineering_in_progress','vibe_engineering_passed','vibe_engineering_complete'].includes(status);

  // Stage 1 — Always: Applied
  stages.push({
    key: 'applied', label: 'Application Received', icon: '📥',
    statuses: ['applied']
  });

  // Stage 2 — Always: Screened
  stages.push({
    key: 'screened', label: 'Resume Screened', icon: '🔍',
    statuses: ['screened']
  });

  // Stage 3 (NEW position) — Vibe Engineering Challenge, BEFORE AI Interview
  if (vibeEnabled) {
    stages.push({
      key: 'vibe', label: 'Vibe Engineering Challenge', icon: '🛠️',
      statuses: ['vibe_engineering_sent', 'vibe_engineering_in_progress',
                 'vibe_engineering_passed', 'vibe_engineering_complete']
    });
  }

  // Mode-specific stages
  if (mode === 'executive') {
    const humanRounds = job?.human_rounds || [];
    humanRounds.forEach((r, i) => {
      stages.push({
        key: `human_round_${i + 1}`,
        label: r.round_name || `Round ${i + 1}`,
        icon: '👤',
        statuses: [`waiting_round_${i + 1}`, `round_${i + 1}_complete`]
      });
    });
    if (humanRounds.length === 0) {
      stages.push({
        key: 'human_interview', label: 'Interview', icon: '👤',
        statuses: ['waiting_technical_interview', 'waiting_hr_interview']
      });
    }
  } else if (mode === 'express') {
    if (job?.ai_interview_enabled !== false) {
      stages.push({
        key: 'ai_interview', label: 'AI Interview', icon: '🤖',
        statuses: ['ai_interview_sent', 'ai_interview_accepted',
                   'ai_interview_in_progress', 'ai_interview_complete']
      });
    }
    stages.push({
      key: 'combined_interview', label: 'Combined Interview', icon: '👤',
      statuses: ['waiting_technical_interview', 'waiting_hr_interview']
    });
  } else if (mode === 'custom') {
    if (job?.ai_interview_enabled !== false) {
      stages.push({
        key: 'ai_interview', label: 'AI Interview', icon: '🤖',
        statuses: ['ai_interview_sent', 'ai_interview_accepted',
                   'ai_interview_in_progress', 'ai_interview_complete']
      });
    }
    const humanRounds = job?.human_rounds || [];
    humanRounds.forEach((r, i) => {
      stages.push({
        key: `human_round_${i + 1}`,
        label: r.round_name || `Round ${i + 1}`,
        icon: '👤',
        statuses: [
          i === 0 ? 'waiting_technical_interview' : `waiting_round_${i + 1}`,
          i === 0 ? 'technical_complete' : `round_${i + 1}_complete`
        ]
      });
    });
    if (humanRounds.length === 0) {
      stages.push({
        key: 'technical', label: 'Technical Interview', icon: '👤',
        statuses: ['waiting_technical_interview']
      });
      stages.push({
        key: 'hr', label: 'HR Interview', icon: '👤',
        statuses: ['waiting_hr_interview']
      });
    }
  } else {
    // Standard: AI Interview → Technical → HR
    if (job?.ai_interview_enabled !== false) {
      stages.push({
        key: 'ai_interview', label: 'AI Interview', icon: '🤖',
        statuses: ['ai_interview_sent', 'ai_interview_accepted',
                   'ai_interview_in_progress', 'ai_interview_complete']
      });
    }
    stages.push({
      key: 'technical', label: 'Technical Interview', icon: '👤',
      statuses: ['waiting_technical_interview']
    });
    stages.push({
      key: 'hr', label: 'HR Interview', icon: '👤',
      statuses: ['waiting_hr_interview']
    });
  }

  // Final stage — Always: Decision
  stages.push({
    key: 'decision', label: 'Final Decision', icon: '🎯',
    statuses: ['evaluating', 'hired', 'rejected']
  });

  return stages;
}

// ── Find which stage the candidate is at ─────────────────────────
function getCurrentStageIndex(stages, status) {
  if (!status) return 0;
  if (status === 'hired') return stages.length - 1;
  for (let i = stages.length - 1; i >= 0; i--) {
    if (stages[i].statuses.includes(status)) return i;
  }
  for (let i = stages.length - 1; i >= 0; i--) {
    if (stages[i].statuses.some(s =>
      status.includes(s) || s.includes(status))) return i;
  }
  return 0;
}

function getRejectedStageIndex(stages, candidate, job) {
  if (!candidate || candidate.status !== 'rejected') return stages.length - 1;
  if (candidate.final_score !== undefined) return stages.length - 1;

  if (candidate.ai_interview_score !== undefined) {
    const idx = stages.findIndex(s => s.key === 'ai_interview');
    return idx >= 0 ? idx : 1;
  }
  if (candidate.vibe_engineering_score !== undefined) {
    const idx = stages.findIndex(s => s.key === 'vibe');
    return idx >= 0 ? idx : 1;
  }
  if (candidate.resume_score !== undefined) {
    const idx = stages.findIndex(s => s.key === 'screened');
    return idx >= 0 ? idx : 1;
  }
  return 0;
}

// ── Status message per stage ─────────────────────────────────────
function getStatusMessage(status) {
  const messages = {
    'applied':                       'Your application is being processed',
    'screened':                      'Resume reviewed — preparing next step',
    'vibe_engineering_sent':         'Coding challenge link sent to your email — complete within 3 days',
    'vibe_engineering_in_progress':  'Coding challenge in progress',
    'vibe_engineering_passed':       'Coding challenge passed — preparing AI interview',
    'vibe_engineering_complete':     'Coding challenge complete — being evaluated',
    'ai_interview_sent':             'AI interview link sent to your email — complete within 3 days',
    'ai_interview_accepted':         'Interview link ready — take it at your convenience',
    'ai_interview_in_progress':      'AI interview in progress',
    'ai_interview_complete':         'AI interview complete — being evaluated',
    'waiting_technical_interview':   'Technical interview scheduled',
    'waiting_hr_interview':          'Technical passed — HR round next',
    'evaluating':                    'Final evaluation in progress',
    'hired':                         'Congratulations! Offer sent to your email',
    'rejected':                      'This role wasn\'t a match this time',
  };
  return messages[status] || 'Processing...';
}

function getRejectionStage(status, stages, stageIdx) {
  if (status !== 'rejected') return null;
  if (stageIdx > 0 && stageIdx < stages.length - 1) {
    return stages[stageIdx - 1]?.label || 'Evaluation';
  }
  return 'Screening';
}

export default function TrackPage({ initialQuery = '' }) {
  const [query, setQuery]           = useState(initialQuery);
  const [loading, setLoading]       = useState(false);
  const [candidate, setCandidate]   = useState(null);
  const [job, setJob]               = useState(null);
  const [notFound, setNotFound]     = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const refreshRef    = useRef(null);
  const hasAutoSearched = useRef(false);

  useEffect(() => {
    if (initialQuery && !hasAutoSearched.current) {
      hasAutoSearched.current = true;
      setQuery(initialQuery);
      doTrack(initialQuery);
    }
  }, [initialQuery]);

  useEffect(() => {
    if (candidate && candidate.id) {
      refreshRef.current = setInterval(() => {
        doTrack(candidate.id, true);
      }, 8000);
    }
    return () => {
      if (refreshRef.current) clearInterval(refreshRef.current);
    };
  }, [candidate?.id]);

  const doTrack = async (searchQuery, silent = false) => {
    const q = (searchQuery || query).trim();
    if (!q) return;
    if (!silent) setLoading(true);
    setNotFound(false);

    try {
      let result = null;

      try {
        const r = await axios.get(`${API_URL}/api/candidates/${q}`);
        result = r.data;
      } catch {
        try {
          const all = await axios.get(`${API_URL}/api/candidates`);
          result = (all.data || []).find(c =>
            c.email?.toLowerCase() === q.toLowerCase() ||
            c.id?.startsWith(q.toLowerCase()) ||
            c.id === q);
        } catch {}
      }

      if (result) {
        setCandidate(result);
        setLastUpdate(new Date().toLocaleTimeString());

        if (result.job_id) {
          try {
            const jr = await axios.get(`${API_URL}/api/jobs/${result.job_id}`);
            setJob(jr.data);
          } catch {
            setJob(null);
          }
        }
      } else if (!silent) {
        setNotFound(true);
        setCandidate(null);
      }
    } catch {
      if (!silent) setNotFound(true);
    }
    if (!silent) setLoading(false);
  };

  const handleTrack = () => doTrack(query);
  const handleKeyDown = (e) => { if (e.key === 'Enter') handleTrack(); };

  const stages       = candidate ? buildStages(candidate, job) : [];
  const stageIdx     = candidate ? getCurrentStageIndex(stages, candidate.status) : 0;
  const isRejected   = candidate?.status === 'rejected';
  const isHired      = candidate?.status === 'hired';
  const isComplete   = isRejected || isHired;
  const rejectedIdx  = isRejected ? getRejectedStageIndex(stages, candidate, job) : stageIdx;

  const visibleStages = stages.filter((_, i) => {
    if (isRejected) return i <= rejectedIdx;
    if (isComplete) return i <= stageIdx;
    return i <= stageIdx + 1;
  });

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '50px 24px 100px' }}>

      <motion.div
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ ...fonts.h1, margin: '0 0 10px' }}>
          <GradientText>Track Your Application</GradientText>
        </h1>
        <p style={{ ...fonts.body, color: theme.textSecondary, margin: 0 }}>
          Enter your tracking ID or email to see live status.
        </p>
      </motion.div>

      <GlassCard hover={false} style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ flex: 1 }} onKeyDown={handleKeyDown}>
            <GlassInput value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Tracking ID or email" />
          </div>
          <AuroraButton onClick={handleTrack} disabled={loading}>
            {loading ? '...' : 'Track'}
          </AuroraButton>
        </div>
      </GlassCard>

      {notFound && (
        <GlassCard hover={false} style={{ textAlign: 'center' }}>
          <p style={{ color: theme.textSecondary, margin: 0 }}>
            No application found. Check your tracking ID or email.
          </p>
        </GlassCard>
      )}

      {candidate && (
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}>
          <GlassCard hover={false} glow>

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between',
              alignItems: 'flex-start', marginBottom: '20px', paddingBottom: '16px',
              borderBottom: `1px solid ${theme.glassBorder}` }}>
              <div>
                <div style={{ ...fonts.h2, color: theme.textPrimary }}>
                  {candidate.applied_role}
                </div>
                <div style={{ fontSize: '13px', color: theme.textTertiary, marginTop: '4px' }}>
                  {candidate.name} · ID: {(candidate.id || '').slice(0, 8).toUpperCase()}
                </div>
                {job && (
                  <div style={{ fontSize: '12px', color: theme.textMuted, marginTop: '4px' }}>
                    Pipeline: {(job.interview_mode || 'standard').charAt(0).toUpperCase() +
                      (job.interview_mode || 'standard').slice(1)}
                  </div>
                )}
              </div>
              {!isComplete && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <motion.div
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    style={{ width: '8px', height: '8px', borderRadius: '50%',
                      background: theme.cyan }} />
                  <span style={{ fontSize: '11px', color: theme.textTertiary }}>Live</span>
                </div>
              )}
            </div>

            {/* Scores */}
            {(candidate.resume_score || candidate.vibe_engineering_score || candidate.ai_interview_score) && (
              <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                {candidate.resume_score && (
                  <ScoreCard label="Resume" value={candidate.resume_score} />
                )}
                {candidate.vibe_engineering_score && (
                  <ScoreCard label="Vibe Eng." value={candidate.vibe_engineering_score} />
                )}
                {candidate.ai_interview_score && (
                  <ScoreCard label="AI Interview" value={candidate.ai_interview_score} />
                )}
                {candidate.final_score && (
                  <ScoreCard label="Final" value={candidate.final_score} />
                )}
              </div>
            )}

            {/* Hired banner */}
            {isHired && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                style={{ background: 'rgba(52,211,153,0.1)',
                  border: '1px solid rgba(52,211,153,0.3)', borderRadius: '12px',
                  padding: '16px', marginBottom: '20px', textAlign: 'center' }}>
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>🎉</div>
                <span style={{ color: theme.success, fontWeight: 700, fontSize: '15px' }}>
                  Congratulations! You've been selected.
                </span>
                <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '6px' }}>
                  Check your email for the offer letter.
                </div>
              </motion.div>
            )}

            {/* Rejected banner */}
            {isRejected && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                style={{ background: 'rgba(255,255,255,0.03)',
                  border: `1px solid ${theme.glassBorder}`, borderRadius: '12px',
                  padding: '16px', marginBottom: '20px', textAlign: 'center' }}>
                <span style={{ color: theme.textSecondary, fontSize: '14px' }}>
                  This role wasn't the right fit this time.
                  A personalized growth report has been sent to your email
                  to help you improve.
                </span>
              </motion.div>
            )}

            {/* Dynamic Timeline */}
            <div style={{ position: 'relative', paddingLeft: '36px' }}>
              {visibleStages.length > 1 && (
                <div style={{ position: 'absolute', left: '15px', top: '12px',
                  bottom: '12px', width: '2px', background: 'rgba(255,255,255,0.06)' }} />
              )}

              {visibleStages.length > 1 && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{
                    height: `${(Math.min(isRejected ? rejectedIdx : stageIdx, visibleStages.length - 1) /
                      Math.max(visibleStages.length - 1, 1)) * 100}%`
                  }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  style={{ position: 'absolute', left: '15px', top: '12px',
                    width: '2px',
                    background: isRejected
                      ? 'linear-gradient(180deg, #34d399, #fb7185)'
                      : theme.gradient,
                    boxShadow: `0 0 8px ${isRejected ? 'rgba(251,113,133,0.4)' : 'rgba(124,108,246,0.5)'}` }} />
              )}

              {visibleStages.map((stage, i) => {
                const realIdx = stages.indexOf(stage);
                const done    = realIdx < (isRejected ? rejectedIdx : stageIdx);
                const current = realIdx === (isRejected ? rejectedIdx : stageIdx);
                const next    = realIdx > (isRejected ? rejectedIdx : stageIdx);
                const isRejectedHere = isRejected && current;

                return (
                  <motion.div key={stage.key}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.12 }}
                    style={{ position: 'relative', marginBottom: '24px',
                      minHeight: '24px' }}>

                    {/* Dot */}
                    <div style={{ position: 'absolute', left: '-36px', top: '0',
                      width: '32px', height: '32px', borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '14px',
                      background: done ? 'rgba(52,211,153,0.15)'
                        : isRejectedHere ? 'rgba(251,113,133,0.15)'
                        : current ? 'rgba(124,108,246,0.2)'
                        : 'rgba(255,255,255,0.04)',
                      border: `2px solid ${done ? theme.success
                        : isRejectedHere ? theme.danger
                        : current ? theme.primary
                        : theme.glassBorder}`,
                      boxShadow: current && !isRejectedHere
                        ? '0 0 16px rgba(124,108,246,0.5)' : 'none' }}>
                      {done ? '✓' : isRejectedHere ? '✗' : stage.icon}

                      {current && !isComplete && (
                        <motion.div
                          animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                          style={{ position: 'absolute', inset: '-2px',
                            borderRadius: '50%',
                            border: `2px solid ${theme.primary}` }} />
                      )}
                    </div>

                    {/* Label */}
                    <div style={{ ...fonts.h3, fontSize: '15px',
                      color: next ? theme.textTertiary
                        : isRejectedHere ? theme.danger
                        : theme.textPrimary }}>
                      {isRejectedHere ? `Rejected at ${stage.label}` : stage.label}
                    </div>

                    {/* Sub-text */}
                    {done && stage.key === 'screened' && candidate.resume_score && (
                      <div style={{ fontSize: '13px', color: theme.success }}>
                        Score: {candidate.resume_score}/100
                      </div>
                    )}
                    {done && stage.key === 'vibe' && candidate.vibe_engineering_score && (
                      <div style={{ fontSize: '13px', color: theme.success }}>
                        Score: {candidate.vibe_engineering_score}/100
                      </div>
                    )}
                    {done && stage.key === 'ai_interview' && candidate.ai_interview_score && (
                      <div style={{ fontSize: '13px', color: theme.success }}>
                        Score: {candidate.ai_interview_score}/100
                      </div>
                    )}
                    {current && !isComplete && (
                      <div style={{ fontSize: '13px', color: theme.primary }}>
                        {getStatusMessage(candidate.status)}
                      </div>
                    )}
                    {isRejectedHere && (
                      <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '4px' }}>
                        A growth report was sent to your email
                      </div>
                    )}
                    {isHired && current && (
                      <div style={{ fontSize: '13px', color: theme.success }}>
                        Offer sent — check your email
                      </div>
                    )}
                    {next && (
                      <div style={{ fontSize: '13px', color: theme.textMuted }}>
                        Coming up next
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>

            {/* Current status box */}
            {!isComplete && (
              <div style={{ marginTop: '8px', padding: '14px',
                background: 'rgba(124,108,246,0.06)', borderRadius: '12px',
                border: `1px solid ${theme.glassBorder}` }}>
                <div style={{ fontSize: '11px', color: theme.textTertiary,
                  textTransform: 'uppercase', letterSpacing: '0.5px',
                  marginBottom: '4px' }}>
                  Current Status
                </div>
                <div style={{ fontSize: '14px', color: theme.textPrimary }}>
                  {getStatusMessage(candidate.status)}
                </div>
              </div>
            )}

            {lastUpdate && (
              <div style={{ marginTop: '12px', fontSize: '11px',
                color: theme.textMuted, textAlign: 'center' }}>
                Auto-refreshing · Last updated: {lastUpdate}
              </div>
            )}

          </GlassCard>
        </motion.div>
      )}
    </div>
  );
}

function ScoreCard({ label, value }) {
  return (
    <div style={{ flex: 1, background: 'rgba(255,255,255,0.03)',
      border: `1px solid ${theme.glassBorder}`, borderRadius: '12px',
      padding: '12px', textAlign: 'center' }}>
      <div style={{ fontSize: '22px', fontWeight: 800,
        color: theme.textPrimary }}>
        {value}
      </div>
      <div style={{ fontSize: '11px', color: theme.textTertiary }}>
        {label}
      </div>
    </div>
  );
}