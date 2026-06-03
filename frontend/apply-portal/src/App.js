import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import AuroraBackground from './AuroraBackground';
import { TopNav, GlassCard, AuroraButton, GradientText } from './components';
import { theme, fonts } from './theme';
import BrowsePage from './pages/BrowsePage';
import JobDetailPage from './pages/JobDetailPage';
import ApplyPage from './pages/ApplyPage';
import TrackPage from './pages/TrackPage';
import InterviewPage from './interview/InterviewPage';

export default function App() {
  const [page, setPage]             = useState('browse');
  const [trackId, setTrackId] = useState('');
  const [selectedJob, setJob]       = useState(null);
  const [successData, setSuccessData] = useState(null);
  const [interviewData, setInterviewData] = useState(null);

  // Check URL for interview token on load
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('interview');
    const name  = params.get('name') || 'Candidate';
    const role  = params.get('role') || 'this role';
    const rounds = parseInt(params.get('rounds')) || 3;

    if (token) {
      setInterviewData({
        token,
        candidateName: decodeURIComponent(name),
        roleName: decodeURIComponent(role),
        roundsTotal: rounds,
        resumeCount: 0,
        currentRound: 1,
      });
      setPage('interview');
    }
  }, []);

  const pageVariants = {
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    exit:    { opacity: 0, y: -16 },
  };

  const goSuccess = (trackingId, form, job) => {
    setSuccessData({ trackingId, form, job });
    setPage('success');
    fireConfetti();
  };

  const fireConfetti = () => {
    const colors = ['#22d3ee', '#7c6cf6', '#e879f9'];
    confetti({ particleCount: 80, spread: 70, origin: { y: 0.3 }, colors });
    setTimeout(() => confetti({ particleCount: 50, angle: 60,
      spread: 55, origin: { x: 0 }, colors }), 250);
    setTimeout(() => confetti({ particleCount: 50, angle: 120,
      spread: 55, origin: { x: 1 }, colors }), 400);
  };

  // Interview page has its own layout — no nav
  if (page === 'interview' && interviewData) {
    return (
      <InterviewPage
        candidateName={interviewData.candidateName}
        roleName={interviewData.roleName}
        roundsTotal={interviewData.roundsTotal}
        resumeCount={interviewData.resumeCount}
        currentRound={interviewData.currentRound}
      />
    );
  }

  return (
    <div style={{ minHeight: '100vh', position: 'relative',
      fontFamily: "'Segoe UI', system-ui, sans-serif", color: theme.textPrimary }}>
      <AuroraBackground />

      <div style={{ position: 'relative', zIndex: 1 }}>
        <TopNav page={page === 'browse' || page === 'track' ? page : 'browse'}
          setPage={(p) => { setPage(p); setJob(null); }} />

        <AnimatePresence mode="wait">
          <motion.div key={page}
            variants={pageVariants}
            initial="initial" animate="animate" exit="exit"
            transition={{ duration: 0.35, ease: 'easeOut' }}>

            {page === 'browse' && (
              <BrowsePage onSelectJob={(j) => { setJob(j); setPage('detail'); }} />
            )}

            {page === 'detail' && selectedJob && (
              <JobDetailPage job={selectedJob}
                onBack={() => setPage('browse')}
                onApply={() => setPage('apply')} />
            )}

            {page === 'apply' && selectedJob && (
              <ApplyPage job={selectedJob}
                onBack={() => setPage('detail')}
                onSuccess={goSuccess} />
            )}

            {page === 'track' && <TrackPage initialQuery={trackId} />}

            {page === 'success' && successData && (
              <SuccessPage data={successData}
                onTrack={(id) => { setTrackId(id || ''); setPage('track'); }}
                onBrowse={() => { setPage('browse'); setJob(null); }} />
            )}

          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Success Page ─────────────────────────────────────────────────
function SuccessPage({ data, onTrack, onBrowse }) {
  const { trackingId, form, job } = data;

  return (
    <div style={{ maxWidth: '540px', margin: '0 auto', padding: '60px 24px 100px',
      textAlign: 'center' }}>
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15 }}
        style={{ fontSize: '72px', marginBottom: '16px' }}>
        ✅
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        style={{ ...fonts.h1, marginBottom: '10px' }}>
        <GradientText>Application Received!</GradientText>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        style={{ ...fonts.body, color: theme.textSecondary, marginBottom: '28px' }}>
        Hi {form?.name}, your application for <strong>{job?.title}</strong> is in.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.4 }}>
        <GlassCard hover={false} glow style={{ marginBottom: '24px' }}>
          <div style={{ ...fonts.caption, color: theme.textTertiary, marginBottom: '8px' }}>
            Your Tracking ID
          </div>
          <div style={{ ...fonts.h1, letterSpacing: '2px' }}>
            <GradientText>{trackingId}</GradientText>
          </div>
          <div style={{ fontSize: '12px', color: theme.textTertiary, marginTop: '10px' }}>
            📧 A confirmation has been sent to {form?.email}
          </div>
        </GlassCard>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}>
        <GlassCard hover={false} style={{ marginBottom: '24px', textAlign: 'left' }}>
          <div style={{ ...fonts.caption, color: theme.textTertiary, marginBottom: '12px' }}>
            What Happens Next
          </div>
          {[
            '🤖 AI reviews your resume within 1 hour',
            '🎯 AI interview link sent to your email',
            '👤 Human interview if shortlisted',
            '📧 Offer or detailed feedback within 3 days',
          ].map((s, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + i * 0.1 }}
              style={{ fontSize: '14px', color: theme.textSecondary,
                marginBottom: '8px' }}>
              {s}
            </motion.div>
          ))}
        </GlassCard>
      </motion.div>

      <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
        <AuroraButton onClick={() => onTrack(trackingId)}>Track My Application →</AuroraButton>
        <AuroraButton variant="ghost" onClick={onBrowse}>Browse More Jobs</AuroraButton>
      </div>
    </div>
  );
}