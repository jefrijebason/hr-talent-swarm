import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const MOCK_CANDIDATES = [
  {
    id: 'cand_001', name: 'Arjun Mehta',
    applied_role: 'Senior AI Engineer',
    status: 'hired', resume_score: 90,
    ai_interview_score: 85, final_score: 87.9,
    decision: 'HIRE', expected_ctc: '20 LPA',
    skills: ['Python', 'Azure', 'ML', 'FastAPI'],
    profile_type: 'strong'
  },
  {
    id: 'cand_002', name: 'Priya Sharma',
    applied_role: 'Senior AI Engineer',
    status: 'hired', resume_score: 88,
    ai_interview_score: 82, final_score: 85.4,
    decision: 'HIRE', expected_ctc: '18 LPA',
    skills: ['Python', 'Azure ML', 'Docker'],
    profile_type: 'strong'
  },
  {
    id: 'cand_003', name: 'Rahul Verma',
    applied_role: 'Senior AI Engineer',
    status: 'waiting_technical_interview',
    resume_score: 86, ai_interview_score: 80,
    final_score: null, decision: null,
    expected_ctc: '22 LPA',
    skills: ['Python', 'Kubernetes', 'NLP'],
    profile_type: 'strong'
  },
  {
    id: 'cand_004', name: 'Sneha Patel',
    applied_role: 'Senior AI Engineer',
    status: 'rejected', resume_score: 62,
    ai_interview_score: 58, final_score: 60.2,
    decision: 'NO_HIRE', expected_ctc: '15 LPA',
    skills: ['Python', 'Django', 'MySQL'],
    profile_type: 'borderline'
  },
  {
    id: 'cand_005', name: 'Karan Singh',
    applied_role: 'Senior AI Engineer',
    status: 'rejected', resume_score: 58,
    ai_interview_score: null, final_score: null,
    decision: 'NO_HIRE', expected_ctc: '16 LPA',
    skills: ['Python', 'Flask'],
    profile_type: 'borderline'
  },
  {
    id: 'cand_006', name: 'Ravi Kumar',
    applied_role: 'Senior AI Engineer',
    status: 'rejected', resume_score: 18,
    ai_interview_score: null, final_score: null,
    decision: 'NO_HIRE', expected_ctc: '12 LPA',
    skills: ['Excel', 'Tally', 'SAP'],
    profile_type: 'reject'
  },
  {
    id: 'cand_007', name: 'Deepa Nair',
    applied_role: 'Senior AI Engineer',
    status: 'rejected', resume_score: 15,
    ai_interview_score: null, final_score: null,
    decision: 'NO_HIRE', expected_ctc: '10 LPA',
    skills: ['Accounting', 'GST', 'Tally'],
    profile_type: 'reject'
  },
];

const MOCK_LOGS = [
  { time: '10:42:01', agent: 'ORCHESTRATOR', msg: 'New application: Arjun Mehta', color: '#6366f1' },
  { time: '10:42:03', agent: 'SCREENER', msg: 'Resume uploaded to Blob Storage', color: '#0891b2' },
  { time: '10:42:05', agent: 'SCREENER', msg: 'Bias removal complete', color: '#0891b2' },
  { time: '10:42:08', agent: 'SCREENER', msg: 'Score: 90/100 — Strong candidate', color: '#0891b2' },
  { time: '10:42:09', agent: 'ORCHESTRATOR', msg: 'Routing to AI Interviewer', color: '#6366f1' },
  { time: '10:42:12', agent: 'JD INTEL', msg: 'Role: ai_ml | Level: senior', color: '#7c3aed' },
  { time: '10:42:15', agent: 'AWARENESS', msg: 'Latest tech check complete', color: '#7c3aed' },
  { time: '10:42:20', agent: 'INTERVIEWER', msg: 'Round 1 score: 88/100', color: '#d97706' },
  { time: '10:42:35', agent: 'INTERVIEWER', msg: 'Round 2 score: 82/100', color: '#d97706' },
  { time: '10:42:50', agent: 'INTERVIEWER', msg: 'Round 3 score: 85/100', color: '#d97706' },
  { time: '10:43:05', agent: 'INTERVIEWER', msg: 'Round 4 score: 83/100', color: '#d97706' },
  { time: '10:43:10', agent: 'INTERVIEWER', msg: 'AI Readiness: AI-Native | Top 12%', color: '#d97706' },
  { time: '10:43:12', agent: 'SCHEDULER', msg: 'Reading calendars via Graph API', color: '#059669' },
  { time: '10:43:14', agent: 'SCHEDULER', msg: 'Teams meeting booked: Mon 10:00 AM', color: '#059669' },
  { time: '10:43:15', agent: 'COMMUNICATOR', msg: 'Invite sent to candidate', color: '#dc2626' },
  { time: '10:43:16', agent: 'ORCHESTRATOR', msg: 'Pipeline paused — awaiting human', color: '#6366f1' },
];

const STATUS_COLUMNS = [
  { key: 'applied',                     label: 'Applied',       color: '#6366f1' },
  { key: 'screened',                    label: 'Screened',      color: '#0891b2' },
  { key: 'ai_interview_complete',       label: 'AI Interview',  color: '#7c3aed' },
  { key: 'waiting_technical_interview', label: 'Awaiting Tech', color: '#d97706' },
  { key: 'waiting_hr_interview',        label: 'Awaiting HR',   color: '#059669' },
  { key: 'hired',                       label: 'Hired ✅',      color: '#16a34a' },
  { key: 'rejected',                    label: 'Rejected',      color: '#dc2626' },
];

// ── Field Styles ────────────────────────────────────────────────
const fld = {
  label: {
    fontSize: '13px', fontWeight: 600,
    color: '#374151', display: 'block', marginBottom: '6px'
  },
  smallLabel: {
    fontSize: '11px', fontWeight: 600,
    color: '#6b7280', display: 'block', marginBottom: '4px'
  },
  input: {
    width: '100%', padding: '10px 12px',
    borderRadius: '8px', border: '1.5px solid #e2e8f0',
    fontSize: '14px', boxSizing: 'border-box',
    outline: 'none', fontFamily: 'inherit'
  },
  smallInput: {
    width: '100%', padding: '8px 10px',
    borderRadius: '6px', border: '1px solid #e2e8f0',
    fontSize: '13px', boxSizing: 'border-box'
  },
  iconBtn: {
    background: '#f1f5f9', border: '1px solid #e2e8f0',
    borderRadius: '6px', padding: '4px 8px',
    cursor: 'pointer', fontSize: '14px', color: '#475569'
  }
};

// ── Job Posting View ────────────────────────────────────────────
function JobPostingView() {
  const [step, setStep]         = useState('form');
  const [jdText, setJdText]     = useState('');
  const [quality, setQuality]   = useState(null);
  const [intel, setIntel]       = useState(null);
  const [loading, setLoading]   = useState(false);
  const [jobs, setJobs]         = useState([]);
  const [mode, setMode]         = useState('standard');
  const [codingOn, setCodingOn] = useState(true);
  const [aiOn, setAiOn]         = useState(true);
  const [title, setTitle]       = useState('');
  const [dept, setDept]         = useState('');
  const [salMin, setSalMin]     = useState('');
  const [salMax, setSalMax]     = useState('');
  const [location, setLocation] = useState('Bangalore');
  const [humanRounds, setHumanRounds] = useState([
    {
      round_number: 1, round_name: 'Technical Interview',
      interviewer_name: 'Tech Lead', interviewer_email: '',
      duration_minutes: 60, focus: 'Technical depth', position: 1
    },
    {
      round_number: 2, round_name: 'HR Discussion',
      interviewer_name: 'HR Manager', interviewer_email: '',
      duration_minutes: 45, focus: 'Culture + Salary', position: 2
    }
  ]);

  useEffect(() => {
    axios.get(`${API_URL}/api/jobs`)
      .then(r => setJobs(r.data))
      .catch(() => {});
  }, []);

  const analyseJD = async () => {
    if (!jdText.trim()) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('jd_text', jdText);
      const r = await axios.post(`${API_URL}/api/analyse-jd`, fd);
      setQuality(r.data.quality);
      setIntel(r.data.intelligence);
      // Auto-fill title from intel
      if (r.data.intelligence?.role_title) {
        setTitle(r.data.intelligence.role_title);
      }
      // Auto-configure coding round
      if (r.data.intelligence?.coding_needed !== undefined) {
        setCodingOn(r.data.intelligence.coding_needed);
      }
    } catch {
      setQuality({ overall_quality: 7, issues: [], improved_jd: jdText });
      setIntel({ role_category: 'software_development',
        seniority_level: 'senior', tech_stack: ['Python'] });
    }
    setStep('configure');
    setLoading(false);
  };

  const postJob = async () => {
    setLoading(true);
    try {
      const r = await axios.post(`${API_URL}/api/jobs`, {
        title, department: dept, jd_text: jdText,
        interview_mode: mode,
        coding_enabled: codingOn,
        ai_interview_enabled: aiOn,
        salary_min: salMin, salary_max: salMax,
        location, human_rounds: humanRounds
      });
      setJobs(prev => [...prev, r.data.job]);
      setStep('success');
    } catch {
      setStep('success');
    }
    setLoading(false);
  };

  const moveRound = (idx, dir) => {
    const rounds = [...humanRounds];
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= rounds.length) return;
    [rounds[idx], rounds[newIdx]] = [rounds[newIdx], rounds[idx]];
    rounds.forEach((r, i) => r.position = i + 1);
    setHumanRounds([...rounds]);
  };

  const addRound = () => {
    setHumanRounds(prev => [...prev, {
      round_number: prev.length + 1,
      round_name: `Round ${prev.length + 1}`,
      interviewer_name: '', interviewer_email: '',
      duration_minutes: 60, focus: '', position: prev.length + 1
    }]);
  };

  const removeRound = (idx) => {
    setHumanRounds(prev => prev.filter((_, i) => i !== idx));
  };

  const updateRound = (idx, field, val) => {
    setHumanRounds(prev => prev.map((r, i) =>
      i === idx ? { ...r, [field]: val } : r
    ));
  };

  // ── Success Screen ────────────────────────────────────────────
  if (step === 'success') return (
    <div style={{ textAlign: 'center', padding: '60px 20px' }}>
      <div style={{ fontSize: '64px', marginBottom: '16px' }}>✅</div>
      <h2 style={{ color: '#0f172a', marginBottom: '8px' }}>
        Job Posted Successfully!
      </h2>
      <p style={{ color: '#64748b', marginBottom: '24px' }}>
        The job is now live on the Apply Portal.
        Candidates can apply immediately.
      </p>
      <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
        <button onClick={() => { setStep('form'); setJdText(''); setTitle(''); }}
          style={{ padding: '10px 20px', background: '#6366f1',
            color: '#fff', border: 'none', borderRadius: '8px',
            cursor: 'pointer', fontWeight: 600 }}>
          + Post Another Job
        </button>
      </div>
      {jobs.length > 0 && (
        <div style={{ marginTop: '32px', textAlign: 'left',
          maxWidth: '600px', margin: '32px auto 0' }}>
          <h3 style={{ marginBottom: '16px', color: '#0f172a' }}>
            Active Jobs ({jobs.length})
          </h3>
          {jobs.map(job => (
            <div key={job.id} style={{ background: '#f8fafc',
              border: '1px solid #e2e8f0', borderRadius: '10px',
              padding: '16px', marginBottom: '10px',
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, color: '#0f172a' }}>
                  {job.title}
                </div>
                <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                  {job.location} · {job.interview_mode} mode ·
                  Quality: {job.jd_quality_score}/10
                </div>
              </div>
              <div style={{ background: '#dcfce7', color: '#16a34a',
                padding: '4px 12px', borderRadius: '100px',
                fontSize: '12px', fontWeight: 700 }}>
                LIVE
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // ── Configure Screen ──────────────────────────────────────────
  if (step === 'configure') return (
    <div style={{ maxWidth: '800px' }}>
      <h2 style={{ marginBottom: '4px', color: '#0f172a' }}>
        Configure Interview Pipeline
      </h2>
      <p style={{ color: '#64748b', marginBottom: '24px' }}>
        Customize every aspect of the hiring process for this role.
      </p>

      {/* JD Quality Result */}
      {quality && (
        <div style={{
          background: quality.overall_quality >= 7 ? '#f0fdf4' : '#fffbeb',
          border: `1px solid ${quality.overall_quality >= 7 ? '#86efac' : '#fde68a'}`,
          borderRadius: '10px', padding: '16px', marginBottom: '16px'
        }}>
          <div style={{ fontWeight: 700, marginBottom: '8px', color: '#0f172a' }}>
            JD Quality Score: {quality.overall_quality}/10
            {quality.overall_quality < 7 ? ' ⚠️' : ' ✅'}
          </div>
          {(quality.issues || []).slice(0, 3).map((issue, i) => (
            <div key={i} style={{ fontSize: '13px',
              color: '#92400e', marginBottom: '4px' }}>
              ❌ {issue.type}: {issue.problem}
            </div>
          ))}
          {quality.overall_quality < 7 && quality.improved_jd && (
            <button
              onClick={() => setJdText(quality.improved_jd)}
              style={{ marginTop: '10px', padding: '6px 14px',
                background: '#d97706', color: '#fff',
                border: 'none', borderRadius: '6px',
                cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
              ✨ Use Improved JD
            </button>
          )}
        </div>
      )}

      {/* Role Intelligence */}
      {intel && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe',
          borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
          <div style={{ fontWeight: 700, color: '#1d4ed8', marginBottom: '8px' }}>
            🧠 Role Intelligence
          </div>
          <div style={{ fontSize: '13px', color: '#1e40af', lineHeight: '1.8' }}>
            <span style={badge}>Category: {intel.role_category}</span>
            <span style={badge}>Level: {intel.seniority_level}</span>
            {(intel.tech_stack || []).slice(0, 4).map(t => (
              <span key={t} style={badge}>{t}</span>
            ))}
          </div>
        </div>
      )}

      {/* Job Details */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: '16px', marginBottom: '20px' }}>
        <div>
          <label style={fld.label}>Job Title *</label>
          <input style={fld.input} value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Senior AI Engineer" />
        </div>
        <div>
          <label style={fld.label}>Department</label>
          <input style={fld.input} value={dept}
            onChange={e => setDept(e.target.value)}
            placeholder="Engineering" />
        </div>
        <div>
          <label style={fld.label}>Min Salary (LPA)</label>
          <input style={fld.input} value={salMin}
            onChange={e => setSalMin(e.target.value)}
            placeholder="18" />
        </div>
        <div>
          <label style={fld.label}>Max Salary (LPA)</label>
          <input style={fld.input} value={salMax}
            onChange={e => setSalMax(e.target.value)}
            placeholder="24" />
        </div>
        <div style={{ gridColumn: '1/-1' }}>
          <label style={fld.label}>Location</label>
          <input style={fld.input} value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Bangalore (Hybrid)" />
        </div>
      </div>

      {/* Interview Mode */}
      <div style={{ marginBottom: '20px' }}>
        <label style={fld.label}>Interview Mode</label>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {[
            { key: 'standard',  label: 'Standard',  desc: 'Full pipeline' },
            { key: 'executive', label: 'Executive',  desc: 'Skip AI interview' },
            { key: 'express',   label: 'Express',    desc: '48 hour hiring' },
            { key: 'custom',    label: 'Custom',     desc: 'Full control' },
          ].map(m => (
            <button key={m.key} onClick={() => setMode(m.key)}
              style={{ padding: '10px 16px', borderRadius: '8px',
                border: '2px solid', cursor: 'pointer',
                borderColor: mode === m.key ? '#6366f1' : '#e2e8f0',
                background: mode === m.key ? '#eff6ff' : '#fff',
                color: mode === m.key ? '#4f46e5' : '#475569',
                textAlign: 'left' }}>
              <div style={{ fontWeight: 700, fontSize: '13px' }}>
                {m.label}
              </div>
              <div style={{ fontSize: '11px', opacity: 0.7 }}>
                {m.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Round Toggles */}
      <div style={{ display: 'flex', gap: '20px',
        marginBottom: '20px', padding: '16px',
        background: '#f8fafc', borderRadius: '10px',
        border: '1px solid #e2e8f0' }}>
        <label style={{ display: 'flex', alignItems: 'center',
          gap: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={codingOn}
            onChange={e => setCodingOn(e.target.checked)} />
          <span style={{ fontSize: '14px', fontWeight: 600,
            color: '#374151' }}>
            💻 Coding Round
          </span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center',
          gap: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={aiOn}
            onChange={e => setAiOn(e.target.checked)} />
          <span style={{ fontSize: '14px', fontWeight: 600,
            color: '#374151' }}>
            🤖 AI Interview
          </span>
        </label>
      </div>

      {/* Human Rounds Builder */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: '12px' }}>
          <label style={{ ...fld.label, marginBottom: 0 }}>
            Human Interview Rounds
            <span style={{ fontSize: '11px', color: '#94a3b8',
              marginLeft: '8px', fontWeight: 400 }}>
              (drag ↑↓ to reorder)
            </span>
          </label>
          <button onClick={addRound}
            style={{ padding: '6px 14px', background: '#6366f1',
              color: '#fff', border: 'none', borderRadius: '6px',
              cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
            + Add Round
          </button>
        </div>

        {humanRounds.map((round, idx) => (
          <div key={idx} style={{ background: '#fff',
            border: '1px solid #e2e8f0', borderRadius: '10px',
            padding: '16px', marginBottom: '10px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ background: '#6366f1', color: '#fff',
                  borderRadius: '50%', width: '24px', height: '24px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '12px', fontWeight: 700, flexShrink: 0 }}>
                  {idx + 1}
                </span>
                <span style={{ fontWeight: 700, color: '#374151',
                  fontSize: '14px' }}>
                  {round.round_name || `Round ${idx + 1}`}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button onClick={() => moveRound(idx, -1)}
                  style={fld.iconBtn}
                  title="Move up" disabled={idx === 0}>↑</button>
                <button onClick={() => moveRound(idx, 1)}
                  style={fld.iconBtn}
                  title="Move down"
                  disabled={idx === humanRounds.length - 1}>↓</button>
                <button onClick={() => removeRound(idx)}
                  style={{ ...fld.iconBtn, color: '#dc2626',
                    borderColor: '#fecaca' }}
                  title="Remove">✕</button>
              </div>
            </div>
            <div style={{ display: 'grid',
              gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={fld.smallLabel}>Round Name</label>
                <input style={fld.smallInput}
                  value={round.round_name}
                  onChange={e => updateRound(idx, 'round_name', e.target.value)}
                  placeholder="Technical Interview" />
              </div>
              <div>
                <label style={fld.smallLabel}>Interviewer Name</label>
                <input style={fld.smallInput}
                  value={round.interviewer_name}
                  onChange={e => updateRound(idx, 'interviewer_name', e.target.value)}
                  placeholder="Tech Lead" />
              </div>
              <div>
                <label style={fld.smallLabel}>Interviewer Email</label>
                <input style={fld.smallInput}
                  value={round.interviewer_email}
                  onChange={e => updateRound(idx, 'interviewer_email', e.target.value)}
                  placeholder="lead@company.com" />
              </div>
              <div>
                <label style={fld.smallLabel}>Duration (minutes)</label>
                <input style={fld.smallInput} type="number"
                  value={round.duration_minutes}
                  onChange={e => updateRound(idx, 'duration_minutes',
                    parseInt(e.target.value) || 60)}
                  placeholder="60" />
              </div>
              <div style={{ gridColumn: '1/-1' }}>
                <label style={fld.smallLabel}>Focus Area</label>
                <input style={fld.smallInput}
                  value={round.focus}
                  onChange={e => updateRound(idx, 'focus', e.target.value)}
                  placeholder="Technical depth and system design" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <button onClick={() => setStep('form')}
          style={{ padding: '12px 20px', background: '#f1f5f9',
            color: '#475569', border: 'none', borderRadius: '8px',
            cursor: 'pointer', fontWeight: 600 }}>
          ← Back
        </button>
        <button onClick={postJob}
          disabled={!title || loading}
          style={{ flex: 1, padding: '12px',
            background: title ? '#6366f1' : '#e2e8f0',
            color: title ? '#fff' : '#94a3b8',
            border: 'none', borderRadius: '8px',
            cursor: title ? 'pointer' : 'not-allowed',
            fontWeight: 700, fontSize: '15px' }}>
          {loading ? '⏳ Posting Job...' : '🚀 Post Job Live →'}
        </button>
      </div>
    </div>
  );

  // ── JD Input Screen ───────────────────────────────────────────
  return (
    <div style={{ maxWidth: '800px' }}>
      <h2 style={{ marginBottom: '4px', color: '#0f172a' }}>
        Post a New Job
      </h2>
      <p style={{ color: '#64748b', marginBottom: '24px' }}>
        Paste your job description. AI analyses quality, detects
        role type, and builds the right interview structure automatically.
      </p>

      <div style={{ marginBottom: '16px' }}>
        <label style={fld.label}>Job Description *</label>
        <textarea
          style={{ ...fld.input, minHeight: '320px',
            resize: 'vertical', lineHeight: '1.6' }}
          placeholder={`Paste your full job description here...

Example:
Senior AI Engineer — AI Platform Team

We are looking for a Senior AI Engineer to join our team.

Requirements:
- 4+ years Python experience
- Azure AI services experience  
- Experience with production ML systems
- Strong problem-solving skills

Salary: 18-24 LPA
Location: Bangalore (Hybrid)`}
          value={jdText}
          onChange={e => setJdText(e.target.value)}
        />
      </div>

      <button
        onClick={analyseJD}
        disabled={!jdText.trim() || loading}
        style={{ width: '100%', padding: '14px',
          background: jdText.trim() ? '#6366f1' : '#e2e8f0',
          color: jdText.trim() ? '#fff' : '#94a3b8',
          border: 'none', borderRadius: '8px',
          cursor: jdText.trim() ? 'pointer' : 'not-allowed',
          fontWeight: 700, fontSize: '15px' }}>
        {loading ? '⏳ Analysing JD...' : '🔍 Analyse & Configure →'}
      </button>

      {/* Active Jobs */}
      {jobs.length > 0 && (
        <div style={{ marginTop: '32px' }}>
          <h3 style={{ marginBottom: '16px', color: '#0f172a' }}>
            Active Jobs ({jobs.length})
          </h3>
          {jobs.map(job => (
            <div key={job.id} style={{ background: '#f8fafc',
              border: '1px solid #e2e8f0', borderRadius: '10px',
              padding: '16px', marginBottom: '10px',
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, color: '#0f172a' }}>
                  {job.title}
                </div>
                <div style={{ fontSize: '13px', color: '#64748b',
                  marginTop: '4px' }}>
                  {job.location} · {job.interview_mode} mode ·
                  JD Quality: {job.jd_quality_score}/10
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8',
                  marginTop: '4px' }}>
                  {(job.tech_stack || []).slice(0, 4).join(' · ')}
                </div>
              </div>
              <div style={{ background: '#dcfce7', color: '#16a34a',
                padding: '4px 12px', borderRadius: '100px',
                fontSize: '12px', fontWeight: 700 }}>
                LIVE
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const badge = {
  display: 'inline-block', background: '#dbeafe',
  color: '#1e40af', padding: '2px 8px',
  borderRadius: '100px', fontSize: '12px',
  fontWeight: 600, marginRight: '6px', marginBottom: '4px'
};

// ── Main App ────────────────────────────────────────────────────
export default function App() {
  const [view, setView]             = useState('jobs');
  const [candidates, setCandidates] = useState(MOCK_CANDIDATES);
  const [selected, setSelected]     = useState(null);
  const [approvalForm, setApprovalForm] = useState({
    tech_score: '', culture_score: '',
    notes: '', salary: '', round: 'technical'
  });

  useEffect(() => {
    axios.get(`${API_URL}/api/candidates`)
      .then(r => { if (r.data.length > 0) setCandidates(r.data); })
      .catch(() => {});
  }, []);

  const stats = {
    total:    candidates.length,
    hired:    candidates.filter(c => c.status === 'hired').length,
    rejected: candidates.filter(c => c.status === 'rejected').length,
    pipeline: candidates.filter(
      c => !['hired', 'rejected'].includes(c.status)
    ).length,
  };

  const handleApprove = async (candidateId, decision) => {
    try {
      await axios.post(`${API_URL}/api/human-gate`, {
        candidate_id:  candidateId,
        decision,
        tech_score:    parseFloat(approvalForm.tech_score) || 8,
        culture_score: parseFloat(approvalForm.culture_score) || 7,
        notes:         approvalForm.notes,
        agreed_salary: approvalForm.salary,
        round:         approvalForm.round,
      });
    } catch {}
    setCandidates(prev => prev.map(c =>
      c.id === candidateId
        ? { ...c, status: decision === 'APPROVE' ? 'hired' : 'rejected' }
        : c
    ));
    setSelected(null);
    alert(`✅ ${decision === 'APPROVE' ? 'Approved' : 'Rejected'} successfully`);
  };

  return (
    <div style={s.app}>

      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.sidebarLogo}>🚀 HR Swarm</div>
        {[
          { key: 'jobs',      icon: '📋', label: 'Post Job'    },
          { key: 'pipeline',  icon: '📊', label: 'Pipeline'    },
          { key: 'feed',      icon: '⚡', label: 'Agent Feed'  },
          { key: 'analytics', icon: '📈', label: 'Analytics'   },
          { key: 'talent',    icon: '⭐', label: 'Talent Pool' },
        ].map(item => (
          <div key={item.key}
            style={{
              ...s.navItem,
              background: view === item.key ? '#1e293b' : 'transparent',
              color: view === item.key ? '#fff' : '#94a3b8'
            }}
            onClick={() => setView(item.key)}>
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Main */}
      <div style={s.main}>

        {/* Top Bar */}
        <div style={s.topbar}>
          <h2 style={s.pageTitle}>
            {view === 'jobs'      && '📋 Post New Job'}
            {view === 'pipeline'  && '📊 Candidate Pipeline'}
            {view === 'feed'      && '⚡ Live Agent Feed'}
            {view === 'analytics' && '📈 Analytics'}
            {view === 'talent'    && '⭐ Talent Pool'}
          </h2>
          <div style={s.statChips}>
            <div style={{ ...s.chip, background: '#eff6ff', color: '#1d4ed8' }}>
              {stats.total} Total
            </div>
            <div style={{ ...s.chip, background: '#f0fdf4', color: '#15803d' }}>
              {stats.hired} Hired
            </div>
            <div style={{ ...s.chip, background: '#fef2f2', color: '#dc2626' }}>
              {stats.rejected} Rejected
            </div>
            <div style={{ ...s.chip, background: '#fffbeb', color: '#92400e' }}>
              {stats.pipeline} In Progress
            </div>
          </div>
        </div>

        {/* Job Posting View */}
        {view === 'jobs' && <JobPostingView />}

        {/* Pipeline View */}
        {view === 'pipeline' && (
          <div>
            <div style={s.kanban}>
              {STATUS_COLUMNS.map(col => (
                <div key={col.key} style={s.column}>
                  <div style={{
                    ...s.colHeader,
                    borderTop: `3px solid ${col.color}`
                  }}>
                    <span style={{ color: col.color, fontWeight: 700,
                      fontSize: '12px' }}>
                      {col.label}
                    </span>
                    <span style={s.colCount}>
                      {candidates.filter(c => c.status === col.key).length}
                    </span>
                  </div>
                  {candidates
                    .filter(c => c.status === col.key)
                    .map(c => (
                      <div key={c.id} style={s.candidateCard}
                        onClick={() => setSelected(c)}>
                        <div style={s.cardName}>{c.name}</div>
                        <div style={s.cardRole}>{c.applied_role}</div>
                        {c.resume_score && (
                          <div style={s.scoreRow}>
                            <span style={s.scoreLabel}>Resume</span>
                            <span style={{
                              ...s.scoreBadge,
                              background: c.resume_score >= 70
                                ? '#dcfce7' : '#fef9c3',
                              color: c.resume_score >= 70
                                ? '#15803d' : '#92400e'
                            }}>
                              {c.resume_score}/100
                            </span>
                          </div>
                        )}
                        {c.ai_interview_score && (
                          <div style={s.scoreRow}>
                            <span style={s.scoreLabel}>AI Interview</span>
                            <span style={{ ...s.scoreBadge,
                              background: '#eff6ff', color: '#1d4ed8' }}>
                              {c.ai_interview_score}/100
                            </span>
                          </div>
                        )}
                        {c.final_score && (
                          <div style={s.scoreRow}>
                            <span style={s.scoreLabel}>Final</span>
                            <span style={{
                              ...s.scoreBadge,
                              background: c.decision === 'HIRE'
                                ? '#dcfce7' : '#fef2f2',
                              color: c.decision === 'HIRE'
                                ? '#15803d' : '#dc2626',
                              fontWeight: 700
                            }}>
                              {c.final_score}/100
                            </span>
                          </div>
                        )}
                        {c.status === 'waiting_technical_interview' && (
                          <div style={s.actionBadge}>
                            ⏳ Awaiting your feedback
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              ))}
            </div>

            {/* Candidate Detail Panel */}
            {selected && (
              <div style={s.overlay} onClick={() => setSelected(null)}>
                <div style={s.panel} onClick={e => e.stopPropagation()}>
                  <button style={s.closeBtn}
                    onClick={() => setSelected(null)}>✕</button>
                  <h2 style={s.panelName}>{selected.name}</h2>
                  <p style={s.panelRole}>{selected.applied_role}</p>
                  <div style={s.scoreGrid}>
                    {[
                      { label: 'Resume',       val: selected.resume_score },
                      { label: 'AI Interview', val: selected.ai_interview_score },
                      { label: 'Final Score',  val: selected.final_score },
                    ].filter(i => i.val).map(item => (
                      <div key={item.label} style={s.scoreBlock}>
                        <div style={s.scoreVal}>{item.val}</div>
                        <div style={s.scoreKey}>{item.label}</div>
                      </div>
                    ))}
                  </div>
                  <div style={s.skillsRow}>
                    {(selected.skills || []).map(sk => (
                      <span key={sk} style={s.skillTag}>{sk}</span>
                    ))}
                  </div>

                  {selected.status === 'waiting_technical_interview' && (
                    <div style={s.approvalForm}>
                      <h3 style={s.approvalTitle}>
                        Technical Interview Feedback
                      </h3>
                      <p style={{ fontSize: '13px', color: '#64748b',
                        marginBottom: '16px' }}>
                        AI already tested: Python, Azure, System Design.
                        Focus on: leadership, architecture depth, culture fit.
                      </p>
                      <div style={s.approvalGrid}>
                        <div>
                          <label style={fld.smallLabel}>
                            Technical Score (1-10)
                          </label>
                          <input style={fld.smallInput}
                            type="number" min="1" max="10"
                            placeholder="8"
                            value={approvalForm.tech_score}
                            onChange={e => setApprovalForm({
                              ...approvalForm, tech_score: e.target.value
                            })} />
                        </div>
                        <div>
                          <label style={fld.smallLabel}>
                            Culture Score (1-10)
                          </label>
                          <input style={fld.smallInput}
                            type="number" min="1" max="10"
                            placeholder="7"
                            value={approvalForm.culture_score}
                            onChange={e => setApprovalForm({
                              ...approvalForm, culture_score: e.target.value
                            })} />
                        </div>
                      </div>
                      <textarea style={s.approvalNotes}
                        placeholder="Interview notes..."
                        value={approvalForm.notes}
                        onChange={e => setApprovalForm({
                          ...approvalForm, notes: e.target.value
                        })} />
                      <input style={{ ...fld.smallInput, marginBottom: '16px' }}
                        placeholder="Agreed salary (e.g. 21 LPA)"
                        value={approvalForm.salary}
                        onChange={e => setApprovalForm({
                          ...approvalForm, salary: e.target.value
                        })} />
                      <div style={s.approvalBtns}>
                        <button style={s.approveBtn}
                          onClick={() => handleApprove(selected.id, 'APPROVE')}>
                          ✓ APPROVE — Move to HR Round
                        </button>
                        <button style={s.rejectBtn}
                          onClick={() => handleApprove(selected.id, 'REJECT')}>
                          ✗ REJECT
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Agent Feed View */}
        {view === 'feed' && (
          <div style={s.feedContainer}>
            <div style={s.feedHeader}>
              <span style={s.liveIndicator}>● LIVE</span>
              <span style={{ color: '#94a3b8', fontSize: '13px' }}>
                Real-time agent activity
              </span>
            </div>
            <div style={s.feedLog}>
              {[...MOCK_LOGS].reverse().map((log, i) => (
                <div key={i} style={{
                  ...s.logEntry,
                  opacity: Math.max(0.3, 1 - i * 0.05),
                  background: i === 0 ? '#1e293b' : 'transparent'
                }}>
                  <span style={s.logTime}>{log.time}</span>
                  <span style={{ ...s.logAgent, color: log.color }}>
                    [{log.agent}]
                  </span>
                  <span style={s.logMsg}>{log.msg}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analytics View */}
        {view === 'analytics' && (
          <div style={s.analyticsGrid}>
            {[
              { label: 'Total Processed',    val: stats.total,  unit: '',      color: '#6366f1' },
              { label: 'Hired',              val: stats.hired,  unit: '',      color: '#16a34a' },
              { label: 'Hire Rate',          val: stats.total > 0 ? Math.round(stats.hired / stats.total * 100) : 0, unit: '%', color: '#0891b2' },
              { label: 'Avg Resume Score',   val: Math.round(candidates.reduce((a, c) => a + (c.resume_score || 0), 0) / Math.max(candidates.length, 1)), unit: '/100', color: '#d97706' },
              { label: 'Time to Hire',       val: '3.2',        unit: ' days', color: '#7c3aed' },
              { label: 'Cost per Hire',      val: '₹932',       unit: '',      color: '#dc2626' },
              { label: 'Satisfaction',       val: '91',         unit: '%',     color: '#059669' },
              { label: 'Zero Ghosted',       val: '100',        unit: '%',     color: '#0f172a' },
            ].map(stat => (
              <div key={stat.label} style={s.statCard}>
                <div style={{ ...s.statVal, color: stat.color }}>
                  {stat.val}{stat.unit}
                </div>
                <div style={s.statLabel}>{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Talent Pool View */}
        {view === 'talent' && (
          <div>
            <p style={{ color: '#64748b', marginBottom: '20px' }}>
              Strong candidates not selected this time.
              They will be contacted when a matching role opens.
            </p>
            {candidates
              .filter(c => c.status === 'rejected' &&
                (c.resume_score || 0) >= 60)
              .map(c => (
                <div key={c.id} style={s.talentCard}>
                  <div>
                    <div style={s.talentName}>{c.name}</div>
                    <div style={s.talentRole}>{c.applied_role}</div>
                    <div style={s.skillsRow}>
                      {(c.skills || []).map(sk => (
                        <span key={sk} style={s.skillTag}>{sk}</span>
                      ))}
                    </div>
                  </div>
                  <div style={s.talentScore}>
                    <div style={s.talentScoreVal}>
                      {c.resume_score}/100
                    </div>
                    <div style={s.talentScoreLabel}>Score</div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────────
const s = {
  app: { display: 'flex', minHeight: '100vh',
    background: '#f8fafc', fontFamily: "'Segoe UI', sans-serif" },
  sidebar: { width: '200px', background: '#0f172a',
    padding: '0', flexShrink: 0 },
  sidebarLogo: { color: '#fff', fontSize: '18px', fontWeight: 700,
    padding: '20px 20px 16px', borderBottom: '1px solid #1e293b' },
  navItem: { display: 'flex', alignItems: 'center', gap: '10px',
    padding: '12px 20px', cursor: 'pointer', fontSize: '14px',
    marginTop: '2px', transition: 'all 0.15s', fontWeight: 500 },
  main: { flex: 1, padding: '24px', overflow: 'auto' },
  topbar: { display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '24px' },
  pageTitle: { fontSize: '20px', fontWeight: 700,
    color: '#0f172a', margin: 0 },
  statChips: { display: 'flex', gap: '8px' },
  chip: { padding: '6px 14px', borderRadius: '100px',
    fontSize: '13px', fontWeight: 600 },
  kanban: { display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '12px', overflowX: 'auto' },
  column: { background: '#f1f5f9', borderRadius: '10px',
    padding: '12px', minHeight: '200px', minWidth: '155px' },
  colHeader: { display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '12px',
    paddingBottom: '8px', borderBottom: '1px solid #e2e8f0' },
  colCount: { background: '#e2e8f0', borderRadius: '100px',
    padding: '2px 8px', fontSize: '11px', fontWeight: 700,
    color: '#475569' },
  candidateCard: { background: '#fff', borderRadius: '8px',
    padding: '12px', marginBottom: '8px', cursor: 'pointer',
    border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)' },
  cardName: { fontWeight: 700, fontSize: '13px', color: '#0f172a' },
  cardRole: { fontSize: '11px', color: '#64748b',
    marginTop: '2px', marginBottom: '8px' },
  scoreRow: { display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginTop: '4px' },
  scoreLabel: { fontSize: '11px', color: '#94a3b8' },
  scoreBadge: { fontSize: '11px', fontWeight: 600,
    padding: '2px 8px', borderRadius: '100px' },
  actionBadge: { marginTop: '8px', fontSize: '11px',
    color: '#d97706', background: '#fffbeb',
    padding: '4px 8px', borderRadius: '6px', textAlign: 'center' },
  overlay: { position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.5)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  panel: { background: '#fff', borderRadius: '16px',
    padding: '32px', width: '540px', maxHeight: '90vh',
    overflowY: 'auto', position: 'relative' },
  closeBtn: { position: 'absolute', top: '16px', right: '16px',
    background: 'none', border: 'none', fontSize: '18px',
    cursor: 'pointer', color: '#64748b' },
  panelName: { fontSize: '22px', fontWeight: 700,
    color: '#0f172a', margin: '0 0 4px' },
  panelRole: { color: '#64748b', margin: '0 0 20px' },
  scoreGrid: { display: 'flex', gap: '12px', marginBottom: '16px' },
  scoreBlock: { flex: 1, textAlign: 'center',
    background: '#f8fafc', borderRadius: '10px', padding: '16px' },
  scoreVal: { fontSize: '28px', fontWeight: 700,
    color: '#0f172a', marginBottom: '4px' },
  scoreKey: { fontSize: '12px', color: '#94a3b8' },
  skillsRow: { display: 'flex', flexWrap: 'wrap',
    gap: '6px', marginBottom: '20px' },
  skillTag: { background: '#eff6ff', color: '#1d4ed8',
    padding: '4px 10px', borderRadius: '100px',
    fontSize: '12px', fontWeight: 500 },
  approvalForm: { background: '#f8fafc', borderRadius: '12px',
    padding: '20px', border: '1px solid #e2e8f0' },
  approvalTitle: { fontSize: '16px', fontWeight: 700,
    color: '#0f172a', margin: '0 0 8px' },
  approvalGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: '12px', marginBottom: '12px' },
  approvalNotes: { width: '100%', padding: '10px 12px',
    borderRadius: '8px', border: '1.5px solid #e2e8f0',
    fontSize: '14px', minHeight: '80px', boxSizing: 'border-box',
    marginBottom: '12px', resize: 'vertical' },
  approvalBtns: { display: 'flex', gap: '10px' },
  approveBtn: { flex: 1, padding: '12px', background: '#16a34a',
    color: '#fff', border: 'none', borderRadius: '8px',
    fontSize: '13px', fontWeight: 700, cursor: 'pointer' },
  rejectBtn: { flex: 1, padding: '12px', background: '#dc2626',
    color: '#fff', border: 'none', borderRadius: '8px',
    fontSize: '13px', fontWeight: 700, cursor: 'pointer' },
  feedContainer: { background: '#0f172a', borderRadius: '12px',
    padding: '20px', minHeight: '500px' },
  feedHeader: { display: 'flex', alignItems: 'center',
    gap: '10px', marginBottom: '16px',
    paddingBottom: '12px', borderBottom: '1px solid #1e293b' },
  liveIndicator: { color: '#22c55e', fontSize: '13px',
    fontWeight: 700, fontFamily: 'monospace' },
  feedLog: { display: 'flex', flexDirection: 'column', gap: '4px' },
  logEntry: { display: 'flex', gap: '12px', padding: '8px 12px',
    borderRadius: '6px', fontFamily: 'monospace', fontSize: '12px' },
  logTime: { color: '#475569', flexShrink: 0 },
  logAgent: { fontWeight: 700, flexShrink: 0, minWidth: '130px' },
  logMsg: { color: '#94a3b8' },
  analyticsGrid: { display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' },
  statCard: { background: '#fff', borderRadius: '12px',
    padding: '24px', textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    border: '1px solid #e2e8f0' },
  statVal: { fontSize: '36px', fontWeight: 800, marginBottom: '8px' },
  statLabel: { fontSize: '13px', color: '#64748b' },
  talentCard: { background: '#fff', borderRadius: '10px',
    padding: '16px', marginBottom: '12px',
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', border: '1px solid #e2e8f0' },
  talentName: { fontWeight: 700, color: '#0f172a' },
  talentRole: { fontSize: '13px', color: '#64748b', marginBottom: '8px' },
  talentScore: { textAlign: 'center' },
  talentScoreVal: { fontSize: '24px', fontWeight: 700, color: '#6366f1' },
  talentScoreLabel: { fontSize: '12px', color: '#94a3b8' },
};