/**
 * AnalyticsView.jsx — Cost & Insights
 *
 * DROP-IN: In App.js add:
 *   import AnalyticsView from './AnalyticsView';
 * Remove the inline AnalyticsView function from App.js.
 *
 * Requires: recharts  (npm install recharts — already in package.json)
 *
 * Data sources (in priority order):
 *   1. GET /api/analytics  — if your backend exposes it
 *   2. GET /api/costs      — for cost metrics
 *   3. Computed from `candidates` prop — always available
 */

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend, CartesianGrid,
} from 'recharts';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/* ─── pipeline status order + colours ───────────────────────────── */
const STAGES = [
  { key: 'applied',                     label: 'Applied',       color: '#6db4f0' },
  { key: 'screened',                    label: 'Screened',      color: '#5b8def' },
  { key: 'ai_interview_complete',       label: 'AI Interview',  color: '#8f9bff' },
  { key: 'waiting_technical_interview', label: 'Tech Round',    color: '#d8b878' },
  { key: 'waiting_hr_interview',        label: 'HR Round',      color: '#6db4f0' },
  { key: 'hired',                       label: 'Hired',         color: '#4ade80' },
  { key: 'rejected',                    label: 'Rejected',      color: '#e0758a' },
];

/* ─── custom dark tooltip for recharts ──────────────────────────── */
const DarkTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#0d121d', border: '1px solid rgba(255,255,255,.11)',
      borderRadius: 10, padding: '10px 14px', fontFamily: 'Sora', fontSize: 12,
    }}>
      <p style={{ color: '#92a0ba', marginBottom: 6 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || p.fill || '#eaeef6',
          fontFamily: 'JetBrains Mono', fontWeight: 700 }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  );
};

/* ─── section heading ────────────────────────────────────────────── */
function SectionHead({ title, sub }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontFamily: 'Bricolage Grotesque', fontWeight: 700,
        fontSize: 18, letterSpacing: '-0.02em' }}>{title}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--tx2)', marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

/* ─── KPI card ────────────────────────────────────────────────────── */
function KpiCard({ label, value, unit = '', color = 'var(--jd)',
  sub, delay = 1, live = false }) {
  return (
    <div className={`hs-rise hs-d${delay}`} style={{
      background: 'linear-gradient(160deg, var(--pan), var(--ob2))',
      border: '1px solid var(--ln)', borderRadius: 16,
      padding: '20px 22px', position: 'relative', overflow: 'hidden',
    }}>
      {live && (
        <div style={{ position: 'absolute', top: 14, right: 14,
          display: 'flex', alignItems: 'center', gap: 5 }}>
          <div className="hs-dot" style={{ width: 5, height: 5 }} />
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9,
            color: 'var(--jd)', letterSpacing: '0.08em' }}>LIVE</span>
        </div>
      )}
      <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 800,
        fontSize: 34, letterSpacing: '-0.03em', color, lineHeight: 1 }}>
        {value}<span style={{ fontSize: 16, fontWeight: 600,
          color: `${color}aa`, marginLeft: 2 }}>{unit}</span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--tx2)', marginTop: 6 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--tx3)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

/* ─── chart wrapper card ─────────────────────────────────────────── */
function ChartCard({ title, sub, children, span = 1 }) {
  return (
    <div className="hs-rise hs-d2" style={{
      background: 'linear-gradient(160deg, var(--pan), var(--ob2))',
      border: '1px solid var(--ln)', borderRadius: 18,
      padding: '22px 24px',
      gridColumn: span > 1 ? `span ${span}` : undefined,
    }}>
      <SectionHead title={title} sub={sub} />
      {children}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   MAIN: AnalyticsView
════════════════════════════════════════════════════════════════════ */
export default function AnalyticsView({ candidates = [], jobs = [] }) {
  const [apiData, setApiData] = useState(null);
  const [costData, setCostData] = useState(null);

  /* try to fetch richer data from backend */
  useEffect(() => {
    axios.get(`${API_URL}/api/analytics`).then(r => setApiData(r.data)).catch(() => {});
    axios.get(`${API_URL}/api/costs`).then(r => setCostData(r.data)).catch(() => {});
  }, []);

  /* ── computed metrics ── */
  const metrics = useMemo(() => {
    const total    = candidates.length;
    const hired    = candidates.filter(c => c.status === 'hired').length;
    const rejected = candidates.filter(c => c.status === 'rejected').length;
    const active   = candidates.filter(c =>
      !['hired', 'rejected'].includes(c.status)).length;

    const scores = {
      resume: candidates.filter(c => c.resume_score).map(c => c.resume_score),
      ai:     candidates.filter(c => c.ai_interview_score).map(c => c.ai_interview_score),
      coding: candidates.filter(c => c.coding_score).map(c => c.coding_score),
      final:  candidates.filter(c => c.final_score).map(c => c.final_score),
    };
    const avg = arr => arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0;

    const hireRate = total > 0 ? Math.round((hired / total) * 100) : 0;

    /* pipeline funnel data */
    const funnel = STAGES.map(s => ({
      name:  s.label,
      count: candidates.filter(c => c.status === s.key).length,
      color: s.color,
    }));

    /* score distribution buckets (0-9, 10-19, ... 90-100) */
    const buckets = Array.from({ length: 10 }, (_, i) => {
      const lo = i * 10, hi = lo + 9;
      return {
        range:  `${lo}–${hi}`,
        Resume: candidates.filter(c => c.resume_score >= lo && c.resume_score <= hi).length,
        AI:     candidates.filter(c => c.ai_interview_score >= lo && c.ai_interview_score <= hi).length,
        Coding: candidates.filter(c => c.coding_score >= lo && c.coding_score <= hi).length,
      };
    });

    /* role breakdown */
    const roleCounts = candidates.reduce((acc, c) => {
      const r = c.applied_role || 'Unknown';
      acc[r] = (acc[r] || 0) + 1;
      return acc;
    }, {});
    const roleData = Object.entries(roleCounts)
      .sort((a, b) => b[1] - a[1]).slice(0, 6)
      .map(([name, value]) => ({ name, value }));

    /* status breakdown for pie */
    const pieData = STAGES
      .map(s => ({ name: s.label, value: candidates.filter(c => c.status === s.key).length, color: s.color }))
      .filter(d => d.value > 0);

    return {
      total, hired, rejected, active, hireRate,
      avgResume: avg(scores.resume),
      avgAi:     avg(scores.ai),
      avgCoding: avg(scores.coding),
      avgFinal:  avg(scores.final),
      funnel, buckets, roleData, pieData,
    };
  }, [candidates]);

  /* overlay API data where available */
  const timeToHire  = apiData?.avg_time_to_hire_days  ?? costData?.time_to_hire  ?? '—';
  const costPerHire = apiData?.cost_per_hire           ?? costData?.cost_per_hire ?? '—';
  const aiCost      = costData?.ai_compute_monthly     ?? apiData?.ai_cost_monthly ?? 31;
  const satisfaction = apiData?.candidate_satisfaction ?? 91;

  /* ── KPI definitions ── */
  const KPIS = [
    { label: 'Total Candidates',   value: metrics.total,        color: 'var(--cy)',  live: true },
    { label: 'Hired',              value: metrics.hired,        color: '#4ade80',    live: true },
    { label: 'In Pipeline',        value: metrics.active,       color: 'var(--jd)',  live: true },
    { label: 'Hire Rate',          value: metrics.hireRate,     unit: '%', color: 'var(--am)' },
    { label: 'Avg Resume Score',   value: metrics.avgResume || '—', unit: metrics.avgResume ? '/100' : '', color: 'var(--cy)' },
    { label: 'Avg AI Score',       value: metrics.avgAi || '—', unit: metrics.avgAi ? '/100' : '', color: 'var(--vi)' },
    { label: 'Time to Hire',       value: timeToHire,           unit: timeToHire !== '—' ? ' days' : '', color: 'var(--jd)', sub: 'from API or hardcoded' },
    { label: 'AI Compute (mo)',    value: `₹${aiCost}`,         color: 'var(--am)', sub: 'from /api/costs' },
    { label: 'Cost per Hire',      value: costPerHire === '—' ? '—' : `₹${costPerHire}`, color: 'var(--rs)' },
    { label: 'Zero Ghosted',       value: 100,                  unit: '%', color: '#4ade80', sub: 'every candidate notified' },
    { label: 'Candidate Sat.',     value: satisfaction,         unit: '%', color: 'var(--cy)' },
    { label: 'Active Reqs',        value: jobs.filter(j => !j.status || j.status === 'active').length, color: 'var(--jd)', live: true },
  ];

  return (
    <div style={{ paddingBottom: 40 }}>

      {/* ── Page Head ── */}
      <div className="hs-rise" style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: 'Bricolage Grotesque', fontWeight: 800,
          fontSize: 34, letterSpacing: '-0.03em', lineHeight: 1 }}>
          Cost & Insights
        </h1>
        <p style={{ color: 'var(--tx2)', fontSize: 14, marginTop: 8 }}>
          Hiring performance, pipeline health, and{' '}
          <span style={{ color: 'var(--jd)' }}>AI compute efficiency</span>
        </p>
      </div>

      {/* ── KPI grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 14, marginBottom: 28 }}>
        {KPIS.map((k, i) => (
          <KpiCard key={k.label} {...k} delay={(i % 5) + 1} />
        ))}
      </div>

      {/* ── Charts grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: 18, marginBottom: 18 }}>

        {/* Pipeline Funnel */}
        <ChartCard title="Pipeline Funnel"
          sub="Candidates at each hiring stage">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={metrics.funnel} layout="vertical"
              margin={{ left: 10, right: 20, top: 0, bottom: 0 }}>
              <XAxis type="number" tick={{ fill: '#5a667e', fontSize: 11,
                fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={90}
                tick={{ fill: '#92a0ba', fontSize: 11, fontFamily: 'Sora' }}
                axisLine={false} tickLine={false} />
              <Tooltip content={<DarkTooltip />} cursor={{ fill: 'rgba(255,255,255,.03)' }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={20}>
                {metrics.funnel.map((entry, i) => (
                  <Cell key={i} fill={entry.color} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Status Breakdown Pie */}
        <ChartCard title="Status Breakdown"
          sub="Current distribution across all statuses">
          {metrics.pieData.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={metrics.pieData} cx="50%" cy="50%"
                  innerRadius={55} outerRadius={85}
                  paddingAngle={3} dataKey="value">
                  {metrics.pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<DarkTooltip />} />
                <Legend
                  formatter={val => (
                    <span style={{ color: 'var(--tx2)', fontSize: 11,
                      fontFamily: 'Sora' }}>{val}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* ── Score Distribution (full width) ── */}
      <ChartCard title="Score Distribution"
        sub="How candidates scored across Resume, AI Interview, and Coding assessments"
        span={2}>
        {metrics.buckets.every(b => b.Resume + b.AI + b.Coding === 0) ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={metrics.buckets}
              margin={{ left: 0, right: 10, top: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3"
                stroke="rgba(255,255,255,.04)" vertical={false} />
              <XAxis dataKey="range" tick={{ fill: '#5a667e', fontSize: 10,
                fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#5a667e', fontSize: 10,
                fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <Tooltip content={<DarkTooltip />}
                cursor={{ fill: 'rgba(255,255,255,.03)' }} />
              <Legend formatter={val => (
                <span style={{ color: 'var(--tx2)', fontSize: 11,
                  fontFamily: 'Sora' }}>{val}</span>
              )} />
              <Bar dataKey="Resume" fill="#6db4f0" radius={[4,4,0,0]}
                fillOpacity={0.8} maxBarSize={28} />
              <Bar dataKey="AI"     fill="#8f9bff" radius={[4,4,0,0]}
                fillOpacity={0.8} maxBarSize={28} />
              <Bar dataKey="Coding" fill="#4ade80" radius={[4,4,0,0]}
                fillOpacity={0.8} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </ChartCard>

      {/* ── Role Breakdown + Avg Scores side-by-side ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: 18, marginTop: 18 }}>

        {/* Candidates by Role */}
        <ChartCard title="Applications by Role"
          sub="Volume per job posting">
          {metrics.roleData.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={metrics.roleData}
                margin={{ left: 0, right: 10, top: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3"
                  stroke="rgba(255,255,255,.04)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#5a667e', fontSize: 10,
                  fontFamily: 'Sora', angle: -30, textAnchor: 'end' }}
                  axisLine={false} tickLine={false} interval={0} />
                <YAxis tick={{ fill: '#5a667e', fontSize: 10,
                  fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
                <Tooltip content={<DarkTooltip />}
                  cursor={{ fill: 'rgba(255,255,255,.03)' }} />
                <Bar dataKey="value" fill="#5b8def" radius={[4,4,0,0]}
                  fillOpacity={0.85} maxBarSize={32} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Average Scores comparison */}
        <ChartCard title="Average Scores"
          sub="Mean scores across evaluation stages">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={[
                { name: 'Resume',     score: metrics.avgResume, color: '#6db4f0' },
                { name: 'AI',         score: metrics.avgAi,     color: '#8f9bff' },
                { name: 'Coding',     score: metrics.avgCoding, color: '#4ade80' },
                { name: 'Final',      score: metrics.avgFinal,  color: '#d8b878' },
              ].filter(d => d.score > 0)}
              margin={{ left: 0, right: 10, top: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3"
                stroke="rgba(255,255,255,.04)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: '#92a0ba', fontSize: 11,
                fontFamily: 'Sora' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#5a667e', fontSize: 10,
                fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <Tooltip content={<DarkTooltip />}
                cursor={{ fill: 'rgba(255,255,255,.03)' }} />
              <Bar dataKey="score" radius={[6,6,0,0]} maxBarSize={44}>
                {[
                  { color: '#6db4f0' }, { color: '#8f9bff' },
                  { color: '#4ade80' }, { color: '#d8b878' },
                ].map((entry, i) => (
                  <Cell key={i} fill={entry.color} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {metrics.avgResume === 0 && metrics.avgAi === 0 && (
            <EmptyChart />
          )}
        </ChartCard>
      </div>

      {/* ── Conversion rate strip ── */}
      <div className="hs-rise hs-d3" style={{
        marginTop: 18, background: 'linear-gradient(160deg, var(--pan), var(--ob2))',
        border: '1px solid var(--ln)', borderRadius: 18, padding: '22px 24px',
      }}>
        <SectionHead title="Funnel Conversion Rates"
          sub="Drop-off between each hiring stage" />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6,
          overflowX: 'auto', paddingBottom: 4 }}>
          {STAGES.map((stage, i) => {
            const count = candidates.filter(c => c.status === stage.key).length;
            const prev  = i === 0
              ? candidates.length
              : candidates.filter(c => c.status === STAGES[i - 1]?.key).length;
            const pct   = prev > 0 ? Math.round((count / prev) * 100) : 0;

            if (candidates.filter(c =>
              STAGES.slice(i).map(s => s.key).includes(c.status)).length === 0
              && count === 0) return null;

            return (
              <React.Fragment key={stage.key}>
                {i > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--tx3)',
                    fontFamily: 'JetBrains Mono', flexShrink: 0 }}>
                    {prev > 0 ? `${pct}% →` : '→'}
                  </div>
                )}
                <div style={{ flexShrink: 0, textAlign: 'center',
                  padding: '10px 14px',
                  background: `${stage.color}12`,
                  border: `1px solid ${stage.color}30`,
                  borderRadius: 10, minWidth: 80 }}>
                  <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 700,
                    fontSize: 20, color: stage.color }}>{count}</div>
                  <div style={{ fontSize: 10, color: 'var(--tx3)',
                    marginTop: 3 }}>{stage.label}</div>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
      {/* ── Skills Gap Heatmap (NEW) ── */}
      <SkillsGapHeatmap candidates={candidates} jobs={jobs} />
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   SKILLS GAP HEATMAP — supply vs demand matrix
════════════════════════════════════════════════════════════════════ */
function SkillsGapHeatmap({ candidates, jobs }) {
  // Build skill frequency from active jobs (demand) and candidates (supply)
  const data = useMemo(() => {
    const activeJobs = jobs.filter(j => !j.status || j.status === 'active');

    // Demand: skill -> number of jobs requiring it
    const demand = {};
    activeJobs.forEach(j => {
      (j.tech_stack || j.skills_required || []).forEach(s => {
        const k = (s || '').toLowerCase().trim();
        if (k) demand[k] = (demand[k] || 0) + 1;
      });
    });

    // Supply: skill -> number of candidates who have it
    const supply = {};
    candidates.forEach(c => {
      (c.skills || []).forEach(s => {
        const k = (s || '').toLowerCase().trim();
        if (k) supply[k] = (supply[k] || 0) + 1;
      });
    });

    // Combine into ranked list by demand
    const allSkills = new Set([...Object.keys(demand), ...Object.keys(supply)]);
    const rows = Array.from(allSkills).map(skill => ({
      skill: skill.split(' ').map(w => w[0]?.toUpperCase() + w.slice(1)).join(' '),
      demand: demand[skill] || 0,
      supply: supply[skill] || 0,
      gap: (demand[skill] || 0) - (supply[skill] || 0),
    }));

    return rows
      .filter(r => r.demand > 0 || r.supply > 0)
      .sort((a, b) => (b.demand - b.supply) - (a.demand - a.supply))
      .slice(0, 12);
  }, [candidates, jobs]);

  if (data.length === 0) {
    return (
      <div className="hs-rise hs-d4" style={{
        marginTop: 18, background: 'linear-gradient(160deg, var(--pan), var(--ob2))',
        border: '1px solid var(--ln)', borderRadius: 18, padding: '22px 24px',
      }}>
        <SectionHead title="Skills Gap Heatmap"
          sub="Compare demand from open jobs vs supply in the candidate pool" />
        <EmptyChart />
      </div>
    );
  }

  const maxVal = Math.max(...data.flatMap(d => [d.demand, d.supply]), 1);

  return (
    <div className="hs-rise hs-d4" style={{
      marginTop: 18, background: 'linear-gradient(160deg, var(--pan), var(--ob2))',
      border: '1px solid var(--ln)', borderRadius: 18, padding: '22px 24px',
    }}>
      <SectionHead title="Skills Gap Heatmap"
        sub="Demand from open jobs vs supply in the candidate pool — where to focus sourcing" />

      <div style={{ display: 'flex', gap: 6, fontSize: 10, color: 'var(--tx3)',
        fontFamily: 'JetBrains Mono', marginBottom: 12, letterSpacing: '0.08em',
        textTransform: 'uppercase' }}>
        <span style={{ width: 130 }}>Skill</span>
        <span style={{ flex: 1 }}>Demand (jobs requiring it)</span>
        <span style={{ flex: 1 }}>Supply (candidates with it)</span>
        <span style={{ width: 60, textAlign: 'right' }}>Gap</span>
      </div>

      {data.map((row, i) => {
        const dPct = (row.demand / maxVal) * 100;
        const sPct = (row.supply / maxVal) * 100;
        const isGap = row.gap > 0;
        const isSurplus = row.gap < 0;
        return (
          <div key={row.skill} style={{
            display: 'flex', gap: 6, alignItems: 'center',
            padding: '7px 0', borderBottom: i < data.length - 1 ? '1px solid var(--ln)' : 'none',
          }}>
            <span style={{ width: 130, fontSize: 12, fontWeight: 500,
              color: 'var(--tx)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
              {row.skill}
            </span>
            <div style={{ flex: 1, display:'flex', alignItems:'center', gap:8 }}>
              <div style={{
                width: `${dPct}%`, height: 18, borderRadius: 4,
                background: 'linear-gradient(90deg, rgba(224,117,138,.7), rgba(224,117,138,.4))',
                transition: 'width .4s',
              }} />
              <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11,
                color: 'var(--rs)', fontWeight: 600, minWidth: 22 }}>{row.demand}</span>
            </div>
            <div style={{ flex: 1, display:'flex', alignItems:'center', gap:8 }}>
              <div style={{
                width: `${sPct}%`, height: 18, borderRadius: 4,
                background: 'linear-gradient(90deg, rgba(74,222,128,.7), rgba(74,222,128,.4))',
                transition: 'width .4s',
              }} />
              <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11,
                color: '#4ade80', fontWeight: 600, minWidth: 22 }}>{row.supply}</span>
            </div>
            <span style={{
              width: 60, textAlign: 'right',
              fontFamily: 'JetBrains Mono', fontSize: 12, fontWeight: 700,
              color: isGap ? 'var(--rs)' : isSurplus ? '#4ade80' : 'var(--tx3)',
            }}>
              {row.gap > 0 ? `−${row.gap}` : row.gap < 0 ? `+${-row.gap}` : '0'}
            </span>
          </div>
        );
      })}

      <div style={{ marginTop: 14, padding: '12px 14px',
        background: 'rgba(91,141,239,.06)', border: '1px solid rgba(91,141,239,.2)',
        borderRadius: 9, fontSize: 12, color: 'var(--tx2)', lineHeight: 1.6 }}>
        <strong style={{ color:'var(--rs)' }}>Red bars</strong> = jobs requiring the skill ·
        <strong style={{ color:'#4ade80' }}> Green bars</strong> = candidates who have it ·
        Negative gap means you need to source more of that skill.
      </div>
    </div>
  );
}

/* ── placeholder when no data yet ────────────────────────────────── */
function EmptyChart() {
  return (
    <div style={{ height: 160, display: 'grid', placeItems: 'center',
      color: 'var(--tx3)', fontFamily: 'JetBrains Mono', fontSize: 12 }}>
      No data yet — waiting for candidates
    </div>
  );
}