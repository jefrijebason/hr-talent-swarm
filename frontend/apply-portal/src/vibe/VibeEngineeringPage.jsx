/**
 * VibeEngineeringPage.jsx
 *
 * AI-augmented coding challenge for HR Swarm.
 *
 * Features:
 *  - Monaco editor (left/center)
 *  - Pyodide for in-browser Python execution (no backend code-exec needed)
 *  - AI assistant chat panel (right) — every interaction logged on backend
 *  - Test runner with pass/fail display
 *  - Submit → backend GPT-4o evaluator → pass/fail
 *  - 30-min countdown timer with auto-submit
 *
 * Required deps in apply-portal:
 *   npm install @monaco-editor/react
 *
 * Pyodide loads from CDN — no install needed.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Editor from '@monaco-editor/react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const PYODIDE_VERSION = '0.26.2';
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

export default function VibeEngineeringPage({ candidateId, candidateName = 'there' }) {
  const [stage, setStage] = useState('loading');   // loading | ready | running | submitting | done
  const [problem, setProblem] = useState(null);
  const [code, setCode] = useState('');
  const [output, setOutput] = useState('');
  const [testResults, setTestResults] = useState([]);
  const [aiMessages, setAiMessages] = useState([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [remaining, setRemaining] = useState(30 * 60);
  const [evaluation, setEvaluation] = useState(null);
  const [error, setError] = useState(null);

  const pyodideRef = useRef(null);
  const chatScrollRef = useRef(null);

  /* ────────────────────────────────────────────────────────────────
     1. Load Pyodide + start session
  ──────────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (!candidateId) {
      setError('Missing candidate ID. Check your invitation link.');
      return;
    }
    (async () => {
      try {
        // Load Pyodide
        if (!window.loadPyodide) {
          await new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = `${PYODIDE_CDN}pyodide.js`;
            s.onload = resolve; s.onerror = reject;
            document.head.appendChild(s);
          });
        }
        pyodideRef.current = await window.loadPyodide({ indexURL: PYODIDE_CDN });

        // Start backend session
        const r = await fetch(`${API_BASE}/api/vibe/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate_id: candidateId }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Failed to start');

        setProblem(data.problem);
        setCode(data.problem.starter_code);
        setRemaining(data.remaining_seconds || data.problem.time_limit_minutes * 60);
        setStage('ready');
      } catch (e) {
        setError(e.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

  /* ────────────────────────────────────────────────────────────────
     2. Countdown timer
  ──────────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (stage !== 'ready' && stage !== 'running') return;
    if (remaining <= 0) {
      handleSubmit();
      return;
    }
    const t = setInterval(() => setRemaining(r => Math.max(0, r - 1)), 1000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, remaining]);

  /* ────────────────────────────────────────────────────────────────
     3. Periodic code snapshot (every 60s)
  ──────────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (stage !== 'ready' || !candidateId) return;
    const t = setInterval(() => {
      fetch(`${API_BASE}/api/vibe/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_id: candidateId, code }),
      }).catch(() => {});
    }, 60000);
    return () => clearInterval(t);
  }, [stage, candidateId, code]);

  /* ────────────────────────────────────────────────────────────────
     4. Auto-scroll AI chat
  ──────────────────────────────────────────────────────────────── */
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [aiMessages]);

  /* ────────────────────────────────────────────────────────────────
     5. Run code + tests
  ──────────────────────────────────────────────────────────────── */
  const runCode = useCallback(async () => {
    if (!pyodideRef.current) return;
    setOutput('Running...\n');
    setStage('running');
    let outputs = [];
    const results = [];

    try {
      // Capture stdout
      pyodideRef.current.runPython(`
import sys, io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()
`);

      // Run user code first
      try {
        pyodideRef.current.runPython(code);
        outputs.push('✓ Code compiled');
      } catch (err) {
        outputs.push(`✗ Code error: ${err.message}`);
        const captured = pyodideRef.current.runPython('sys.stdout.getvalue()');
        if (captured) outputs.push(captured);
        pyodideRef.current.runPython('sys.stdout = _old_stdout');
        setOutput(outputs.join('\n'));
        setStage('ready');
        return;
      }

      // Run each visible test
      for (const test of problem.visible_tests) {
        try {
          // Reset stdout buffer per test
          pyodideRef.current.runPython('sys.stdout = io.StringIO()');
          pyodideRef.current.runPython(test.code);
          const out = pyodideRef.current.runPython('sys.stdout.getvalue()');
          results.push({ name: test.name, passed: true, output: out });
          outputs.push(`✓ ${test.name}`);
          if (out) outputs.push(`  ${out.trim()}`);
        } catch (err) {
          results.push({ name: test.name, passed: false, error: err.message });
          outputs.push(`✗ ${test.name}`);
          outputs.push(`  ${err.message.split('\n').slice(-3).join('\n  ')}`);
        }
      }

      pyodideRef.current.runPython('sys.stdout = _old_stdout');
    } catch (err) {
      outputs.push(`Runtime error: ${err.message}`);
    }

    setOutput(outputs.join('\n'));
    setTestResults(results);
    setStage('ready');
  }, [code, problem]);

  /* ────────────────────────────────────────────────────────────────
     6. AI assistant
  ──────────────────────────────────────────────────────────────── */
  const askAI = useCallback(async () => {
    if (!aiInput.trim() || aiLoading) return;
    const userMsg = aiInput.trim();
    setAiInput('');
    setAiMessages(m => [...m, { role: 'user', content: userMsg }]);
    setAiLoading(true);

    try {
      const r = await fetch(`${API_BASE}/api/vibe/ai-help`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          message: userMsg,
          code_context: code,
        }),
      });
      const data = await r.json();
      setAiMessages(m => [...m, { role: 'assistant', content: data.response || data.detail }]);
    } catch (e) {
      setAiMessages(m => [...m, { role: 'assistant', content: `Error: ${e.message}` }]);
    }
    setAiLoading(false);
  }, [aiInput, aiLoading, candidateId, code]);

  /* ────────────────────────────────────────────────────────────────
     7. Submit
  ──────────────────────────────────────────────────────────────── */
  const handleSubmit = useCallback(async () => {
    if (stage === 'submitting' || stage === 'done') return;
    setStage('submitting');
    try {
      const r = await fetch(`${API_BASE}/api/vibe/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          final_code: code,
          test_results: testResults,
        }),
      });
      const data = await r.json();
      setEvaluation(data);
      setStage('done');
    } catch (e) {
      setError(e.message);
      setStage('ready');
    }
  }, [stage, candidateId, code, testResults]);

  /* ────────────────────────────────────────────────────────────────
     RENDER
  ──────────────────────────────────────────────────────────────── */
  if (error) return <ErrorScreen message={error} />;
  if (stage === 'loading' || !problem) return <LoadingScreen />;
  if (stage === 'done') return <ResultScreen evaluation={evaluation} />;

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const timeLow = remaining < 300;
  const passedCount = testResults.filter(t => t.passed).length;

  return (
    <div style={S.page}>
      {/* ─── TOP BAR ─── */}
      <div style={S.topBar}>
        <div style={S.brand}>
          <span style={S.brandMark}>◈</span>
          <div>
            <div style={S.brandTitle}>{problem.title}</div>
            <div style={S.brandSub}>Vibe Engineering Challenge</div>
          </div>
        </div>
        <div style={{ ...S.timer, color: timeLow ? '#e0758a' : '#5b8def' }}>
          ⏱ {String(mins).padStart(2,'0')}:{String(secs).padStart(2,'0')}
        </div>
        <button style={S.submitBtn} onClick={handleSubmit}
          disabled={stage === 'submitting'}>
          {stage === 'submitting' ? 'Evaluating...' : 'Submit ↗'}
        </button>
      </div>

      {/* ─── MAIN GRID ─── */}
      <div style={S.grid}>
        {/* LEFT: Problem statement */}
        <div style={S.leftPanel}>
          <div style={S.panelHeader}>Problem</div>
          <div style={S.problemText}>
            {problem.description.split('\n').map((line, i) => {
              const trimmed = line.trim();
              if (trimmed.startsWith('## ')) {
                return <h3 key={i} style={S.h3}>{trimmed.replace('## ', '')}</h3>;
              }
              if (trimmed.startsWith('# ')) {
                return <h2 key={i} style={S.h2}>{trimmed.replace('# ', '')}</h2>;
              }
              if (trimmed.startsWith('- ')) {
                return <li key={i} style={S.li}>{trimmed.replace('- ', '')}</li>;
              }
              return <p key={i} style={S.p}>{trimmed}</p>;
            })}
          </div>
        </div>

        {/* CENTER: Editor + Output */}
        <div style={S.center}>
          <div style={S.editorWrap}>
            <div style={S.panelHeader}>
              <span>solution.py</span>
              <button style={S.runBtn} onClick={runCode}
                disabled={stage === 'running'}>
                {stage === 'running' ? 'Running...' : '▶ Run Tests'}
              </button>
            </div>
            <Editor
              height="100%"
              defaultLanguage="python"
              value={code}
              onChange={v => setCode(v || '')}
              theme="vs-dark"
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                fontFamily: 'JetBrains Mono, Consolas, monospace',
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>

          <div style={S.outputWrap}>
            <div style={S.panelHeader}>
              <span>Test Output</span>
              <span style={S.testCount}>
                {testResults.length > 0 && `${passedCount}/${testResults.length} tests passing`}
              </span>
            </div>
            <pre style={S.output}>{output || '// Click "Run Tests" to see output'}</pre>
          </div>
        </div>

        {/* RIGHT: AI Assistant */}
        <div style={S.rightPanel}>
          <div style={S.panelHeader}>
            🤖 AI Assistant
            <span style={S.aiBadge}>{aiMessages.length} msgs</span>
          </div>
          <div style={S.chatLog} ref={chatScrollRef}>
            {aiMessages.length === 0 && (
              <div style={S.aiHint}>
                Ask anything. Strategic AI usage is part of your evaluation.
                <br/><br/>
                Example: <em>"What's wrong with the window-reset logic in my rate limiter?"</em>
              </div>
            )}
            {aiMessages.map((m, i) => (
              <div key={i} style={m.role === 'user' ? S.msgUser : S.msgAI}>
                <div style={S.msgRole}>{m.role === 'user' ? 'You' : 'AI'}</div>
                <div style={S.msgContent}>{m.content}</div>
              </div>
            ))}
            {aiLoading && <div style={S.msgAI}><div style={S.msgRole}>AI</div><div style={S.msgContent}>...thinking</div></div>}
          </div>
          <div style={S.chatInputWrap}>
            <textarea
              style={S.chatInput}
              value={aiInput}
              onChange={e => setAiInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  askAI();
                }
              }}
              placeholder="Ask the AI anything (Enter to send, Shift+Enter for newline)"
              rows={3}
            />
            <button style={S.askBtn} onClick={askAI} disabled={aiLoading || !aiInput.trim()}>
              {aiLoading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


/* ════ Loading / error / result screens ════ */
function LoadingScreen() {
  return (
    <div style={S.fullCenter}>
      <div style={S.orb}>◈</div>
      <h2 style={{ color: '#eaeef6', fontFamily: 'Bricolage Grotesque' }}>
        Loading challenge...
      </h2>
      <p style={{ color: '#92a0ba' }}>Spinning up Python in your browser (~10 sec first time)</p>
    </div>
  );
}

function ErrorScreen({ message }) {
  return (
    <div style={S.fullCenter}>
      <div style={{ ...S.orb, color: '#e0758a' }}>✕</div>
      <h2 style={{ color: '#eaeef6' }}>Something went wrong</h2>
      <p style={{ color: '#92a0ba', maxWidth: 500, textAlign: 'center' }}>{message}</p>
    </div>
  );
}

function ResultScreen({ evaluation }) {
  if (!evaluation) return <LoadingScreen />;
  const passed = evaluation.passed;
  const score = evaluation.overall_score || 0;
  const color = passed ? '#4ade80' : '#e0758a';
  return (
    <div style={S.fullCenter}>
      <div style={{ ...S.orb, color, borderColor: color + '44' }}>
        {passed ? '✓' : '✕'}
      </div>
      <h1 style={{ color, fontFamily: 'Bricolage Grotesque', margin: '12px 0' }}>
        {passed ? 'Challenge Passed!' : 'Thanks for trying'}
      </h1>
      <div style={{
        fontSize: 56, fontWeight: 800, color, fontFamily: 'JetBrains Mono',
      }}>
        {score}<span style={{ fontSize: 24, color: '#92a0ba' }}>/100</span>
      </div>
      <p style={{ color: '#92a0ba', maxWidth: 600, textAlign: 'center',
                  fontSize: 14, lineHeight: 1.7, marginTop: 16 }}>
        {evaluation.feedback}
      </p>
      {evaluation.rubric_scores && (
        <div style={{ marginTop: 28, display: 'grid', gap: 8, width: 500 }}>
          {Object.entries(evaluation.rubric_scores).map(([k, v]) => (
            <div key={k} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '10px 14px', background: '#172033',
              borderRadius: 10, border: '1px solid rgba(255,255,255,.08)',
              fontSize: 13, color: '#92a0ba',
            }}>
              <span>{k.replace(/_/g, ' ')}</span>
              <span style={{ color: '#eaeef6', fontFamily: 'JetBrains Mono',
                             fontWeight: 700 }}>{v.score}/100</span>
            </div>
          ))}
        </div>
      )}
      {passed && (
        <p style={{ color: '#5b8def', marginTop: 24, fontSize: 13 }}>
          ✓ Next step: AI interview link will arrive in your inbox shortly.
        </p>
      )}
    </div>
  );
}


/* ════ STYLES ════ */
const S = {
  page: {
    fontFamily: 'Sora, system-ui, sans-serif',
    background: '#080b12', color: '#eaeef6',
    minHeight: '100vh', display: 'flex', flexDirection: 'column',
  },
  topBar: {
    display: 'flex', alignItems: 'center', gap: 20,
    padding: '14px 24px', borderBottom: '1px solid rgba(255,255,255,.08)',
    background: 'rgba(13,18,29,.6)', backdropFilter: 'blur(12px)',
  },
  brand: { display: 'flex', alignItems: 'center', gap: 14, flex: 1 },
  brandMark: {
    width: 38, height: 38, borderRadius: 11,
    background: 'linear-gradient(135deg,#5b8def,#6db4f0)',
    display: 'grid', placeItems: 'center', fontSize: 20, color: '#fff',
  },
  brandTitle: { fontFamily: 'Bricolage Grotesque', fontWeight: 800,
                fontSize: 18, letterSpacing: '-0.02em' },
  brandSub: { fontSize: 10, color: '#5a667e', letterSpacing: '0.16em',
              textTransform: 'uppercase', fontFamily: 'JetBrains Mono' },
  timer: {
    fontFamily: 'JetBrains Mono', fontSize: 22, fontWeight: 700,
    padding: '8px 18px', borderRadius: 10,
    background: 'rgba(91,141,239,.1)', border: '1px solid rgba(91,141,239,.25)',
  },
  submitBtn: {
    background: 'linear-gradient(135deg,#5b8def,#3f6fd1)',
    color: '#fff', border: 'none', padding: '12px 28px', borderRadius: 11,
    fontWeight: 700, fontSize: 14, cursor: 'pointer', fontFamily: 'Sora',
    boxShadow: '0 8px 28px -8px rgba(91,141,239,0.6)',
  },
  grid: {
    flex: 1, display: 'grid',
    gridTemplateColumns: '320px 1fr 380px',
    gap: 1, background: 'rgba(255,255,255,.05)', overflow: 'hidden',
  },
  leftPanel: { background: '#0d121d', overflowY: 'auto' },
  center:    { background: '#0d121d', display: 'flex', flexDirection: 'column' },
  rightPanel:{ background: '#0d121d', display: 'flex', flexDirection: 'column' },
  panelHeader: {
    padding: '12px 16px', fontSize: 11, fontWeight: 700,
    color: '#92a0ba', letterSpacing: '0.1em', textTransform: 'uppercase',
    fontFamily: 'JetBrains Mono', borderBottom: '1px solid rgba(255,255,255,.05)',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  problemText: { padding: '14px 18px', fontSize: 13, lineHeight: 1.7, color: '#c9d2e1' },
  h2: { fontFamily: 'Bricolage Grotesque', fontWeight: 700, fontSize: 17,
        marginTop: 16, marginBottom: 8, color: '#eaeef6' },
  h3: { fontFamily: 'Bricolage Grotesque', fontWeight: 600, fontSize: 14,
        marginTop: 14, marginBottom: 6, color: '#5b8def',
        textTransform: 'uppercase', letterSpacing: '0.06em' },
  p: { marginBottom: 8 },
  li: { marginBottom: 4, marginLeft: 14, listStyle: 'disc' },
  editorWrap: { flex: 1, display: 'flex', flexDirection: 'column',
                borderBottom: '1px solid rgba(255,255,255,.05)' },
  outputWrap: { height: '30%', display: 'flex', flexDirection: 'column' },
  output: {
    flex: 1, padding: '12px 16px', margin: 0,
    fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
    color: '#c9d2e1', overflowY: 'auto', whiteSpace: 'pre-wrap',
  },
  runBtn: {
    background: 'rgba(91,141,239,.12)', color: '#5b8def',
    border: '1px solid rgba(91,141,239,.3)', padding: '5px 14px',
    borderRadius: 7, fontSize: 11, fontWeight: 700, cursor: 'pointer',
    fontFamily: 'JetBrains Mono', letterSpacing: '0.04em',
  },
  testCount: { color: '#5b8def', fontFamily: 'JetBrains Mono', fontSize: 10,
               letterSpacing: '0.05em' },
  chatLog: {
    flex: 1, overflowY: 'auto', padding: '12px 16px',
    display: 'flex', flexDirection: 'column', gap: 12,
  },
  aiHint: { color: '#5a667e', fontSize: 12, fontStyle: 'italic',
            lineHeight: 1.7, padding: 20, textAlign: 'center' },
  msgUser: { alignSelf: 'flex-end', maxWidth: '85%',
             background: 'rgba(91,141,239,.12)',
             border: '1px solid rgba(91,141,239,.25)',
             borderRadius: 11, padding: 10 },
  msgAI:   { alignSelf: 'flex-start', maxWidth: '85%',
             background: '#172033', border: '1px solid rgba(255,255,255,.08)',
             borderRadius: 11, padding: 10 },
  msgRole: { fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
             color: '#5a667e', textTransform: 'uppercase',
             fontFamily: 'JetBrains Mono', marginBottom: 4 },
  msgContent: { fontSize: 13, color: '#eaeef6', lineHeight: 1.6,
                whiteSpace: 'pre-wrap' },
  aiBadge: { background: '#172033', color: '#5b8def', padding: '2px 7px',
             borderRadius: 5, fontSize: 10, fontFamily: 'JetBrains Mono' },
  chatInputWrap: {
    padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,.05)',
    display: 'flex', gap: 8,
  },
  chatInput: {
    flex: 1, background: '#0d121d', color: '#eaeef6',
    border: '1px solid rgba(255,255,255,.08)', borderRadius: 10,
    padding: 10, fontSize: 13, fontFamily: 'Sora', resize: 'none',
    outline: 'none',
  },
  askBtn: {
    background: 'rgba(91,141,239,.15)', color: '#5b8def',
    border: '1px solid rgba(91,141,239,.3)', padding: '0 18px',
    borderRadius: 10, fontWeight: 700, fontSize: 12, cursor: 'pointer',
    fontFamily: 'JetBrains Mono',
  },
  fullCenter: {
    minHeight: '100vh', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    background: '#080b12', color: '#eaeef6',
    fontFamily: 'Sora, system-ui, sans-serif', padding: 24,
  },
  orb: {
    width: 80, height: 80, borderRadius: '50%',
    background: 'linear-gradient(135deg,#5b8def33,#6db4f033)',
    border: '2px solid rgba(91,141,239,.4)', color: '#5b8def',
    display: 'grid', placeItems: 'center', fontSize: 36,
    marginBottom: 20,
  },
};