import { useState, useEffect } from 'react';
import { activityApi } from '../../services/api/hr';
import type { InactiveMember, FleetSession } from '../../types/hr';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

const getInactiveColor = (days: number): string => {
  if (days > 60) return '#f85149';
  if (days > 30) return '#d29922';
  return '#3fb950';
};

export function ActivityTab({ corpId: _corpId }: { corpId: number }) {
  const [daysThreshold, setDaysThreshold] = useState(30);
  const [inactive, setInactive] = useState<InactiveMember[]>([]);
  const [fleets, setFleets] = useState<FleetSession[]>([]);
  const [loadingInactive, setLoadingInactive] = useState(true);
  const [loadingFleets, setLoadingFleets] = useState(true);

  useEffect(() => {
    setLoadingInactive(true);
    activityApi.getInactive(daysThreshold)
      .then(setInactive)
      .catch(err => console.error('Failed to load inactive members:', err))
      .finally(() => setLoadingInactive(false));
  }, [daysThreshold]);

  useEffect(() => {
    setLoadingFleets(true);
    activityApi.getFleetSessions({ limit: 50 })
      .then(setFleets)
      .catch(err => console.error('Failed to load fleet sessions:', err))
      .finally(() => setLoadingFleets(false));
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Inactive Members */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Inactive Members ({inactive.length})</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>Threshold</span>
            <select value={daysThreshold} onChange={e => setDaysThreshold(Number(e.target.value))} style={{
              background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
              borderRadius: '4px', color: '#fff', padding: '0.35rem 0.5rem', fontSize: '0.8rem', cursor: 'pointer',
            }}>
              {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>{d} days</option>)}
            </select>
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', overflow: 'hidden',
        }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '1.5fr 140px 80px 80px 80px',
            gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
            fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
          }}>
            <span>Character</span><span>Last Login</span>
            <span style={{ textAlign: 'right' }}>Days</span>
            <span style={{ textAlign: 'right' }}>Fleets</span>
            <span style={{ textAlign: 'right' }}>Kills</span>
          </div>

          {loadingInactive ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
          ) : inactive.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No inactive members</div>
          ) : (
            <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
              {inactive.map((m, idx) => (
                <div key={m.character_id} style={{
                  display: 'grid', gridTemplateColumns: '1.5fr 140px 80px 80px 80px',
                  gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem',
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                }}>
                  <span>{m.character_name}</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'rgba(255,255,255,0.55)' }}>
                    {m.last_login_at ? formatDate(m.last_login_at) : 'Never'}
                  </span>
                  <span style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: getInactiveColor(m.days_inactive) }}>
                    {m.days_inactive}
                  </span>
                  <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>{m.fleet_count_30d}</span>
                  <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>{m.kill_count_30d}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Fleet Sessions */}
      <div>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>Recent Fleet Sessions ({fleets.length})</div>

        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', overflow: 'hidden',
        }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '1.5fr 1.2fr 1fr 140px 140px',
            gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
            fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
          }}>
            <span>Fleet</span><span>Character</span><span>Ship</span><span>Start</span><span>End</span>
          </div>

          {loadingFleets ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
          ) : fleets.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No fleet sessions</div>
          ) : (
            <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
              {fleets.map((s, idx) => (
                <div key={s.id} style={{
                  display: 'grid', gridTemplateColumns: '1.5fr 1.2fr 1fr 140px 140px',
                  gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem',
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.8)' }}>{s.fleet_name || 'Unknown'}</span>
                  <span>{s.character_name}</span>
                  <span style={{ color: 'rgba(255,255,255,0.6)' }}>{s.ship_name || 'Unknown'}</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'rgba(255,255,255,0.55)' }}>{formatDate(s.start_time)}</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'rgba(255,255,255,0.55)' }}>{s.end_time ? formatDate(s.end_time) : 'Ongoing'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
