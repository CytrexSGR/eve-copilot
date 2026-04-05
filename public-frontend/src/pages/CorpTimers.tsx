import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { timerApi } from '../services/api/timers';
import type { StructureTimer, TimerSummary, TimerCreateRequest } from '../types/timers';
import { URGENCY_COLORS, CATEGORY_LABELS, TIMER_TYPE_LABELS, RESULT_COLORS, formatTimeUntil } from '../types/timers';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

type CategoryFilter = 'all' | string;

export function CorpTimers() {
  const { account } = useAuth();
  const corpId = account?.corporation_id;

  const [timers, setTimers] = useState<StructureTimer[]>([]);
  const [summary, setSummary] = useState<TimerSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState(72);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<TimerCreateRequest>({
    structureName: '', category: 'tcurfc', systemId: 0, timerType: 'armor', timerEnd: '',
  });

  const loadTimers = async () => {
    setLoading(true);
    try {
      const params: { hours: number; category?: string } = { hours };
      if (categoryFilter !== 'all') params.category = categoryFilter;
      const res = await timerApi.getUpcoming(params);
      setTimers(res.timers);
      setSummary(res.summary);
    } catch (err) {
      console.error('Failed to load timers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTimers(); }, [hours, categoryFilter]);

  const handleCreate = async () => {
    if (!form.structureName || !form.systemId || !form.timerEnd) return;
    setCreating(true);
    try {
      await timerApi.create(form);
      setForm({ structureName: '', category: 'tcurfc', systemId: 0, timerType: 'armor', timerEnd: '' });
      setShowCreate(false);
      await loadTimers();
    } catch (err) {
      console.error('Failed to create timer:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await timerApi.remove(id);
      await loadTimers();
    } catch (err) {
      console.error('Failed to delete timer:', err);
    }
  };

  const handleResult = async (id: number, result: string) => {
    try {
      await timerApi.update(id, { result, isActive: false });
      await loadTimers();
    } catch (err) {
      console.error('Failed to update timer:', err);
    }
  };

  const inputStyle = {
    background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
    borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem', fontSize: '0.8rem', outline: 'none',
  };

  return (
    <div>
        {corpId && <CorpPageHeader corpId={corpId} title="Timers" subtitle="Structure timers, reinforcement tracking, and outcomes" />}

        {!corpId ? (
          <div style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: '8px', padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)',
          }}>
            No corporation found.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Summary cards */}
            {summary && (
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {(['critical', 'urgent', 'upcoming', 'planned'] as const).map(urg => (
                  <div key={urg} style={{
                    background: 'var(--bg-secondary)', border: `1px solid ${URGENCY_COLORS[urg]}44`,
                    borderRadius: '8px', padding: '0.75rem 1rem', minWidth: '120px',
                  }}>
                    <div style={{ fontSize: '0.7rem', color: URGENCY_COLORS[urg], textTransform: 'uppercase', fontWeight: 700 }}>{urg}</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: URGENCY_COLORS[urg] }}>
                      {summary[urg]}
                    </div>
                  </div>
                ))}
                <div style={{
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
                  borderRadius: '8px', padding: '0.75rem 1rem', minWidth: '120px',
                }}>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700 }}>Total</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace' }}>{summary.total}</div>
                </div>
              </div>
            )}

            {/* Controls */}
            <div style={{
              background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
              borderRadius: '8px', padding: '0.75rem 1rem',
              display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>Lookahead</span>
                <select value={hours} onChange={e => setHours(Number(e.target.value))} style={{ ...inputStyle, cursor: 'pointer' }}>
                  {[24, 48, 72, 168].map(h => <option key={h} value={h}>{h}h ({Math.round(h / 24)}d)</option>)}
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>Category</span>
                <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
                  <option value="all">All</option>
                  {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
              <div style={{ flex: 1 }} />
              <button onClick={() => setShowCreate(!showCreate)} style={{
                background: showCreate ? 'rgba(255,255,255,0.05)' : 'rgba(63,185,80,0.15)',
                border: '1px solid rgba(63,185,80,0.3)', borderRadius: '6px',
                color: '#3fb950', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
              }}>
                {showCreate ? 'Cancel' : 'Add Timer'}
              </button>
            </div>

            {/* Create form */}
            {showCreate && (
              <div style={{
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
                borderRadius: '8px', padding: '1rem',
                display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem',
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Structure Name</label>
                  <input value={form.structureName} onChange={e => setForm({ ...form, structureName: e.target.value })} style={inputStyle} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>System ID</label>
                  <input type="number" value={form.systemId || ''} onChange={e => setForm({ ...form, systemId: Number(e.target.value) })} style={inputStyle} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Category</label>
                  <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} style={{ ...inputStyle, cursor: 'pointer' }}>
                    {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Timer Type</label>
                  <select value={form.timerType} onChange={e => setForm({ ...form, timerType: e.target.value })} style={{ ...inputStyle, cursor: 'pointer' }}>
                    {Object.entries(TIMER_TYPE_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Timer End (UTC)</label>
                  <input type="datetime-local" value={form.timerEnd} onChange={e => setForm({ ...form, timerEnd: e.target.value })} style={inputStyle} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Notes</label>
                  <input value={form.notes || ''} onChange={e => setForm({ ...form, notes: e.target.value })} style={inputStyle} />
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                  <button onClick={handleCreate} disabled={creating} style={{
                    background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
                    borderRadius: '6px', color: '#3fb950', padding: '0.4rem 1.25rem',
                    fontSize: '0.8rem', fontWeight: 600, cursor: creating ? 'not-allowed' : 'pointer',
                  }}>
                    {creating ? 'Creating...' : 'Create'}
                  </button>
                </div>
              </div>
            )}

            {/* Timer table */}
            <div style={{
              background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
              borderRadius: '8px', overflow: 'hidden',
            }}>
              <div style={{
                display: 'grid', gridTemplateColumns: '1.5fr 100px 80px 1fr 100px 100px 80px 100px',
                gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
                fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
              }}>
                <span>Structure</span><span>Category</span><span>Type</span>
                <span>System / Region</span><span>Timer End</span><span>Time Left</span>
                <span>Urgency</span><span></span>
              </div>

              {loading ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
              ) : timers.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No timers found</div>
              ) : (
                <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                  {timers.map((timer, idx) => {
                    const urgColor = URGENCY_COLORS[timer.urgency] || '#8b949e';
                    return (
                      <div key={timer.id} style={{
                        display: 'grid', gridTemplateColumns: '1.5fr 100px 80px 1fr 100px 100px 80px 100px',
                        gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem',
                        background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                        borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                        borderLeft: `3px solid ${urgColor}`,
                      }}>
                        <span style={{ fontWeight: 600 }}>
                          {timer.structureName}
                          {timer.cynoJammed && <span style={{ color: '#a855f7', fontSize: '0.7rem', marginLeft: '0.4rem' }}>JAMMED</span>}
                        </span>
                        <span style={{
                          padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem',
                          background: 'rgba(0,212,255,0.1)', color: '#00d4ff', textAlign: 'center',
                        }}>{CATEGORY_LABELS[timer.category] || timer.category}</span>
                        <span style={{
                          fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)', textTransform: 'capitalize',
                        }}>{TIMER_TYPE_LABELS[timer.timerType] || timer.timerType}</span>
                        <span style={{ color: 'rgba(255,255,255,0.6)' }}>
                          {timer.systemName} <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)' }}>/ {timer.regionName}</span>
                        </span>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'rgba(255,255,255,0.5)' }}>
                          {formatDate(timer.timerEnd)}
                        </span>
                        <span style={{ fontFamily: 'monospace', fontWeight: 700, color: urgColor }}>
                          {formatTimeUntil(timer.hoursUntil)}
                        </span>
                        <span style={{
                          padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                          background: `${urgColor}22`, color: urgColor, textTransform: 'uppercase', textAlign: 'center',
                        }}>{timer.urgency}</span>
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          {timer.result ? (
                            <span style={{
                              padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                              background: `${RESULT_COLORS[timer.result] || '#8b949e'}22`,
                              color: RESULT_COLORS[timer.result] || '#8b949e',
                              textTransform: 'capitalize',
                            }}>{timer.result}</span>
                          ) : (
                            <>
                              <button onClick={() => handleResult(timer.id, 'defended')} title="Defended" style={{
                                background: 'rgba(63,185,80,0.1)', border: '1px solid rgba(63,185,80,0.3)',
                                borderRadius: '3px', color: '#3fb950', padding: '1px 4px', fontSize: '0.65rem', cursor: 'pointer',
                              }}>D</button>
                              <button onClick={() => handleResult(timer.id, 'destroyed')} title="Destroyed" style={{
                                background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                                borderRadius: '3px', color: '#f85149', padding: '1px 4px', fontSize: '0.65rem', cursor: 'pointer',
                              }}>X</button>
                              <button onClick={() => handleDelete(timer.id)} title="Delete" style={{
                                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '3px', color: 'rgba(255,255,255,0.3)', padding: '1px 4px', fontSize: '0.65rem', cursor: 'pointer',
                              }}>Del</button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
    </div>
  );
}
