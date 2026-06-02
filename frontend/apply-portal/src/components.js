import React, { useState, useRef, useEffect } from 'react';
import { motion, useInView, animate } from 'framer-motion';
import { theme } from './theme';

// ── Glass Card ───────────────────────────────────────────────────
export function GlassCard({ children, style = {}, hover = true,
  glow = false, onClick, ...props }) {
  return (
    <motion.div
      onClick={onClick}
      whileHover={hover ? {
        scale: 1.012, borderColor: theme.glassGlow,
        boxShadow: '0 8px 40px rgba(124,108,246,0.18)'
      } : {}}
      transition={theme.spring}
      style={{
        background: theme.glass,
        backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
        border: `1px solid ${theme.glassBorder}`,
        borderRadius: '20px', padding: '24px',
        cursor: onClick ? 'pointer' : 'default',
        boxShadow: glow ? '0 8px 32px rgba(124,108,246,0.12)' : '0 4px 24px rgba(0,0,0,0.2)',
        ...style
      }}
      {...props}>
      {children}
    </motion.div>
  );
}

// ── Aurora Button ────────────────────────────────────────────────
export function AuroraButton({ children, onClick, disabled,
  variant = 'primary', style = {}, full = false }) {
  const variants = {
    primary: { background: theme.gradient, color: '#fff' },
    ghost: { background: theme.glassHover, color: theme.textSecondary,
      border: `1px solid ${theme.glassBorder}` },
    danger: { background: 'rgba(251,113,133,0.1)', color: theme.danger,
      border: '1px solid rgba(251,113,133,0.3)' },
  };
  return (
    <motion.button
      onClick={onClick} disabled={disabled}
      whileHover={!disabled ? { scale: 1.03,
        boxShadow: variant === 'primary' ? '0 8px 30px rgba(124,108,246,0.45)' : 'none' } : {}}
      whileTap={!disabled ? { scale: 0.97 } : {}}
      transition={theme.spring}
      style={{
        padding: '14px 30px', borderRadius: '14px', border: 'none',
        fontSize: '15px', fontWeight: 700,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1, width: full ? '100%' : 'auto',
        fontFamily: 'inherit', letterSpacing: '0.2px',
        ...variants[variant], ...style
      }}>
      {children}
    </motion.button>
  );
}

// ── Gradient Text ────────────────────────────────────────────────
export function GradientText({ children, style = {} }) {
  return (
    <span style={{
      background: theme.gradient, WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent', backgroundClip: 'text', ...style
    }}>{children}</span>
  );
}

// ── Scroll Reveal ────────────────────────────────────────────────
export function ScrollReveal({ children, delay = 0, y = 30, style = {} }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-40px' });
  return (
    <motion.div ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: [0.21, 0.5, 0.36, 1] }}
      style={style}>
      {children}
    </motion.div>
  );
}

// ── Stagger Container + Item ──────────────────────────────────────
export function Stagger({ children, style = {} }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-40px' });
  return (
    <motion.div ref={ref}
      initial="hidden" animate={inView ? 'show' : 'hidden'}
      variants={{ show: { transition: { staggerChildren: 0.08 } } }}
      style={style}>
      {children}
    </motion.div>
  );
}
export function StaggerItem({ children, style = {} }) {
  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { duration: 0.5 } } }}
      style={style}>
      {children}
    </motion.div>
  );
}

// ── Animated Counter ─────────────────────────────────────────────
export function AnimatedCounter({ to, suffix = '', duration = 1.5, style = {} }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const c = animate(0, to, { duration, ease: 'easeOut',
      onUpdate: v => setDisplay(Math.round(v)) });
    return () => c.stop();
  }, [inView, to, duration]);
  return <span ref={ref} style={style}>{display}{suffix}</span>;
}

// ── Animated Ring ────────────────────────────────────────────────
export function AnimatedRing({ score, max = 10, size = 150 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const [display, setDisplay] = useState(0);
  const radius = (size - 22) / 2;
  const circ = 2 * Math.PI * radius;
  useEffect(() => {
    if (!inView) return;
    const c = animate(0, score, { duration: 1.8, ease: 'easeOut',
      onUpdate: v => setDisplay(v) });
    return () => c.stop();
  }, [inView, score]);
  const offset = circ - (display / max) * circ;
  return (
    <div ref={ref} style={{ position: 'relative', width: size, height: size, margin: '0 auto' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <defs>
          <linearGradient id="rg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={theme.cyan} />
            <stop offset="50%" stopColor={theme.primary} />
            <stop offset="100%" stopColor={theme.magenta} />
          </linearGradient>
        </defs>
        <circle cx={size/2} cy={size/2} r={radius} fill="none"
          stroke="rgba(255,255,255,0.06)" strokeWidth="11" />
        <circle cx={size/2} cy={size/2} r={radius} fill="none"
          stroke="url(#rg)" strokeWidth="11" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ filter: 'drop-shadow(0 0 10px rgba(124,108,246,0.6))' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex',
        flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: '36px', fontWeight: 800, color: theme.textPrimary }}>
          {display.toFixed(1)}
        </div>
        <div style={{ fontSize: '12px', color: theme.textTertiary }}>out of {max}</div>
      </div>
    </div>
  );
}

// ── Skill Pill ───────────────────────────────────────────────────
export function SkillPill({ children, active = false, delay = 0 }) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ ...theme.spring, delay }}
      style={{
        display: 'inline-block', padding: '6px 14px', borderRadius: '100px',
        fontSize: '12px', fontWeight: 600,
        background: active ? 'rgba(124,108,246,0.18)' : 'rgba(255,255,255,0.04)',
        color: active ? '#b8acff' : theme.textSecondary,
        border: `1px solid ${active ? 'rgba(124,108,246,0.4)' : theme.glassBorder}`,
        boxShadow: active ? '0 0 14px rgba(124,108,246,0.2)' : 'none',
      }}>
      {children}
    </motion.span>
  );
}

// ── Glass Input ──────────────────────────────────────────────────
export function GlassInput({ label, value, onChange, placeholder,
  type = 'text', error, textarea, style = {} }) {
  const [focused, setFocused] = useState(false);
  const C = textarea ? 'textarea' : 'input';
  return (
    <div style={style}>
      {label && (
        <label style={{ fontSize: '13px', fontWeight: 600,
          color: theme.textSecondary, display: 'block', marginBottom: '7px' }}>
          {label}
        </label>
      )}
      <C type={type} value={value} onChange={onChange} placeholder={placeholder}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        style={{
          width: '100%', padding: '13px 16px', borderRadius: '13px',
          background: 'rgba(255,255,255,0.03)',
          border: `1.5px solid ${error ? theme.danger : focused ? theme.primary : theme.glassBorder}`,
          color: theme.textPrimary, fontSize: '14px', outline: 'none',
          boxSizing: 'border-box', fontFamily: 'inherit',
          minHeight: textarea ? '90px' : 'auto', resize: textarea ? 'vertical' : 'none',
          boxShadow: focused ? '0 0 22px rgba(124,108,246,0.18)' : 'none',
          transition: 'border 0.2s, box-shadow 0.2s',
        }} />
      {error && <div style={{ fontSize: '11px', color: theme.danger, marginTop: '5px' }}>⚠️ {error}</div>}
    </div>
  );
}

// ── Stat Chip ────────────────────────────────────────────────────
export function StatChip({ label, value, icon }) {
  return (
    <motion.div whileHover={{ y: -3 }} transition={theme.spring}
      style={{ background: 'rgba(255,255,255,0.03)',
        border: `1px solid ${theme.glassBorder}`, borderRadius: '14px',
        padding: '12px 18px', minWidth: '92px' }}>
      <div style={{ fontSize: '11px', color: theme.textTertiary, marginBottom: '5px' }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: '15px', fontWeight: 700, color: theme.textPrimary }}>
        {value}
      </div>
    </motion.div>
  );
}

// ── Top Nav ──────────────────────────────────────────────────────
export function TopNav({ page, setPage }) {
  return (
    <motion.div
      initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      style={{ position: 'sticky', top: 0, zIndex: 50,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '18px 32px', background: 'rgba(8,6,15,0.6)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${theme.glassBorder}` }}>
      <div onClick={() => setPage('browse')}
        style={{ fontSize: '20px', fontWeight: 800, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span>✦</span>
        <GradientText>Careers</GradientText>
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        {[{ k: 'browse', l: 'Browse Jobs' }, { k: 'track', l: 'Track Application' }].map(t => (
          <button key={t.k} onClick={() => setPage(t.k)}
            style={{ padding: '8px 18px', borderRadius: '10px',
              border: 'none', cursor: 'pointer', fontSize: '14px', fontWeight: 600,
              fontFamily: 'inherit',
              background: page === t.k ? 'rgba(124,108,246,0.15)' : 'transparent',
              color: page === t.k ? '#b8acff' : theme.textSecondary,
              boxShadow: page === t.k ? '0 0 16px rgba(124,108,246,0.15)' : 'none',
              transition: 'all 0.2s' }}>
            {t.l}
          </button>
        ))}
      </div>
    </motion.div>
  );
}