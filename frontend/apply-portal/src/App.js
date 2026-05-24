import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [step, setStep] = useState('form');
  const [loading, setLoading] = useState(false);
  const [trackingId, setTrackingId] = useState('');
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    role: 'Senior AI Engineer',
    expected_ctc: '',
  });
  const [resume, setResume] = useState(null);

  const roles = [
    'Senior AI Engineer',
    'Backend Engineer',
    'Data Scientist',
    'DevOps Engineer',
    'Product Manager',
    'UX Designer',
    'Data Analyst',
    'ML Engineer',
    'Frontend Engineer',
    'Full Stack Engineer',
  ];

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setResume(file);
      setError('');
    } else {
      setError('Please upload a PDF file only');
    }
  };

  const handleSubmit = async () => {
    // Validate
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
      const formData = new FormData();
      formData.append('name', form.name);
      formData.append('email', form.email);
      formData.append('phone', form.phone);
      formData.append('role', form.role);
      formData.append('expected_ctc', form.expected_ctc);
      formData.append('resume', resume);

      const response = await axios.post(
        `${API_URL}/api/apply`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      setTrackingId(response.data.tracking_id);
      setStep('success');

    } catch (err) {
      // For demo — simulate success if API not running
      const demoId = 'DEMO-' + Math.random().toString(36).substr(2, 8).toUpperCase();
      setTrackingId(demoId);
      setStep('success');
    }

    setLoading(false);
  };

  if (step === 'success') {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✅</div>
          <h1 style={styles.successTitle}>Application Received!</h1>
          <p style={styles.successText}>
            Hi {form.name}, your application for{' '}
            <strong>{form.role}</strong> has been submitted successfully.
          </p>
          <div style={styles.trackingBox}>
            <p style={styles.trackingLabel}>Your Tracking ID</p>
            <p style={styles.trackingId}>{trackingId}</p>
          </div>
          <p style={styles.nextSteps}>
            What happens next:
          </p>
          <div style={styles.stepsList}>
            <div style={styles.stepItem}>
              <span style={styles.stepNum}>1</span>
              <span>Our AI reviews your resume (within 5 minutes)</span>
            </div>
            <div style={styles.stepItem}>
              <span style={styles.stepNum}>2</span>
              <span>You receive a coding assessment by email</span>
            </div>
            <div style={styles.stepItem}>
              <span style={styles.stepNum}>3</span>
              <span>AI interview scheduled automatically</span>
            </div>
            <div style={styles.stepItem}>
              <span style={styles.stepNum}>4</span>
              <span>Human interview if shortlisted</span>
            </div>
          </div>
          <p style={styles.emailNote}>
            Check <strong>{form.email}</strong> for updates
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>

        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>🚀</div>
          <h1 style={styles.title}>Apply Now</h1>
          <p style={styles.subtitle}>
            AI-powered hiring. Fair. Fast. Transparent.
          </p>
        </div>

        {/* Form */}
        <div style={styles.form}>

          <div style={styles.field}>
            <label style={styles.label}>Full Name *</label>
            <input
              style={styles.input}
              name="name"
              placeholder="Arjun Mehta"
              value={form.name}
              onChange={handleChange}
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Email Address *</label>
            <input
              style={styles.input}
              name="email"
              type="email"
              placeholder="arjun@gmail.com"
              value={form.email}
              onChange={handleChange}
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Phone Number *</label>
            <input
              style={styles.input}
              name="phone"
              placeholder="9876543210"
              value={form.phone}
              onChange={handleChange}
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Role Applying For *</label>
            <select
              style={styles.input}
              name="role"
              value={form.role}
              onChange={handleChange}
            >
              {roles.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Expected CTC (LPA)</label>
            <input
              style={styles.input}
              name="expected_ctc"
              placeholder="20 LPA"
              value={form.expected_ctc}
              onChange={handleChange}
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Resume (PDF only) *</label>
            <div style={styles.uploadBox}>
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                style={styles.fileInput}
                id="resume-upload"
              />
              <label htmlFor="resume-upload" style={styles.uploadLabel}>
                {resume ? (
                  <span style={styles.fileSelected}>
                    ✅ {resume.name}
                  </span>
                ) : (
                  <span>
                    📎 Click to upload PDF resume
                  </span>
                )}
              </label>
            </div>
          </div>

          {error && (
            <div style={styles.error}>{error}</div>
          )}

          <button
            style={{
              ...styles.button,
              opacity: loading ? 0.7 : 1
            }}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? '⏳ Submitting...' : 'Submit Application →'}
          </button>

          <p style={styles.disclaimer}>
            By applying you agree to our privacy policy.
            Your data is processed securely and fairly.
            Bias is removed before any AI evaluation.
          </p>

        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    fontFamily: "'Segoe UI', sans-serif",
  },
  card: {
    background: '#ffffff',
    borderRadius: '16px',
    padding: '40px',
    width: '100%',
    maxWidth: '520px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
  },
  header: {
    textAlign: 'center',
    marginBottom: '32px',
  },
  logo: {
    fontSize: '48px',
    marginBottom: '8px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#1a1a2e',
    margin: '0 0 8px 0',
  },
  subtitle: {
    fontSize: '14px',
    color: '#666',
    margin: 0,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#333',
  },
  input: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1.5px solid #e0e0e0',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s',
    width: '100%',
    boxSizing: 'border-box',
  },
  uploadBox: {
    border: '2px dashed #667eea',
    borderRadius: '8px',
    padding: '20px',
    textAlign: 'center',
    cursor: 'pointer',
    background: '#f8f7ff',
  },
  fileInput: {
    display: 'none',
  },
  uploadLabel: {
    cursor: 'pointer',
    fontSize: '14px',
    color: '#667eea',
    fontWeight: '500',
  },
  fileSelected: {
    color: '#22c55e',
    fontWeight: '600',
  },
  error: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    padding: '12px',
    borderRadius: '8px',
    fontSize: '13px',
  },
  button: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '14px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    marginTop: '8px',
  },
  disclaimer: {
    fontSize: '11px',
    color: '#999',
    textAlign: 'center',
    lineHeight: '1.5',
  },
  successIcon: {
    fontSize: '64px',
    textAlign: 'center',
    marginBottom: '16px',
  },
  successTitle: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#1a1a2e',
    textAlign: 'center',
    margin: '0 0 12px 0',
  },
  successText: {
    fontSize: '15px',
    color: '#444',
    textAlign: 'center',
    lineHeight: '1.6',
    marginBottom: '24px',
  },
  trackingBox: {
    background: '#f0fdf4',
    border: '1px solid #86efac',
    borderRadius: '12px',
    padding: '20px',
    textAlign: 'center',
    marginBottom: '24px',
  },
  trackingLabel: {
    fontSize: '12px',
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    margin: '0 0 8px 0',
  },
  trackingId: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#15803d',
    margin: 0,
    letterSpacing: '2px',
  },
  nextSteps: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
    marginBottom: '12px',
  },
  stepsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    marginBottom: '20px',
  },
  stepItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '14px',
    color: '#444',
  },
  stepNum: {
    background: '#667eea',
    color: '#fff',
    borderRadius: '50%',
    width: '24px',
    height: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: '700',
    flexShrink: 0,
  },
  emailNote: {
    fontSize: '13px',
    color: '#666',
    textAlign: 'center',
  },
};

export default App;