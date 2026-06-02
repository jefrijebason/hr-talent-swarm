import React from 'react';
import { motion } from 'framer-motion';
import NeuralField from './NeuralField';
import AIIndicator from './AIOrb';
import { iTheme } from './interviewTheme';

export default function InterviewIntro({
  mode = 'fresh',
  candidateName = 'there',
  roleName = 'this role',
  roundsTotal = 3,
  estMinutes = 8,
  currentRound = 1,
  onBegin,
  onContactHR,
}) {
  return (
    <div style={s.wrap}>
      <NeuralField />
      <div style={s.content}>

        {/* ─── FRESH START ─── */}
        {mode === 'fresh' && (
          <motion.div style={s.card}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}>

            <motion.div style={s.ariaRow}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}>
              <AIIndicator state="idle" size="small" />
              <span style={s.ariaLabel}>ARIA</span>
              <span style={s.ariaSub}>AI Interviewer</span>
            </motion.div>

            <motion.h1 style={s.title}
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5 }}>
              Hello {candidateName},
              <br />
              <span style={{ color: iTheme.primary }}>
                let's get to know you
              </span>
            </motion.h1>

            <motion.p style={s.subtitle}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}>
              This is a conversation to understand how you think —
              not a test to trip you up. Take your time and be yourself.
            </motion.p>

            <motion.div style={s.infoRow}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}>
              <InfoChip icon="🎯" label="Rounds" value={`${roundsTotal}`} />
              <InfoChip icon="⏱" label="Duration" value={`~${estMinutes} min`} />
              <InfoChip icon="💬" label="Format" value="Text" />
            </motion.div>

            <motion.div style={s.guideBox}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}>
              <div style={s.guideTitle}>Before we start</div>
              {[
                'Thoughtful answers beat fast ones — take your time',
                'Be specific with real examples from your experience',
                'There are no trick questions',
                'You can resume once if disconnected',
              ].map((t, i) => (
                <motion.div key={i} style={s.guideItem}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 + i * 0.08 }}>
                  <span style={s.guideCheck}>✓</span> {t}
                </motion.div>
              ))}
            </motion.div>

            <PrimaryButton onClick={onBegin}>
              Begin Interview
            </PrimaryButton>

            <p style={s.fineprint}>
              Applying for {roleName}
            </p>
          </motion.div>
        )}

        {/* ─── RESUME (Scenario 1) ─── */}
        {mode === 'resume' && (
          <motion.div style={s.card}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}>

            <div style={s.ariaRow}>
              <AIIndicator state="idle" size="small" />
              <span style={s.ariaLabel}>ARIA</span>
            </div>

            <h1 style={s.title}>
              Welcome back,{' '}
              <span style={{ color: iTheme.primary }}>{candidateName}</span>
            </h1>

            <p style={s.subtitle}>
              Let's pick up where we left off — you were on
              round {currentRound} of {roundsTotal}.
            </p>

            <div style={s.progressBox}>
              <div style={s.progressRow}>
                <span style={s.progressLabel}>Progress</span>
                <span style={s.progressVal}>
                  Round {currentRound}/{roundsTotal}
                </span>
              </div>
              <div style={s.progressBar}>
                <motion.div style={s.progressFill}
                  initial={{ width: 0 }}
                  animate={{ width: `${((currentRound - 1) / roundsTotal) * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.3 }} />
              </div>
            </div>

            <div style={s.warnBox}>
              <div style={s.warnRow}>
                <span style={s.warnIcon}>⚠️</span>
                <span style={s.warnTitle}>This is your only resume</span>
              </div>
              <p style={s.warnText}>
                To keep things fair, the interview can be resumed only once.
                Please find a quiet spot and complete it in one sitting this time.
              </p>
            </div>

            <PrimaryButton onClick={onBegin}>
              Resume Interview
            </PrimaryButton>
          </motion.div>
        )}

        {/* ─── LOCKED ─── */}
        {mode === 'locked' && (
          <motion.div style={s.card}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}>

            <div style={s.lockIcon}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
                stroke="#a8a29e" strokeWidth="1.5" strokeLinecap="round">
                <rect x="3" y="11" width="18" height="11" rx="3" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>

            <h1 style={s.title}>Interview Locked</h1>

            <p style={s.subtitle}>
              This interview has already been resumed once and
              can't be continued automatically.
            </p>

            <div style={s.lockedBox}>
              <p style={{ ...s.subtitle, marginBottom: 0 }}>
                If you experienced a genuine technical issue,
                our HR team can help. Reach out and we'll sort
                it out for you.
              </p>
            </div>

            <SecondaryButton onClick={onContactHR}>
              Contact HR Team
            </SecondaryButton>
          </motion.div>
        )}

      </div>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────
function InfoChip({ icon, label, value }) {
  return (
    <div style={s.chip}>
      <span style={{ fontSize: '16px' }}>{icon}</span>
      <div>
        <div style={s.chipValue}>{value}</div>
        <div style={s.chipLabel}>{label}</div>
      </div>
    </div>
  );
}

function PrimaryButton({ children, onClick }) {
  return (
    <motion.button onClick={onClick}
      whileHover={{ scale: 1.02,
        boxShadow: '0 8px 24px rgba(79,70,229,0.3)' }}
      whileTap={{ scale: 0.98 }}
      transition={iTheme.spring}
      style={s.primaryBtn}>
      {children}
    </motion.button>
  );
}

function SecondaryButton({ children, onClick }) {
  return (
    <motion.button onClick={onClick}
      whileHover={{ scale: 1.02,
        boxShadow: '0 6px 20px rgba(79,70,229,0.2)',
        borderColor: 'rgba(79,70,229,0.5)' }}
      whileTap={{ scale: 0.98 }}
      transition={iTheme.spring}
      style={s.secondaryBtn}>
      {children}
    </motion.button>
  );
}

// ── Styles ───────────────────────────────────────────────────────
const s = {
  wrap: {
    minHeight: '100vh', position: 'relative',
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
  },
  content: {
    position: 'relative', zIndex: 1,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    minHeight: '100vh', padding: '40px 20px',
  },
  card: {
    maxWidth: '480px', width: '100%',
    background: '#ffffff',
    border: '1px solid rgba(0,0,0,0.06)',
    borderRadius: '20px', padding: '40px',
    boxShadow: '0 16px 48px rgba(0,0,0,0.3), 0 6px 16px rgba(0,0,0,0.2)',
  },
  ariaRow: {
    display: 'flex', alignItems: 'center', gap: '10px',
    marginBottom: '28px',
  },
  ariaLabel: {
    fontSize: '15px', fontWeight: 700, color: '#1c1917',
  },
  ariaSub: {
    fontSize: '13px', color: '#a8a29e',
  },
  title: {
    fontSize: '28px', fontWeight: 800, color: '#1c1917',
    lineHeight: 1.2, margin: '0 0 14px', letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: '15px', color: '#57534e', lineHeight: 1.65,
    margin: '0 0 24px',
  },
  infoRow: {
    display: 'flex', gap: '10px', marginBottom: '24px',
  },
  chip: {
    display: 'flex', alignItems: 'center', gap: '8px',
    background: '#f5f5f4', border: '1px solid #e7e5e4',
    borderRadius: '12px', padding: '10px 14px', flex: 1,
  },
  chipValue: {
    fontSize: '14px', fontWeight: 700, color: '#1c1917',
  },
  chipLabel: {
    fontSize: '10px', color: '#a8a29e',
    textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  guideBox: {
    background: 'rgba(79,70,229,0.04)',
    border: '1px solid rgba(79,70,229,0.12)',
    borderRadius: '14px', padding: '20px', marginBottom: '28px',
  },
  guideTitle: {
    fontSize: '12px', fontWeight: 700, color: '#a8a29e',
    textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '14px',
  },
  guideItem: {
    fontSize: '14px', color: '#57534e', lineHeight: 1.5,
    marginBottom: '10px', display: 'flex', gap: '10px',
    alignItems: 'flex-start',
  },
  guideCheck: {
    color: '#059669', fontWeight: 700, flexShrink: 0, marginTop: '1px',
  },
  primaryBtn: {
    width: '100%', padding: '15px', border: 'none', borderRadius: '14px',
    background: iTheme.gradient, color: '#fff', fontSize: '16px',
    fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
  },
secondaryBtn: {
    width: '100%', padding: '15px', borderRadius: '14px',
    background: 'linear-gradient(135deg, rgba(79,70,229,0.08), rgba(99,102,241,0.08))',
    color: '#4f46e5',
    border: '1px solid rgba(79,70,229,0.25)',
    fontSize: '15px', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
  },
  fineprint: {
    fontSize: '12px', color: '#a8a29e', textAlign: 'center',
    marginTop: '16px',
  },
  progressBox: {
    background: '#f5f5f4', border: '1px solid #e7e5e4',
    borderRadius: '14px', padding: '18px', marginBottom: '20px',
  },
  progressRow: {
    display: 'flex', justifyContent: 'space-between', marginBottom: '10px',
  },
  progressLabel: {
    fontSize: '12px', color: '#a8a29e',
    textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600,
  },
  progressVal: {
    fontSize: '13px', color: '#1c1917', fontWeight: 700,
  },
  progressBar: {
    height: '6px', background: '#e7e5e4',
    borderRadius: '100px', overflow: 'hidden',
  },
  progressFill: {
    height: '100%', background: iTheme.gradient,
    borderRadius: '100px',
  },
  warnBox: {
    background: 'rgba(217,119,6,0.06)',
    border: '1px solid rgba(217,119,6,0.2)',
    borderRadius: '14px', padding: '18px', marginBottom: '24px',
  },
  warnRow: {
    display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px',
  },
  warnIcon: { fontSize: '16px' },
  warnTitle: {
    fontSize: '14px', fontWeight: 700, color: '#d97706',
  },
  warnText: {
    fontSize: '13px', color: '#57534e', lineHeight: 1.5, margin: 0,
  },
  lockIcon: { marginBottom: '16px' },
  lockedBox: {
    background: '#f5f5f4', border: '1px solid #e7e5e4',
    borderRadius: '14px', padding: '18px', marginBottom: '24px',
  },
};