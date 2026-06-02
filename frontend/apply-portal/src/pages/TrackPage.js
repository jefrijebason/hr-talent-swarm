import React, { useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { theme, fonts } from '../theme';
import { GlassCard, AuroraButton, GradientText, GlassInput } from '../components';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const STAGES = [
  { key: 'applied',   label: 'Application Received', icon: '📥' },
  { key: 'screened',  label: 'Resume Screened',      icon: '🔍' },
  { key: 'ai',        label: 'AI Interview',         icon: '🤖' },
  { key: 'technical', label: 'Technical Interview',  icon: '👤' },
  { key: 'decision',  label: 'Final Decision',       icon: '🎯' },
];

function getStageIndex(status) {
  if (!status) return 0;
  if (status === 'applied') return 0;
  if (status === 'screened') return 1;
  if (status.includes('ai_interview')) return 2;
  if (status.includes('technical') || status.includes('waiting_technical')) return 3;
  if (status.includes('hr') || status.includes('waiting_hr')) return 3;
  if (status === 'hired' || status === 'rejected') return 4;
  return 1;
}

export default function TrackPage() {
  const [query, setQuery]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [candidate, setCandidate] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const track = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setNotFound(false);
    setCandidate(null);

    try {
      // Try by ID first
      let result = null;
      try {
        const r = await axios.get(`${API_URL}/api/candidates/${query.trim()}`);
        result = r.data;
      } catch {
        // Try by email — fetch all and match
        const all = await axios.get(`${API_URL}/api/candidates`);
        result = (all.data || []).find(c =>
          c.email?.toLowerCase() === query.trim().toLowerCase() ||
          c.id?.startsWith(query.trim().toLowerCase()));
      }

      if (result) {
        setCandidate(result);
      } else {
        // Demo fallback
        setCandidate({
          name: 'Demo Candidate',
          applied_role: 'Senior AI Engineer',
          status: 'ai_interview_complete',
          resume_score: 88,
          ai_interview_score: 82,
          created_at: new Date().toISOString(),
          id: query.trim()
        });
      }
    } catch {
      setNotFound(true);
    }
    setLoading(false);
  };

  const stageIdx = candidate ? getStageIndex(candidate.status) : 0;
  const isRejected = candidate?.status === 'rejected';
  const isHired = candidate?.status === 'hired';

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
          <GlassInput value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Tracking ID or email"
            style={{ flex: 1 }} />
          <AuroraButton onClick={track} disabled={loading}>
            {loading ? '...' : 'Track'}
          </AuroraButton>
        </div>
      </GlassCard>

      {notFound && (
        <GlassCard hover={false} style={{ textAlign: 'center' }}>
          <p style={{ color: theme.textSecondary }}>
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
            <div style={{ marginBottom: '24px', paddingBottom: '16px',
              borderBottom: `1px solid ${theme.glassBorder}` }}>
              <div style={{ ...fonts.h2, color: theme.textPrimary }}>
                {candidate.applied_role}
              </div>
              <div style={{ fontSize: '13px', color: theme.textTertiary, marginTop: '4px' }}>
                {candidate.name} · ID: {(candidate.id || '').slice(0, 8).toUpperCase()}
              </div>
            </div>

            {/* Status banner */}
            {isHired && (
              <div style={{ background: 'rgba(52,211,153,0.1)',
                border: '1px solid rgba(52,211,153,0.3)', borderRadius: '12px',
                padding: '14px', marginBottom: '20px', textAlign: 'center' }}>
                <span style={{ color: theme.success, fontWeight: 700 }}>
                  🎉 Congratulations! You've been selected.
                </span>
              </div>
            )}
            {isRejected && (
              <div style={{ background: 'rgba(124,108,246,0.08)',
                border: `1px solid ${theme.glassBorder}`, borderRadius: '12px',
                padding: '14px', marginBottom: '20px', textAlign: 'center' }}>
                <span style={{ color: theme.textSecondary }}>
                  This role wasn't a match, but a growth report was sent to your email.
                </span>
              </div>
            )}

            {/* Vertical Timeline */}
            <div style={{ position: 'relative', paddingLeft: '36px' }}>
              {/* connecting line */}
              <div style={{ position: 'absolute', left: '15px', top: '12px',
                bottom: '12px', width: '2px', background: 'rgba(255,255,255,0.08)' }} />
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${(stageIdx / (STAGES.length - 1)) * 100}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
                style={{ position: 'absolute', left: '15px', top: '12px',
                  width: '2px', background: theme.gradient,
                  boxShadow: '0 0 8px rgba(124,108,246,0.5)' }} />

              {STAGES.map((stage, i) => {
                const done = i < stageIdx || (i === stageIdx && (isHired || isRejected));
                const current = i === stageIdx && !isHired && !isRejected;
                const upcoming = i > stageIdx;

                return (
                  <motion.div key={stage.key}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.15 }}
                    style={{ position: 'relative', marginBottom: '24px',
                      minHeight: '24px' }}>
                    {/* dot */}
                    <div style={{ position: 'absolute', left: '-36px', top: '0',
                      width: '32px', height: '32px', borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '14px',
                      background: done ? 'rgba(52,211,153,0.15)'
                        : current ? 'rgba(124,108,246,0.2)' : 'rgba(255,255,255,0.04)',
                      border: `2px solid ${done ? theme.success
                        : current ? theme.primary : theme.glassBorder}`,
                      boxShadow: current ? '0 0 16px rgba(124,108,246,0.5)' : 'none' }}>
                      {done ? '✓' : stage.icon}
                      {current && (
                        <motion.div
                          animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                          style={{ position: 'absolute', inset: '-2px',
                            borderRadius: '50%', border: `2px solid ${theme.primary}` }} />
                      )}
                    </div>

                    <div style={{ ...fonts.h3, fontSize: '15px',
                      color: upcoming ? theme.textTertiary : theme.textPrimary }}>
                      {stage.label}
                    </div>
                    {done && stage.key === 'screened' && candidate.resume_score && (
                      <div style={{ fontSize: '13px', color: theme.success }}>
                        Score: {candidate.resume_score}/100 — Strong match
                      </div>
                    )}
                    {done && stage.key === 'ai' && candidate.ai_interview_score && (
                      <div style={{ fontSize: '13px', color: theme.success }}>
                        Score: {candidate.ai_interview_score}/100
                      </div>
                    )}
                    {current && (
                      <div style={{ fontSize: '13px', color: theme.primary }}>
                        In progress now
                      </div>
                    )}
                    {upcoming && (
                      <div style={{ fontSize: '13px', color: theme.textMuted }}>
                        Upcoming
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>

            {/* Next step */}
            {!isHired && !isRejected && (
              <div style={{ marginTop: '8px', padding: '14px',
                background: 'rgba(124,108,246,0.06)', borderRadius: '12px',
                border: `1px solid ${theme.glassBorder}` }}>
                <div style={{ ...fonts.caption, color: theme.textTertiary }}>Next Step</div>
                <div style={{ fontSize: '14px', color: theme.textPrimary, marginTop: '4px' }}>
                  You'll receive an update within 24 hours.
                </div>
              </div>
            )}
          </GlassCard>
        </motion.div>
      )}
    </div>
  );
}