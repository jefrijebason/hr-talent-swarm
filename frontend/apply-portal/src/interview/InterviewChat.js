import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AIIndicator from './AIOrb';
import { iTheme } from './interviewTheme';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function InterviewChat({
  roundsTotal = 3,
  onComplete,
  candidateName = 'there',
  roleName = 'Senior AI Engineer',
  candidateId = '',
}) {
  const [messages, setMessages]     = useState([]);
  const [input, setInput]           = useState('');
  const [aiState, setAiState]       = useState('idle');
  const [currentRound, setCurrentRound] = useState(1);
  const [isTyping, setIsTyping]     = useState(false);
  const [canSend, setCanSend]       = useState(false);
  const [allAnswers, setAllAnswers] = useState([]);
  const chatEndRef = useRef(null);
  const inputRef   = useRef(null);

  const QUESTIONS = [
    {
      round: 1,
      title: 'Your Experience',
      question: `Tell me about a project you're most proud of. What was the challenge, what did you build, and what was the impact?`,
      followUp: 'That sounds interesting. What was the most difficult technical decision you made during that project?',
    },
    {
      round: 2,
      title: 'Problem Solving',
      question: `Imagine you need to design a system that processes 10,000 resumes per hour and ranks candidates in real-time. Walk me through your approach.`,
      followUp: 'Good thinking. How would you handle a sudden spike to 100,000 resumes?',
    },
    {
      round: 3,
      title: 'Growth & Vision',
      question: `What's a technology or approach you've been exploring recently? Why does it excite you, and how would you apply it here?`,
      followUp: `That's a great perspective. Where do you see yourself contributing the most in your first 90 days?`,
    },
    {
      round: 4,
      title: 'Leadership',
      question: `Tell me about a time you disagreed with a team decision. How did you handle it, and what was the outcome?`,
      followUp: 'How do you approach mentoring junior developers?',
    },
    {
      round: 5,
      title: 'Culture & Values',
      question: `What does a great engineering culture look like to you? What's non-negotiable?`,
      followUp: 'If you could change one thing about how most companies hire, what would it be?',
    },
  ];

  const activeQuestions = QUESTIONS.slice(0, roundsTotal);

  useEffect(() => {
    // Start with first question after a warm delay
    const timer = setTimeout(() => {
      addAIMessage(
        `Great to have you here, ${candidateName}. Let's start with something you know best — yourself.`,
        () => {
          setTimeout(() => {
            addAIMessage(activeQuestions[0].question, () => setCanSend(true));
          }, 800);
        }
      );
    }, 600);
    return () => clearTimeout(timer);
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const addAIMessage = (text, onDone) => {
    setAiState('speaking');
    setIsTyping(true);
    setCanSend(false);

    // Simulate typing delay based on message length
    const delay = Math.min(1800, 600 + text.length * 8);

    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [...prev, { role: 'ai', text, time: new Date() }]);
      setAiState('listening');
      if (onDone) setTimeout(onDone, 300);
    }, delay);
  };

  const handleSend = () => {
    if (!input.trim() || !canSend) return;

    const answer = input.trim();
    setInput('');
    setCanSend(false);

    // Add user message
    setMessages(prev => [...prev, { role: 'user', text: answer, time: new Date() }]);
    setAiState('processing');

    const updatedAnswers = [...allAnswers, {
      round: currentRound,
      question: activeQuestions[currentRound - 1].question,
      answer,
    }];
    setAllAnswers(updatedAnswers);

    // Evaluate answer on backend in real-time
    (async () => {
      try {
        const fd = new FormData();
        fd.append('candidate_id', candidateId);
        fd.append('question', activeQuestions[currentRound - 1].question);
        fd.append('answer', answer);
        fd.append('round_num', currentRound.toString());
        
        const evalResponse = await fetch(`${API_URL}/api/ai-interview/evaluate-answer`, {
          method: 'POST',
          body: fd
        });
        const evalData = await evalResponse.json();
        console.log(`[ARIA] Round ${currentRound} evaluated:`, evalData);
      } catch (e) {
        console.log('[ARIA] Evaluation error (non-blocking):', e);
      }
    })();

    // Check if this was the follow-up answer (even answer in round)
    const messagesInRound = messages.filter(m => m.role === 'user').length + 1;
    const isFollowUp = messagesInRound % 2 === 0;

    if (isFollowUp && currentRound < roundsTotal) {
      // Move to next round
      setTimeout(() => {
        const encouragements = [
          'Thank you, that was really insightful.',
          'Great answer. I appreciate the depth.',
          'That tells me a lot, thank you.',
          'Really well explained.',
          'Wonderful, I can see your thinking clearly.',
        ];
        const enc = encouragements[Math.min(currentRound - 1, encouragements.length - 1)];
        const nextRound = currentRound + 1;
        setCurrentRound(nextRound);

        addAIMessage(enc, () => {
          setTimeout(() => {
            addAIMessage(
              `Let's move to round ${nextRound} — ${activeQuestions[nextRound - 1].title}.`,
              () => {
                setTimeout(() => {
                  addAIMessage(activeQuestions[nextRound - 1].question, () => setCanSend(true));
                }, 600);
              }
            );
          }, 500);
        });
      }, 1200);
    } else if (isFollowUp && currentRound === roundsTotal) {
      // Interview complete
      setTimeout(() => {
        addAIMessage(
          `Thank you so much, ${candidateName}. That was a genuinely enjoyable conversation. I've learned a lot about how you think. Your results will be ready in just a moment.`,
          () => {
            setTimeout(() => {
              onComplete(updatedAnswers);
            }, 1500);
          }
        );
      }, 1200);
    } else {
      // Ask follow-up
      setTimeout(() => {
        addAIMessage(activeQuestions[currentRound - 1].followUp, () => setCanSend(true));
      }, 1200);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const progress = ((currentRound - 1) / roundsTotal) * 100 +
    (canSend ? 0 : (1 / roundsTotal) * 50);

  return (
    <div style={s.wrap}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerLeft}>
          <AIIndicator state={aiState} size="small" />
          <div>
            <div style={s.headerTitle}>ARIA</div>
            <div style={s.headerSub}>
              {aiState === 'processing' ? 'Thinking...'
                : aiState === 'speaking' ? 'Typing...'
                : aiState === 'listening' ? 'Listening'
                : 'AI Interviewer'}
            </div>
          </div>
        </div>
        <div style={s.headerRight}>
          <span style={s.roundBadge}>
            Round {currentRound}/{roundsTotal}
          </span>
          <span style={s.roundTitle}>
            {activeQuestions[currentRound - 1]?.title}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div style={s.progressWrap}>
        <motion.div style={s.progressFill}
          animate={{ width: `${Math.min(progress, 100)}%` }}
          transition={{ duration: 0.5 }} />
      </div>

      {/* Chat area */}
      <div style={s.chatArea}>
        <div style={s.chatInner}>
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                style={{ display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: '14px' }}>
                <div style={msg.role === 'ai' ? s.aiBubble : s.userBubble}>
                  {msg.role === 'ai' && (
                    <div style={s.bubbleLabel}>ARIA</div>
                  )}
                  <div style={s.bubbleText}>{msg.text}</div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ display: 'flex', marginBottom: '14px' }}>
              <div style={{ ...s.aiBubble, padding: '14px 20px' }}>
                <div style={s.bubbleLabel}>ARIA</div>
                <div style={s.typingDots}>
                  {[0, 1, 2].map(i => (
                    <motion.span key={i}
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 0.8, repeat: Infinity,
                        delay: i * 0.2 }}
                      style={s.dot} />
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div style={s.inputArea}>
        <div style={s.inputWrap}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={canSend
              ? 'Type your answer... (Enter to send, Shift+Enter for new line)'
              : 'Waiting for ARIA...'}
            disabled={!canSend}
            rows={2}
            style={{
              ...s.input,
              opacity: canSend ? 1 : 0.5,
            }}
          />
          <motion.button
            onClick={handleSend}
            disabled={!canSend || !input.trim()}
            whileHover={canSend && input.trim() ? { scale: 1.05 } : {}}
            whileTap={canSend && input.trim() ? { scale: 0.95 } : {}}
            style={{
              ...s.sendBtn,
              opacity: canSend && input.trim() ? 1 : 0.3,
            }}>
            Send →
          </motion.button>
        </div>
        <div style={s.inputHint}>
          Take your time. Be specific with examples.
        </div>
      </div>
    </div>
  );
}

const s = {
  wrap: {
    height: '100vh', display: 'flex', flexDirection: 'column',
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    background: '#1e1e2e',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '14px 24px', background: '#ffffff',
    borderBottom: '1px solid #e7e5e4',
  },
  headerLeft: {
    display: 'flex', alignItems: 'center', gap: '12px',
  },
  headerTitle: {
    fontSize: '15px', fontWeight: 700, color: '#1c1917',
  },
  headerSub: {
    fontSize: '12px', color: '#a8a29e',
  },
  headerRight: {
    display: 'flex', alignItems: 'center', gap: '10px',
  },
  roundBadge: {
    background: 'rgba(79,70,229,0.08)', color: '#4f46e5',
    padding: '4px 12px', borderRadius: '100px',
    fontSize: '12px', fontWeight: 700,
  },
  roundTitle: {
    fontSize: '13px', color: '#57534e', fontWeight: 600,
  },
  progressWrap: {
    height: '3px', background: '#e7e5e4',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #4f46e5, #6366f1)',
    borderRadius: '0 2px 2px 0',
  },
  chatArea: {
    flex: 1, overflow: 'auto', padding: '24px',
    background: '#1e1e2e',
  },
  chatInner: {
    maxWidth: '680px', margin: '0 auto',
  },
  aiBubble: {
    maxWidth: '80%', padding: '16px 20px',
    background: '#ffffff', borderRadius: '18px 18px 18px 4px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
  },
  userBubble: {
    maxWidth: '80%', padding: '16px 20px',
    background: 'linear-gradient(135deg, #4f46e5, #6366f1)',
    borderRadius: '18px 18px 4px 18px',
    color: '#ffffff',
  },
  bubbleLabel: {
    fontSize: '11px', fontWeight: 700, color: '#a8a29e',
    textTransform: 'uppercase', letterSpacing: '0.5px',
    marginBottom: '6px',
  },
  bubbleText: {
    fontSize: '14px', lineHeight: 1.6, color: 'inherit',
  },
  typingDots: {
    display: 'flex', gap: '4px', alignItems: 'center', height: '20px',
  },
  dot: {
    width: '6px', height: '6px', borderRadius: '50%',
    background: '#6366f1', display: 'inline-block',
  },
  inputArea: {
    padding: '16px 24px 20px', background: '#ffffff',
    borderTop: '1px solid #e7e5e4',
  },
  inputWrap: {
    display: 'flex', gap: '10px', maxWidth: '680px', margin: '0 auto',
  },
  input: {
    flex: 1, padding: '12px 16px', borderRadius: '14px',
    border: '1.5px solid #e7e5e4', fontSize: '14px',
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    outline: 'none', resize: 'none', color: '#1c1917',
    background: '#f5f5f4',
    lineHeight: 1.5,
  },
  sendBtn: {
    padding: '12px 24px', borderRadius: '14px', border: 'none',
    background: 'linear-gradient(135deg, #4f46e5, #6366f1)',
    color: '#fff', fontSize: '14px', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
    alignSelf: 'flex-end',
  },
  inputHint: {
    maxWidth: '680px', margin: '8px auto 0',
    fontSize: '12px', color: '#a8a29e', textAlign: 'center',
  },
};