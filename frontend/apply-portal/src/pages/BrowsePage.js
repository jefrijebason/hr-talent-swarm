import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { theme, fonts } from '../theme';
import {
  GlassCard, AuroraButton, GradientText, SkillPill,
  GlassInput, StatChip, ScrollReveal, AnimatedCounter
} from '../components';
import { FILTER_OPTIONS } from '../mockData';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function BrowsePage({ onSelectJob }) {
  const [jobs, setJobs]         = useState([]);
  const [selected, setSelected] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch]     = useState('');
  const [loc, setLoc]           = useState('All Locations');
  const [dept, setDept]         = useState('All Departments');
  const [exp, setExp]           = useState('All Levels');
  const [isMobile, setIsMobile] = useState(window.innerWidth < 900);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 900);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

useEffect(() => {
  let isFirst = true;

  const loadJobs = () => {
    const wasFirst = isFirst; // capture current state for this call
    if (wasFirst) setIsLoading(true);

    axios.get(`${API_URL}/api/jobs`)
      .then(r => {
        const activeJobs = (r.data || []).filter(j => j.status !== 'closed');
        setJobs(activeJobs);
        if (wasFirst) {
          setSelected(activeJobs[0] || null);
        } else {
          setSelected(prev =>
            activeJobs.find(j => j.id === prev?.id) || prev
          );
        }
      })
      .catch(() => {
        if (wasFirst) { setJobs([]); setSelected(null); }
      })
      .finally(() => {
        if (wasFirst) {
          setIsLoading(false);
          isFirst = false; // only flip AFTER loading state cleared
        }
      });
  };

  loadJobs();
  const t = setInterval(loadJobs, 10000);
  return () => clearInterval(t);
}, []);

  const filtered = jobs.filter(j => {
    const matchSearch = !search ||
      j.title?.toLowerCase().includes(search.toLowerCase()) ||
      (j.tech_stack || []).some(s => s.toLowerCase().includes(search.toLowerCase()));
    const matchLoc = loc === 'All Locations' || (j.location || '').includes(loc);
    const matchDept = dept === 'All Departments' || j.department === dept;
    return matchSearch && matchLoc && matchDept;
  });

  if (isLoading) {
    return (
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 24px 80px' }}>
        <div style={{ textAlign: 'center', marginBottom: '40px', opacity: 0.6 }}>
          <h1 style={{ ...fonts.display, margin: '0 0 14px' }}>
            <GradientText>Loading roles...</GradientText>
          </h1>
          <p style={{ ...fonts.body, color: theme.textSecondary, margin: '0' }}>Fetching live job listings</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '380px 1fr', gap: '20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {[1, 2, 3].map(i => (
              <motion.div key={i}
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}>
                <GlassCard style={{ padding: '18px', height: '140px', background: 'rgba(255,255,255,0.04)' }} />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    );
  }

 if (jobs.length === 0) {
    return (
      <div style={{ maxWidth: '600px', margin: '0 auto', padding: '80px 24px 100px', textAlign: 'center' }}>
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}>
          <div style={{ fontSize: '64px', marginBottom: '20px', opacity: 0.85 }}>🌱</div>
          <h2 style={{ ...fonts.h1, color: theme.textPrimary, marginBottom: '14px' }}>
            <GradientText>New opportunities coming soon</GradientText>
          </h2>
          <p style={{ ...fonts.body, color: theme.textSecondary,
            marginBottom: '8px', lineHeight: 1.7, maxWidth: '440px', margin: '0 auto 8px' }}>
            We're not actively hiring for any roles at this moment, but we're always
            growing and adding new positions.
          </p>
          <p style={{ ...fonts.body, color: theme.textSecondary,
            lineHeight: 1.7, maxWidth: '440px', margin: '0 auto' }}>
            This page refreshes automatically — check back soon, and you'll see new
            roles the instant they go live.
          </p>
        </motion.div>
      </div>
    );
  }
 

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 24px 80px' }}>

      <motion.div
        initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ ...fonts.display, margin: '0 0 14px' }}>
          <GradientText>Find Your Next Role</GradientText>
        </h1>
        <p style={{ ...fonts.body, color: theme.textSecondary, margin: '0 0 24px' }}>
          AI-powered hiring that's fair, fast, and transparent.
          Every candidate gets feedback.
        </p>
        <div style={{ display: 'flex', gap: '32px', justifyContent: 'center' }}>
          {[
            { n: 500, s: '+', l: 'Hired' },
            { n: 21, s: 's', l: 'AI Process' },
            { n: 100, s: '%', l: 'Get Feedback' },
          ].map(stat => (
            <div key={stat.l} style={{ textAlign: 'center' }}>
              <div style={{ ...fonts.h1, color: theme.textPrimary }}>
                <AnimatedCounter to={stat.n} suffix={stat.s} />
              </div>
              <div style={{ ...fonts.caption, color: theme.textTertiary }}>{stat.l}</div>
            </div>
          ))}
        </div>
      </motion.div>

      <ScrollReveal>
        <GlassCard hover={false} style={{ marginBottom: '28px' }}>
          <GlassInput
            placeholder="🔍  Search roles or skills..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ marginBottom: '14px' }}
          />
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {[
              { val: loc, set: setLoc, opts: FILTER_OPTIONS.locations },
              { val: dept, set: setDept, opts: FILTER_OPTIONS.departments },
              { val: exp, set: setExp, opts: FILTER_OPTIONS.experience },
            ].map((f, i) => (
              <select key={i} value={f.val} onChange={e => f.set(e.target.value)}
                style={{ padding: '10px 14px', borderRadius: '11px',
                  background: 'rgba(255,255,255,0.04)',
                  border: `1px solid ${theme.glassBorder}`,
                  color: theme.textSecondary, fontSize: '13px',
                  fontFamily: 'inherit', cursor: 'pointer', outline: 'none' }}>
                {f.opts.map(o => <option key={o} value={o} style={{ background: theme.surface }}>{o}</option>)}
              </select>
            ))}
            <div style={{ marginLeft: 'auto', alignSelf: 'center',
              fontSize: '13px', color: theme.textTertiary }}>
              {filtered.length} {filtered.length === 1 ? 'role' : 'roles'} found
            </div>
          </div>
        </GlassCard>
      </ScrollReveal>

      <div style={{ display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '380px 1fr', gap: '20px' }}>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filtered.map((job, i) => (
            <motion.div key={job.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.4 }}>
              <GlassCard
                onClick={() => isMobile ? onSelectJob(job) : setSelected(job)}
                glow={!isMobile && selected?.id === job.id}
                style={{ padding: '18px',
                  borderColor: !isMobile && selected?.id === job.id
                    ? theme.glassGlow : theme.glassBorder }}>
                <div style={{ ...fonts.h3, color: theme.textPrimary, marginBottom: '4px' }}>
                  {job.title}
                </div>
                <div style={{ fontSize: '12px', color: theme.textTertiary, marginBottom: '10px' }}>
                  {job.department} · {job.location}
                </div>
                <div style={{ fontSize: '13px', color: theme.textSecondary, marginBottom: '10px' }}>
                  ₹{job.salary_min}-{job.salary_max} LPA · {job.experience_required}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                  {(job.tech_stack || []).slice(0, 3).map(s => (
                    <SkillPill key={s}>{s}</SkillPill>
                  ))}
                  {(job.tech_stack || []).length > 3 && (
                    <SkillPill>+{job.tech_stack.length - 3}</SkillPill>
                  )}
                </div>
                <div style={{ marginTop: '10px', fontSize: '11px', color: theme.success }}>
                  ● Actively hiring · {job.posted_days_ago}d ago
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {!isMobile && selected && (
          <div style={{ position: 'sticky', top: '90px', alignSelf: 'start' }}>
            <AnimatePresence mode="wait">
              <motion.div key={selected.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}>
                <GlassCard hover={false} glow>
                  <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'flex-start', marginBottom: '16px' }}>
                    <div>
                      <h2 style={{ ...fonts.h1, color: theme.textPrimary, margin: '0 0 6px' }}>
                        {selected.title}
                      </h2>
                      <div style={{ fontSize: '14px', color: theme.textTertiary }}>
                        {selected.department} · {selected.location}
                      </div>
                    </div>
                    <span style={{ background: 'rgba(52,211,153,0.12)', color: theme.success,
                      padding: '5px 12px', borderRadius: '100px', fontSize: '11px',
                      fontWeight: 700 }}>HIRING</span>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap',
                    marginBottom: '20px' }}>
                    <StatChip icon="💰" label="Salary" value={`₹${selected.salary_min}-${selected.salary_max}L`} />
                    <StatChip icon="💼" label="Experience" value={selected.experience_required} />
                    <StatChip icon="📋" label="Type" value={selected.employment_type} />
                    <StatChip icon="🏠" label="Mode" value={selected.work_mode} />
                  </div>

                  <div style={{ marginBottom: '20px' }}>
                    <div style={{ ...fonts.caption, color: theme.textTertiary, marginBottom: '8px' }}>
                      Skills Required
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {(selected.tech_stack || []).map(s => <SkillPill key={s}>{s}</SkillPill>)}
                    </div>
                  </div>

                  <div style={{ marginBottom: '24px' }}>
                    <div style={{ ...fonts.caption, color: theme.textTertiary, marginBottom: '8px' }}>
                      About the Role
                    </div>
                    <p style={{ ...fonts.body, color: theme.textSecondary, margin: 0,
                      maxHeight: '120px', overflow: 'hidden' }}>
                      {selected.jd_text?.slice(0, 220)}...
                    </p>
                  </div>

                  <AuroraButton full onClick={() => onSelectJob(selected)}>
                    View Full Details & Apply →
                  </AuroraButton>
                </GlassCard>
              </motion.div>
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}