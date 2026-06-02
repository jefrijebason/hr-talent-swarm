import React from 'react';
import { motion } from 'framer-motion';
import { iTheme } from './interviewTheme';

export default function AIIndicator({ state = 'idle', size = 'normal' }) {
  // state: idle | speaking | listening | processing

  const dotSize = size === 'small' ? 10 : 14;
  const ringSize = size === 'small' ? 28 : 38;

  const pulseConfig = {
    idle:       { scale: [1, 1.2, 1],    dur: 2.5 },
    speaking:   { scale: [1, 1.4, 1],    dur: 1.2 },
    listening:  { scale: [1, 1.15, 1],   dur: 1.8 },
    processing: { scale: [1, 1.5, 0.9, 1], dur: 0.7 },
  }[state];

  return (
    <div style={{ position: 'relative', width: ringSize, height: ringSize,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>

      {/* Pulse ring */}
      <motion.div
        animate={{ scale: [1, 1.8], opacity: [0.4, 0] }}
        transition={{ duration: pulseConfig.dur * 1.2, repeat: Infinity, ease: 'easeOut' }}
        style={{ position: 'absolute', width: ringSize, height: ringSize,
          borderRadius: '50%', border: `1.5px solid ${iTheme.primary}` }} />

      {/* Soft glow behind */}
      <motion.div
        animate={{ scale: pulseConfig.scale, opacity: [0.3, 0.6, 0.3] }}
        transition={{ duration: pulseConfig.dur, repeat: Infinity, ease: 'easeInOut' }}
        style={{ position: 'absolute', width: dotSize * 2.5, height: dotSize * 2.5,
          borderRadius: '50%', background: iTheme.primary, filter: 'blur(10px)',
          opacity: 0.3 }} />

      {/* Core dot */}
      <motion.div
        animate={{ scale: pulseConfig.scale }}
        transition={{ duration: pulseConfig.dur, repeat: Infinity, ease: 'easeInOut' }}
        style={{ width: dotSize, height: dotSize, borderRadius: '50%',
          background: iTheme.gradient,
          boxShadow: `0 0 12px ${iTheme.primary}` }} />
    </div>
  );
}