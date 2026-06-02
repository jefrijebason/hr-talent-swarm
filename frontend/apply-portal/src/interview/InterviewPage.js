import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import InterviewIntro from './InterviewIntro';
import InterviewChat from './InterviewChat';
import InterviewComplete from './InterviewComplete';

export default function InterviewPage({
  candidateName = 'Arjun',
  roleName = 'Senior AI Engineer',
  roundsTotal = 3,
  resumeCount = 0,
  currentRound = 1,
}) {
  const [phase, setPhase]     = useState('intro');
  // intro | chat | complete
  const [answers, setAnswers] = useState([]);

  // Determine intro mode
  const getIntroMode = () => {
    if (resumeCount >= 1) return 'locked';
    if (currentRound > 1) return 'resume';
    return 'fresh';
  };

  const handleBegin = () => setPhase('chat');

  const handleComplete = (finalAnswers) => {
    setAnswers(finalAnswers);
    setPhase('complete');
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