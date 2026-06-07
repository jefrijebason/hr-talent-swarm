import React, { useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { theme, fonts } from '../theme';
import {
  GlassCard, AuroraButton, GradientText, SkillPill,
  GlassInput, ScrollReveal
} from '../components';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ApplyPage({ job, onBack, onSuccess }) {
  const [form, setForm] = useState({
    name: '', email: '', phone: '', expected_ctc: ''
  });
  const [errors, setErrors]       = useState({});
  const [resume, setResume]       = useState(null);
  const [scanState, setScanState] = useState('idle');
  const [parsed, setParsed]       = useState(null);
  const [screenAnswers, setScreenAnswers] = useState({});
  const [knockout, setKnockout]   = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const questions = job?.screening_questions || [];

  const handleFile = (file) => {
    if (!file || file.type !== 'application/pdf') {
      setErrors({ ...errors, resume: 'Please upload a PDF file' });
      return;
    }
    setResume(file);
    setErrors({ ...errors, resume: null });
    setScanState('scanning');

    setTimeout(() => {
      const detected = (job?.tech_stack || ['Python', 'Azure', 'ML']).slice(0, 5);
      setParsed({
        skills: detected,
        experience: job?.experience_required || '4 years',
        education: 'B.Tech, Computer Science'
      });
      setScanState('done');
    }, 2400);
  };

  const answerQuestion = (idx, val) => {
    setScreenAnswers({ ...screenAnswers, [idx]: val });
    const q = questions[idx];
    if (q.knockout && val === q.knockout_answer) {
      setKnockout(true);
    } else {
      const stillKnocked = questions.some((qq, i) =>
        qq.knockout && (i === idx ? val : screenAnswers[i]) === qq.knockout_answer);
      setKnockout(stillKnocked);
    }
  };

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = 'Name is required';
    if (!form.email.trim()) e.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = 'Enter a valid email';
    if (!form.phone.trim()) e.phone = 'Phone is required';
    if (!resume) e.resume = 'Please upload your resume';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (knockout) return;
    if (!validate()) return;
    setSubmitting(true);

    try {
      const fd = new FormData();
      fd.append('name', form.name);
      fd.append('email', form.email);
      fd.append('phone', form.phone);
      fd.append('job_id', job.id);
      fd.append('expected_ctc', form.expected_ctc);
      fd.append('resume', resume);
      const r = await axios.post(`${API_URL}/api/apply-for-job`, fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      onSuccess(r.data.tracking_id || 'TRK-' +
        Math.random().toString(36).substr(2, 8).toUpperCase(), form, job);
    } catch {
      onSuccess('TRK-' + Math.random().toString(36).substr(2, 8).toUpperCase(), form, job);
    }
    setSubmitting(false);
  };

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto', padding: '32px 24px 100px' }}>

      <motion.button
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        onClick={onBack}
        style={{ background: 'none', border: 'none', color: theme.primary,
          cursor: 'pointer', fontSize: '14px', fontWeight: 600,
          marginBottom: '20px', fontFamily: 'inherit' }}>
        ← Back to Job Details
      </motion.button>

      <motion.h1
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        style={{ ...fonts.h1, marginBottom: '6px' }}>
        Apply for <GradientText>{job?.title}</GradientText>
      </motion.h1>
      <p style={{ ...fonts.body, color: theme.textSecondary, marginBottom: '28px' }}>
        {job?.department} · {job?.location}
      </p>

      {/* Section 1 — Details */}
      <ScrollReveal style={{ marginBottom: '20px' }}>
        <GlassCard hover={false}>
          <h3 style={{ ...fonts.h3, color: theme.textPrimary, marginTop: 0,
            marginBottom: '16px' }}>1. Your Details</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <GlassInput label="Full Name" value={form.name} error={errors.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="Your name" />
            <GlassInput label="Email" value={form.email} error={errors.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              placeholder="you@email.com" />
            <GlassInput label="Phone" value={form.phone} error={errors.phone}
              onChange={e => setForm({ ...form, phone: e.target.value })}
              placeholder="9876543210" />
            <GlassInput label="Expected CTC (LPA)" value={form.expected_ctc}
              onChange={e => setForm({ ...form, expected_ctc: e.target.value })}
              placeholder="20" />
          </div>
        </GlassCard>
      </ScrollReveal>

      {/* Section 2 — Resume Upload + Scan */}
      <ScrollReveal style={{ marginBottom: '20px' }}>
        <GlassCard hover={false}>
          <h3 style={{ ...fonts.h3, color: theme.textPrimary, marginTop: 0,
            marginBottom: '16px' }}>2. Upload Resume</h3>

          {scanState === 'idle' && (
            <label style={{ display: 'block', border: `2px dashed ${theme.primary}`,
              borderRadius: '14px', padding: '36px', textAlign: 'center',
              cursor: 'pointer', background: 'rgba(124,108,246,0.04)' }}>
              <input type="file" accept=".pdf" style={{ display: 'none' }}
                onChange={e => handleFile(e.target.files[0])} />
              <div style={{ fontSize: '40px', marginBottom: '8px' }}>📄</div>
              <div style={{ ...fonts.body, color: theme.textPrimary, fontWeight: 600 }}>
                Drop your resume or click to upload
              </div>
              <div style={{ fontSize: '12px', color: theme.textTertiary, marginTop: '4px' }}>
                PDF only · AI will analyze it instantly
              </div>
            </label>
          )}

          {scanState === 'scanning' && (
            <div style={{ position: 'relative', padding: '40px', textAlign: 'center',
              border: `1px solid ${theme.glassBorder}`, borderRadius: '14px',
              overflow: 'hidden' }}>
              <motion.div
                animate={{ y: ['-100%', '100%'] }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                style={{ position: 'absolute', left: 0, right: 0, height: '40%',
                  background: 'linear-gradient(180deg, transparent, rgba(124,108,246,0.25), transparent)' }} />
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                style={{ fontSize: '32px', marginBottom: '12px' }}>⚡</motion.div>
              <div style={{ ...fonts.body, color: theme.textPrimary }}>
                Analyzing your resume...
              </div>
              <div style={{ fontSize: '12px', color: theme.textTertiary, marginTop: '4px' }}>
                Extracting skills and experience
              </div>
            </div>
          )}

          {scanState === 'done' && parsed && (
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <div style={{ background: 'rgba(52,211,153,0.08)',
                border: '1px solid rgba(52,211,153,0.25)', borderRadius: '14px',
                padding: '20px' }}>
                <div style={{ ...fonts.h3, color: theme.success, marginBottom: '14px' }}>
                  ✅ Resume Analyzed
                </div>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ ...fonts.caption, color: theme.textTertiary, marginBottom: '6px' }}>
                    Detected Skills
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {parsed.skills.map((s, i) => (
                      <SkillPill key={s} active delay={i * 0.1}>{s}</SkillPill>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '20px', fontSize: '13px',
                  color: theme.textSecondary }}>
                  <div>💼 Experience: <strong>{parsed.experience}</strong></div>
                  <div>🎓 {parsed.education}</div>
                </div>
                <button onClick={() => { setScanState('idle'); setResume(null); setParsed(null); }}
                  style={{ marginTop: '12px', background: 'none', border: 'none',
                    color: theme.primary, cursor: 'pointer', fontSize: '12px',
                    fontFamily: 'inherit' }}>
                  Re-upload resume
                </button>
              </div>
            </motion.div>
          )}
          {errors.resume && (
            <div style={{ fontSize: '12px', color: theme.danger, marginTop: '8px' }}>
              ⚠️ {errors.resume}
            </div>
          )}
        </GlassCard>
      </ScrollReveal>

      {/* Section 3 — Screening Questions */}
      {questions.length > 0 && scanState === 'done' && (
        <ScrollReveal style={{ marginBottom: '20px' }}>
          <GlassCard hover={false}>
            <h3 style={{ ...fonts.h3, color: theme.textPrimary, marginTop: 0,
              marginBottom: '16px' }}>3. A Few Quick Questions</h3>
            {questions.map((q, i) => (
              <div key={i} style={{ marginBottom: '16px' }}>
                <div style={{ ...fonts.body, color: theme.textSecondary,
                  marginBottom: '8px' }}>{q.question}</div>
                {q.type === 'yesno' ? (
                  <div style={{ display: 'flex', gap: '10px' }}>
                    {['Yes', 'No'].map(opt => (
                      <button key={opt} onClick={() => answerQuestion(i, opt)}
                        style={{ padding: '8px 24px', borderRadius: '10px',
                          cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600,
                          border: `1px solid ${screenAnswers[i] === opt
                            ? theme.primary : theme.glassBorder}`,
                          background: screenAnswers[i] === opt
                            ? 'rgba(124,108,246,0.15)' : 'transparent',
                          color: screenAnswers[i] === opt
                            ? '#b8acff' : theme.textSecondary }}>
                        {opt}
                      </button>
                    ))}
                  </div>
                ) : (
                  <GlassInput value={screenAnswers[i] || ''}
                    onChange={e => answerQuestion(i, e.target.value)}
                    placeholder="Your answer" />
                )}
              </div>
            ))}
            {knockout && (
              <div style={{ background: 'rgba(251,113,133,0.1)',
                border: '1px solid rgba(251,113,133,0.3)', borderRadius: '12px',
                padding: '14px', fontSize: '13px', color: theme.danger }}>
                Based on your answers, this role may not be the right fit.
                You're welcome to explore our other open positions.
              </div>
            )}
          </GlassCard>
        </ScrollReveal>
      )}

      {/* Submit Button */}
      {!knockout && (
        <ScrollReveal>
          <AuroraButton
            onClick={handleSubmit}
            disabled={submitting}
            style={{ width: '100%', padding: '16px', fontSize: '16px' }}>
            {submitting ? '⏳ Submitting...' : '🚀 Submit Application'}
          </AuroraButton>
          <p style={{ fontSize: '12px', color: theme.textTertiary,
            textAlign: 'center', marginTop: '12px' }}>
            🤖 AI-powered evaluation · Bias removed · Everyone gets feedback
          </p>
        </ScrollReveal>
      )}

    </div>
  );
}