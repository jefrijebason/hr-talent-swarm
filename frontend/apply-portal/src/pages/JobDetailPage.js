import React from 'react';
import { motion } from 'framer-motion';
import { theme, fonts } from '../theme';
import {
  GlassCard, AuroraButton, GradientText, SkillPill,
  StatChip, ScrollReveal, Stagger, StaggerItem
} from '../components';

export default function JobDetailPage({ job, onBack, onApply }) {
  if (!job) return null;

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '32px 24px 100px' }}>

      {/* Back */}
      <motion.button
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        onClick={onBack}
        style={{ background: 'none', border: 'none', color: theme.primary,
          cursor: 'pointer', fontSize: '14px', fontWeight: 600,
          marginBottom: '20px', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', gap: '6px' }}>
        ← Back to All Jobs
      </motion.button>

      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}>
        <GlassCard hover={false} glow style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
            alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1 style={{ ...fonts.h1, margin: '0 0 8px' }}>
                <GradientText>{job.title}</GradientText>
              </h1>
              <div style={{ fontSize: '14px', color: theme.textTertiary }}>
                {job.department} · {job.location}
              </div>
            </div>
            <span style={{ background: 'rgba(52,211,153,0.12)', color: theme.success,
              padding: '6px 14px', borderRadius: '100px', fontSize: '12px',
              fontWeight: 700 }}>● HIRING</span>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}>
            <StatChip icon="💰" label="Salary" value={`₹${job.salary_min}-${job.salary_max}L`} />
            <StatChip icon="💼" label="Experience" value={job.experience_required} />
            <StatChip icon="📋" label="Type" value={job.employment_type} />
            <StatChip icon="🏠" label="Mode" value={job.work_mode} />
          </div>

          <AuroraButton full onClick={onApply}>
            Apply for this Position →
          </AuroraButton>
        </GlassCard>
      </motion.div>

      {/* About the Company */}
      {job.company_about && (
        <ScrollReveal style={{ marginBottom: '20px' }}>
          <GlassCard hover={false}>
            <SectionTitle icon="📋">About the Company</SectionTitle>
            <p style={{ ...fonts.body, color: theme.textSecondary, margin: 0 }}>
              {job.company_about}
            </p>
          </GlassCard>
        </ScrollReveal>
      )}

      {/* Team You'll Join */}
      {job.team_name && (
        <ScrollReveal style={{ marginBottom: '20px' }}>
          <GlassCard hover={false}>
            <SectionTitle icon="🎯">The Team You'll Join</SectionTitle>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '160px',
                background: 'rgba(124,108,246,0.06)', borderRadius: '12px',
                padding: '14px', border: `1px solid ${theme.glassBorder}` }}>
                <div style={{ ...fonts.caption, color: theme.textTertiary }}>Team</div>
                <div style={{ ...fonts.h3, color: theme.textPrimary, marginTop: '4px' }}>
                  {job.team_name}
                </div>
                <div style={{ fontSize: '13px', color: theme.textSecondary, marginTop: '2px' }}>
                  {job.team_size}
                </div>
              </div>
              <div style={{ flex: 1, minWidth: '160px',
                background: 'rgba(34,211,238,0.06)', borderRadius: '12px',
                padding: '14px', border: `1px solid ${theme.glassBorder}` }}>
                <div style={{ ...fonts.caption, color: theme.textTertiary }}>You'll Report To</div>
                <div style={{ ...fonts.h3, color: theme.textPrimary, marginTop: '4px' }}>
                  {job.reports_to}
                </div>
              </div>
            </div>
          </GlassCard>
        </ScrollReveal>
      )}

      {/* Why Work Here */}
      {(job.why_work_here || []).length > 0 && (
        <ScrollReveal style={{ marginBottom: '20px' }}>
          <GlassCard hover={false}>
            <SectionTitle icon="✨">Why Work Here</SectionTitle>
            <Stagger style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {job.why_work_here.map((w, i) => (
                <StaggerItem key={i}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: theme.success, fontSize: '16px' }}>✓</span>
                    <span style={{ ...fonts.body, color: theme.textSecondary }}>{w}</span>
                  </div>
                </StaggerItem>
              ))}
            </Stagger>
          </GlassCard>
        </ScrollReveal>
      )}

      {/* Job Description */}
      <ScrollReveal style={{ marginBottom: '20px' }}>
        <GlassCard hover={false}>
          <SectionTitle icon="📝">Role Description</SectionTitle>
          <div style={{ ...fonts.body, color: theme.textSecondary,
            whiteSpace: 'pre-wrap' }}>
            {job.jd_text}
          </div>
        </GlassCard>
      </ScrollReveal>

      {/* Skills */}
      <ScrollReveal style={{ marginBottom: '20px' }}>
        <GlassCard hover={false}>
          <SectionTitle icon="🛠">Skills We're Looking For</SectionTitle>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {(job.tech_stack || []).map(s => <SkillPill key={s} active>{s}</SkillPill>)}
          </div>
        </GlassCard>
      </ScrollReveal>

      {/* Benefits */}
      {(job.benefits || []).length > 0 && (
        <ScrollReveal style={{ marginBottom: '20px' }}>
          <GlassCard hover={false}>
            <SectionTitle icon="🎁">Benefits & Perks</SectionTitle>
            <div style={{ display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '10px' }}>
              {job.benefits.map((b, i) => (
                <motion.div key={b}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                  style={{ background: 'rgba(255,255,255,0.03)',
                    border: `1px solid ${theme.glassBorder}`, borderRadius: '12px',
                    padding: '12px 14px', fontSize: '13px', color: theme.textSecondary,
                    textAlign: 'center' }}>
                  {b}
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </ScrollReveal>
      )}

      {/* Hiring Timeline */}
      {(job.hiring_timeline || []).length > 0 && (
        <ScrollReveal style={{ marginBottom: '24px' }}>
          <GlassCard hover={false}>
            <SectionTitle icon="⏱">What to Expect</SectionTitle>
            <div style={{ position: 'relative', paddingLeft: '24px' }}>
              <div style={{ position: 'absolute', left: '7px', top: '8px', bottom: '8px',
                width: '2px', background: theme.gradient, opacity: 0.4 }} />
              {job.hiring_timeline.map((t, i) => (
                <motion.div key={i}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  style={{ position: 'relative', marginBottom: '16px' }}>
                  <div style={{ position: 'absolute', left: '-24px', top: '4px',
                    width: '10px', height: '10px', borderRadius: '50%',
                    background: theme.primary,
                    boxShadow: '0 0 10px rgba(124,108,246,0.6)' }} />
                  <div style={{ ...fonts.h3, color: theme.textPrimary, fontSize: '15px' }}>
                    {t.stage}
                  </div>
                  <div style={{ fontSize: '13px', color: theme.textTertiary }}>
                    {t.time}
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </ScrollReveal>
      )}

      {/* Final Apply CTA */}
      <ScrollReveal>
        <div style={{ textAlign: 'center' }}>
          <AuroraButton onClick={onApply}
            style={{ padding: '16px 48px', fontSize: '16px' }}>
            Apply for this Position →
          </AuroraButton>
          <p style={{ fontSize: '12px', color: theme.textTertiary, marginTop: '14px' }}>
            🤖 AI-powered evaluation · Bias removed before review · Everyone gets feedback
          </p>
        </div>
      </ScrollReveal>
    </div>
  );
}

function SectionTitle({ icon, children }) {
  return (
    <h3 style={{ ...fonts.h2, color: theme.textPrimary,
      margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
      <span>{icon}</span> {children}
    </h3>
  );
}