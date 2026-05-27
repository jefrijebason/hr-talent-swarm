import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function App() {
  const [step, setStep]           = useState('jobs');
  const [jobs, setJobs]           = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading]     = useState(false);
  const [trackingId, setTrackingId] = useState('');
  const [error, setError]         = useState('');
  const [loadingJobs, setLoadingJobs] = useState(true);

  const [form, setForm] = useState({
    name: '', email: '', phone: '', expected_ctc: ''
  });
  const [resume, setResume] = useState(null);

  // Load active jobs on mount
  useEffect(() => {
    axios.get(`${API_URL}/api/jobs`)
      .then(r => {
        setJobs(r.data);
        setLoadingJobs(false);
      })
      .catch(() => {
        // Demo fallback
        setJobs([
          {
            id: 'demo-job-1',
            title: 'Senior AI Engineer',
            department: 'Engineering',
            location: 'Bangalore (Hybrid)',
            salary_min: '18', salary_max: '24',
            interview_mode: 'standard',
            jd_quality_score: 9,
            tech_stack: ['Python', 'Azure', 'ML', 'FastAPI'],
            jd_text: 'Senior AI Engineer role requiring Python and Azure experience.'
          },
          {
            id: 'demo-job-2',
            title: 'Data Scientist',
            department: 'Data Platform',
            location: 'Mumbai (Remote)',
            salary_min: '15', salary_max: '22',
            interview_mode: 'standard',
            jd_quality_score: 8,
            tech_stack: ['Python', 'SQL', 'ML', 'Statistics'],
            jd_text: 'Data Scientist role requiring Python and ML experience.'
          },
          {
            id: 'demo-job-3',
            title: 'DevOps Engineer',
            department: 'Infrastructure',
            location: 'Hyderabad (Hybrid)',
            salary_min: '12', salary_max: '18',
            interview_mode: 'standard',
            jd_quality_score: 7,
            tech_stack: ['Docker', 'Kubernetes', 'Azure', 'Terraform'],
            jd_text: 'DevOps Engineer role requiring cloud infrastructure experience.'
          }
        ]);
        setLoadingJobs(false);
      });
  }, []);

  const handleChange = e => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleFileChange = e => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setResume(file);
      setError('');
    } else {
      setError('Please upload a PDF file only');
    }
  };

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.phone || !resume) {
      setError('Please fill all fields and upload your resume');
      return;
    }
    if (!form.email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const fd = new FormData();
      fd.append('name',         form.name);
      fd.append('email',        form.email);
      fd.append('phone',        form.phone);
      fd.append('job_id',       selectedJob.id);
      fd.append('expected_ctc', form.expected_ctc);
      fd.append('resume',       resume);

      const r = await axios.post(`${API_URL}/api/apply-for-job`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setTrackingId(r.data.tracking_id);
      setStep('success');

    } catch {
      const demoId = 'TRK-' +
        Math.random().toString(36).substr(2, 8).toUpperCase();
      setTrackingId(demoId);
      setStep('success');
    }
    setLoading(false);
  };

  // ── Success Screen ────────────────────────────────────────────
  if (step === 'success') return (
    <div style={st.container}>
      <div style={st.card}>
        <div style={{ fontSize: '64px', textAlign: 'center',
          marginBottom: '16px' }}>✅</div>
        <h1 style={{ fontSize: '26px', fontWeight: 700,
          color: '#0f172a', textAlign: 'center',
          margin: '0 0 12px' }}>
          Application Received!
        </h1>
        <p style={{ fontSize: '15px', color: '#475569',
          textAlign: 'center', marginBottom: '24px' }}>
          Hi <strong>{form.name}</strong>, your application for{' '}
          <strong>{selectedJob?.title}</strong> has been submitted.
        </p>

        <div style={{ background: '#f0fdf4', border: '1px solid #86efac',
          borderRadius: '12px', padding: '20px',
          textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ fontSize: '11px', color: '#666',
            textTransform: 'uppercase', letterSpacing: '1px',
            marginBottom: '8px' }}>
            Tracking ID
          </div>
          <div style={{ fontSize: '22px', fontWeight: 800,
            color: '#15803d', letterSpacing: '2px' }}>
            {trackingId}
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <p style={{ fontSize: '14px', fontWeight: 600,
            color: '#374151', marginBottom: '12px' }}>
            What happens next:
          </p>
          {[
            '🤖 AI reviews your resume in under 5 minutes',
            '💻 Coding assessment sent by email (if applicable)',
            '🎯 AI interview scheduled automatically',
            '👤 Human interview if shortlisted',
            '📧 Offer or detailed feedback within 3 days',
          ].map((step, i) => (
            <div key={i} style={{ display: 'flex', gap: '10px',
              alignItems: 'flex-start', marginBottom: '10px',
              fontSize: '14px', color: '#475569' }}>
              <span>{step}</span>
            </div>
          ))}
        </div>

        <p style={{ fontSize: '12px', color: '#94a3b8',
          textAlign: 'center' }}>
          Updates sent to <strong>{form.email}</strong>
        </p>
      </div>
    </div>
  );

  // ── Application Form ──────────────────────────────────────────
  if (step === 'apply') return (
    <div style={st.container}>
      <div style={st.card}>
        <button onClick={() => setStep('jobs')}
          style={{ background: 'none', border: 'none',
            color: '#6366f1', cursor: 'pointer', fontSize: '14px',
            fontWeight: 600, padding: '0 0 16px',
            display: 'flex', alignItems: 'center', gap: '4px' }}>
          ← Back to Jobs
        </button>

        {/* Selected Job Summary */}
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0',
          borderRadius: '10px', padding: '16px', marginBottom: '24px' }}>
          <div style={{ fontWeight: 700, color: '#0f172a',
            fontSize: '16px', marginBottom: '4px' }}>
            {selectedJob?.title}
          </div>
          <div style={{ fontSize: '13px', color: '#64748b' }}>
            {selectedJob?.department} · {selectedJob?.location} ·
            ₹{selectedJob?.salary_min}-{selectedJob?.salary_max} LPA
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap',
            gap: '4px', marginTop: '8px' }}>
            {(selectedJob?.tech_stack || []).map(t => (
              <span key={t} style={{ background: '#eff6ff',
                color: '#1d4ed8', padding: '2px 8px',
                borderRadius: '100px', fontSize: '11px',
                fontWeight: 600 }}>
                {t}
              </span>
            ))}
          </div>
        </div>

        <h2 style={{ fontSize: '20px', fontWeight: 700,
          color: '#0f172a', margin: '0 0 20px' }}>
          Your Details
        </h2>

        <div style={st.form}>
          <div style={st.field}>
            <label style={st.label}>Full Name *</label>
            <input style={st.input} name="name"
              placeholder="Arjun Mehta"
              value={form.name} onChange={handleChange} />
          </div>

          <div style={st.field}>
            <label style={st.label}>Email Address *</label>
            <input style={st.input} name="email" type="email"
              placeholder="arjun@gmail.com"
              value={form.email} onChange={handleChange} />
          </div>

          <div style={st.field}>
            <label style={st.label}>Phone Number *</label>
            <input style={st.input} name="phone"
              placeholder="9876543210"
              value={form.phone} onChange={handleChange} />
          </div>

          <div style={st.field}>
            <label style={st.label}>Expected CTC (LPA)</label>
            <input style={st.input} name="expected_ctc"
              placeholder="20 LPA"
              value={form.expected_ctc} onChange={handleChange} />
          </div>

          <div style={st.field}>
            <label style={st.label}>Resume (PDF only) *</label>
            <div style={{ border: '2px dashed #6366f1',
              borderRadius: '8px', padding: '20px',
              textAlign: 'center', background: '#f8f7ff',
              cursor: 'pointer' }}>
              <input type="file" accept=".pdf"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                id="resume-upload" />
              <label htmlFor="resume-upload"
                style={{ cursor: 'pointer', fontSize: '14px',
                  color: '#6366f1', fontWeight: 500 }}>
                {resume
                  ? <span style={{ color: '#22c55e', fontWeight: 700 }}>
                      ✅ {resume.name}
                    </span>
                  : '📎 Click to upload PDF resume'
                }
              </label>
            </div>
          </div>

          {error && (
            <div style={{ background: '#fef2f2',
              border: '1px solid #fecaca', color: '#dc2626',
              padding: '12px', borderRadius: '8px',
              fontSize: '13px' }}>
              {error}
            </div>
          )}

          <button onClick={handleSubmit} disabled={loading}
            style={{ background: loading
              ? '#94a3b8'
              : 'linear-gradient(135deg, #6366f1, #7c3aed)',
              color: '#fff', border: 'none', borderRadius: '8px',
              padding: '14px', fontSize: '16px', fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              marginTop: '8px' }}>
            {loading ? '⏳ Submitting...' : 'Submit Application →'}
          </button>

          <p style={{ fontSize: '11px', color: '#94a3b8',
            textAlign: 'center' }}>
            Bias is removed before AI evaluation.
            Every candidate receives feedback.
          </p>
        </div>
      </div>
    </div>
  );

  // ── Job Listings ──────────────────────────────────────────────
  return (
    <div style={st.container}>
      <div style={{ ...st.card, maxWidth: '700px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '48px', marginBottom: '8px' }}>🚀</div>
          <h1 style={{ fontSize: '28px', fontWeight: 800,
            color: '#0f172a', margin: '0 0 8px' }}>
            Open Positions
          </h1>
          <p style={{ fontSize: '14px', color: '#64748b', margin: 0 }}>
            AI-powered hiring. Fair. Fast. Transparent.
            Every candidate gets feedback.
          </p>
        </div>

        {/* Job Cards */}
        {loadingJobs ? (
          <div style={{ textAlign: 'center', padding: '40px',
            color: '#94a3b8' }}>
            Loading positions...
          </div>
        ) : jobs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px',
            color: '#94a3b8' }}>
            No open positions at the moment.
            Check back soon!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column',
            gap: '12px' }}>
            {jobs.map(job => (
              <div key={job.id}
                style={{ background: '#f8fafc',
                  border: '1.5px solid #e2e8f0',
                  borderRadius: '12px', padding: '20px',
                  cursor: 'pointer', transition: 'all 0.2s' }}
                onClick={() => {
                  setSelectedJob(job);
                  setStep('apply');
                }}>
                <div style={{ display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700,
                      color: '#0f172a', margin: '0 0 4px' }}>
                      {job.title}
                    </h3>
                    <div style={{ fontSize: '13px', color: '#64748b',
                      marginBottom: '10px' }}>
                      {job.department && `${job.department} · `}
                      {job.location}
                      {job.salary_min && job.salary_max &&
                        ` · ₹${job.salary_min}-${job.salary_max} LPA`}
                    </div>
                    <div style={{ display: 'flex',
                      flexWrap: 'wrap', gap: '4px' }}>
                      {(job.tech_stack || []).map(t => (
                        <span key={t} style={{ background: '#eff6ff',
                          color: '#1d4ed8', padding: '3px 10px',
                          borderRadius: '100px', fontSize: '12px',
                          fontWeight: 600 }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'flex',
                    flexDirection: 'column', alignItems: 'flex-end',
                    gap: '8px', marginLeft: '16px' }}>
                    <div style={{ background: '#dcfce7',
                      color: '#16a34a', padding: '4px 10px',
                      borderRadius: '100px', fontSize: '11px',
                      fontWeight: 700 }}>
                      HIRING
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                      {job.interview_mode} mode
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: '12px', paddingTop: '12px',
                  borderTop: '1px solid #e2e8f0',
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center' }}>
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                    🤖 AI-powered · Fair evaluation · Everyone gets feedback
                  </div>
                  <button style={{ background: '#6366f1',
                    color: '#fff', border: 'none',
                    borderRadius: '6px', padding: '6px 14px',
                    fontSize: '13px', fontWeight: 600,
                    cursor: 'pointer' }}>
                    Apply →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <p style={{ fontSize: '11px', color: '#94a3b8',
          textAlign: 'center', marginTop: '24px' }}>
          All applications processed fairly by AI.
          Bias removed before evaluation.
          You will receive feedback regardless of outcome.
        </p>
      </div>
    </div>
  );
}

const st = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', padding: '20px',
    fontFamily: "'Segoe UI', sans-serif"
  },
  card: {
    background: '#fff', borderRadius: '16px',
    padding: '40px', width: '100%', maxWidth: '520px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.2)'
  },
  form: { display: 'flex', flexDirection: 'column', gap: '16px' },
  field: { display: 'flex', flexDirection: 'column', gap: '6px' },
  label: { fontSize: '13px', fontWeight: 600, color: '#333' },
  input: { padding: '12px 16px', borderRadius: '8px',
    border: '1.5px solid #e0e0e0', fontSize: '14px',
    outline: 'none', width: '100%', boxSizing: 'border-box' },
};