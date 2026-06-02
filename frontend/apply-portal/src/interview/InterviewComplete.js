import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import NeuralField from './NeuralField';
import AIIndicator from './AIOrb';
import { iTheme } from './interviewTheme';

export default function InterviewComplete({
  candidateName = 'there',
  roleName = 'this role',
  roundsTotal = 3,
  answers = [],
}) {
  const [phase, setPhase] = useState('processing');
  // processing | revealed

  useEffect(() => {
    const timer = setTimeout(() => setPhase('revealed'), 3500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div style={s.wrap}>
      <NeuralField />
      <div style={s.content}>

        {/* Processing */}
        {phase === 'processing' && (
          <motion.div style={s.card}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}>
            <div style={{ marginBottom: '24px' }}>
              <AIIndicator state="processing" size="normal" />
            </div>
            <h2 style={s.title}>Analyzing your responses...</h2>
            <p style={s.subtitle}>
              ARIA is building your AI Readiness Profile.
              This takes a few moments.
            </p>
            <div style={s.stepsBox}>
              {[
                'Evaluating technical depth',
                'Assessing problem-solving approach',
                'Building your profile',
              ].map((step, i) => (
                <motion.div key={i} style={s.stepItem}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.8 }}>
                  <motion.span
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.3 }}
                    style={{ color: iTheme.primary }}>●</motion.span>
                  <span>{step}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Revealed */}
        {phase === 'revealed' && (
          <motion.div style={s.card}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}>

            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              style={{ fontSize: '48px', textAlign: 'center', marginBottom: '16px' }}>
              ✅
            </motion.div>

            <h2 style={{ ...s.title, textAlign: 'center' }}>
              Interview Complete!
            </h2>

            <p style={{ ...s.subtitle, textAlign: 'center' }}>
              Great job, {candidateName}. ARIA has finished building
              your profile.
            </p>

            {/* Summary card */}
            <div style={s.summaryBox}>
              <div style={s.summaryTitle}>Interview Summary</div>
              <div style={s.summaryGrid}>
                <div style={s.summaryItem}>
                  <div style={s.summaryValue}>{roundsTotal}</div>
                  <div style={s.summaryLabel}>Rounds</div>
                </div>
                <div style={s.summaryItem}>
                  <div style={s.summaryValue}>{answers.length}</div>
                  <div style={s.summaryLabel}>Answers</div>
                </div>
                <div style={s.summaryItem}>
                  <div style={{ ...s.summaryValue, color: '#059669' }}>✓</div>
                  <div style={s.summaryLabel}>Complete</div>
                </div>
              </div>
            </div>

            {/* What's next */}
            <div style={s.nextBox}>
              <div style={s.nextTitle}>What happens next</div>
              {[
                'Your AI Readiness Profile is being finalized',
                'Results are sent to the hiring team',
                'If shortlisted, you\'ll hear about the next round within 24 hours',
                'You\'ll receive a personal growth report by email',
              ].map((t, i) => (
                <motion.div key={i} style={s.nextItem}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}>
                  <span style={s.nextCheck}>✓</span> {t}
                </motion.div>
              ))}
            </div>

            <p style={s.fineprint}>
              Thank you for your time, {candidateName}. We genuinely
              appreciate it — regardless of outcome, you'll
              receive detailed feedback.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}

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
  title: {
    fontSize: '24px', fontWeight: 800, color: '#1c1917',
    margin: '0 0 12px',
  },
  subtitle: {
    fontSize: '15px', color: '#57534e', lineHeight: 1.6,
    margin: '0 0 24px',
  },
  stepsBox: {
    display: 'flex', flexDirection: 'column', gap: '12px',
  },
  stepItem: {
    display: 'flex', gap: '10px', alignItems: 'center',
    fontSize: '14px', color: '#57534e',
  },
  summaryBox: {
    background: '#f5f5f4', border: '1px solid #e7e5e4',
    borderRadius: '14px', padding: '20px', marginBottom: '20px',
  },
  summaryTitle: {
    fontSize: '12px', fontWeight: 700, color: '#a8a29e',
    textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '14px',
  },
  summaryGrid: {
    display: 'flex', gap: '12px',
  },
  summaryItem: {
    flex: 1, textAlign: 'center', background: '#ffffff',
    borderRadius: '10px', padding: '14px 8px',
    border: '1px solid #e7e5e4',
  },
  summaryValue: {
    fontSize: '22px', fontWeight: 800, color: '#1c1917', marginBottom: '2px',
  },
  summaryLabel: {
    fontSize: '11px', color: '#a8a29e', textTransform: 'uppercase',
    letterSpacing: '0.4px',
  },
  nextBox: {
    background: 'rgba(79,70,229,0.04)',
    border: '1px solid rgba(79,70,229,0.12)',
    borderRadius: '14px', padding: '20px', marginBottom: '20px',
  },
  nextTitle: {
    fontSize: '12px', fontWeight: 700, color: '#a8a29e',
    textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '14px',
  },
  nextItem: {
    fontSize: '14px', color: '#57534e', lineHeight: 1.5,
    marginBottom: '10px', display: 'flex', gap: '10px',
    alignItems: 'flex-start',
  },
  nextCheck: {
    color: '#059669', fontWeight: 700, flexShrink: 0,
  },
  fineprint: {
    fontSize: '13px', color: '#a8a29e', textAlign: 'center',
    lineHeight: 1.5,
  },
};