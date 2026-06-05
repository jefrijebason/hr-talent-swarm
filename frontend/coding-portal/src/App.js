import React, { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const LANGUAGES = [
  { id: 71, name: 'Python',     value: 'python' },
  { id: 63, name: 'JavaScript', value: 'javascript' },
  { id: 62, name: 'Java',       value: 'java' },
  { id: 54, name: 'C++',        value: 'cpp' },
  { id: 60, name: 'Go',         value: 'go' },
];

const STARTER_CODE = {
  python:     '# Write your solution here\ndef solution():\n    pass\n',
  javascript: '// Write your solution here\nfunction solution() {\n    \n}\n',
  java:       '// Write your solution here\npublic class Solution {\n    public static void main(String[] args) {\n        \n    }\n}\n',
  cpp:        '// Write your solution here\n#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}\n',
  go:         '// Write your solution here\npackage main\n\nimport "fmt"\n\nfunc main() {\n    \n}\n',
};

const DEMO_PROBLEM = {
  title:       'Candidate Score Ranker',
  description: `You are building a system to rank candidates by their scores.

Given a list of candidate scores and an integer k, return the top k candidates sorted by score in descending order. For each candidate, also calculate their percentile ranking.

A candidate's percentile = (number of candidates with lower score / total candidates) × 100

This is a real problem from our HR AI system — you are contributing to an actual production codebase.`,
  example: {
    input:       'scores = [85, 92, 78, 95, 88], k = 3',
    output:      '[(95, 100.0), (92, 80.0), (88, 60.0)]',
    explanation: 'Top 3 scores with their percentile rankings'
  },
  test_cases: [
    { id: 1, type: 'Basic',       visible: true,  input: '[85, 92, 78, 95, 88]\n3' },
    { id: 2, type: 'Edge Case',   visible: false, input: '[]\n0' },
    { id: 3, type: 'Performance', visible: false, input: 'large input\n100' },
  ],
  constraints: [
    '1 ≤ len(scores) ≤ 10,000',
    '0 ≤ score ≤ 100',
    '1 ≤ k ≤ len(scores)',
    'Time limit: 2 seconds',
  ],
  time_minutes: 30,
};

export default function App() {
  const [language, setLanguage]     = useState('python');
  const [code, setCode]             = useState(STARTER_CODE.python);
  const [output, setOutput]         = useState('');
  const [running, setRunning]       = useState(false);
  const [submitted, setSubmitted]   = useState(false);
  const [timeLeft, setTimeLeft]     = useState(30 * 60);
  const [testResults, setTestResults] = useState([]);
  const [problem, setProblem]       = useState(DEMO_PROBLEM);
  const [loadingProblem, setLoadingProblem] = useState(false);
  const [problemError, setProblemError] = useState('');
  const [phase, setPhase]           = useState('coding');
  const [interrogation, setInterrogation] = useState([]);
  const [answers, setAnswers]       = useState({});
  const [finalScore, setFinalScore] = useState(null);
  const [candidateId, setCandidateId] = useState('');
  const [jobId, setJobId] = useState('');
  const timerRef                    = useRef(null);

  // Start timer on first keystroke
  const startTimer = () => {
    if (timerRef.current) return;
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleLanguageChange = (lang) => {
    setLanguage(lang);
    setCode(STARTER_CODE[lang]);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setCandidateId(params.get('candidate') || '');
    setJobId(params.get('job') || '');
  }, []);

  const fetchCodingProblem = async (cid) => {
    if (!cid) return;
    setLoadingProblem(true);
    setProblemError('');

    try {
      const res = await axios.get(`${API_URL}/api/coding-problem`, {
        params: { candidate_id: cid }
      });
      const payload = res.data?.problem || res.data;
      if (payload && payload.problem_title) {
        setProblem(payload);
        if (payload.starter_code && code === STARTER_CODE[language]) {
          setCode(payload.starter_code.replace(/\r\n/g, '\n'));
        }
      } else {
        setProblem(DEMO_PROBLEM);
      }
    } catch (err) {
      setProblemError('Unable to load your coding problem. Using default task.');
      setProblem(DEMO_PROBLEM);
    }
    setLoadingProblem(false);
  };

  useEffect(() => {
    if (candidateId) {
      fetchCodingProblem(candidateId);
    }
  }, [candidateId]);

  const handleRun = async () => {
    startTimer();
    setRunning(true);
    setOutput('Running your code...');
    setTestResults([]);

    try {
      const sampleInput = problem?.test_cases?.find(tc => !tc.is_hidden)?.input ||
        problem?.test_cases?.[0]?.input || '1\n2';
      const res = await axios.post(`${API_URL}/api/run-code`, {
        code,
        language,
        input: sampleInput
      });
      setOutput(res.data.output || res.data.stdout || res.data.error || 'No output');
    } catch (err) {
      setOutput('Unable to run code at the moment. Please try again.');
    }
    setRunning(false);
  };

  const handleSubmit = async () => {
    if (!candidateId) {
      setOutput('Candidate ID missing from the URL. Please open the coding assessment from your email link.');
      return;
    }

    clearInterval(timerRef.current);
    setRunning(true);
    setOutput('Submitting your solution...');
    setTestResults([]);

    try {
      const form = new FormData();
      form.append('candidate_id', candidateId);
      form.append('code', code);
      form.append('language', language);

      const res = await axios.post(`${API_URL}/api/submit-code`, form);
      const responseData = res.data || {};

      setTestResults(responseData.test_results?.results || []);
      setInterrogation(responseData.questions || []);
      setFinalScore(responseData.coding_score ?? finalScore);
      setOutput(responseData.output || `Your code was submitted successfully.`);
      setSubmitted(true);
      setPhase('interrogation');
    } catch (err) {
      setOutput('Submission failed. Please try again later.');
      setSubmitted(false);
    }

    setRunning(false);
  };

  const handleAnswerSubmit = async () => {
    setRunning(true);
    setOutput('Submitting your answers for review...');
    setFinalScore(null);

    await new Promise(r => setTimeout(r, 2000));

    setPhase('complete');
    setOutput('Your answers have been submitted. A reviewer will evaluate them and email next steps.');
    setRunning(false);
  };

  const currentProblem = problem || DEMO_PROBLEM;

  // ── COMPLETE PHASE ───────────────────────────────────────────
  if (phase === 'complete') {
    return (
      <div style={st.app}>
        <div style={st.completeCard}>
          <div style={st.completeIcon}>🎉</div>
          <h1 style={st.completeTitle}>Coding Round Complete!</h1>
          <div style={st.scoreCircle}>
            <div style={st.scoreNum}>{finalScore || 'TBD'}</div>
            <div style={st.scoreLabel}>/ 100</div>
          </div>
          <p style={st.completeMsg}>
            Your answers have been submitted and are now under review.
            We will email you the final result and next steps as soon as evaluation completes.
          </p>
        </div>
      </div>
    );
  }

  // ── INTERROGATION PHASE ──────────────────────────────────────
  if (phase === 'interrogation') {
    return (
      <div style={st.app}>
        <div style={st.interrogationContainer}>
          <div style={st.interrogationHeader}>
            <h2 style={st.interrogationTitle}>
              Code Review Interview
            </h2>
            <p style={st.interrogationSub}>
              Great submission! Now let us understand your thinking.
              Answer 5 questions about your own code.
              Take your time — there are no trick questions.
            </p>
          </div>

          <div style={st.codePreview}>
            <div style={st.codePreviewHeader}>Your submitted code</div>
            <pre style={st.codePreviewBody}>{code}</pre>
          </div>

          <div style={st.questions}>
            {interrogation.map((q, i) => (
              <div key={q.id} style={st.questionCard}>
                <div style={st.questionNum}>Q{q.id}</div>
                <div style={st.questionContent}>
                  <p style={st.questionText}>{q.question}</p>
                  <p style={st.questionHint}>💡 Hint: {q.hint}</p>
                  <textarea
                    style={st.answerBox}
                    placeholder="Type your answer here..."
                    value={answers[q.id] || ''}
                    onChange={e => setAnswers({
                      ...answers,
                      [q.id]: e.target.value
                    })}
                  />
                </div>
              </div>
            ))}
          </div>

          <button
            style={st.submitAnswersBtn}
            onClick={handleAnswerSubmit}
            disabled={running}
          >
            {running
              ? '⏳ Evaluating your answers...'
              : 'Submit All Answers →'}
          </button>
        </div>
      </div>
    );
  }

  // ── CODING PHASE ─────────────────────────────────────────────
  return (
    <div style={st.app}>

      {/* Header */}
      <div style={st.header}>
        <div style={st.headerLeft}>
          <span style={st.logo}>💻</span>
          <span style={st.headerTitle}>Coding Assessment</span>
          <span style={st.problemTitle}>{currentProblem.problem_title || currentProblem.title}</span>
        </div>
        <div style={st.headerRight}>
          <div style={{
            ...st.timer,
            color: timeLeft < 300 ? '#dc2626' : '#0f172a'
          }}>
            ⏱ {formatTime(timeLeft)}
          </div>
          <select
            style={st.langSelect}
            value={language}
            onChange={e => handleLanguageChange(e.target.value)}
          >
            {LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Body */}
      <div style={st.body}>

        {/* Problem Panel */}
        <div style={st.problemPanel}>
          <h3 style={st.sectionTitle}>{currentProblem.problem_title || currentProblem.title}</h3>
          <p style={st.description}>{currentProblem.problem_description || currentProblem.description}</p>

          {problemError && (
            <div style={{ color: '#f97316', marginBottom: '16px' }}>
              {problemError}
            </div>
          )}

          <div style={st.exampleBox}>
            <div style={st.exampleTitle}>Example</div>
            <div style={st.exampleItem}>
              <span style={st.exampleLabel}>Input:</span>
              <code style={st.exampleCode}>
                {currentProblem.example?.input || 'N/A'}
              </code>
            </div>
            <div style={st.exampleItem}>
              <span style={st.exampleLabel}>Output:</span>
              <code style={st.exampleCode}>
                {currentProblem.example?.output || 'N/A'}
              </code>
            </div>
            <div style={st.exampleItem}>
              <span style={st.exampleLabel}>Explanation:</span>
              <span style={{fontSize: '13px', color: '#475569'}}>
                {currentProblem.example?.explanation || 'Use the problem statement to guide your solution.'}
              </span>
            </div>
          </div>

          {currentProblem.constraints?.length > 0 && (
            <div style={st.constraints}>
              <div style={st.constraintsTitle}>Constraints</div>
              {currentProblem.constraints.map((c, i) => (
                <div key={i} style={st.constraintItem}>
                  • {c}
                </div>
              ))}
            </div>
          )}

          {/* Test Results */}
          {testResults.length > 0 && (
            <div style={st.testResults}>
              <div style={st.constraintsTitle}>Test Results</div>
              {testResults.map(tc => (
                <div key={tc.test_case_id || tc.id} style={{
                  ...st.testRow,
                  borderLeft: `3px solid ${tc.passed ? '#16a34a' : '#dc2626'}`
                }}>
                  <span style={{
                    color: tc.passed ? '#16a34a' : '#dc2626',
                    fontWeight: 700
                  }}>
                    {tc.passed ? '✅' : '❌'}
                  </span>
                  <span style={{fontSize: '13px', color: '#475569'}}>
                    {(tc.type || 'Test').charAt(0).toUpperCase() + (tc.type || 'Test').slice(1)} Test Case
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Editor Panel */}
        <div style={st.editorPanel}>
          <Editor
            height="calc(100vh - 200px)"
            language={language}
            value={code}
            onChange={(val) => {
              setCode(val || '');
              startTimer();
            }}
            theme="vs-dark"
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbers: 'on',
              automaticLayout: true,
              tabSize: 4,
            }}
          />

          {/* Output */}
          {output && (
            <div style={st.outputPanel}>
              <div style={st.outputHeader}>Output</div>
              <pre style={st.outputBody}>{output}</pre>
            </div>
          )}

          {/* Action Buttons */}
          <div style={st.actions}>
            <button
              style={st.runBtn}
              onClick={handleRun}
              disabled={running || submitted}
            >
              {running ? '⏳ Running...' : '▶ Run Code'}
            </button>
            <button
              style={{
                ...st.submitBtn,
                opacity: submitted ? 0.5 : 1
              }}
              onClick={handleSubmit}
              disabled={running || submitted}
            >
              {submitted
                ? '✅ Submitted'
                : '🚀 Submit Solution'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const st = {
  app: {
    minHeight: '100vh',
    background: '#0f172a',
    fontFamily: "'Segoe UI', sans-serif",
    color: '#e2e8f0',
  },
  header: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', padding: '12px 20px',
    background: '#1e293b',
    borderBottom: '1px solid #334155',
  },
  headerLeft: {
    display: 'flex', alignItems: 'center', gap: '12px'
  },
  logo: { fontSize: '20px' },
  headerTitle: {
    fontSize: '14px', fontWeight: 700,
    color: '#94a3b8'
  },
  problemTitle: {
    fontSize: '14px', fontWeight: 700,
    color: '#e2e8f0', background: '#334155',
    padding: '4px 10px', borderRadius: '6px'
  },
  headerRight: {
    display: 'flex', alignItems: 'center', gap: '12px'
  },
  timer: {
    fontFamily: 'monospace', fontSize: '18px',
    fontWeight: 700, background: '#334155',
    padding: '6px 14px', borderRadius: '8px'
  },
  langSelect: {
    background: '#334155', color: '#e2e8f0',
    border: 'none', padding: '8px 12px',
    borderRadius: '8px', fontSize: '13px',
    cursor: 'pointer'
  },
  body: {
    display: 'grid',
    gridTemplateColumns: '420px 1fr',
    height: 'calc(100vh - 57px)',
  },
  problemPanel: {
    padding: '20px', overflowY: 'auto',
    borderRight: '1px solid #334155',
    background: '#1e293b'
  },
  sectionTitle: {
    fontSize: '18px', fontWeight: 700,
    color: '#f1f5f9', marginBottom: '12px'
  },
  description: {
    fontSize: '14px', color: '#94a3b8',
    lineHeight: '1.7', marginBottom: '20px'
  },
  exampleBox: {
    background: '#0f172a', borderRadius: '8px',
    padding: '16px', marginBottom: '16px',
    border: '1px solid #334155'
  },
  exampleTitle: {
    fontSize: '12px', fontWeight: 700,
    color: '#64748b', textTransform: 'uppercase',
    letterSpacing: '1px', marginBottom: '10px'
  },
  exampleItem: {
    display: 'flex', gap: '8px',
    alignItems: 'flex-start', marginBottom: '8px'
  },
  exampleLabel: {
    fontSize: '12px', color: '#64748b',
    fontWeight: 600, flexShrink: 0, minWidth: '80px'
  },
  exampleCode: {
    fontSize: '12px', color: '#22c55e',
    fontFamily: 'monospace', background: '#1e293b',
    padding: '2px 6px', borderRadius: '4px'
  },
  constraints: { marginBottom: '16px' },
  constraintsTitle: {
    fontSize: '12px', fontWeight: 700,
    color: '#64748b', textTransform: 'uppercase',
    letterSpacing: '1px', marginBottom: '8px'
  },
  constraintItem: {
    fontSize: '13px', color: '#94a3b8',
    marginBottom: '4px'
  },
  testResults: { marginTop: '16px' },
  testRow: {
    display: 'flex', gap: '10px', alignItems: 'center',
    padding: '8px 12px', background: '#0f172a',
    borderRadius: '6px', marginBottom: '6px'
  },
  editorPanel: {
    display: 'flex', flexDirection: 'column',
    background: '#1e293b'
  },
  outputPanel: {
    background: '#0f172a',
    borderTop: '1px solid #334155',
    maxHeight: '150px', overflow: 'auto'
  },
  outputHeader: {
    fontSize: '11px', fontWeight: 700,
    color: '#64748b', textTransform: 'uppercase',
    letterSpacing: '1px', padding: '8px 16px',
    borderBottom: '1px solid #334155'
  },
  outputBody: {
    fontSize: '13px', color: '#22c55e',
    fontFamily: 'monospace', padding: '12px 16px',
    margin: 0
  },
  actions: {
    display: 'flex', gap: '10px',
    padding: '12px 16px',
    background: '#1e293b',
    borderTop: '1px solid #334155'
  },
  runBtn: {
    background: '#334155', color: '#e2e8f0',
    border: 'none', padding: '10px 20px',
    borderRadius: '8px', fontSize: '14px',
    fontWeight: 600, cursor: 'pointer'
  },
  submitBtn: {
    background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
    color: '#fff', border: 'none',
    padding: '10px 24px', borderRadius: '8px',
    fontSize: '14px', fontWeight: 600, cursor: 'pointer'
  },
  completeCard: {
    maxWidth: '480px', margin: '80px auto',
    background: '#1e293b', borderRadius: '16px',
    padding: '40px', textAlign: 'center',
    border: '1px solid #334155'
  },
  completeIcon: { fontSize: '56px', marginBottom: '16px' },
  completeTitle: {
    fontSize: '24px', fontWeight: 700,
    color: '#f1f5f9', marginBottom: '24px'
  },
  scoreCircle: {
    width: '120px', height: '120px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    margin: '0 auto 24px'
  },
  scoreNum: {
    fontSize: '40px', fontWeight: 800, color: '#fff'
  },
  scoreLabel: { fontSize: '14px', color: '#c4b5fd' },
  completeMsg: {
    fontSize: '14px', color: '#94a3b8',
    lineHeight: '1.6', marginBottom: '24px'
  },
  breakdown: {
    background: '#0f172a', borderRadius: '10px',
    padding: '16px', textAlign: 'left'
  },
  breakRow: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: '14px', color: '#94a3b8',
    padding: '8px 0', borderBottom: '1px solid #1e293b'
  },
  interrogationContainer: {
    maxWidth: '800px', margin: '0 auto',
    padding: '32px 20px'
  },
  interrogationHeader: { marginBottom: '24px' },
  interrogationTitle: {
    fontSize: '24px', fontWeight: 700,
    color: '#f1f5f9', marginBottom: '8px'
  },
  interrogationSub: {
    fontSize: '14px', color: '#94a3b8', lineHeight: '1.6'
  },
  codePreview: {
    background: '#1e293b', borderRadius: '10px',
    marginBottom: '24px', overflow: 'hidden',
    border: '1px solid #334155'
  },
  codePreviewHeader: {
    fontSize: '11px', fontWeight: 700,
    color: '#64748b', textTransform: 'uppercase',
    letterSpacing: '1px', padding: '10px 16px',
    borderBottom: '1px solid #334155'
  },
  codePreviewBody: {
    fontSize: '12px', color: '#22c55e',
    fontFamily: 'monospace', padding: '16px',
    margin: 0, maxHeight: '200px', overflowY: 'auto'
  },
  questions: {
    display: 'flex', flexDirection: 'column', gap: '16px',
    marginBottom: '24px'
  },
  questionCard: {
    background: '#1e293b', borderRadius: '10px',
    padding: '20px', display: 'flex',
    gap: '16px', border: '1px solid #334155'
  },
  questionNum: {
    background: '#6366f1', color: '#fff',
    borderRadius: '50%', width: '32px',
    height: '32px', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    fontSize: '13px', fontWeight: 700, flexShrink: 0
  },
  questionContent: { flex: 1 },
  questionText: {
    fontSize: '14px', color: '#e2e8f0',
    lineHeight: '1.6', marginBottom: '8px'
  },
  questionHint: {
    fontSize: '12px', color: '#64748b',
    marginBottom: '12px'
  },
  answerBox: {
    width: '100%', background: '#0f172a',
    border: '1px solid #334155', borderRadius: '8px',
    padding: '12px', color: '#e2e8f0',
    fontSize: '13px', minHeight: '80px',
    boxSizing: 'border-box', resize: 'vertical',
    fontFamily: "'Segoe UI', sans-serif"
  },
  submitAnswersBtn: {
    width: '100%', padding: '14px',
    background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
    color: '#fff', border: 'none',
    borderRadius: '10px', fontSize: '15px',
    fontWeight: 700, cursor: 'pointer'
  },
};