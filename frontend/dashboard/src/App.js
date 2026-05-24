import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// ── Mock Data for Demo ──────────────────────────────────────────
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
  { time: '10:43:10', agent: 'INTERVIEWER', msg: 'AI Readiness Profile: AI-Native | Top 12%', color: '#d97706' },
  { time: '10:43:12', agent: 'SCHEDULER', msg: 'Reading interviewer calendars via Graph API', color: '#059669' },
  { time: '10:43:14', agent: 'SCHEDULER', msg: 'Teams meeting booked: Mon Jun 23 10:00 AM', color: '#059669' },
  { time: '10:43:15', agent: 'COMMUNICATOR', msg: 'Interview invite sent to arjun@gmail.com', color: '#dc2626' },
  { time: '10:43:16', agent: 'ORCHESTRATOR', msg: 'Pipeline paused — waiting human approval', color: '#6366f1' },
];

const STATUS_COLUMNS = [
  { key: 'applied',                    label: 'Applied',          color: '#6366f1' },
  { key: 'screened',                   label: 'Screened',         color: '#0891b2' },
  { key: 'ai_interview_complete',      label: 'AI Interview',     color: '#7c3aed' },
  { key: 'waiting_technical_interview', label: 'Awaiting Tech',   color: '#d97706' },
  { key: 'waiting_hr_interview',       label: 'Awaiting HR',      color: '#059669' },
  { key: 'hired',                      label: 'Hired ✅',         color: '#16a34a' },
  { key: 'rejected',                   label: 'Rejected',         color: '#dc2626' },
];

export default function App() {
  const [view, setView]               = useState('pipeline');
  const [candidates, setCandidates]   = useState(MOCK_CANDIDATES);
  const [logs, setLogs]               = useState(MOCK_LOGS);
  const [selected, setSelected]       = useState(null);
  const [approvalForm, setApprovalForm] = useState({
    tech_score: '', culture_score: '',
    notes: '', salary: '', round: 'technical'
  });
  const [logIdx, setLogIdx]           = useState(0);

  // Simulate live agent feed
  useEffect(() => {
    const interval = setInterval(() => {
      setLogIdx(prev => (prev + 1) % MOCK_LOGS.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Try to load real data from API
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
      c => !['hired','rejected'].includes(c.status)
    ).length,
  };

  const handleApprove = async (candidateId, decision) => {
    try {
      await axios.post(`${API_URL}/api/human-gate`, {
        candidate_id:    candidateId,
        decision:        decision,
        tech_score:      parseFloat(approvalForm.tech_score) || 8,
        culture_score:   parseFloat(approvalForm.culture_score) || 7,
        notes:           approvalForm.notes,
        agreed_salary:   approvalForm.salary,
        round:           approvalForm.round,
      });
      setCandidates(prev => prev.map(c =>
        c.id === candidateId
          ? { ...c, status: decision === 'APPROVE' ? 'hired' : 'rejected' }
          : c
      ));
      setSelected(null);
      alert(`✅ ${decision === 'APPROVE' ? 'Approved' : 'Rejected'} successfully`);
    } catch (err) {
      // Demo mode
      setCandidates(prev => prev.map(c =>
        c.id === candidateId
          ? { ...c, status: decision === 'APPROVE' ? 'hired' : 'rejected' }
          : c
      ));
      setSelected(null);
      alert(`✅ ${decision === 'APPROVE' ? 'Approved' : 'Rejected'} (Demo mode)`);
    }
  };

  return (
    <div style={s.app}>

      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.sidebarLogo}>🚀 HR Swarm</div>
        {[
          { key: 'pipeline',  icon: '📊', label: 'Pipeline'   },
          { key: 'feed',      icon: '⚡', label: 'Agent Feed' },
          { key: 'analytics', icon: '📈', label: 'Analytics'  },
          { key: 'talent',    icon: '⭐', label: 'Talent Pool' },
        ].map(item => (
          <div
            key={item.key}
            style={{
              ...s.navItem,
              background: view === item.key ? '#1e293b' : 'transparent'
            }}
            onClick={() => setView(item.key)}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Main */}
      <div style={s.main}>

        {/* Top Bar */}
        <div style={s.topbar}>
          <div>
            <h2 style={s.pageTitle}>
              {view === 'pipeline'  && 'Candidate Pipeline'}
              {view === 'feed'      && 'Live Agent Feed'}
              {view === 'analytics' && 'Analytics'}
              {view === 'talent'    && 'Talent Pool'}
            </h2>
          </div>
          <div style={s.statChips}>
            <div style={{...s.chip, background:'#eff6ff', color:'#1d4ed8'}}>
              {stats.total} Total
            </div>
            <div style={{...s.chip, background:'#f0fdf4', color:'#15803d'}}>
              {stats.hired} Hired
            </div>
            <div style={{...s.chip, background:'#fef2f2', color:'#dc2626'}}>
              {stats.rejected} Rejected
            </div>
            <div style={{...s.chip, background:'#fffbeb', color:'#92400e'}}>
              {stats.pipeline} In Progress
            </div>
          </div>
        </div>

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
                    <span style={{color: col.color, fontWeight: 700}}>
                      {col.label}
                    </span>
                    <span style={s.colCount}>
                      {candidates.filter(c => c.status === col.key).length}
                    </span>
                  </div>
                  {candidates
                    .filter(c => c.status === col.key)
                    .map(c => (
                      <div
                        key={c.id}
                        style={s.candidateCard}
                        onClick={() => setSelected(c)}
                      >
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
                            <span style={{
                              ...s.scoreBadge,
                              background: '#eff6ff',
                              color: '#1d4ed8'
                            }}>
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
                            ⏳ Awaiting feedback
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
                  <button
                    style={s.closeBtn}
                    onClick={() => setSelected(null)}
                  >✕</button>

                  <h2 style={s.panelName}>{selected.name}</h2>
                  <p style={s.panelRole}>{selected.applied_role}</p>

                  <div style={s.scoreGrid}>
                    {[
                      { label: 'Resume',       val: selected.resume_score },
                      { label: 'AI Interview', val: selected.ai_interview_score },
                      { label: 'Final Score',  val: selected.final_score },
                    ].map(item => item.val && (
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

                  {/* Human Approval Form */}
                  {selected.status === 'waiting_technical_interview' && (
                    <div style={s.approvalForm}>
                      <h3 style={s.approvalTitle}>
                        Technical Interview Feedback
                      </h3>
                      <div style={s.approvalGrid}>
                        <div>
                          <label style={s.approvalLabel}>
                            Technical Score (1-10)
                          </label>
                          <input
                            style={s.approvalInput}
                            type="number" min="1" max="10"
                            placeholder="8"
                            value={approvalForm.tech_score}
                            onChange={e => setApprovalForm({
                              ...approvalForm,
                              tech_score: e.target.value
                            })}
                          />
                        </div>
                        <div>
                          <label style={s.approvalLabel}>
                            Culture Score (1-10)
                          </label>
                          <input
                            style={s.approvalInput}
                            type="number" min="1" max="10"
                            placeholder="7"
                            value={approvalForm.culture_score}
                            onChange={e => setApprovalForm({
                              ...approvalForm,
                              culture_score: e.target.value
                            })}
                          />
                        </div>
                      </div>
                      <textarea
                        style={s.approvalNotes}
                        placeholder="Interview notes..."
                        value={approvalForm.notes}
                        onChange={e => setApprovalForm({
                          ...approvalForm,
                          notes: e.target.value
                        })}
                      />
                      <input
                        style={s.approvalInput}
                        placeholder="Agreed salary (e.g. 21 LPA)"
                        value={approvalForm.salary}
                        onChange={e => setApprovalForm({
                          ...approvalForm,
                          salary: e.target.value
                        })}
                      />
                      <div style={s.approvalBtns}>
                        <button
                          style={s.approveBtn}
                          onClick={() => handleApprove(selected.id, 'APPROVE')}
                        >
                          ✓ APPROVE — Move to HR Round
                        </button>
                        <button
                          style={s.rejectBtn}
                          onClick={() => handleApprove(selected.id, 'REJECT')}
                        >
                          ✗ REJECT — Send Rejection
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
              <span style={{color: '#94a3b8', fontSize: '13px'}}>
                Agent activity — real time
              </span>
            </div>
            <div style={s.feedLog}>
              {[...MOCK_LOGS].reverse().map((log, i) => (
                <div
                  key={i}
                  style={{
                    ...s.logEntry,
                    opacity: i === 0 ? 1 : Math.max(0.3, 1 - i * 0.06),
                    background: i === 0 ? '#1e293b' : 'transparent'
                  }}
                >
                  <span style={s.logTime}>{log.time}</span>
                  <span style={{
                    ...s.logAgent,
                    color: log.color
                  }}>
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
              { label: 'Total Processed',   val: stats.total,    unit: '',      color: '#6366f1' },
              { label: 'Hired',             val: stats.hired,    unit: '',      color: '#16a34a' },
              { label: 'Hire Rate',         val: stats.total > 0 ? Math.round(stats.hired/stats.total*100) : 0, unit: '%', color: '#0891b2' },
              { label: 'Avg Resume Score',  val: Math.round(candidates.reduce((a,c) => a + (c.resume_score||0), 0) / candidates.length), unit: '/100', color: '#d97706' },
              { label: 'Time to Hire',      val: 3.2,            unit: ' days', color: '#7c3aed' },
              { label: 'Cost per Hire',     val: '₹932',         unit: '',      color: '#dc2626' },
              { label: 'Candidate Satisfaction', val: 91,        unit: '%',     color: '#059669' },
              { label: 'Zero Ghosted',      val: '100',          unit: '%',     color: '#0f172a' },
            ].map(stat => (
              <div key={stat.label} style={s.statCard}>
                <div style={{
                  ...s.statVal,
                  color: stat.color
                }}>
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
            <p style={{color: '#64748b', marginBottom: '20px'}}>
              Strong candidates who were not selected this time.
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

const s = {
  app: {
    display: 'flex', minHeight: '100vh',
    background: '#f8fafc',
    fontFamily: "'Segoe UI', sans-serif"
  },
  sidebar: {
    width: '200px', background: '#0f172a',
    padding: '20px 0', flexShrink: 0
  },
  sidebarLogo: {
    color: '#fff', fontSize: '18px',
    fontWeight: 700, padding: '0 20px 24px',
    borderBottom: '1px solid #1e293b'
  },
  navItem: {
    display: 'flex', alignItems: 'center',
    gap: '10px', padding: '12px 20px',
    color: '#94a3b8', cursor: 'pointer',
    fontSize: '14px', marginTop: '4px',
    borderRadius: '0', transition: 'all 0.2s'
  },
  main: {
    flex: 1, padding: '24px', overflow: 'auto'
  },
  topbar: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '24px'
  },
  pageTitle: {
    fontSize: '22px', fontWeight: 700,
    color: '#0f172a', margin: 0
  },
  statChips: { display: 'flex', gap: '8px' },
  chip: {
    padding: '6px 14px', borderRadius: '100px',
    fontSize: '13px', fontWeight: 600
  },
  kanban: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '12px', overflowX: 'auto'
  },
  column: {
    background: '#f1f5f9', borderRadius: '10px',
    padding: '12px', minHeight: '200px', minWidth: '160px'
  },
  colHeader: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '12px',
    paddingBottom: '8px', borderBottom: '1px solid #e2e8f0'
  },
  colCount: {
    background: '#e2e8f0', borderRadius: '100px',
    padding: '2px 8px', fontSize: '12px',
    fontWeight: 700, color: '#475569'
  },
  candidateCard: {
    background: '#fff', borderRadius: '8px',
    padding: '12px', marginBottom: '8px',
    cursor: 'pointer', border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    transition: 'transform 0.2s'
  },
  cardName: { fontWeight: 700, fontSize: '13px', color: '#0f172a' },
  cardRole: { fontSize: '11px', color: '#64748b', marginTop: '2px', marginBottom: '8px' },
  scoreRow: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginTop: '4px'
  },
  scoreLabel: { fontSize: '11px', color: '#94a3b8' },
  scoreBadge: {
    fontSize: '11px', fontWeight: 600,
    padding: '2px 8px', borderRadius: '100px'
  },
  actionBadge: {
    marginTop: '8px', fontSize: '11px',
    color: '#d97706', background: '#fffbeb',
    padding: '4px 8px', borderRadius: '6px',
    textAlign: 'center'
  },
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', zIndex: 100
  },
  panel: {
    background: '#fff', borderRadius: '16px',
    padding: '32px', width: '520px',
    maxHeight: '90vh', overflowY: 'auto',
    position: 'relative'
  },
  closeBtn: {
    position: 'absolute', top: '16px', right: '16px',
    background: 'none', border: 'none',
    fontSize: '18px', cursor: 'pointer', color: '#64748b'
  },
  panelName: {
    fontSize: '22px', fontWeight: 700,
    color: '#0f172a', margin: '0 0 4px'
  },
  panelRole: { color: '#64748b', margin: '0 0 20px' },
  scoreGrid: {
    display: 'flex', gap: '16px', marginBottom: '16px'
  },
  scoreBlock: {
    flex: 1, textAlign: 'center',
    background: '#f8fafc', borderRadius: '10px',
    padding: '16px'
  },
  scoreVal: {
    fontSize: '28px', fontWeight: 700,
    color: '#0f172a', marginBottom: '4px'
  },
  scoreKey: { fontSize: '12px', color: '#94a3b8' },
  skillsRow: {
    display: 'flex', flexWrap: 'wrap',
    gap: '6px', marginBottom: '20px'
  },
  skillTag: {
    background: '#eff6ff', color: '#1d4ed8',
    padding: '4px 10px', borderRadius: '100px',
    fontSize: '12px', fontWeight: 500
  },
  approvalForm: {
    background: '#f8fafc', borderRadius: '12px',
    padding: '20px', border: '1px solid #e2e8f0'
  },
  approvalTitle: {
    fontSize: '16px', fontWeight: 700,
    color: '#0f172a', margin: '0 0 16px'
  },
  approvalGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: '12px', marginBottom: '12px'
  },
  approvalLabel: {
    fontSize: '12px', fontWeight: 600,
    color: '#475569', display: 'block', marginBottom: '4px'
  },
  approvalInput: {
    width: '100%', padding: '10px 12px',
    borderRadius: '8px', border: '1.5px solid #e2e8f0',
    fontSize: '14px', boxSizing: 'border-box',
    marginBottom: '12px'
  },
  approvalNotes: {
    width: '100%', padding: '10px 12px',
    borderRadius: '8px', border: '1.5px solid #e2e8f0',
    fontSize: '14px', minHeight: '80px',
    boxSizing: 'border-box', marginBottom: '12px',
    resize: 'vertical'
  },
  approvalBtns: { display: 'flex', gap: '10px' },
  approveBtn: {
    flex: 1, padding: '12px',
    background: '#16a34a', color: '#fff',
    border: 'none', borderRadius: '8px',
    fontSize: '13px', fontWeight: 700,
    cursor: 'pointer'
  },
  rejectBtn: {
    flex: 1, padding: '12px',
    background: '#dc2626', color: '#fff',
    border: 'none', borderRadius: '8px',
    fontSize: '13px', fontWeight: 700,
    cursor: 'pointer'
  },
  feedContainer: {
    background: '#0f172a', borderRadius: '12px',
    padding: '20px', minHeight: '500px'
  },
  feedHeader: {
    display: 'flex', alignItems: 'center',
    gap: '10px', marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid #1e293b'
  },
  liveIndicator: {
    color: '#22c55e', fontSize: '13px',
    fontWeight: 700, fontFamily: 'monospace'
  },
  feedLog: {
    display: 'flex', flexDirection: 'column', gap: '4px'
  },
  logEntry: {
    display: 'flex', gap: '12px',
    padding: '8px 12px', borderRadius: '6px',
    fontFamily: 'monospace', fontSize: '12px'
  },
  logTime: { color: '#475569', flexShrink: 0 },
  logAgent: { fontWeight: 700, flexShrink: 0, minWidth: '120px' },
  logMsg: { color: '#94a3b8' },
  analyticsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px'
  },
  statCard: {
    background: '#fff', borderRadius: '12px',
    padding: '24px', textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    border: '1px solid #e2e8f0'
  },
  statVal: {
    fontSize: '36px', fontWeight: 800,
    marginBottom: '8px'
  },
  statLabel: { fontSize: '13px', color: '#64748b' },
  talentCard: {
    background: '#fff', borderRadius: '10px',
    padding: '16px', marginBottom: '12px',
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', border: '1px solid #e2e8f0'
  },
  talentName: { fontWeight: 700, color: '#0f172a' },
  talentRole: { fontSize: '13px', color: '#64748b', marginBottom: '8px' },
  talentScore: { textAlign: 'center' },
  talentScoreVal: {
    fontSize: '24px', fontWeight: 700, color: '#6366f1'
  },
  talentScoreLabel: { fontSize: '12px', color: '#94a3b8' },
};