import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export default function AuroraBackground() {
  const meshRef = useRef(null);

  useEffect(() => {
    const handleMove = (e) => {
      if (!meshRef.current) return;
      const x = (e.clientX / window.innerWidth - 0.5) * 16;
      const y = (e.clientY / window.innerHeight - 0.5) * 16;
      meshRef.current.style.transform = `translate(${x}px, ${y}px)`;
    };
    window.addEventListener('mousemove', handleMove);
    return () => window.removeEventListener('mousemove', handleMove);
  }, []);

  return (
    <div style={styles.wrapper}>
      <div style={styles.base} />
      <div ref={meshRef} style={styles.mesh} />

      <motion.div style={{ ...styles.blob, ...styles.blob1 }}
        animate={{ x: [0, 70, -30, 0], y: [0, -50, 30, 0], scale: [1, 1.15, 0.95, 1] }}
        transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }} />
      <motion.div style={{ ...styles.blob, ...styles.blob2 }}
        animate={{ x: [0, -90, 50, 0], y: [0, 40, -60, 0], scale: [1, 0.9, 1.1, 1] }}
        transition={{ duration: 24, repeat: Infinity, ease: 'easeInOut' }} />
      <motion.div style={{ ...styles.blob, ...styles.blob3 }}
        animate={{ x: [0, 50, -70, 0], y: [0, -35, 50, 0], scale: [1, 1.08, 0.92, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }} />

      {[...Array(16)].map((_, i) => (
        <motion.div key={i}
          style={{ ...styles.particle,
            left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%` }}
          animate={{ y: [0, -25, 0], opacity: [0.15, 0.5, 0.15] }}
          transition={{ duration: 5 + Math.random() * 4, repeat: Infinity,
            delay: Math.random() * 4, ease: 'easeInOut' }} />
      ))}

      <div style={styles.noise} />
      <div style={styles.vignette} />
    </div>
  );
}

const styles = {
  wrapper: { position: 'fixed', inset: 0, zIndex: 0, overflow: 'hidden', pointerEvents: 'none' },
  base: { position: 'absolute', inset: 0,
    background: 'linear-gradient(135deg, #08060f 0%, #0f0b1e 50%, #08060f 100%)' },
  mesh: { position: 'absolute', inset: '-50px',
    backgroundImage: `linear-gradient(rgba(124,108,246,0.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(124,108,246,0.05) 1px, transparent 1px)`,
    backgroundSize: '56px 56px', transition: 'transform 0.4s ease-out' },
  blob: { position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.4 },
  blob1: { width: '520px', height: '520px',
    background: 'radial-gradient(circle, #22d3ee 0%, transparent 70%)', top: '-120px', left: '-80px' },
  blob2: { width: '480px', height: '480px',
    background: 'radial-gradient(circle, #7c6cf6 0%, transparent 70%)', top: '25%', right: '-120px' },
  blob3: { width: '420px', height: '420px',
    background: 'radial-gradient(circle, #e879f9 0%, transparent 70%)', bottom: '-120px', left: '25%' },
  particle: { position: 'absolute', width: '2px', height: '2px', borderRadius: '50%',
    background: '#a78bfa', boxShadow: '0 0 8px #a78bfa' },
  noise: { position: 'absolute', inset: 0, opacity: 0.04,
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
    mixBlendMode: 'overlay' },
  vignette: { position: 'absolute', inset: 0,
    background: 'radial-gradient(ellipse at center, transparent 35%, rgba(8,6,15,0.7) 100%)' },
};