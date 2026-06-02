export const theme = {
  // Base
  void:     '#08060f',
  surface:  '#0f0b1e',
  elevated: '#16112a',

  // Glass
  glass:       'rgba(255,255,255,0.03)',
  glassHover:  'rgba(255,255,255,0.05)',
  glassBorder: 'rgba(255,255,255,0.06)',
  glassGlow:   'rgba(124,108,246,0.25)',

  // Accent
  primary:  '#7c6cf6',
  cyan:     '#22d3ee',
  magenta:  '#e879f9',
  gradient: 'linear-gradient(135deg, #22d3ee 0%, #7c6cf6 50%, #e879f9 100%)',
  gradientSoft: 'linear-gradient(135deg, rgba(34,211,238,0.15), rgba(124,108,246,0.15), rgba(232,121,249,0.15))',

  // Text
  textPrimary:   '#faf9ff',
  textSecondary: '#b4abd4',
  textTertiary:  '#756b96',
  textMuted:     '#4a4263',

  // Status
  success: '#34d399',
  warning: '#fbbf24',
  danger:  '#fb7185',

  // Spring presets
  spring:     { type: 'spring', stiffness: 300, damping: 25 },
  springSoft: { type: 'spring', stiffness: 200, damping: 30 },
};

export const fonts = {
  display: { fontSize: '52px', fontWeight: 800, letterSpacing: '-1.5px', lineHeight: 1.05 },
  h1:      { fontSize: '32px', fontWeight: 800, letterSpacing: '-0.5px', lineHeight: 1.15 },
  h2:      { fontSize: '22px', fontWeight: 700, letterSpacing: '-0.3px', lineHeight: 1.2 },
  h3:      { fontSize: '17px', fontWeight: 700, lineHeight: 1.3 },
  body:    { fontSize: '15px', fontWeight: 400, lineHeight: 1.65 },
  small:   { fontSize: '13px', fontWeight: 400, lineHeight: 1.5 },
  caption: { fontSize: '11px', fontWeight: 600, letterSpacing: '0.5px', textTransform: 'uppercase' },
};