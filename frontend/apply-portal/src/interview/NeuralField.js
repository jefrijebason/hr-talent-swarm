import React from 'react';
import { motion } from 'framer-motion';
import { iTheme } from './interviewTheme';

export default function NeuralField() {
  return (
    <div style={styles.wrapper}>
      <div style={styles.base} />

      {/* Subtle indigo glow — top right */}
      <motion.div
        animate={{ opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        style={styles.glow1} />

      {/* Subtle indigo glow — bottom left */}
      <motion.div
        animate={{ opacity: [0.2, 0.4, 0.2] }}
        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        style={styles.glow2} />

      {/* Dot grid */}
      <div style={styles.dots} />

      {/* Subtle noise */}
      <div style={styles.noise} />

      {/* Vignette */}
      <div style={styles.vignette} />
    </div>
  );
}

const styles = {
  wrapper: {
    position: 'fixed', inset: 0, zIndex: 0,
    overflow: 'hidden', pointerEvents: 'none',
  },
  base: {
    position: 'absolute', inset: 0,
    background: `linear-gradient(145deg, ${iTheme.bg} 0%, #1a1a2a 50%, ${iTheme.bg} 100%)`,
  },
  glow1: {
    position: 'absolute', top: '-180px', right: '-120px',
    width: '550px', height: '550px', borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%)',
    filter: 'blur(50px)',
  },
  glow2: {
    position: 'absolute', bottom: '-180px', left: '-80px',
    width: '450px', height: '450px', borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(79,70,229,0.08) 0%, transparent 70%)',
    filter: 'blur(50px)',
  },
  dots: {
    position: 'absolute', inset: 0, opacity: 0.25,
    backgroundImage: `radial-gradient(circle, rgba(255,255,255,0.08) 1px, transparent 1px)`,
    backgroundSize: '30px 30px',
  },
  noise: {
    position: 'absolute', inset: 0, opacity: 0.03,
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
    mixBlendMode: 'overlay',
  },
  vignette: {
    position: 'absolute', inset: 0,
    background: 'radial-gradient(ellipse at center, transparent 40%, rgba(20,20,36,0.5) 100%)',
  },
};