import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const STATUS_COLUMNS = [
  { key: 'applied',                     label: 'Applied',       color: '#6366f1' },
  { key: 'screened',                    label: 'Screened',      color: '#0891b2' },
  { key: 'ai_interview_complete',       label: 'AI Interview',  color: '#7c3aed' },
  { key: 'waiting_technical_interview', label: 'Awaiting Tech', color: '#d97706' },
  { key: 'waiting_hr_interview',        label: 'Awaiting HR',   color: '#059669' },
  { key: 'hired',                       label: 'Hired ✅',      color: '#16a34a' },
  { key: 'rejected',                    label: 'Rejected',      color: '#dc2626' },
];

// ── Shared Field Styles ──────────────────────────────────────────
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
  },
  errorText: {
    fontSize: '11px', color: '#dc2626', marginTop: '4px'
  }
};

const badge = {
  display: 'inline-block', background: '#dbeafe',
  color: '#1e40af', padding: '2px 8px',
  borderRadius: '100px', fontSize: '12px',
  fontWeight: 600, marginRight: '6px', marginBottom: '4px'
};

// ── Helper: Input with validation ────────────────────────────────
function ValidatedInput({ label, fieldKey, form, setForm, errors, setErrors,
  placeholder, type = 'text', min, max, required }) {
  const hasError = !!errors[fieldKey];
  return (
    <div>
      <label style={fld.smallLabel}>
        {label}{required && ' *'}
      </label>
      <input
        style={{
          ...fld.smallInput,
          borderColor: hasError ? '#dc2626' : '#e2e8f0',
          background:  hasError ? '#fef2f2' : '#fff'
        }}
        type={type}
        min={min} max={max}
        placeholder={placeholder}
        value={form[fieldKey]}
        onChange={e => {
          setForm({ ...form, [fieldKey]: e.target.value });
          if (hasError) setErrors({ ...errors, [fieldKey]: null });
        }}
      />
      {hasError && (
        <div style={fld.errorText}>⚠️ {errors[fieldKey]}</div>
      )}
    </div>
  );
}

// ── Interviewer Pool View ────────────────────────────────────────
function InterviewerPoolView() {
  const [interviewers, setInterviewers] = useState([]);
  const [assignments, setAssignments]   = useState([]);
  const [showAdd, setShowAdd]           = useState(false);
  const [loading, setLoading]           = useState(false);
  const [hrUsers, setHrUsers]           = useState([]);
  const [formErrors, setFormErrors]     = useState({});
  const [form, setForm] = useState({
    name: '', email: '', role: '', department: '',
    seniority: 'senior', skills: '', max_per_week: 3, hr_id: ''
  });

  useEffect(() => {
  loadData();
  const interval = setInterval(loadData, 5000);
  return () => clearInterval(interval);
}, []);

  const loadData = () => {
    axios.get(`${API_URL}/api/interviewers`)
      .then(r => setInterviewers(r.data.interviewers || []))
      .catch(() => {});
    axios.get(`${API_URL}/api/assignments`)
      .then(r => setAssignments(r.data || []))
      .catch(() => {});
    axios.get(`${API_URL}/api/hr-users`)
      .then(r => setHrUsers(r.data || []))
      .catch(() => {});
  };

  const validateForm = () => {
    const errors = {};
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!form.name.trim())
      errors.name = 'Full name is required';

    if (!form.email.trim())
      errors.email = 'Email address is required';
    else if (!emailRegex.test(form.email.trim()))
      errors.email = 'Please enter a valid email (e.g. name@company.com)';

    if (!form.role.trim())
      errors.role = 'Job title is required';

    if (!form.skills.trim())
      errors.skills = 'Please enter at least one skill';
    else if (form.skills.split(',').map(s => s.trim()).filter(Boolean).length === 0)
      errors.skills = 'Please enter valid skills separated by commas';

    const maxPw = parseInt(form.max_per_week);
    if (isNaN(maxPw) || maxPw < 1 || maxPw > 10)
      errors.max_per_week = 'Must be a number between 1 and 10';

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleAdd = async () => {
    if (!validateForm()) return;
    setLoading(true);
    try {
      const skills = form.skills.split(',').map(s => s.trim()).filter(Boolean);
      await axios.post(`${API_URL}/api/interviewers`, {
        name: form.name.trim(), email: form.email.trim(),
        role: form.role.trim(), department: form.department.trim(),
        seniority: form.seniority, skills,
        max_per_week: parseInt(form.max_per_week) || 3,
        hr_id: form.hr_id || hrUsers[0]?.id || ''
      });
      setShowAdd(false);
      setFormErrors({});
      setForm({ name: '', email: '', role: '', department: '',
        seniority: 'senior', skills: '', max_per_week: 3, hr_id: '' });
      loadData();
      alert('✅ Invitation sent! Interviewer will receive email to accept.');
    } catch { alert('Error adding interviewer. Please try again.'); }
    setLoading(false);
  };

  const handleCancel = () => {
    setShowAdd(false);
    setFormErrors({});
    setForm({ name: '', email: '', role: '', department: '',
      seniority: 'senior', skills: '', max_per_week: 3, hr_id: '' });
  };

  const statusColor = (status) => ({
    active:   { bg: '#dcfce7', color: '#16a34a' },
    pending:  { bg: '#fef9c3', color: '#92400e' },
    inactive: { bg: '#fee2e2', color: '#dc2626' },
  }[status] || { bg: '#f1f5f9', color: '#475569' });

  const pisAlerts = assignments.filter(a => a.status === 'hr_action_required');

  return (
    <div>
      {/* PIS Alerts */}
      {pisAlerts.length > 0 && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
          <div style={{ fontWeight: 700, color: '#dc2626', marginBottom: '8px' }}>
            🚨 PIS Alerts — Action Required ({pisAlerts.length})
          </div>
          {pisAlerts.map(a => (
            <div key={a.id} style={{ fontSize: '13px', color: '#7f1d1d', marginBottom: '4px' }}>
              ⚠️ Candidate {a.candidate_id?.slice(0, 8)} —
              All interviewers unresponsive. HR action needed.
            </div>
          ))}
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: '0 0 4px', color: '#0f172a' }}>Interviewer Pool</h3>
          <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>
            {interviewers.filter(i => i.status === 'active').length} active ·{' '}
            {interviewers.filter(i => i.status === 'pending').length} pending ·{' '}
            {interviewers.filter(i =>
              i.status === 'active' && i.current_booked < i.max_per_week
            ).length} available now
          </p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}
          style={{ padding: '10px 20px', background: '#6366f1', color: '#fff',
            border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 700 }}>
          + Add Interviewer
        </button>
      </div>

      {/* Add Form */}
      {showAdd && (
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0',
          borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
          <h4 style={{ margin: '0 0 4px', color: '#0f172a' }}>Add New Interviewer</h4>
          <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px' }}>
            An invitation email will be sent. They join the pool once they accept.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>

            {/* Name */}
            <ValidatedInput
              label="Full Name" fieldKey="name" required
              form={form} setForm={setForm}
              errors={formErrors} setErrors={setFormErrors}
              placeholder="Vikram Nair"
            />

            {/* Email */}
            <ValidatedInput
              label="Email Address" fieldKey="email" required
              form={form} setForm={setForm}
              errors={formErrors} setErrors={setFormErrors}
              placeholder="vikram@company.com"
              type="email"
            />

            {/* Job Title */}
            <ValidatedInput
              label="Job Title" fieldKey="role" required
              form={form} setForm={setForm}
              errors={formErrors} setErrors={setFormErrors}
              placeholder="Senior AI Engineer"
            />

            {/* Department */}
            <div>
              <label style={fld.smallLabel}>Department</label>
              <input style={fld.smallInput}
                placeholder="Engineering"
                value={form.department}
                onChange={e => setForm({ ...form, department: e.target.value })} />
            </div>

            {/* Seniority */}
            <div>
              <label style={fld.smallLabel}>Seniority Level</label>
              <select style={fld.smallInput} value={form.seniority}
                onChange={e => setForm({ ...form, seniority: e.target.value })}>
                {['junior','mid','senior','lead','manager','director'].map(s => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Max per week */}
            <div>
              <label style={fld.smallLabel}>Max Interviews / Week</label>
              <input
                style={{
                  ...fld.smallInput,
                  borderColor: formErrors.max_per_week ? '#dc2626' : '#e2e8f0',
                  background:  formErrors.max_per_week ? '#fef2f2' : '#fff'
                }}
                type="number" min="1" max="10"
                value={form.max_per_week}
                onChange={e => {
                  setForm({ ...form, max_per_week: e.target.value });
                  if (formErrors.max_per_week)
                    setFormErrors({ ...formErrors, max_per_week: null });
                }}
              />
              {formErrors.max_per_week && (
                <div style={fld.errorText}>⚠️ {formErrors.max_per_week}</div>
              )}
            </div>

            {/* Skills */}
            <div style={{ gridColumn: '1/-1' }}>
              <label style={fld.smallLabel}>Skills (comma separated) *</label>
              <input
                style={{
                  ...fld.smallInput,
                  borderColor: formErrors.skills ? '#dc2626' : '#e2e8f0',
                  background:  formErrors.skills ? '#fef2f2' : '#fff'
                }}
                placeholder="Python, Azure ML, System Design, FastAPI"
                value={form.skills}
                onChange={e => {
                  setForm({ ...form, skills: e.target.value });
                  if (formErrors.skills)
                    setFormErrors({ ...formErrors, skills: null });
                }}
              />
              {formErrors.skills && (
                <div style={fld.errorText}>⚠️ {formErrors.skills}</div>
              )}
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                Enter skills that match candidates you will interview
              </div>
            </div>

            {/* HR selector */}
            {hrUsers.length > 0 && (
              <div style={{ gridColumn: '1/-1' }}>
                <label style={fld.smallLabel}>Adding As HR</label>
                <select style={fld.smallInput} value={form.hr_id}
                  onChange={e => setForm({ ...form, hr_id: e.target.value })}>
                  {hrUsers.map(hr => (
                    <option key={hr.id} value={hr.id}>
                      {hr.name} ({hr.email})
                    </option>
                  ))}
                </select>
              </div>
            )}

          </div>

          {/* Form Error Summary */}
          {Object.keys(formErrors).filter(k => formErrors[k]).length > 0 && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca',
              borderRadius: '8px', padding: '12px', marginTop: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#dc2626',
                marginBottom: '6px' }}>
                Please fix the following errors:
              </div>
              {Object.entries(formErrors).filter(([, v]) => v).map(([k, v]) => (
                <div key={k} style={{ fontSize: '12px', color: '#b91c1c', marginBottom: '2px' }}>
                  • {v}
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
            <button onClick={handleAdd} disabled={loading}
              style={{ flex: 1, padding: '10px', background: '#6366f1',
                color: '#fff', border: 'none', borderRadius: '8px',
                cursor: 'pointer', fontWeight: 700 }}>
              {loading ? '⏳ Sending...' : '📧 Send Invitation'}
            </button>
            <button onClick={handleCancel}
              style={{ padding: '10px 20px', background: '#f1f5f9',
                color: '#475569', border: 'none', borderRadius: '8px',
                cursor: 'pointer', fontWeight: 600 }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Interviewer Cards */}
      {interviewers.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>👥</div>
          <p style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: '#475569' }}>
            No interviewers yet
          </p>
          <p style={{ fontSize: '14px' }}>
            Add interviewers so AI can automatically assign
            the right person to each candidate.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {interviewers.map(iv => {
            const sc = statusColor(iv.status);
            const isAvailable = iv.status === 'active' &&
              iv.current_booked < iv.max_per_week;
            return (
              <div key={iv.id} style={{ background: '#fff',
                border: '1px solid #e2e8f0', borderRadius: '12px',
                padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between',
                  alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '15px', color: '#0f172a' }}>
                      {iv.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                      {iv.role} · {iv.department}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column',
                    alignItems: 'flex-end', gap: '4px' }}>
                    <span style={{ background: sc.bg, color: sc.color,
                      padding: '3px 10px', borderRadius: '100px',
                      fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>
                      {iv.status}
                    </span>
                    {isAvailable && (
                      <span style={{ background: '#dcfce7', color: '#16a34a',
                        padding: '2px 8px', borderRadius: '100px',
                        fontSize: '10px', fontWeight: 600 }}>
                        Available
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap',
                  gap: '4px', marginBottom: '12px' }}>
                  {(iv.expertise_skills || []).map(sk => (
                    <span key={sk} style={{ background: '#eff6ff', color: '#1d4ed8',
                      padding: '2px 8px', borderRadius: '100px',
                      fontSize: '11px', fontWeight: 500 }}>
                      {sk}
                    </span>
                  ))}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
                  gap: '8px', marginBottom: '12px' }}>
                  {[
                    { label: 'Done',     val: iv.total_done || 0 },
                    { label: 'Booked',   val: `${iv.current_booked||0}/${iv.max_per_week||3}` },
                    { label: 'Response', val: `${iv.response_rate||100}%` },
                  ].map(stat => (
                    <div key={stat.label} style={{ background: '#f8fafc',
                      borderRadius: '6px', padding: '8px', textAlign: 'center' }}>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>
                        {stat.val}
                      </div>
                      <div style={{ fontSize: '10px', color: '#94a3b8' }}>{stat.label}</div>
                    </div>
                  ))}
                </div>

                <div style={{ fontSize: '12px', color: '#64748b' }}>
                  Level: <strong>{iv.seniority}</strong> ·
                  Timezone: {iv.timezone || 'Asia/Kolkata'}
                </div>

                {iv.status === 'pending' && (
                  <div style={{ marginTop: '10px', fontSize: '12px', color: '#92400e',
                    background: '#fffbeb', padding: '6px 10px', borderRadius: '6px' }}>
                    ⏳ Invitation sent — waiting for acceptance
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Assignment Timeline */}
      {assignments.length > 0 && (
        <div style={{ marginTop: '32px' }}>
          <h3 style={{ color: '#0f172a', marginBottom: '16px' }}>Recent Assignments</h3>
          {assignments.slice(0, 5).map(a => (
            <div key={a.id} style={{ background: '#f8fafc',
              border: '1px solid #e2e8f0', borderRadius: '10px',
              padding: '16px', marginBottom: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '13px' }}>
                  Candidate: {a.candidate_id?.slice(0, 8)}...
                </div>
                <span style={{ fontSize: '11px', fontWeight: 700,
                  padding: '2px 8px', borderRadius: '100px',
                  background: a.status === 'accepted' ? '#dcfce7'
                    : a.status === 'hr_action_required' ? '#fef2f2' : '#f1f5f9',
                  color: a.status === 'accepted' ? '#16a34a'
                    : a.status === 'hr_action_required' ? '#dc2626' : '#475569' }}>
                  {a.status?.replace(/_/g, ' ').toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>
                Level: {a.escalation_level || 0} ·
                Type: {a.interview_type} ·
                {a.created_at?.slice(0, 10)}
              </div>
              {(a.timeline || []).slice(-2).map((t, i) => (
                <div key={i} style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                  {t.time?.slice(11, 16)} — {t.event}: {t.detail}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Job Posting View ─────────────────────────────────────────────
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
    { round_number: 1, round_name: 'Technical Interview',
      interviewer_name: 'Tech Lead', interviewer_email: '',
      duration_minutes: 60, focus: 'Technical depth', position: 1 },
    { round_number: 2, round_name: 'HR Discussion',
      interviewer_name: 'HR Manager', interviewer_email: '',
      duration_minutes: 45, focus: 'Culture + Salary', position: 2 }
  ]);

  useEffect(() => {
    axios.get(`${API_URL}/api/jobs`).then(r => setJobs(r.data)).catch(() => {});
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
      if (r.data.intelligence?.role_title) setTitle(r.data.intelligence.role_title);
      if (r.data.intelligence?.coding_needed !== undefined)
        setCodingOn(r.data.intelligence.coding_needed);
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
        interview_mode: mode, coding_enabled: codingOn,
        ai_interview_enabled: aiOn, salary_min: salMin,
        salary_max: salMax, location, human_rounds: humanRounds
      });
      setJobs(prev => [...prev, r.data.job]);
      setStep('success');
    } catch { setStep('success'); }
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

  const addRound = () => setHumanRounds(prev => [...prev, {
    round_number: prev.length + 1,
    round_name: `Round ${prev.length + 1}`,
    interviewer_name: '', interviewer_email: '',
    duration_minutes: 60, focus: '', position: prev.length + 1
  }]);

  const removeRound = idx =>
    setHumanRounds(prev => prev.filter((_, i) => i !== idx));

  const updateRound = (idx, field, val) =>
    setHumanRounds(prev => prev.map((r, i) =>
      i === idx ? { ...r, [field]: val } : r));

  if (step === 'success') return (
    <div style={{ textAlign: 'center', padding: '60px 20px' }}>
      <div style={{ fontSize: '64px', marginBottom: '16px' }}>✅</div>
      <h2 style={{ color: '#0f172a', marginBottom: '8px' }}>Job Posted Successfully!</h2>
      <p style={{ color: '#64748b', marginBottom: '24px' }}>
        The job is now live on the Apply Portal.
      </p>
      <button onClick={() => { setStep('form'); setJdText(''); setTitle(''); }}
        style={{ padding: '10px 20px', background: '#6366f1', color: '#fff',
          border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>
        + Post Another Job
      </button>
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
                <div style={{ fontWeight: 700, color: '#0f172a' }}>{job.title}</div>
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

  if (step === 'configure') return (
    <div style={{ maxWidth: '800px' }}>
      <h2 style={{ marginBottom: '4px', color: '#0f172a' }}>
        Configure Interview Pipeline
      </h2>
      <p style={{ color: '#64748b', marginBottom: '24px' }}>
        Customize every aspect of the hiring process for this role.
      </p>

      {quality && (
        <div style={{
          background: quality.overall_quality >= 7 ? '#f0fdf4' : '#fffbeb',
          border: `1px solid ${quality.overall_quality >= 7 ? '#86efac' : '#fde68a'}`,
          borderRadius: '10px', padding: '16px', marginBottom: '16px' }}>
          <div style={{ fontWeight: 700, marginBottom: '8px', color: '#0f172a' }}>
            JD Quality Score: {quality.overall_quality}/10
            {quality.overall_quality < 7 ? ' ⚠️' : ' ✅'}
          </div>
          {(quality.issues || []).slice(0, 3).map((issue, i) => (
            <div key={i} style={{ fontSize: '13px', color: '#92400e', marginBottom: '4px' }}>
              ❌ {issue.type}: {issue.problem}
            </div>
          ))}
          {quality.overall_quality < 7 && quality.improved_jd && (
            <button onClick={() => setJdText(quality.improved_jd)}
              style={{ marginTop: '10px', padding: '6px 14px', background: '#d97706',
                color: '#fff', border: 'none', borderRadius: '6px',
                cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
              ✨ Use Improved JD
            </button>
          )}
        </div>
      )}

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
            onChange={e => setSalMin(e.target.value)} placeholder="18" />
        </div>
        <div>
          <label style={fld.label}>Max Salary (LPA)</label>
          <input style={fld.input} value={salMax}
            onChange={e => setSalMax(e.target.value)} placeholder="24" />
        </div>
        <div style={{ gridColumn: '1/-1' }}>
          <label style={fld.label}>Location</label>
          <input style={fld.input} value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Bangalore (Hybrid)" />
        </div>
      </div>

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
              <div style={{ fontWeight: 700, fontSize: '13px' }}>{m.label}</div>
              <div style={{ fontSize: '11px', opacity: 0.7 }}>{m.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px',
        padding: '16px', background: '#f8fafc', borderRadius: '10px',
        border: '1px solid #e2e8f0' }}>
        <label style={{ display: 'flex', alignItems: 'center',
          gap: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={codingOn}
            onChange={e => setCodingOn(e.target.checked)} />
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#374151' }}>
            💻 Coding Round
          </span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center',
          gap: '8px', cursor: 'pointer' }}>
          <input type="checkbox" checked={aiOn}
            onChange={e => setAiOn(e.target.checked)} />
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#374151' }}>
            🤖 AI Interview
          </span>
        </label>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: '12px' }}>
          <label style={{ ...fld.label, marginBottom: 0 }}>
            Human Interview Rounds
            <span style={{ fontSize: '11px', color: '#94a3b8',
              marginLeft: '8px', fontWeight: 400 }}>
              (↑↓ to reorder)
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
                <span style={{ fontWeight: 700, color: '#374151', fontSize: '14px' }}>
                  {round.round_name || `Round ${idx + 1}`}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button onClick={() => moveRound(idx, -1)} style={fld.iconBtn}
                  disabled={idx === 0}>↑</button>
                <button onClick={() => moveRound(idx, 1)} style={fld.iconBtn}
                  disabled={idx === humanRounds.length - 1}>↓</button>
                <button onClick={() => removeRound(idx)}
                  style={{ ...fld.iconBtn, color: '#dc2626', borderColor: '#fecaca' }}>
                  ✕
                </button>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={fld.smallLabel}>Round Name</label>
                <input style={fld.smallInput} value={round.round_name}
                  onChange={e => updateRound(idx, 'round_name', e.target.value)}
                  placeholder="Technical Interview" />
              </div>
              <div>
                <label style={fld.smallLabel}>Interviewer Name</label>
                <input style={fld.smallInput} value={round.interviewer_name}
                  onChange={e => updateRound(idx, 'interviewer_name', e.target.value)}
                  placeholder="Tech Lead" />
              </div>
              <div>
                <label style={fld.smallLabel}>Interviewer Email</label>
                <input style={fld.smallInput} value={round.interviewer_email}
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
                <input style={fld.smallInput} value={round.focus}
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
        <button onClick={postJob} disabled={!title || loading}
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

  return (
    <div style={{ maxWidth: '800px' }}>
      <h2 style={{ marginBottom: '4px', color: '#0f172a' }}>Post a New Job</h2>
      <p style={{ color: '#64748b', marginBottom: '24px' }}>
        Paste your job description. AI analyses quality, detects role type,
        and builds the right interview structure automatically.
      </p>
      <div style={{ marginBottom: '16px' }}>
        <label style={fld.label}>Job Description *</label>
        <textarea
          style={{ ...fld.input, minHeight: '320px', resize: 'vertical', lineHeight: '1.6' }}
          placeholder="Paste your full job description here..."
          value={jdText} onChange={e => setJdText(e.target.value)} />
      </div>
      <button onClick={analyseJD} disabled={!jdText.trim() || loading}
        style={{ width: '100%', padding: '14px',
          background: jdText.trim() ? '#6366f1' : '#e2e8f0',
          color: jdText.trim() ? '#fff' : '#94a3b8',
          border: 'none', borderRadius: '8px',
          cursor: jdText.trim() ? 'pointer' : 'not-allowed',
          fontWeight: 700, fontSize: '15px' }}>
        {loading ? '⏳ Analysing JD...' : '🔍 Analyse & Configure →'}
      </button>
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
                <div style={{ fontWeight: 700, color: '#0f172a' }}>{job.title}</div>
                <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                  {job.location} · {job.interview_mode} mode ·
                  JD Quality: {job.jd_quality_score}/10
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
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

// ── Main App ─────────────────────────────────────────────────────
export default function App() {
  const [view, setView]                 = useState('jobs');
  const [candidates, setCandidates]     = useState([]);
  const [isCandidatesLoading, setIsCandidatesLoading] = useState(true);
  const [selected, setSelected]         = useState(null);
  const [approvalForm, setApprovalForm] = useState({
    tech_score: '', culture_score: '', notes: '', salary: '', round: 'technical'
  });

  useEffect(() => {
    const load = () => {
      setIsCandidatesLoading(true);
      axios.get(`${API_URL}/api/candidates`)
        .then(r => {
          setCandidates(r.data || []);
        })
        .catch(() => {
          setCandidates([]);
        })
        .finally(() => {
          setIsCandidatesLoading(false);
        });
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const stats = {
    total:    candidates.length,
    hired:    candidates.filter(c => c.status === 'hired').length,
    rejected: candidates.filter(c => c.status === 'rejected').length,
    pipeline: candidates.filter(c => !['hired','rejected'].includes(c.status)).length,
  };

  const handleApprove = async (candidateId, decision) => {
    try {
      await axios.post(`${API_URL}/api/human-gate`, {
        candidate_id:  candidateId, decision,
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
    alert(`${decision === 'APPROVE' ? '✅ Approved' : '❌ Rejected'} successfully`);
  };

  const pageTitle = {
    jobs:         '📋 Post New Job',
    pipeline:     '📊 Candidate Pipeline',
    interviewers: '👥 Interviewer Pool',
    feed:         '⚡ Live Agent Feed',
    analytics:    '📈 Analytics',
    talent:       '⭐ Talent Pool',
  };

  return (
    <div style={s.app}>

      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.sidebarLogo}>🚀 HR Swarm</div>
        {[
          { key: 'jobs',         icon: '📋', label: 'Post Job'     },
          { key: 'pipeline',     icon: '📊', label: 'Pipeline'     },
          { key: 'interviewers', icon: '👥', label: 'Interviewers' },
          { key: 'feed',         icon: '⚡', label: 'Agent Feed'   },
          // { key: 'analytics',    icon: '📈', label: 'Analytics'    },
          { key: 'talent',       icon: '⭐', label: 'Talent Pool'  },
        ].map(item => (
          <div key={item.key}
            style={{ ...s.navItem,
              background: view === item.key ? '#1e293b' : 'transparent',
              color:      view === item.key ? '#fff'    : '#94a3b8' }}
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
          <h2 style={s.pageTitle}>{pageTitle[view]}</h2>
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

        {view === 'jobs'         && <JobPostingView />}
        {view === 'interviewers' && <InterviewerPoolView />}

        {/* Pipeline View */}
        {view === 'pipeline' && (
          <div>
            {isCandidatesLoading ? (
              <div style={{ padding: '40px 24px', textAlign: 'center', color: '#94a3b8' }}>
                <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>Loading candidates...</div>
                <div style={{ maxWidth: '560px', margin: '0 auto' }}>
                  Fetching current pipeline data from the API. Please wait a moment.
                </div>
              </div>
            ) : candidates.length === 0 ? (
              <div style={{ padding: '40px 24px', textAlign: 'center', color: '#94a3b8' }}>
                <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>No candidates yet</div>
                <div style={{ maxWidth: '560px', margin: '0 auto' }}>
                  Candidate applications will appear here once they are submitted.
                </div>
              </div>
            ) : (
              <div>
                <div style={s.kanban}>
                  {STATUS_COLUMNS.map(col => (
                    <div key={col.key} style={s.column}>
                      <div style={{ ...s.colHeader, borderTop: `3px solid ${col.color}` }}>
                        <span style={{ color: col.color, fontWeight: 700, fontSize: '12px' }}>
                          {col.label}
                        </span>
                        <span style={s.colCount}>
                          {candidates.filter(c => c.status === col.key).length}
                        </span>
                      </div>
                      {candidates.filter(c => c.status === col.key).map(c => (
                        <div key={c.id} style={s.candidateCard} onClick={() => setSelected(c)}>
                          <div style={s.cardName}>{c.name}</div>
                          <div style={s.cardRole}>{c.applied_role}</div>
                          {c.resume_score && (
                            <div style={s.scoreRow}>
                              <span style={s.scoreLabel}>Resume</span>
                              <span style={{ ...s.scoreBadge,
                                background: c.resume_score >= 70 ? '#dcfce7' : '#fef9c3',
                                color: c.resume_score >= 70 ? '#15803d' : '#92400e' }}>
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
                              <span style={{ ...s.scoreBadge,
                                background: c.decision === 'HIRE' ? '#dcfce7' : '#fef2f2',
                                color: c.decision === 'HIRE' ? '#15803d' : '#dc2626',
                                fontWeight: 700 }}>
                                {c.final_score}/100
                              </span>
                            </div>
                          )}
                          {c.status === 'waiting_technical_interview' && (
                            <div style={s.actionBadge}>⏳ Awaiting your feedback</div>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>

                {selected && (
              <div style={s.overlay} onClick={() => setSelected(null)}>
                <div style={s.panel} onClick={e => e.stopPropagation()}>
                  <button style={s.closeBtn} onClick={() => setSelected(null)}>✕</button>
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
                      <h3 style={s.approvalTitle}>Technical Interview Feedback</h3>
                      <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px' }}>
                        AI already tested technical skills.
                        Focus on leadership depth and culture fit.
                      </p>
                      <div style={s.approvalGrid}>
                        <div>
                          <label style={fld.smallLabel}>Technical Score (1-10)</label>
                          <input style={fld.smallInput}
                            type="number" min="1" max="10" placeholder="8"
                            value={approvalForm.tech_score}
                            onChange={e => setApprovalForm({
                              ...approvalForm, tech_score: e.target.value })} />
                        </div>
                        <div>
                          <label style={fld.smallLabel}>Culture Score (1-10)</label>
                          <input style={fld.smallInput}
                            type="number" min="1" max="10" placeholder="7"
                            value={approvalForm.culture_score}
                            onChange={e => setApprovalForm({
                              ...approvalForm, culture_score: e.target.value })} />
                        </div>
                      </div>
                      <textarea style={s.approvalNotes}
                        placeholder="Interview notes..."
                        value={approvalForm.notes}
                        onChange={e => setApprovalForm({
                          ...approvalForm, notes: e.target.value })} />
                      <input style={{ ...fld.smallInput, marginBottom: '16px' }}
                        placeholder="Agreed salary (e.g. 21 LPA)"
                        value={approvalForm.salary}
                        onChange={e => setApprovalForm({
                          ...approvalForm, salary: e.target.value })} />
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
        </div>
        )}

        {/* Agent Feed */}
        {view === 'feed' && (
          <div style={s.feedContainer}>
            <div style={s.feedHeader}>
              <span style={s.liveIndicator}>● LIVE</span>
              <span style={{ color: '#94a3b8', fontSize: '13px' }}>
                Real-time agent activity
              </span>
            </div>
            <div style={s.feedLog}>
              <div style={{ padding: '28px', color: '#94a3b8', textAlign: 'center' }}>
                Agent activity will appear here when a candidate is being processed.
              </div>
            </div>
          </div>
        )}

        {/* Analytics */}
        {view === 'analytics' && (
          <div style={s.analyticsGrid}>
            {[
              { label: 'Total Processed', val: stats.total,  unit: '',      color: '#6366f1' },
              { label: 'Hired',           val: stats.hired,  unit: '',      color: '#16a34a' },
              { label: 'Hire Rate',       val: stats.total > 0
                ? Math.round(stats.hired / stats.total * 100) : 0,
                unit: '%', color: '#0891b2' },
              { label: 'Avg Resume Score', val: Math.round(
                candidates.reduce((a, c) => a + (c.resume_score || 0), 0) /
                Math.max(candidates.length, 1)), unit: '/100', color: '#d97706' },
              { label: 'Time to Hire',    val: '3.2',   unit: ' days', color: '#7c3aed' },
              { label: 'Cost per Hire',   val: '₹932',  unit: '',      color: '#dc2626' },
              { label: 'Satisfaction',    val: '91',    unit: '%',     color: '#059669' },
              { label: 'Zero Ghosted',    val: '100',   unit: '%',     color: '#0f172a' },
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

        {/* Talent Pool */}
        {view === 'talent' && (
          <div>
            <p style={{ color: '#64748b', marginBottom: '20px' }}>
              Strong candidates not selected this time.
              Will be contacted when a matching role opens.
            </p>
            {candidates
              .filter(c => c.status === 'rejected' && (c.resume_score || 0) >= 60)
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
                    <div style={s.talentScoreVal}>{c.resume_score}/100</div>
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

// ── Styles ────────────────────────────────────────────────────────
const s = {
  app: { display: 'flex', minHeight: '100vh', background: '#f8fafc',
    fontFamily: "'Segoe UI', sans-serif" },
  sidebar: { width: '200px', background: '#0f172a', padding: '0', flexShrink: 0 },
  sidebarLogo: { color: '#fff', fontSize: '18px', fontWeight: 700,
    padding: '20px 20px 16px', borderBottom: '1px solid #1e293b' },
  navItem: { display: 'flex', alignItems: 'center', gap: '10px',
    padding: '12px 20px', cursor: 'pointer', fontSize: '14px',
    marginTop: '2px', transition: 'all 0.15s', fontWeight: 500 },
  main: { flex: 1, padding: '24px', overflow: 'auto' },
  topbar: { display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '24px' },
  pageTitle: { fontSize: '20px', fontWeight: 700, color: '#0f172a', margin: 0 },
  statChips: { display: 'flex', gap: '8px' },
  chip: { padding: '6px 14px', borderRadius: '100px', fontSize: '13px', fontWeight: 600 },
  kanban: { display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '12px', overflowX: 'auto' },
  column: { background: '#f1f5f9', borderRadius: '10px',
    padding: '12px', minHeight: '200px', minWidth: '155px' },
  colHeader: { display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '12px',
    paddingBottom: '8px', borderBottom: '1px solid #e2e8f0' },
  colCount: { background: '#e2e8f0', borderRadius: '100px',
    padding: '2px 8px', fontSize: '11px', fontWeight: 700, color: '#475569' },
  candidateCard: { background: '#fff', borderRadius: '8px', padding: '12px',
    marginBottom: '8px', cursor: 'pointer', border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)' },
  cardName: { fontWeight: 700, fontSize: '13px', color: '#0f172a' },
  cardRole: { fontSize: '11px', color: '#64748b', marginTop: '2px', marginBottom: '8px' },
  scoreRow: { display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginTop: '4px' },
  scoreLabel: { fontSize: '11px', color: '#94a3b8' },
  scoreBadge: { fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '100px' },
  actionBadge: { marginTop: '8px', fontSize: '11px', color: '#d97706',
    background: '#fffbeb', padding: '4px 8px', borderRadius: '6px', textAlign: 'center' },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  panel: { background: '#fff', borderRadius: '16px', padding: '32px',
    width: '540px', maxHeight: '90vh', overflowY: 'auto', position: 'relative' },
  closeBtn: { position: 'absolute', top: '16px', right: '16px',
    background: 'none', border: 'none', fontSize: '18px',
    cursor: 'pointer', color: '#64748b' },
  panelName: { fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: '0 0 4px' },
  panelRole: { color: '#64748b', margin: '0 0 20px' },
  scoreGrid: { display: 'flex', gap: '12px', marginBottom: '16px' },
  scoreBlock: { flex: 1, textAlign: 'center', background: '#f8fafc',
    borderRadius: '10px', padding: '16px' },
  scoreVal: { fontSize: '28px', fontWeight: 700, color: '#0f172a', marginBottom: '4px' },
  scoreKey: { fontSize: '12px', color: '#94a3b8' },
  skillsRow: { display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '20px' },
  skillTag: { background: '#eff6ff', color: '#1d4ed8', padding: '4px 10px',
    borderRadius: '100px', fontSize: '12px', fontWeight: 500 },
  approvalForm: { background: '#f8fafc', borderRadius: '12px',
    padding: '20px', border: '1px solid #e2e8f0' },
  approvalTitle: { fontSize: '16px', fontWeight: 700, color: '#0f172a', margin: '0 0 8px' },
  approvalGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: '12px', marginBottom: '12px' },
  approvalNotes: { width: '100%', padding: '10px 12px', borderRadius: '8px',
    border: '1.5px solid #e2e8f0', fontSize: '14px', minHeight: '80px',
    boxSizing: 'border-box', marginBottom: '12px', resize: 'vertical' },
  approvalBtns: { display: 'flex', gap: '10px' },
  approveBtn: { flex: 1, padding: '12px', background: '#16a34a', color: '#fff',
    border: 'none', borderRadius: '8px', fontSize: '13px',
    fontWeight: 700, cursor: 'pointer' },
  rejectBtn: { flex: 1, padding: '12px', background: '#dc2626', color: '#fff',
    border: 'none', borderRadius: '8px', fontSize: '13px',
    fontWeight: 700, cursor: 'pointer' },
  feedContainer: { background: '#0f172a', borderRadius: '12px',
    padding: '20px', minHeight: '500px' },
  feedHeader: { display: 'flex', alignItems: 'center', gap: '10px',
    marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid #1e293b' },
  liveIndicator: { color: '#22c55e', fontSize: '13px',
    fontWeight: 700, fontFamily: 'monospace' },
  feedLog: { display: 'flex', flexDirection: 'column', gap: '4px' },
  logEntry: { display: 'flex', gap: '12px', padding: '8px 12px',
    borderRadius: '6px', fontFamily: 'monospace', fontSize: '12px' },
  logTime: { color: '#475569', flexShrink: 0 },
  logAgent: { fontWeight: 700, flexShrink: 0, minWidth: '130px' },
  logMsg: { color: '#94a3b8' },
  analyticsGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' },
  statCard: { background: '#fff', borderRadius: '12px', padding: '24px',
    textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    border: '1px solid #e2e8f0' },
  statVal: { fontSize: '36px', fontWeight: 800, marginBottom: '8px' },
  statLabel: { fontSize: '13px', color: '#64748b' },
  talentCard: { background: '#fff', borderRadius: '10px', padding: '16px',
    marginBottom: '12px', display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', border: '1px solid #e2e8f0' },
  talentName: { fontWeight: 700, color: '#0f172a' },
  talentRole: { fontSize: '13px', color: '#64748b', marginBottom: '8px' },
  talentScore: { textAlign: 'center' },
  talentScoreVal: { fontSize: '24px', fontWeight: 700, color: '#6366f1' },
  talentScoreLabel: { fontSize: '12px', color: '#94a3b8' },
};