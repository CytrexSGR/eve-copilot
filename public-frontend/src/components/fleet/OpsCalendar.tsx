import { useState, useEffect, useRef, useCallback } from 'react';
import { opsCalendarApi } from '../../services/api/fleet';
import type { ScheduledOperation } from '../../types/fleet';
import { useAuth } from '../../hooks/useAuth';

/* ── colour helpers ──────────────────────────────────────── */

const importanceColor: Record<string, string> = {
  normal:    '#58a6ff',   // blue
  important: '#d29922',   // yellow/amber
  cta:       '#f85149',   // red
};

const importanceBg: Record<string, string> = {
  normal:    'rgba(88,166,255,0.10)',
  important: 'rgba(210,153,34,0.10)',
  cta:       'rgba(248,81,73,0.12)',
};

const importanceBorder: Record<string, string> = {
  normal:    'rgba(88,166,255,0.30)',
  important: 'rgba(210,153,34,0.40)',
  cta:       'rgba(248,81,73,0.50)',
};

const opTypeLabels: Record<string, string> = {
  stratop:  'Stratop',
  roam:     'Roam',
  mining:   'Mining',
  defense:  'Defense',
  other:    'Other',
};

/* ── countdown logic ─────────────────────────────────────── */

function formatCountdown(formupTime: string): string {
  const diff = new Date(formupTime).getTime() - Date.now();
  if (diff <= 0) return 'NOW';
  const totalSec = Math.floor(diff / 1000);
  const d = Math.floor(totalSec / 86400);
  const h = Math.floor((totalSec % 86400) / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

function isWithinHour(formupTime: string): boolean {
  const diff = new Date(formupTime).getTime() - Date.now();
  return diff > 0 && diff < 3600_000;
}

function isPast(formupTime: string): boolean {
  return new Date(formupTime).getTime() <= Date.now();
}

/* ── date formatting ─────────────────────────────────────── */

function fmtEveDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')} EVE`;
}

/* ── component ───────────────────────────────────────────── */

const EMPTY_FORM = {
  title: '' as string,
  description: '' as string,
  formup_system: '' as string,
  formup_time: '' as string,
  op_type: 'stratop' as string,
  importance: 'normal' as string,
  max_pilots: '' as string,
  doctrine_name: '' as string,
};

export function OpsCalendar({ corpId: _corpId }: { corpId: number }) {
  const { account } = useAuth();
  const [ops, setOps] = useState<ScheduledOperation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [, setTick] = useState(0);               // forces re-render for countdown
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── data loading ── */

  const loadOps = useCallback(async () => {
    try {
      const data = await opsCalendarApi.list(14);
      setOps(data.sort((a, b) => new Date(a.formup_time).getTime() - new Date(b.formup_time).getTime()));
    } catch (err) {
      console.error('Failed to load ops calendar:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadOps(); }, [loadOps]);

  /* ── countdown ticker (1 s when any op < 1 h away) ── */

  useEffect(() => {
    const anyClose = ops.some(op => !op.is_cancelled && isWithinHour(op.formup_time));
    if (anyClose && !tickRef.current) {
      tickRef.current = setInterval(() => setTick(t => t + 1), 1000);
    } else if (!anyClose && tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    return () => { if (tickRef.current) clearInterval(tickRef.current); };
  }, [ops]);

  /* ── create handler ── */

  const handleCreate = async () => {
    if (!form.title.trim() || !form.formup_time) return;
    setCreating(true);
    try {
      await opsCalendarApi.create({
        title: form.title.trim(),
        description: form.description || undefined,
        formup_system: form.formup_system || undefined,
        formup_time: new Date(form.formup_time).toISOString(),
        op_type: form.op_type,
        importance: form.importance,
        max_pilots: form.max_pilots ? Number(form.max_pilots) : undefined,
        doctrine_name: form.doctrine_name || undefined,
        fc_character_id: account?.primary_character_id ?? 0,
        fc_name: account?.primary_character_name ?? 'Unknown',
        corporation_id: _corpId,
      });
      setForm({ ...EMPTY_FORM });
      setShowCreate(false);
      setLoading(true);
      await loadOps();
    } catch (err) {
      console.error('Failed to create op:', err);
    } finally {
      setCreating(false);
    }
  };

  /* ── cancel / start handlers ── */

  const handleCancel = async (opId: number) => {
    try {
      await opsCalendarApi.cancel(opId);
      await loadOps();
    } catch (err) {
      console.error('Failed to cancel op:', err);
    }
  };

  const handleStart = async (opId: number) => {
    try {
      await opsCalendarApi.start(opId);
      await loadOps();
    } catch (err) {
      console.error('Failed to start op:', err);
    }
  };

  /* ── shared styles ── */

  const inputStyle: React.CSSProperties = {
    background: 'rgba(0,0,0,0.3)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: '#fff',
    padding: '0.4rem 0.6rem',
    fontSize: '0.8rem',
    outline: 'none',
    width: '100%',
  };

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    appearance: 'auto' as React.CSSProperties['appearance'],
  };

  const labelStyle: React.CSSProperties = {
    fontSize: '0.7rem',
    color: 'rgba(255,255,255,0.4)',
    textTransform: 'uppercase',
    marginBottom: '0.2rem',
  };

  /* ── render ── */

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header + New Op button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
          Upcoming Operations ({ops.filter(o => !o.is_cancelled).length})
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            background: showCreate ? 'rgba(255,255,255,0.05)' : 'rgba(88,166,255,0.15)',
            border: '1px solid rgba(88,166,255,0.3)',
            borderRadius: '6px',
            color: '#58a6ff',
            padding: '0.4rem 1rem',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {showCreate ? 'Cancel' : 'Schedule Op'}
        </button>
      </div>

      {/* Create form (collapsible) */}
      {showCreate && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: '0.75rem',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Title *</label>
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} style={inputStyle} placeholder="e.g. Stratop - K-6K16" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Formup Time (EVE) *</label>
            <input type="datetime-local" value={form.formup_time} onChange={e => setForm({ ...form, formup_time: e.target.value })} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Formup System</label>
            <input value={form.formup_system} onChange={e => setForm({ ...form, formup_system: e.target.value })} style={inputStyle} placeholder="e.g. Jita" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Op Type</label>
            <select value={form.op_type} onChange={e => setForm({ ...form, op_type: e.target.value })} style={selectStyle}>
              <option value="stratop">Stratop</option>
              <option value="roam">Roam</option>
              <option value="mining">Mining</option>
              <option value="defense">Defense</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Importance</label>
            <select value={form.importance} onChange={e => setForm({ ...form, importance: e.target.value })} style={selectStyle}>
              <option value="normal">Normal</option>
              <option value="important">Important</option>
              <option value="cta">CTA</option>
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Doctrine</label>
            <input value={form.doctrine_name} onChange={e => setForm({ ...form, doctrine_name: e.target.value })} style={inputStyle} placeholder="e.g. Cerberus" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Max Pilots</label>
            <input type="number" value={form.max_pilots} onChange={e => setForm({ ...form, max_pilots: e.target.value })} style={inputStyle} placeholder="optional" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={labelStyle}>Description</label>
            <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} style={inputStyle} placeholder="optional notes" />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              onClick={handleCreate}
              disabled={creating || !form.title.trim() || !form.formup_time}
              style={{
                background: 'rgba(88,166,255,0.15)',
                border: '1px solid rgba(88,166,255,0.3)',
                borderRadius: '6px',
                color: '#58a6ff',
                padding: '0.4rem 1.25rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: creating || !form.title.trim() || !form.formup_time ? 'not-allowed' : 'pointer',
                opacity: creating || !form.title.trim() || !form.formup_time ? 0.5 : 1,
              }}
            >
              {creating ? 'Scheduling...' : 'Schedule'}
            </button>
          </div>
        </div>
      )}

      {/* Ops list */}
      {loading ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>
          Loading operations...
        </div>
      ) : ops.length === 0 ? (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '2rem',
          textAlign: 'center',
          color: 'rgba(255,255,255,0.3)',
          fontSize: '0.85rem',
        }}>
          No upcoming operations scheduled
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {ops.map(op => {
            const imp = op.importance || 'normal';
            const color = importanceColor[imp] || importanceColor.normal;
            const bg = importanceBg[imp] || importanceBg.normal;
            const border = importanceBorder[imp] || importanceBorder.normal;
            const past = isPast(op.formup_time);
            const cancelled = op.is_cancelled;
            const started = !!op.fleet_operation_id;

            return (
              <div key={op.id} style={{
                background: cancelled ? 'rgba(255,255,255,0.02)' : bg,
                border: `1px solid ${cancelled ? 'rgba(255,255,255,0.08)' : border}`,
                borderLeft: cancelled ? '3px solid rgba(255,255,255,0.15)' : `3px solid ${color}`,
                borderRadius: '8px',
                padding: '0.75rem 1rem',
                opacity: cancelled ? 0.45 : 1,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '1rem',
              }}>
                {/* Left: Op info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{
                      fontWeight: 600, fontSize: '0.9rem',
                      textDecoration: cancelled ? 'line-through' : 'none',
                    }}>
                      {op.title}
                    </span>
                    <span style={{
                      padding: '2px 6px', borderRadius: '3px', fontSize: '0.65rem',
                      fontWeight: 700, textTransform: 'uppercase',
                      background: `${color}20`, color,
                    }}>
                      {imp === 'cta' ? 'CTA' : imp}
                    </span>
                    <span style={{
                      padding: '2px 6px', borderRadius: '3px', fontSize: '0.65rem',
                      fontWeight: 600,
                      background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.5)',
                    }}>
                      {opTypeLabels[op.op_type] || op.op_type}
                    </span>
                    {started && (
                      <span style={{
                        padding: '2px 6px', borderRadius: '3px', fontSize: '0.65rem',
                        fontWeight: 700, background: 'rgba(63,185,80,0.15)', color: '#3fb950',
                      }}>LIVE</span>
                    )}
                    {cancelled && (
                      <span style={{
                        padding: '2px 6px', borderRadius: '3px', fontSize: '0.65rem',
                        fontWeight: 700, background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)',
                      }}>CANCELLED</span>
                    )}
                  </div>

                  <div style={{
                    display: 'flex', gap: '1rem', marginTop: '0.3rem',
                    fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', flexWrap: 'wrap',
                  }}>
                    <span>FC: {op.fc_name}</span>
                    <span>{fmtEveDate(op.formup_time)}</span>
                    {op.formup_system && <span>System: {op.formup_system}</span>}
                    {op.doctrine_name && <span>Doctrine: {op.doctrine_name}</span>}
                    {op.max_pilots && <span>Max: {op.max_pilots}</span>}
                  </div>

                  {op.description && (
                    <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', marginTop: '0.2rem' }}>
                      {op.description}
                    </div>
                  )}
                </div>

                {/* Right: countdown + actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                  {/* Countdown */}
                  {!cancelled && !started && (
                    <div style={{
                      fontFamily: 'monospace',
                      fontSize: past ? '0.85rem' : '0.9rem',
                      fontWeight: 700,
                      color: past ? '#3fb950' : isWithinHour(op.formup_time) ? '#f85149' : color,
                      minWidth: '70px',
                      textAlign: 'right',
                    }}>
                      {formatCountdown(op.formup_time)}
                    </div>
                  )}

                  {/* Action buttons */}
                  {!cancelled && !started && (
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      {past && (
                        <button onClick={() => handleStart(op.id)} style={{
                          background: 'rgba(63,185,80,0.15)',
                          border: '1px solid rgba(63,185,80,0.3)',
                          borderRadius: '4px',
                          color: '#3fb950',
                          padding: '3px 8px',
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}>Start</button>
                      )}
                      <button onClick={() => handleCancel(op.id)} style={{
                        background: 'rgba(248,81,73,0.08)',
                        border: '1px solid rgba(248,81,73,0.25)',
                        borderRadius: '4px',
                        color: '#f85149',
                        padding: '3px 8px',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}>Cancel</button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
