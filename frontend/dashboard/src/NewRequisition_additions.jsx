/**
 * ═══════════════════════════════════════════════════════════════════════════
 *  NEW REQUISITION DRAWER — additions for ARIA backend
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Add these 3 new fields to your existing New Requisition drawer:
 *   1. ☐ Include Vibe Engineering Challenge toggle
 *   2. Pass Threshold slider (60-90, default 70)
 *   3. (Optional, collapsible) Dimension Weight Overrides
 *
 * These map directly to fields on the job document that ARIA reads:
 *   job.coding_assessment_enabled
 *   job.pass_threshold
 *   job.dimension_weights  (optional)
 *
 * INTEGRATION:
 * In your existing NewRequisitionDrawer component, add these 3 useState calls
 * at the top, paste the JSX inside the drawer body (right after the AI Interview
 * Setup section, before Publish), and include them in your submit payload.
 */

/* ───────────────────────────────────────────────────────────────────────────
   STEP 1 — add to the component's useState block:
─────────────────────────────────────────────────────────────────────────── */
/*
  const [codingEnabled, setCodingEnabled] = useState(false);
  const [passThreshold, setPassThreshold] = useState(70);
  const [showWeightOverride, setShowWeightOverride] = useState(false);
  const [dimensionWeights, setDimensionWeights] = useState({
    first_principles: 25,
    ai_fluency:       25,
    decomposition:    20,
    taste:            15,
    verification:     15,
  });
*/

/* ───────────────────────────────────────────────────────────────────────────
   STEP 2 — paste this JSX inside the drawer body (after AI Interview Setup
   section, before the Publish button at the bottom):
─────────────────────────────────────────────────────────────────────────── */

const NewRequisitionFields_JSX = `
{/* ═══ Vibe Engineering Challenge toggle ═══ */}
<div style={{
  background: 'linear-gradient(160deg, rgba(143,155,255,0.06), rgba(91,141,239,0.04))',
  border: '1px solid rgba(143,155,255,0.18)',
  borderRadius: 14, padding: 18, marginBottom: 20,
}}>
  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
    <span style={{
      fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.12em',
      textTransform: 'uppercase', color: '#8f9bff',
      background: 'rgba(143,155,255,0.12)', padding: '3px 9px',
      borderRadius: 6, fontWeight: 600,
    }}>New · Engineering</span>
    <span style={{
      fontFamily: 'Bricolage Grotesque', fontWeight: 700, fontSize: 16,
    }}>Vibe Engineering Challenge</span>
  </div>
  <p style={{
    fontSize: 12, color: 'var(--txt-2)', marginBottom: 14, lineHeight: 1.55,
  }}>
    For dev roles: candidates solve a real-world challenge using AI tools —
    testing prompting skill, validation, and judgment, not memorized algorithms.
    Skips LeetCode-style waste of time.
  </p>
  <div style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4,
  }}>
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt)' }}>
        Include Vibe Engineering Challenge
      </div>
      <div style={{ fontSize: 11, color: 'var(--txt-3)', marginTop: 4 }}>
        Runs before AI Interview. Failed candidates do not proceed.
      </div>
    </div>
    <div
      className={\`switch \${codingEnabled ? 'on' : ''}\`}
      onClick={() => setCodingEnabled(!codingEnabled)}
    />
  </div>
</div>

{/* ═══ Pass Threshold slider ═══ */}
<div className="field">
  <div className="field-lbl" style={{ display: 'flex', justifyContent: 'space-between' }}>
    <span>AI Interview Pass Threshold</span>
    <span style={{
      fontFamily: 'JetBrains Mono, monospace', fontSize: 14,
      color: passThreshold >= 80 ? '#e0758a' : passThreshold >= 70 ? '#5b8def' : '#d8b878',
      fontWeight: 700,
    }}>
      {passThreshold}/100
    </span>
  </div>
  <div style={{ padding: '8px 4px 4px' }}>
    <input
      type="range"
      min={60} max={90} step={1}
      value={passThreshold}
      onChange={e => setPassThreshold(Number(e.target.value))}
      style={{ width: '100%', accentColor: '#5b8def', cursor: 'pointer' }}
    />
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      fontSize: 10, color: 'var(--txt-3)',
      fontFamily: 'JetBrains Mono, monospace', marginTop: 6,
      textTransform: 'uppercase', letterSpacing: '0.06em',
    }}>
      <span>Lenient (60)</span>
      <span>Standard (70)</span>
      <span>Strict (90)</span>
    </div>
  </div>
  <div style={{
    fontSize: 11, color: 'var(--txt-3)', marginTop: 8, lineHeight: 1.5,
  }}>
    {passThreshold >= 80
      ? '⚠ Strict — only top candidates will pass. Recommended for senior/staff roles.'
      : passThreshold >= 70
      ? '✓ Standard — balanced threshold. Recommended for most roles.'
      : 'ℹ Lenient — broader funnel. Recommended for high-volume / junior pipelines.'}
  </div>
</div>

{/* ═══ Dimension Weight Overrides (collapsible) ═══ */}
<div style={{
  border: '1px solid var(--line)', borderRadius: 12,
  background: 'var(--panel)', padding: '14px 16px', marginBottom: 20,
}}>
  <div
    onClick={() => setShowWeightOverride(!showWeightOverride)}
    style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      cursor: 'pointer', userSelect: 'none',
    }}>
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt)' }}>
        Override Dimension Weights
      </div>
      <div style={{ fontSize: 11, color: 'var(--txt-3)', marginTop: 4 }}>
        Advanced: customize what ARIA prioritizes (default auto-detected from JD)
      </div>
    </div>
    <span style={{
      fontFamily: 'JetBrains Mono, monospace', fontSize: 14,
      color: 'var(--txt-3)', transform: showWeightOverride ? 'rotate(90deg)' : 'none',
      transition: 'transform 0.2s',
    }}>▸</span>
  </div>

  {showWeightOverride && (
    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--line)' }}>
      {[
        { key: 'first_principles', label: 'First-Principles Thinking', desc: 'Questioning assumptions' },
        { key: 'ai_fluency',       label: 'AI Tool Fluency',           desc: 'Using AI effectively' },
        { key: 'decomposition',    label: 'Problem Decomposition',     desc: 'Breaking down problems' },
        { key: 'taste',            label: 'Taste / Judgment',          desc: 'Picking good vs great' },
        { key: 'verification',     label: 'Verification Skill',        desc: 'Catching AI mistakes' },
      ].map(d => (
        <div key={d.key} style={{ marginBottom: 14 }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', marginBottom: 6,
          }}>
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--txt)' }}>{d.label}</span>
              <span style={{ fontSize: 10, color: 'var(--txt-3)', marginLeft: 8 }}>{d.desc}</span>
            </div>
            <span style={{
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
              color: '#5b8def', fontWeight: 700,
            }}>{dimensionWeights[d.key]}%</span>
          </div>
          <input
            type="range" min={0} max={50} step={5}
            value={dimensionWeights[d.key]}
            onChange={e => setDimensionWeights({
              ...dimensionWeights, [d.key]: Number(e.target.value),
            })}
            style={{ width: '100%', accentColor: '#5b8def' }}
          />
        </div>
      ))}
      <div style={{
        fontSize: 11, color: 'var(--txt-3)', textAlign: 'center',
        fontFamily: 'JetBrains Mono, monospace',
        padding: '8px 12px', background: 'var(--panel-2)', borderRadius: 8, marginTop: 4,
      }}>
        Total: {Object.values(dimensionWeights).reduce((a, b) => a + b, 0)}%
        {Object.values(dimensionWeights).reduce((a, b) => a + b, 0) !== 100 &&
         ' (will auto-normalize on save)'}
      </div>
    </div>
  )}
</div>
`;

/* ───────────────────────────────────────────────────────────────────────────
   STEP 3 — include the new fields in your submit payload.
   In your "Publish Requisition" handler, add these to the POST body:
─────────────────────────────────────────────────────────────────────────── */
/*
  const payload = {
    // ... your existing fields (title, department, location, salary, jd, knowledge_base, etc.)

    // NEW:
    coding_assessment_enabled: codingEnabled,
    pass_threshold:            passThreshold,
    dimension_weights:         showWeightOverride
      ? {
          first_principles: dimensionWeights.first_principles / 100,
          ai_fluency:       dimensionWeights.ai_fluency       / 100,
          decomposition:    dimensionWeights.decomposition    / 100,
          taste:            dimensionWeights.taste            / 100,
          verification:     dimensionWeights.verification     / 100,
        }
      : null,  // null = let ARIA auto-detect from JD
  };

  await axios.post('/api/jobs', payload);
*/

/* ───────────────────────────────────────────────────────────────────────────
   STEP 4 — backend side: make sure your /api/jobs endpoint accepts the new
   fields and stores them on the job document. ARIA's question_generator.py
   reads these via:
     - job.pass_threshold
     - job.dimension_weights
   The coding_assessment_enabled flag is consumed by the pipeline router
   (Phase 2 — Vibe Engineering Challenge build).
─────────────────────────────────────────────────────────────────────────── */

export {};