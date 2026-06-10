import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const AGENTS = {
  scout:    { label: 'SCOUT',    color: '#6db4f0', icon: '🔍' },
  aria:     { label: 'ARIA',     color: '#8f9bff', icon: '🤖' },
  coder:    { label: 'CODER',    color: '#4ade80', icon: '💻' },
  scorer:   { label: 'SCORER',   color: '#d8b878', icon: '📊' },
  notifier: { label: 'NOTIFY',   color: '#6db4f0', icon: '📧' },
  guardian: { label: 'GUARDIAN', color: '#e0758a', icon: '🛡' },
  system:   { label: 'SYSTEM',   color: '#5a667e', icon: '⚙' },
};

const agentKey = raw => {
  const s = (raw || '').toLowerCase();
  for (const k of Object.keys(AGENTS)) if (s.includes(k)) return k;
  return 'system';
};

const levelColor = lvl => {
  const l = (lvl || '').toLowerCase();
  if (l.includes('error') || l.includes('fail'))   return '#e0758a';
  if (l.includes('warn'))                           return '#d8b878';
  if (l.includes('success') || l.includes('done')) return '#4ade80';
  return '#5a667e';
};

function FeedEntry({ event: e, highlight }) {
  const key   = agentKey(e.agent || e.agent_type || e.source);
  const agent = AGENTS[key];
  const time  = e.timestamp || e.time || e.created_at;
  const msg   = e.message || e.msg || e.detail || e.event || '';
  return (
    <div style={{ display:'flex', padding:'4px 0',
      borderLeft: highlight ? `2px solid ${agent.color}` : '2px solid transparent' }}
      onMouseEnter={ev => ev.currentTarget.style.background='rgba(255,255,255,0.025)'}
      onMouseLeave={ev => ev.currentTarget.style.background='transparent'}>
      <span style={{ color:'#3d4d61', width:68, flexShrink:0, paddingLeft:16, fontSize:11, paddingTop:1 }}>
        {time ? new Date(time).toLocaleTimeString('en-IN',
          { hour:'2-digit', minute:'2-digit', second:'2-digit' }) : '--:--:--'}
      </span>
      <span style={{ width:76, flexShrink:0, fontWeight:700, fontSize:10,
        color:agent.color, letterSpacing:'0.06em', paddingTop:1 }}>
        [{agent.label}]
      </span>
      <span style={{ width:56, flexShrink:0, fontSize:10, paddingTop:1,
        color:levelColor(e.level||e.type), textTransform:'uppercase' }}>
        {String(e.level||e.type||'info').slice(0,7)}
      </span>
      <span style={{ flex:1, color:'#92a0ba', lineHeight:1.65, fontSize:12, paddingRight:16 }}>
        {msg}
        {e.candidate_id && <span style={{ color:'#5b8def', marginLeft:8 }}>#{e.candidate_id.slice(0,8)}</span>}
        {e.score != null && <span style={{ color:'#d8b878', marginLeft:8 }}>score={e.score}</span>}
      </span>
    </div>
  );
}

function AgentChip({ label, count, active, onClick, color, icon }) {
  return (
    <div onClick={onClick} style={{
      display:'flex', alignItems:'center', gap:7, padding:'7px 13px',
      borderRadius:9, cursor:'pointer', userSelect:'none',
      background: active ? `${color}18` : 'var(--pan)',
      border: `1px solid ${active ? `${color}44` : 'var(--ln)'}`,
      color: active ? color : 'var(--tx2)',
      fontFamily:'JetBrains Mono', fontSize:11, fontWeight:700,
    }}>
      <span>{icon}</span><span>{label}</span>
      {count > 0 && (
        <span style={{ background: active ? `${color}22` : 'var(--pan2)',
          color: active ? color : 'var(--tx3)',
          padding:'1px 6px', borderRadius:6, fontSize:10 }}>
          {count}
        </span>
      )}
    </div>
  );
}

function StatBubble({ label, value, color='var(--jd)' }) {
  return (
    <div style={{ textAlign:'center', padding:'12px 18px', minWidth:90,
      background:'var(--pan)', border:'1px solid var(--ln)', borderRadius:12 }}>
      <div style={{ fontFamily:'JetBrains Mono', fontWeight:700,
        fontSize:22, color, letterSpacing:'-0.02em' }}>{value}</div>
      <div style={{ fontSize:11, color:'var(--tx3)', marginTop:3 }}>{label}</div>
    </div>
  );
}

function EmptyState() {
  const [dots, setDots] = useState('.');
  useEffect(() => {
    const t = setInterval(() => setDots(d => d.length >= 3 ? '.' : d + '.'), 600);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center',
      justifyContent:'center', height:'100%', minHeight:280,
      fontFamily:'JetBrains Mono', color:'var(--tx3)', userSelect:'none' }}>
      <div style={{ fontSize:40, marginBottom:20, opacity:.25 }}>▋</div>
      <div style={{ fontSize:13, color:'#3d4d61', marginBottom:8 }}>
        waiting for agent events{dots}
      </div>
      <div style={{ fontSize:11, color:'#2a3447', textAlign:'center', maxWidth:320 }}>
        Submit a candidate on the Apply Portal to watch<br />
        the 6-agent pipeline run in real-time.
      </div>
    </div>
  );
}

export default function AgentFeedView() {
  const [events,     setEvents]     = useState([]);
  const [paused,     setPaused]     = useState(false);
  const [filter,     setFilter]     = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [connected,  setConnected]  = useState(false);
  const bottomRef = useRef(null);
  const seenIds   = useRef(new Set());
  const pausedRef = useRef(false);
  useEffect(() => { pausedRef.current = paused; }, [paused]);

  const fetchFeed = useCallback(async () => {
    if (pausedRef.current) return;
    const ENDPOINTS = [
      `${API_URL}/api/agent-feed`,
      `${API_URL}/api/logs`,
      `${API_URL}/api/events`,
      `${API_URL}/api/feed`,
    ];
    for (const url of ENDPOINTS) {
      try {
        const r = await axios.get(url, { timeout: 3000 });
        let data = null;
        if (Array.isArray(r.data))  data = r.data;
        else if (r.data?.events)    data = r.data.events;
        else if (r.data?.logs)      data = r.data.logs;
        else if (r.data?.feed)      data = r.data.feed;
        if (!data) continue;
        setConnected(true);
        const fresh = data.filter(e => {
          const id = e.id || `${e.timestamp}${e.message}`;
          if (seenIds.current.has(id)) return false;
          seenIds.current.add(id); return true;
        });
        if (fresh.length > 0) setEvents(prev => [...prev, ...fresh].slice(-300));
        return;
      } catch {}
    }
  }, []);

  useEffect(() => {
    fetchFeed();
    const t = setInterval(fetchFeed, 2000);
    return () => clearInterval(t);
  }, [fetchFeed]);

  useEffect(() => {
    if (autoScroll && !paused) bottomRef.current?.scrollIntoView({ behavior:'smooth' });
  }, [events, autoScroll, paused]);

  const agentCounts = useMemo(() =>
    events.reduce((acc, e) => {
      const k = agentKey(e.agent || e.agent_type || e.source);
      acc[k] = (acc[k] || 0) + 1; return acc;
    }, {}), [events]);

  const shown = useMemo(() =>
    filter === 'all' ? events
      : events.filter(e => agentKey(e.agent || e.agent_type || e.source) === filter),
    [events, filter]);

  const last30s  = events.filter(e =>
    Date.now() - new Date(e.timestamp||e.time||0).getTime() < 30_000).length;
  const errCount = events.filter(e =>
    (e.level||'').toLowerCase().includes('error')).length;

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'calc(100vh - 160px)' }}>

      <div className="hs-rise" style={{ flexShrink:0, marginBottom:20 }}>
        <div style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between' }}>
          <div>
            <h1 style={{ fontFamily:'Bricolage Grotesque', fontWeight:800,
              fontSize:34, letterSpacing:'-0.03em', lineHeight:1 }}>
              Live Operations
            </h1>
            <p style={{ color:'var(--tx2)', fontSize:14, marginTop:8 }}>
              Real-time <span style={{ color:'var(--jd)' }}>agent activity</span> across
              the hiring pipeline
            </p>
          </div>
          <div style={{ display:'flex', gap:10 }}>
            <button onClick={() => setEvents([])}
              style={{ padding:'9px 16px', borderRadius:10, cursor:'pointer',
                background:'var(--pan)', border:'1px solid var(--ln)',
                color:'var(--tx3)', fontFamily:'JetBrains Mono', fontSize:11 }}>
              Clear
            </button>
            <button onClick={() => setPaused(p => !p)}
              style={{ padding:'9px 18px', borderRadius:10, cursor:'pointer',
                background: paused ? 'rgba(91,141,239,.1)' : 'var(--pan)',
                border:`1px solid ${paused ? 'rgba(91,141,239,.35)' : 'var(--ln)'}`,
                color: paused ? 'var(--jd)' : 'var(--tx2)',
                fontFamily:'JetBrains Mono', fontSize:11, fontWeight:700 }}>
              {paused ? '▶ Resume' : '⏸ Pause'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ display:'flex', gap:12, marginBottom:16, flexShrink:0 }}>
        <StatBubble label="Total Events" value={events.length} color="var(--jd)" />
        <StatBubble label="Last 30s"     value={last30s}       color="var(--cy)" />
        <StatBubble label="Errors"       value={errCount}
          color={errCount > 0 ? 'var(--rs)' : 'var(--tx3)'} />
        <StatBubble label="Status"
          value={connected ? 'LIVE' : 'WAITING'}
          color={connected ? '#4ade80' : 'var(--tx3)'} />
      </div>

      <div style={{ display:'flex', gap:8, marginBottom:14,
        flexShrink:0, flexWrap:'wrap' }}>
        <AgentChip label="ALL" count={events.length} active={filter==='all'}
          onClick={() => setFilter('all')} color="var(--tx2)" icon="◈" />
        {Object.entries(AGENTS)
          .filter(([k]) => (agentCounts[k]||0) > 0)
          .map(([k,a]) => (
            <AgentChip key={k} label={a.label} icon={a.icon}
              count={agentCounts[k]||0} active={filter===k}
              onClick={() => setFilter(filter===k ? 'all' : k)}
              color={a.color} />
          ))}
      </div>

      <div style={{ flex:1, background:'#050810', border:'1px solid var(--ln)',
        borderRadius:16, overflow:'hidden', display:'flex',
        flexDirection:'column', minHeight:0 }}>

        <div style={{ padding:'11px 16px', borderBottom:'1px solid rgba(255,255,255,.05)',
          display:'flex', alignItems:'center', gap:12, flexShrink:0,
          background:'rgba(255,255,255,.02)' }}>
          <div style={{ display:'flex', gap:7 }}>
            {['#e0758a','#d8b878','#4ade80'].map(c => (
              <div key={c} style={{ width:11, height:11, borderRadius:'50%',
                background:c, opacity:.55 }} />
            ))}
          </div>
          <span style={{ fontFamily:'JetBrains Mono', fontSize:11,
            color:'#2a3447', flex:1, textAlign:'center' }}>
            hr-swarm@orchestrator — agent-feed
          </span>
          <button onClick={() => setAutoScroll(a => !a)}
            style={{ background:'none', border:'none', cursor:'pointer',
              fontFamily:'JetBrains Mono', fontSize:10,
              color: autoScroll ? 'var(--jd)' : '#3d4d61' }}>
            ↓ auto-scroll {autoScroll ? 'ON' : 'OFF'}
          </button>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <div className="hs-dot" style={{ opacity: paused ? .3 : 1 }} />
            <span style={{ fontFamily:'JetBrains Mono', fontSize:10,
              color: paused ? '#3d4d61' : 'var(--tx2)' }}>
              {paused ? 'PAUSED' : `${shown.length} events`}
            </span>
          </div>
        </div>

        {shown.length > 0 && (
          <div style={{ display:'flex', padding:'6px 0',
            borderBottom:'1px solid rgba(255,255,255,.04)',
            fontFamily:'JetBrains Mono', fontSize:9, color:'#2a3447',
            textTransform:'uppercase', letterSpacing:'0.1em', flexShrink:0 }}>
            <span style={{ width:70, paddingLeft:18 }}>Time</span>
            <span style={{ width:78 }}>Agent</span>
            <span style={{ width:58 }}>Level</span>
            <span style={{ flex:1 }}>Message</span>
          </div>
        )}

        <div className="hs-scr" style={{ flex:1, overflowY:'auto',
          fontFamily:'JetBrains Mono', fontSize:12 }}>
          {shown.length === 0 ? <EmptyState /> : (
            <>
              {shown.map((e,i) => (
                <FeedEntry key={e.id||i} event={e} highlight={filter!=='all'} />
              ))}
              <div ref={bottomRef} style={{ height:12 }} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}