/**
 * PipelineView.jsx — Talent Pipeline + Candidate Journey Timeline
 *
 * DROP-IN: In App.js replace `import` line with:
 *   import PipelineView from './PipelineView';
 * Remove the inline PipelineView function from App.js entirely.
 *
 * Uses the same DESIGN_CSS variables already injected by App.js.
 * API calls: GET /api/candidates, POST /api/human-gate
 */

import React, { useState, useMemo, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/* ─── status column definitions ─────────────────────────────────── */
const COLS = [
  { key: 'applied',                     label: 'Applied',       color: '#6db4f0', icon: '📥' },
  { key: 'screened',                    label: 'Screened',      color: '#5b8def', icon: '🔍' },
  { key: 'ai_interview_complete',       label: 'AI Interview',  color: '#8f9bff', icon: '🤖' },
  { key: 'waiting_technical_interview', label: 'Awaiting Tech', color: '#d8b878', icon: '⏳' },
  { key: 'waiting_hr_interview',        label: 'Awaiting HR',   color: '#6db4f0', icon: '🎤' },
  { key: 'hired',                       label: 'Hired',         color: '#4ade80', icon: '✅' },
  { key: 'rejected',                    label: 'Rejected',      color: '#e0758a', icon: '✕'  },
];

/* ─── status → human-readable journey label ─────────────────────── */
const JOURNEY = {
  applied:                     { label: 'Application received',          icon: '📥', color: '#6db4f0' },
  screened:                    { label: 'Resume screened by AI',         icon: '🔍', color: '#5b8def' },
  ai_interview_complete:       { label: 'AI interview completed',        icon: '🤖', color: '#8f9bff' },
  waiting_technical_interview: { label: 'Shortlisted — awaiting tech review', icon: '⏳', color: '#d8b878' },
  waiting_hr_interview:        { label: 'Technical round cleared',       icon: '🎤', color: '#6db4f0' },
  hired:                       { label: 'Offer extended — hired! 🎉',    icon: '✅', color: '#4ade80' },
  rejected:                    { label: 'Not selected this time',        icon: '✕',  color: '#e0758a' },
};

const STATUS_ORDER = [
  'applied','screened','ai_interview_complete',
  'waiting_technical_interview','waiting_hr_interview','hired','rejected',
];

/* ════════════════════════════════════════════════════════════════════
   SCORE RING — SVG percentage circle
════════════════════════════════════════════════════════════════════ */
function ScoreRing({ score, max = 100, label, color = 'var(--jd)', size = 84 }) {
  if (!score) return null;
  const pct   = Math.min((score / max) * 100, 100);
  const r     = (size - 10) / 2;
  const circ  = 2 * Math.PI * r;
  const dash  = (pct / 100) * circ;

  return (
    <div style={{ textAlign: 'center', flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r}
          fill="none" stroke="var(--pan2)" strokeWidth={6} />
        <circle cx={size/2} cy={size/2} r={r}
          fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray .8s cubic-bezier(.4,0,.2,1)' }} />
        <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
          style={{ transform: 'rotate(90deg)', transformOrigin: `${size/2}px ${size/2}px`,
            fill: color, fontFamily: 'JetBrains Mono', fontWeight: 700, fontSize: 18 }}>
          {score}
        </text>
      </svg>
      <div style={{ fontSize: 11, color: 'var(--tx2)', marginTop: 4 }}>{label}</div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   JOURNEY TIMELINE  — builds synthetic steps from candidate data
════════════════════════════════════════════════════════════════════ */
function JourneyTimeline({ candidate }) {
  const currentIdx = STATUS_ORDER.indexOf(candidate.status);
  const isRejected = candidate.status === 'rejected';

  /* Build steps: every status up to current (or up to rejected) */
  const steps = useMemo(() => {
    const reachable = isRejected
      ? [...STATUS_ORDER.slice(0, currentIdx), 'rejected']
      : STATUS_ORDER.slice(0, currentIdx + 1);

    return reachable.map((key, i) => {
      const j    = JOURNEY[key] || { label: key, icon: '●', color: 'var(--tx3)' };
      const done = i < reachable.length - 1;
      const cur  = i === reachable.length - 1;

      /* attach real scores to relevant steps */
      let detail = null;
      if (key === 'screened' && candidate.resume_score)
        detail = `Resume score: ${candidate.resume_score}/100`;
      if (key === 'ai_interview_complete' && candidate.ai_interview_score)
        detail = `AI interview score: ${candidate.ai_interview_score}/100`;
      if (key === 'waiting_technical_interview' && candidate.final_score)
        detail = `Final score: ${candidate.final_score}/100`;
      if (key === 'hired' && candidate.agreed_salary)
        detail = `Salary agreed: ${candidate.agreed_salary}`;

      /* use real timeline timestamps if the API provided them */
      const ts = candidate.timeline?.find(t => t.status === key)?.time;

      return { key, j, done, cur, detail, ts };
    });
  }, [candidate, currentIdx, isRejected]);

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--tx)',
        letterSpacing: '0.1em', textTransform: 'uppercase',
        fontFamily: 'JetBrains Mono', marginBottom: 16 }}>
        Candidate Journey
      </div>

      {steps.map((step, i) => (
        <div key={step.key} style={{ display: 'flex', gap: 14, position: 'relative' }}>
          {/* connector line */}
          {i < steps.length - 1 && (
            <div style={{
              position: 'absolute', left: 17, top: 36, bottom: 0,
              width: 2,
              background: step.done
                ? `linear-gradient(180deg, ${step.j.color}66, var(--ln2))`
                : 'var(--ln)',
            }} />
          )}

          {/* icon */}
          <div style={{
            width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
            display: 'grid', placeItems: 'center', fontSize: 14,
            background: step.cur
              ? `linear-gradient(135deg, ${step.j.color}33, ${step.j.color}11)`
              : step.done ? 'var(--pan2)' : 'transparent',
            border: `2px solid ${step.cur ? step.j.color : step.done ? 'var(--ln2)' : 'var(--ln)'}`,
            color: step.cur || step.done ? step.j.color : 'var(--tx3)',
            position: 'relative', zIndex: 1,
          }}>
            {step.j.icon}
          </div>

          {/* text */}
          <div style={{ paddingBottom: i < steps.length - 1 ? 20 : 0 }}>
            <div style={{
              fontSize: 14, fontWeight: step.cur ? 600 : 400,
              color: step.cur ? 'var(--tx)' : step.done ? 'var(--tx2)' : 'var(--tx3)',
            }}>
              {step.j.label}
            </div>
            {step.detail && (
              <div style={{ fontSize: 12, color: step.j.color,
                fontFamily: 'JetBrains Mono', marginTop: 2 }}>
                {step.detail}
              </div>
            )}
            {step.ts && (
              <div style={{ fontSize: 11, color: 'var(--tx3)',
                fontFamily: 'JetBrains Mono', marginTop: 2 }}>
                {new Date(step.ts).toLocaleDateString('en-IN',
                  { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   AI INTERVIEW SUMMARY  — ARIA briefing (5-dimension + anti-cheat + transcript)
   Reads from candidate.interview_briefing (new ARIA structure)
   Falls back to legacy candidate.ai_summary / interview_answers fields.
════════════════════════════════════════════════════════════════════ */

/* Dimension metadata for display */
const DIMENSIONS_META = [
  { key: 'first_principles', label: 'First Principles',  desc: 'Questioning assumptions',  icon: '◆' },
  { key: 'ai_fluency',       label: 'AI Fluency',         desc: 'Using AI as force multiplier', icon: '⚡' },
  { key: 'decomposition',    label: 'Decomposition',      desc: 'Breaking down problems',   icon: '◫' },
  { key: 'taste',            label: 'Taste',              desc: 'Picking good vs great',    icon: '✦' },
  { key: 'verification',     label: 'Verification',       desc: 'Catching AI mistakes',     icon: '✓' },
];

/* Verdict styling */
const VERDICT_STYLES = {
  STRONG_PASS: { bg: 'rgba(74,222,128,.12)',  border: 'rgba(74,222,128,.4)',  color: '#4ade80', label: 'STRONG PASS' },
  PASS:        { bg: 'rgba(91,141,239,.12)',  border: 'rgba(91,141,239,.4)',  color: '#5b8def', label: 'PASS'        },
  MARGINAL:    { bg: 'rgba(216,184,120,.12)', border: 'rgba(216,184,120,.4)', color: '#d8b878', label: 'MARGINAL'    },
  FAIL:        { bg: 'rgba(224,117,138,.12)', border: 'rgba(224,117,138,.4)', color: '#e0758a', label: 'FAIL'        },
};

/* Anti-cheat severity styling */
const SEVERITY_STYLES = {
  none:   { bg: 'rgba(74,222,128,.1)',  color: '#4ade80', label: 'Clean'  },
  low:    { bg: 'rgba(109,180,240,.1)', color: '#6db4f0', label: 'Low'    },
  medium: { bg: 'rgba(216,184,120,.1)', color: '#d8b878', label: 'Medium' },
  high:   { bg: 'rgba(224,117,138,.1)', color: '#e0758a', label: 'High'   },
};

function AIInterviewSummary({ candidate }) {
  const [showTranscript, setShowTranscript] = useState(false);

  // ── 1. NEW briefing (preferred) ──
  const briefing = candidate.interview_briefing;

  // ── 2. LEGACY fallback ──
  const legacySummary   = candidate.ai_summary || candidate.interview_summary;
  const legacyAnswers   = candidate.interview_answers || candidate.key_answers || [];
  const legacyStrengths = candidate.strengths || [];
  const legacyConcerns  = candidate.concerns  || [];

  // If NEITHER source has data, render nothing
  const hasNewBriefing = briefing && (briefing.composite_score !== undefined || briefing.summary);
  const hasLegacyData  = legacySummary || legacyAnswers.length > 0 || legacyStrengths.length > 0;
  if (!hasNewBriefing && !hasLegacyData) return null;

  // If only LEGACY data is available, render the simpler legacy view
  if (!hasNewBriefing && hasLegacyData) {
    return <LegacyAISummary
      summary={legacySummary} answers={legacyAnswers}
      strengths={legacyStrengths} concerns={legacyConcerns} />;
  }

  // ── 3. NEW briefing view ──
  const verdict     = briefing.verdict || (briefing.passed ? 'PASS' : 'FAIL');
  const vStyle      = VERDICT_STYLES[verdict] || VERDICT_STYLES.PASS;
  const compScore   = briefing.composite_score || 0;
  const passThresh  = briefing.pass_threshold || 70;
  const dimensions  = briefing.dimension_scores || {};
  const weights     = briefing.weights || {};
  const antiCheat   = briefing.anti_cheat || {};
  const severity    = antiCheat.severity || 'none';
  const sStyle      = SEVERITY_STYLES[severity] || SEVERITY_STYLES.none;
  const flags       = antiCheat.flags || [];
  const flagCount   = antiCheat.flag_count || 0;
  const strengths   = briefing.strengths   || [];
  const concerns    = briefing.concerns    || [];
  const redFlags    = briefing.red_flags   || [];
  const focusOn     = briefing.focus_on    || [];
  const alreadyTested  = briefing.do_not_test_again   || [];
  const suggestedQs    = briefing.suggested_questions || [];
  const resumeValid    = briefing.resume_validation   || [];
  const transcript     = briefing.transcript || [];

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--tx)',
          letterSpacing: '0.1em', textTransform: 'uppercase',
          fontFamily: 'JetBrains Mono' }}>
          ARIA Interview Report
        </div>
        <div style={{ fontSize: 10, color: 'var(--tx3)',
          fontFamily: 'JetBrains Mono', letterSpacing: '0.06em' }}>
          {briefing.questions_asked || 0} questions ·
          {' '}{Math.round(briefing.duration_minutes || 0)} min
        </div>
      </div>

      {/* ── Verdict + Composite Score ── */}
      <div style={{
        background: vStyle.bg, border: `1px solid ${vStyle.border}`,
        borderRadius: 14, padding: 18, marginBottom: 14,
        display: 'flex', alignItems: 'center', gap: 18,
      }}>
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: `conic-gradient(${vStyle.color} ${compScore * 3.6}deg, var(--pan2) 0)`,
            display: 'grid', placeItems: 'center',
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: '50%',
              background: 'var(--pan)', display: 'grid', placeItems: 'center',
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: vStyle.color,
                  fontFamily: 'JetBrains Mono', lineHeight: 1 }}>
                  {compScore}
                </div>
                <div style={{ fontSize: 8, color: 'var(--tx3)',
                  fontFamily: 'JetBrains Mono', marginTop: 2 }}>
                  /100
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              fontFamily: 'JetBrains Mono', fontSize: 10, fontWeight: 700,
              letterSpacing: '0.1em', padding: '4px 10px', borderRadius: 6,
              background: vStyle.color + '22', color: vStyle.color,
              border: `1px solid ${vStyle.border}`,
            }}>
              {vStyle.label}
            </span>
            <span style={{ fontSize: 11, color: 'var(--tx3)',
              fontFamily: 'JetBrains Mono' }}>
              threshold: {passThresh}
            </span>
            {briefing.talent_reserve_eligible && (
              <span style={{
                fontFamily: 'JetBrains Mono', fontSize: 9, fontWeight: 700,
                letterSpacing: '0.08em', padding: '3px 8px', borderRadius: 5,
                background: 'rgba(216,184,120,.15)', color: '#d8b878',
                border: '1px solid rgba(216,184,120,.3)',
              }}>
                ⭐ RESERVE
              </span>
            )}
          </div>
          {briefing.verdict_reasoning && (
            <div style={{ fontSize: 12, color: 'var(--tx2)', lineHeight: 1.5 }}>
              {briefing.verdict_reasoning}
            </div>
          )}
        </div>
      </div>

      {/* ── 5-Dimension Scores ── */}
      {Object.keys(dimensions).length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--tx3)',
            letterSpacing: '0.1em', textTransform: 'uppercase',
            fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
            Dimension Scores
          </div>
          <div style={{ background: 'var(--pan2)', border: '1px solid var(--ln)',
            borderRadius: 10, padding: 12 }}>
            {DIMENSIONS_META.map(d => {
              const score  = dimensions[d.key];
              const weight = weights[d.key];
              if (score === undefined) return null;
              const barColor = score >= 80 ? '#4ade80'
                            : score >= 65 ? '#5b8def'
                            : score >= 50 ? '#d8b878' : '#e0758a';
              return (
                <div key={d.key} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ color: barColor, fontSize: 13 }}>{d.icon}</span>
                      <span style={{ fontSize: 12, color: 'var(--tx)', fontWeight: 500 }}>
                        {d.label}
                      </span>
                      {weight !== undefined && (
                        <span style={{ fontSize: 9, color: 'var(--tx3)',
                          fontFamily: 'JetBrains Mono' }}>
                          ×{Math.round(weight * 100)}%
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: 12, color: barColor, fontWeight: 700,
                      fontFamily: 'JetBrains Mono' }}>
                      {score}
                    </span>
                  </div>
                  <div style={{ height: 4, background: 'var(--pan)',
                    borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: `${score}%`, height: '100%',
                      background: barColor, transition: 'width .4s' }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Anti-cheat status ── */}
      <div style={{
        background: sStyle.bg, border: `1px solid ${sStyle.color}40`,
        borderRadius: 10, padding: '10px 14px', marginBottom: 14,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 14 }}>
            {severity === 'none' ? '🛡' : severity === 'high' ? '⚠' : '◑'}
          </span>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: sStyle.color,
              fontFamily: 'JetBrains Mono', textTransform: 'uppercase',
              letterSpacing: '0.08em' }}>
              Integrity Check: {sStyle.label}
            </div>
            <div style={{ fontSize: 11, color: 'var(--tx3)', marginTop: 2 }}>
              {flagCount === 0
                ? 'No anti-cheat flags raised during interview'
                : `${flagCount} flag${flagCount > 1 ? 's' : ''} raised`}
            </div>
          </div>
        </div>
        {flags.length > 0 && (
          <div style={{ fontSize: 10, color: 'var(--tx3)',
            fontFamily: 'JetBrains Mono' }}>
            {flags.slice(0, 2).map(f => f.type).join(', ')}
            {flags.length > 2 && ` +${flags.length - 2}`}
          </div>
        )}
      </div>

      {/* ── Summary ── */}
      {briefing.summary && (
        <div style={{ background: 'rgba(91,141,239,.06)',
          border: '1px solid rgba(91,141,239,.18)',
          borderRadius: 12, padding: 14, marginBottom: 14, fontSize: 13,
          color: 'var(--tx2)', lineHeight: 1.7 }}>
          {briefing.summary}
        </div>
      )}

      {/* ── Red flags (high severity) ── */}
      {redFlags.length > 0 && (
        <div style={{ background: 'rgba(224,117,138,.08)',
          border: '1px solid rgba(224,117,138,.3)', borderRadius: 10,
          padding: 12, marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#e0758a',
            textTransform: 'uppercase', letterSpacing: '0.1em',
            fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
            🚩 Red Flags
          </div>
          {redFlags.map((rf, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--tx2)',
              marginBottom: 4, display: 'flex', gap: 6 }}>
              <span style={{ color: '#e0758a' }}>!</span>{rf}
            </div>
          ))}
        </div>
      )}

      {/* ── Strengths + Concerns side-by-side ── */}
      {(strengths.length > 0 || concerns.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: 12, marginBottom: 12 }}>
          {strengths.length > 0 && (
            <div style={{ background: 'rgba(74,222,128,.06)',
              border: '1px solid rgba(74,222,128,.2)', borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#4ade80',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
                Strengths
              </div>
              {strengths.slice(0, 4).map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--tx2)',
                  marginBottom: 4, display: 'flex', gap: 6 }}>
                  <span style={{ color: '#4ade80', flexShrink: 0 }}>+</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          )}
          {concerns.length > 0 && (
            <div style={{ background: 'rgba(216,184,120,.06)',
              border: '1px solid rgba(216,184,120,.2)', borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#d8b878',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
                Concerns
              </div>
              {concerns.slice(0, 4).map((c, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--tx2)',
                  marginBottom: 4, display: 'flex', gap: 6 }}>
                  <span style={{ color: '#d8b878', flexShrink: 0 }}>–</span>
                  <span>{c}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Resume Validation ── */}
      {resumeValid.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--tx3)',
            letterSpacing: '0.1em', textTransform: 'uppercase',
            fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
            Resume Validation
          </div>
          <div style={{ background: 'var(--pan2)', border: '1px solid var(--ln)',
            borderRadius: 10, overflow: 'hidden' }}>
            {resumeValid.slice(0, 5).map((rv, i) => {
              const v = rv.verdict || 'unprobed';
              const vColors = {
                supports:    { bg: 'rgba(74,222,128,.1)',  c: '#4ade80', icon: '✓' },
                contradicts: { bg: 'rgba(224,117,138,.1)', c: '#e0758a', icon: '✗' },
                unprobed:    { bg: 'rgba(255,255,255,.03)', c: 'var(--tx3)', icon: '○' },
              };
              const vc = vColors[v] || vColors.unprobed;
              return (
                <div key={i} style={{
                  padding: '10px 12px', display: 'flex', alignItems: 'flex-start', gap: 10,
                  borderTop: i > 0 ? '1px solid var(--ln)' : 'none',
                  background: vc.bg,
                }}>
                  <span style={{ color: vc.c, fontSize: 13, flexShrink: 0,
                    fontFamily: 'JetBrains Mono', fontWeight: 700 }}>
                    {vc.icon}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: 'var(--tx)',
                      marginBottom: 2, fontWeight: 500 }}>
                      {rv.claim}
                    </div>
                    {rv.evidence && (
                      <div style={{ fontSize: 11, color: 'var(--tx3)',
                        lineHeight: 1.5, fontStyle: 'italic' }}>
                        {rv.evidence}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Focus On (for human round) ── */}
      {focusOn.length > 0 && (
        <div style={{ background: 'rgba(91,141,239,.06)',
          border: '1px solid rgba(91,141,239,.2)', borderRadius: 10,
          padding: 12, marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#5b8def',
            textTransform: 'uppercase', letterSpacing: '0.1em',
            fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
            🎯 Focus on (Human Round)
          </div>
          {focusOn.slice(0, 4).map((f, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--tx2)',
              marginBottom: 4, display: 'flex', gap: 6 }}>
              <span style={{ color: '#5b8def', flexShrink: 0 }}>→</span>
              <span>{f}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Already Tested + Suggested Questions ── */}
      {(alreadyTested.length > 0 || suggestedQs.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns:
          alreadyTested.length > 0 && suggestedQs.length > 0 ? '1fr 1fr' : '1fr',
          gap: 12, marginBottom: 14 }}>
          {alreadyTested.length > 0 && (
            <div style={{ background: 'var(--pan2)', border: '1px solid var(--ln)',
              borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--tx2)',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
                ✓ Already Tested
              </div>
              {alreadyTested.slice(0, 4).map((t, i) => (
                <div key={i} style={{ fontSize: 11, color: 'var(--tx3)',
                  marginBottom: 4 }}>
                  · {t}
                </div>
              ))}
            </div>
          )}
          {suggestedQs.length > 0 && (
            <div style={{ background: 'rgba(143,155,255,.06)',
              border: '1px solid rgba(143,155,255,.2)', borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#8f9bff',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
                💡 Suggested Qs
              </div>
              {suggestedQs.slice(0, 3).map((q, i) => (
                <div key={i} style={{ fontSize: 11, color: 'var(--tx2)',
                  marginBottom: 6, lineHeight: 1.5 }}>
                  → {q}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Collapsible transcript ── */}
      {transcript.length > 0 && (
        <div style={{ border: '1px solid var(--ln)', borderRadius: 10,
          background: 'var(--pan2)', overflow: 'hidden' }}>
          <div onClick={() => setShowTranscript(!showTranscript)}
            style={{ padding: '12px 14px', cursor: 'pointer', userSelect: 'none',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--tx2)',
              textTransform: 'uppercase', letterSpacing: '0.1em',
              fontFamily: 'JetBrains Mono' }}>
              Full Transcript ({transcript.length} turns)
            </span>
            <span style={{ fontFamily: 'JetBrains Mono', fontSize: 14,
              color: 'var(--tx3)',
              transform: showTranscript ? 'rotate(90deg)' : 'none',
              transition: 'transform .2s' }}>
              ▸
            </span>
          </div>
          {showTranscript && (
            <div style={{ borderTop: '1px solid var(--ln)',
              maxHeight: 420, overflowY: 'auto' }}>
              {transcript.map((turn, i) => {
                const score = turn.evaluation?.dimension_score;
                const scoreColor = score >= 75 ? '#4ade80'
                                : score >= 50 ? '#d8b878' : '#e0758a';
                return (
                  <div key={i} style={{
                    padding: '12px 14px',
                    borderTop: i > 0 ? '1px solid var(--ln)' : 'none',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between',
                      marginBottom: 6, fontSize: 10, color: 'var(--tx3)',
                      fontFamily: 'JetBrains Mono', textTransform: 'uppercase',
                      letterSpacing: '0.06em' }}>
                      <span>
                        Q{i + 1}
                        {turn.is_probe && <span style={{ marginLeft: 6,
                          color: '#8f9bff' }}>· probe</span>}
                        {turn.dimension && <span style={{ marginLeft: 6 }}>
                          · {turn.dimension.replace(/_/g, ' ')}
                        </span>}
                      </span>
                      {score !== undefined && (
                        <span style={{ color: scoreColor, fontWeight: 700 }}>
                          {score}/100
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--jd)',
                      marginBottom: 4, lineHeight: 1.5 }}>
                      Q: {turn.q}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--tx2)',
                      lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                      A: {turn.a}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── LEGACY AI summary view (pre-ARIA candidates) ────────────── */
function LegacyAISummary({ summary, answers, strengths, concerns }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--tx)',
        letterSpacing: '0.1em', textTransform: 'uppercase',
        fontFamily: 'JetBrains Mono', marginBottom: 12 }}>
        AI Interview Report
        <span style={{ marginLeft: 8, fontSize: 9,
          color: 'var(--tx3)', letterSpacing: '0.05em' }}>
          (legacy format)
        </span>
      </div>

      {summary && (
        <div style={{ background: 'rgba(91,141,239,.06)',
          border: '1px solid rgba(91,141,239,.18)',
          borderRadius: 12, padding: 14, marginBottom: 12, fontSize: 13,
          color: 'var(--tx2)', lineHeight: 1.7 }}>
          {summary}
        </div>
      )}

      {(strengths.length > 0 || concerns.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: 12, marginBottom: 12 }}>
          {strengths.length > 0 && (
            <div style={{ background: 'rgba(74,222,128,.06)',
              border: '1px solid rgba(74,222,128,.2)', borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#4ade80',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
                Strengths
              </div>
              {strengths.slice(0, 3).map((s, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--tx2)',
                  marginBottom: 4, display: 'flex', gap: 6 }}>
                  <span style={{ color: '#4ade80' }}>+</span>{s}
                </div>
              ))}
            </div>
          )}
          {concerns.length > 0 && (
            <div style={{ background: 'rgba(224,117,138,.06)',
              border: '1px solid rgba(224,117,138,.2)', borderRadius: 10, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--rs)',
                textTransform: 'uppercase', letterSpacing: '0.1em',
                fontFamily: 'JetBrains Mono', marginBottom: 8 }}>
                Watch-outs
              </div>
              {concerns.slice(0, 3).map((c, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--tx2)',
                  marginBottom: 4, display: 'flex', gap: 6 }}>
                  <span style={{ color: 'var(--rs)' }}>–</span>{c}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {answers.slice(0, 3).map((qa, i) => (
        <div key={i} style={{ marginBottom: 10, padding: 12,
          background: 'var(--pan2)', borderRadius: 10,
          border: '1px solid var(--ln)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--jd)', marginBottom: 4 }}>
            Q: {qa.question || qa.q}
          </div>
          <div style={{ fontSize: 12, color: 'var(--tx2)', lineHeight: 1.6 }}>
            {qa.answer || qa.a}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   CANDIDATE DETAIL PANEL  — slide-over
════════════════════════════════════════════════════════════════════ */
function CandidatePanel({ candidate, onClose, onApproved }) {
  const [form, setForm]     = useState({ tech_score:'', culture_score:'', notes:'', salary:'' });
  const [loading, setLoad]  = useState(false);
  const [detail, setDetail] = useState(candidate);

  /* try to fetch enriched candidate detail */
  useEffect(() => {
    setDetail(candidate);
    if (!candidate?.id) return;
    axios.get(`${API_URL}/api/candidates/${candidate.id}`)
      .then(r => setDetail(r.data || candidate))
      .catch(() => {}); // fall back to passed-in data
  }, [candidate]);

  const handleDecision = async decision => {
    if (loading) return;
    setLoad(true);
    try {
      await axios.post(`${API_URL}/api/human-gate`, {
        candidate_id:  detail.id,
        decision,
        tech_score:    parseFloat(form.tech_score)    || 8,
        culture_score: parseFloat(form.culture_score) || 7,
        notes:         form.notes,
        agreed_salary: form.salary,
        round:         'technical',
      });
      onApproved(detail.id, decision);
      onClose();
    } catch (err) {
      console.error('human-gate error:', err);
    }
    setLoad(false);
  };

  const d = detail;
  const awaiting = d.status === 'waiting_technical_interview';
  const decisionColor = d.decision === 'HIRE'
    ? { bg: 'rgba(74,222,128,.15)', color: '#4ade80', border: 'rgba(74,222,128,.3)' }
    : d.decision === 'REJECT'
    ? { bg: 'rgba(224,117,138,.15)', color: 'var(--rs)', border: 'rgba(224,117,138,.3)' }
    : null;

  return (
    <>
      {/* overlay */}
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(3,5,8,.7)',
        backdropFilter: 'blur(4px)', zIndex: 50 }} onClick={onClose} />

      {/* panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, height: '100vh',
        width: 560, maxWidth: '92vw', zIndex: 51,
        background: 'linear-gradient(180deg,var(--ob2),var(--ob))',
        borderLeft: '1px solid var(--ln2)',
        display: 'flex', flexDirection: 'column',
        boxShadow: '-30px 0 80px -20px rgba(0,0,0,.7)',
        animation: 'hs-rise .34s cubic-bezier(.3,.9,.3,1)',
      }}>

        {/* ── head ── */}
        <div style={{ padding: '24px 28px 20px', borderBottom: '1px solid var(--ln)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
          flexShrink: 0 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: 'Bricolage Grotesque', fontWeight: 800,
              fontSize: 22, letterSpacing: '-0.02em', marginBottom: 4 }}>
              {d.name}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 13, color: 'var(--tx2)' }}>{d.applied_role}</span>
              {d.email && (
                <span style={{ fontSize: 11, color: 'var(--tx3)',
                  fontFamily: 'JetBrains Mono' }}>{d.email}</span>
              )}
            </div>
            {/* current status pill */}
            <div style={{ marginTop: 8 }}>
              {(() => {
                const col = COLS.find(c => c.key === d.status) || COLS[0];
                return (
                  <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, letterSpacing: '0.1em',
                    textTransform: 'uppercase', fontWeight: 700,
                    background: `${col.color}20`, color: col.color,
                    padding: '4px 10px', borderRadius: 100 }}>
                    {col.icon} {col.label}
                  </span>
                );
              })()}
              {decisionColor && (
                <span style={{ marginLeft: 8, fontFamily: 'JetBrains Mono', fontSize: 10,
                  letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 700,
                  background: decisionColor.bg, color: decisionColor.color,
                  border: `1px solid ${decisionColor.border}`,
                  padding: '4px 10px', borderRadius: 100 }}>
                  AI says: {d.decision}
                </span>
              )}
            </div>
          </div>
          <div className="hs-ico" style={{ flexShrink: 0 }} onClick={onClose}>✕</div>
        </div>

        {/* ── scrollable body ── */}
        <div className="hs-scr2" style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>

          {/* Score rings */}
          <div style={{ display: 'flex', gap: 20, marginBottom: 24,
            padding: 20, background: 'var(--pan)',
            border: '1px solid var(--ln)', borderRadius: 14,
            justifyContent: 'center', flexWrap: 'wrap' }}>
            <ScoreRing score={d.resume_score}         label="Resume"       color="var(--cy)" />
            <ScoreRing score={d.ai_interview_score}   label="AI Interview" color="var(--jd)" />
            <ScoreRing score={d.coding_score}         label="Coding"       color="var(--vi)" />
            <ScoreRing score={d.final_score}          label="Final"        color="var(--am)" />
          </div>

          {/* Skills */}
          {(d.skills || []).length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--tx)',
                letterSpacing: '0.1em', textTransform: 'uppercase',
                fontFamily: 'JetBrains Mono', marginBottom: 10 }}>
                Skills
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {d.skills.map(sk => (
                  <span key={sk} style={{ background: 'var(--jdim)', color: 'var(--jd)',
                    padding: '4px 10px', borderRadius: 100, fontSize: 12 }}>{sk}</span>
                ))}
              </div>
            </div>
          )}

          {/* AI Interview report */}
          <AIInterviewSummary candidate={d} />

          {/* Journey timeline */}
          <JourneyTimeline candidate={d} />

          {/* ── Technical interview feedback form (HR action) ── */}
          {awaiting && (
            <div style={{
              background: 'linear-gradient(160deg,rgba(91,141,239,.06),rgba(143,155,255,.04))',
              border: '1px solid rgba(91,141,239,.22)', borderRadius: 14, padding: 20,
              marginBottom: 8,
            }}>
              <div style={{ fontFamily: 'Bricolage Grotesque', fontWeight: 700,
                fontSize: 16, marginBottom: 4 }}>
                ⏳ Your Feedback Required
              </div>
              <p style={{ fontSize: 13, color: 'var(--tx2)', marginBottom: 16, lineHeight: 1.5 }}>
                AI already covered technical depth. Focus on <strong style={{ color: 'var(--jd)' }}>leadership,
                communication, and culture fit</strong> in your round.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                {[['tech_score','Technical Score (1–10)'],['culture_score','Culture Score (1–10)']].map(([k,l]) => (
                  <div key={k}>
                    <label style={{ fontSize: 11, color: 'var(--tx2)', display: 'block', marginBottom: 4 }}>
                      {l}
                    </label>
                    <input style={{
                      width: '100%', background: 'var(--pan)', border: '1px solid var(--ln)',
                      color: 'var(--tx)', borderRadius: 9, padding: '9px 12px',
                      fontFamily: 'Sora', fontSize: 13, outline: 'none',
                    }}
                      type="number" min="1" max="10" placeholder="8"
                      value={form[k]}
                      onChange={e => setForm({ ...form, [k]: e.target.value })} />
                  </div>
                ))}
              </div>

              <textarea style={{
                width: '100%', background: 'var(--pan)', border: '1px solid var(--ln)',
                color: 'var(--tx)', borderRadius: 10, padding: '10px 12px',
                fontFamily: 'Sora', fontSize: 13, outline: 'none',
                minHeight: 80, resize: 'vertical', lineHeight: 1.6, marginBottom: 12,
              }}
                placeholder="Interview notes, key observations…"
                value={form.notes}
                onChange={e => setForm({ ...form, notes: e.target.value })} />

              <input style={{
                width: '100%', background: 'var(--pan)', border: '1px solid var(--ln)',
                color: 'var(--tx)', borderRadius: 9, padding: '9px 12px',
                fontFamily: 'Sora', fontSize: 13, outline: 'none', marginBottom: 16,
              }}
                placeholder="Agreed salary (e.g. 21 LPA)"
                value={form.salary}
                onChange={e => setForm({ ...form, salary: e.target.value })} />

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  style={{
                    flex: 1, padding: 13, fontFamily: 'Sora', fontWeight: 700,
                    fontSize: 13, cursor: loading ? 'not-allowed' : 'pointer',
                    borderRadius: 10, border: '1px solid rgba(74,222,128,.4)',
                    background: 'rgba(74,222,128,.12)', color: '#4ade80',
                    transition: 'all .18s',
                  }}
                  disabled={loading}
                  onClick={() => handleDecision('APPROVE')}>
                  {loading ? '⏳' : '✓'} Approve — HR Round
                </button>
                <button
                  style={{
                    flex: 1, padding: 13, fontFamily: 'Sora', fontWeight: 700,
                    fontSize: 13, cursor: loading ? 'not-allowed' : 'pointer',
                    borderRadius: 10, border: '1px solid rgba(224,117,138,.4)',
                    background: 'rgba(224,117,138,.12)', color: 'var(--rs)',
                    transition: 'all .18s',
                  }}
                  disabled={loading}
                  onClick={() => handleDecision('REJECT')}>
                  {loading ? '⏳' : '✗'} Reject
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PIPELINE VIEW — main export
════════════════════════════════════════════════════════════════════ */
export default function PipelineView({ candidates, loading, onRefresh,
  jobs = [], initialJobFilter = null, onJobFilterChange }) {
  const [selected, setSelected] = useState(null);
  const [search,   setSearch]   = useState('');
  const [colFilter, setColFilter] = useState('all');
  const [jobFilter, setJobFilter] = useState(initialJobFilter || 'all');

  // Sync external filter changes (e.g. clicking "View Pipeline" on a job card)
  useEffect(() => {
    setJobFilter(initialJobFilter || 'all');
  }, [initialJobFilter]);

  const setJobFilterAndNotify = (val) => {
    setJobFilter(val);
    if (onJobFilterChange) onJobFilterChange(val === 'all' ? null : val);
  };

  const handleApproved = (id, decision) => {
    // Optimistic update — parent will re-fetch on next poll
    if (onRefresh) onRefresh();
  };

  /* filtered + searched candidates */
  const filtered = useMemo(() => {
    let list = candidates;
    if (jobFilter !== 'all') {
      const job = jobs.find(j => j.id === jobFilter);
      if (job) {
        list = list.filter(c =>
          c.job_id === job.id || c.applied_role === job.title
        );
      }
    }
    if (colFilter !== 'all')
      list = list.filter(c => c.status === colFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(c =>
        (c.name || '').toLowerCase().includes(q) ||
        (c.applied_role || '').toLowerCase().includes(q) ||
        (c.email || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [candidates, jobFilter, colFilter, search, jobs]);

  // Scoped candidates for stats/chips (job-filtered but not status-filtered)
  const scopedCandidates = useMemo(() => {
    if (jobFilter === 'all') return candidates;
    const job = jobs.find(j => j.id === jobFilter);
    if (!job) return candidates;
    return candidates.filter(c =>
      c.job_id === job.id || c.applied_role === job.title
    );
  }, [candidates, jobFilter, jobs]);

  /* stat strip */
  const stats = useMemo(() => ({
    total:    scopedCandidates.length,
    pipeline: scopedCandidates.filter(c => !['hired','rejected'].includes(c.status)).length,
    hired:    scopedCandidates.filter(c => c.status === 'hired').length,
    awaiting: scopedCandidates.filter(c => c.status === 'waiting_technical_interview').length,
  }), [scopedCandidates]);

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--tx3)' }}>
      <div style={{ fontFamily: 'JetBrains Mono', fontSize: 14,
        color: 'var(--tx2)', marginBottom: 8 }}>Loading pipeline…</div>
      <div style={{ width: 48, height: 3, background: 'var(--jd)',
        borderRadius: 2, margin: '0 auto', animation: 'hs-rise 1s ease infinite alternate' }} />
    </div>
  );

  if (candidates.length === 0) return (
    <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--tx3)' }}>
      <div style={{ fontSize: 56, marginBottom: 16 }}>⊞</div>
      <div style={{ fontFamily: 'Bricolage Grotesque', fontWeight: 700,
        fontSize: 22, color: 'var(--tx2)', marginBottom: 8 }}>Pipeline is empty</div>
      <p style={{ fontSize: 14 }}>Candidate applications will appear here in real-time.</p>
    </div>
  );

  return (
    <div style={{ position: 'relative', zIndex: 1 }}>

      {/* candidate detail panel */}
      {selected && (
        <CandidatePanel
          candidate={selected}
          onClose={() => setSelected(null)}
          onApproved={handleApproved}
        />
      )}

      {/* ── Page Head ── */}
      <div className="hs-rise" style={{ display: 'flex', alignItems: 'flex-end',
        justifyContent: 'space-between', marginBottom: 26 }}>
        <div>
          <h1 style={{ fontFamily: 'Bricolage Grotesque', fontWeight: 800,
            fontSize: 34, letterSpacing: '-0.03em', lineHeight: 1 }}>
            Talent Pipeline
          </h1>
          <p style={{ color: 'var(--tx2)', fontSize: 14, marginTop: 8 }}>
            Real-time view of every candidate across your{' '}
            <span style={{ color: 'var(--jd)' }}>hiring funnel</span>
          </p>
        </div>
        {stats.awaiting > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px',
            background: 'rgba(216,184,120,.1)', border: '1px solid rgba(216,184,120,.3)',
            borderRadius: 12, fontSize: 13, color: 'var(--am)', fontWeight: 600,
          }}>
            ⏳ {stats.awaiting} candidate{stats.awaiting > 1 ? 's' : ''} awaiting your feedback
          </div>
        )}
      </div>

      {/* ── Stat strip ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)',
        gap: 14, marginBottom: 24 }}>
        {[
          { val: stats.total,    lbl: 'Total Candidates', color: 'var(--cy)', ico: '⊞' },
          { val: stats.pipeline, lbl: 'In Pipeline',      color: 'var(--jd)', ico: '◎' },
          { val: stats.hired,    lbl: 'Hired',            color: '#4ade80',   ico: '✅' },
          { val: stats.awaiting, lbl: 'Need Your Action', color: 'var(--am)', ico: '⏳' },
        ].map((s, i) => (
          <div key={s.lbl}
            className={`hs-rise hs-d${i + 1}`}
            style={{ background: 'linear-gradient(160deg,var(--pan),var(--ob2))',
              border: '1px solid var(--ln)', borderRadius: 14,
              padding: '16px 18px', position: 'relative', overflow: 'hidden',
              cursor: i === 3 && stats.awaiting > 0 ? 'pointer' : 'default' }}
            onClick={() => i === 3 && setColFilter(
              colFilter === 'waiting_technical_interview' ? 'all' : 'waiting_technical_interview'
            )}>
            <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 700,
              fontSize: 28, letterSpacing: '-0.02em', color: s.color }}>{s.val}</div>
            <div style={{ fontSize: 12, color: 'var(--tx2)', marginTop: 4 }}>{s.lbl}</div>
            <div style={{ position: 'absolute', right: -6, bottom: -6,
              fontSize: 44, opacity: .06 }}>{s.ico}</div>
          </div>
        ))}
      </div>

      {/* ── Job filter dropdown ── */}
      <div style={{ display:'flex', gap:12, marginBottom:14, alignItems:'center', flexWrap:'wrap' }}>
        <div style={{ display:'flex', alignItems:'center', gap:10,
          background:'var(--pan)', border:`1px solid ${jobFilter !== 'all' ? 'rgba(91,141,239,.4)' : 'var(--ln)'}`,
          borderRadius:11, padding:'9px 14px', minWidth:340 }}>
          <span style={{ fontSize:11, color:'var(--tx3)',
            fontFamily:'JetBrains Mono', letterSpacing:'0.08em',
            textTransform:'uppercase' }}>Job</span>
          <select
            value={jobFilter}
            onChange={e => setJobFilterAndNotify(e.target.value)}
            style={{ background:'none', border:'none', outline:'none',
              color:'var(--tx)', fontFamily:'Sora', fontSize:13, flex:1,
              cursor:'pointer' }}>
            <option value="all" style={{ background:'var(--pan2)' }}>All Jobs ({candidates.length} candidates)</option>
            {jobs.map(j => {
              const count = candidates.filter(c =>
                c.job_id === j.id || c.applied_role === j.title
              ).length;
              return (
                <option key={j.id} value={j.id} style={{ background:'var(--pan2)' }}>
                  {j.title} ({count}) {j.status === 'closed' ? ' — closed' : ''}
                </option>
              );
            })}
          </select>
        </div>
        {jobFilter !== 'all' && (
          <button onClick={() => setJobFilterAndNotify('all')}
            style={{ padding:'8px 14px', borderRadius:9, cursor:'pointer',
              background:'rgba(91,141,239,.1)', border:'1px solid rgba(91,141,239,.3)',
              color:'var(--jd)', fontFamily:'JetBrains Mono', fontSize:11, fontWeight:600 }}>
            ✕ Clear job filter
          </button>
        )}
      </div>

      {/* ── Search + Filter bar ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 22, alignItems: 'center' }}>
        {/* search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, maxWidth: 360,
          background: 'var(--pan)', border: '1px solid var(--ln)',
          borderRadius: 11, padding: '9px 14px' }}>
          <span style={{ color: 'var(--tx3)', fontSize: 15 }}>⌕</span>
          <input style={{ background: 'none', border: 'none', outline: 'none',
            color: 'var(--tx)', fontFamily: 'Sora', fontSize: 13, width: '100%' }}
            placeholder="Search candidates…"
            value={search} onChange={e => setSearch(e.target.value)} />
          {search && (
            <span style={{ cursor: 'pointer', color: 'var(--tx3)', fontSize: 12 }}
              onClick={() => setSearch('')}>✕</span>
          )}
        </div>

        {/* status filter chips */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <Chip active={colFilter === 'all'} onClick={() => setColFilter('all')}
            label="All" count={scopedCandidates.length} />
          {COLS.filter(c => scopedCandidates.some(x => x.status === c.key)).map(col => (
            <Chip key={col.key}
              active={colFilter === col.key}
              onClick={() => setColFilter(colFilter === col.key ? 'all' : col.key)}
              label={col.label}
              count={scopedCandidates.filter(c => c.status === col.key).length}
              color={col.color}
            />
          ))}
        </div>
      </div>

      {/* ── Kanban board ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${COLS.length}, minmax(150px, 1fr))`,
        gap: 12, overflowX: 'auto', paddingBottom: 12,
      }}>
        {COLS.map(col => {
          const colCands = filtered.filter(c => c.status === col.key);
          return (
            <div key={col.key} style={{
              background: 'linear-gradient(160deg,var(--pan),var(--ob2))',
              border: `1px solid ${colFilter === col.key
                ? `${col.color}44` : 'var(--ln)'}`,
              borderRadius: 14, padding: 12, minHeight: 240,
              transition: 'border-color .2s',
            }}>
              {/* column header */}
              <div style={{ display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 12, paddingBottom: 10,
                borderBottom: `2px solid ${col.color}33` }}>
                <span style={{ color: col.color, fontWeight: 700, fontSize: 11,
                  fontFamily: 'JetBrains Mono', textTransform: 'uppercase',
                  letterSpacing: '0.08em' }}>
                  {col.icon} {col.label}
                </span>
                <span style={{ background: `${col.color}20`, color: col.color,
                  borderRadius: 100, padding: '2px 8px',
                  fontSize: 11, fontWeight: 700, fontFamily: 'JetBrains Mono' }}>
                  {colCands.length}
                </span>
              </div>

              {/* candidate cards */}
              {colCands.map((c, i) => (
                <KanbanCard key={c.id} candidate={c} col={col}
                  delay={i % 5 + 1}
                  onClick={() => setSelected(c)} />
              ))}

              {colCands.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--tx3)',
                  textAlign: 'center', paddingTop: 20,
                  fontFamily: 'JetBrains Mono' }}>—</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Kanban card ──────────────────────────────────────────────────── */
function KanbanCard({ candidate: c, col, delay, onClick }) {
  const awaiting = c.status === 'waiting_technical_interview';
  return (
    <div
      className={`hs-ccard hs-rise hs-d${delay}`}
      onClick={onClick}
      style={{ cursor: 'pointer' }}
    >
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 2 }}>{c.name}</div>
      <div style={{ fontSize: 11, color: 'var(--tx3)', marginBottom: 8,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {c.applied_role}
      </div>

      {/* score mini bars */}
      {c.resume_score && <ScoreBar label="Resume" val={c.resume_score} color="var(--cy)" />}
      {c.ai_interview_score && <ScoreBar label="AI" val={c.ai_interview_score} color="var(--jd)" />}
      {c.final_score && (
        <div style={{ marginTop: 6, display: 'flex', justifyContent: 'space-between',
          alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--tx3)' }}>Final</span>
          <span style={{
            fontSize: 11, fontWeight: 700, fontFamily: 'JetBrains Mono',
            padding: '2px 8px', borderRadius: 100,
            background: c.decision === 'HIRE' ? 'rgba(74,222,128,.15)' : 'rgba(224,117,138,.15)',
            color: c.decision === 'HIRE' ? '#4ade80' : 'var(--rs)',
          }}>
            {c.final_score}/100
          </span>
        </div>
      )}

      {awaiting && (
        <div style={{ marginTop: 8, fontSize: 10, color: 'var(--am)',
          background: 'rgba(216,184,120,.1)', padding: '3px 8px',
          borderRadius: 6, textAlign: 'center', fontWeight: 600 }}>
          ⏳ Your action needed
        </div>
      )}

      {c.decision === 'HIRE' && c.status !== 'hired' && (
        <div style={{ marginTop: 6, fontSize: 10, color: '#4ade80',
          background: 'rgba(74,222,128,.1)', padding: '3px 8px',
          borderRadius: 6, textAlign: 'center', fontWeight: 600 }}>
          ✓ AI recommends hire
        </div>
      )}
    </div>
  );
}

/* ── Score mini bar inside kanban card ───────────────────────────── */
function ScoreBar({ label, val, color }) {
  return (
    <div style={{ marginBottom: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 2 }}>
        <span style={{ fontSize: 10, color: 'var(--tx3)' }}>{label}</span>
        <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono',
          color, fontWeight: 600 }}>{val}</span>
      </div>
      <div style={{ height: 3, borderRadius: 2, background: 'var(--pan)',
        overflow: 'hidden' }}>
        <div style={{ height: '100%', borderRadius: 2, background: color,
          width: `${Math.min(val, 100)}%`,
          transition: 'width .8s cubic-bezier(.4,0,.2,1)' }} />
      </div>
    </div>
  );
}

/* ── Filter chip ────────────────────────────────────────────────── */
function Chip({ active, onClick, label, count, color }) {
  return (
    <div onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '7px 13px', borderRadius: 9, cursor: 'pointer',
      fontSize: 12, fontWeight: 500, transition: 'all .15s',
      background: active ? (color ? `${color}20` : 'var(--pan2)') : 'var(--pan)',
      border: `1px solid ${active ? (color || 'var(--jd)') + '44' : 'var(--ln)'}`,
      color: active ? (color || 'var(--jd)') : 'var(--tx2)',
    }}>
      {label}
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10,
        color: active ? (color || 'var(--jd)') : 'var(--tx3)' }}>
        {count}
      </span>
    </div>
  );
}