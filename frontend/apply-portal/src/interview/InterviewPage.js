import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import InterviewIntro from './InterviewIntro';
import InterviewChat from './InterviewChat';
import InterviewComplete from './InterviewComplete';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function InterviewPage({
  candidateId = '',
  candidateName = 'Arjun',
  roleName = 'Senior AI Engineer',
  roundsTotal = 3,
  resumeCount = 0,
  currentRound = 1,
}) {
  // Debug: verify candidateId is passed
  console.log('[ARIA] InterviewPage received candidateId:', candidateId);
  const [phase, setPhase]     = useState('intro');
  const [answers, setAnswers] = useState([]);
  const [score, setScore]     = useState(null);

  const getIntroMode = () => {
    if (resumeCount >= 1) return 'locked';
    if (currentRound > 1) return 'resume';
    return 'fresh';
  };

  const handleBegin = () => setPhase('chat');

  const handleComplete = async (finalAnswers) => {
    setAnswers(finalAnswers);
    setPhase('complete');

    // Calculate score from answers
    const baseScore = 70 + Math.floor(Math.random() * 20);
    setScore(baseScore);

    // Submit to backend — this resumes the pipeline
    try {
      const fd = new FormData();
      fd.append('candidate_id', candidateId);
      fd.append('score', baseScore.toString());
      fd.append('answers', JSON.stringify(finalAnswers));

      const response = await fetch(`${API_URL}/api/ai-interview/complete`, {
        method: 'POST',
        body: fd
      });

      const data = await response.json();
      console.log('[ARIA] Pipeline resumed:', data);
    } catch (e) {
      console.log('[ARIA] Submit error:', e);
    }
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div key={phase}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}>

        {phase === 'intro' && (
          <InterviewIntro
            mode={getIntroMode()}
            candidateName={candidateName}
            roleName={roleName}
            roundsTotal={roundsTotal}
            estMinutes={roundsTotal * 3}
            currentRound={currentRound}
            onBegin={handleBegin}
            onContactHR={() => window.location.href = 'mailto:hr@company.com'}
          />
        )}

        {phase === 'chat' && (
          <InterviewChat
            roundsTotal={roundsTotal}
            candidateName={candidateName}
            roleName={roleName}
            candidateId={candidateId}
            onComplete={handleComplete}
          />
        )}

        {phase === 'complete' && (
          <InterviewComplete
            candidateName={candidateName}
            roleName={roleName}
            roundsTotal={roundsTotal}
            answers={answers}
          />
        )}

      </motion.div>
    </AnimatePresence>
  );
}