import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/military',
  timeout: 30000,
  withCredentials: true,
});

interface InfestedSystem {
  system_id: number;
  system_name: string;
  security: number;
  security_class: string;
}

interface Incursion {
  constellation_id: number;
  constellation_name: string;
  region_id: number;
  region_name: string;
  state: string;
  influence: number;
  has_boss: boolean;
  staging_system_id: number;
  staging_system_name: string;
  staging_security: number;
  security_class: string;
  infested_systems: InfestedSystem[];
  system_count: number;
  type: string;
}

const STATE_COLORS: Record<string, string> = {
  established: '#f85149',
  mobilizing: '#d29922',
  withdrawing: '#3fb950',
};

const STATE_LABELS: Record<string, string> = {
  established: 'Established',
  mobilizing: 'Mobilizing',
  withdrawing: 'Withdrawing',
};

function secColor(sec: number): string {
  if (sec >= 0.9) return '#2EFF2E';
  if (sec >= 0.7) return '#3fb950';
  if (sec >= 0.5) return '#d29922';
  if (sec >= 0.3) return '#f0883e';
  if (sec > 0.0) return '#f85149';
  return '#cc0000';
}

export function IncursionsTab() {
  const [incursions, setIncursions] = useState<Incursion[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/incursions');
      setIncursions(data.incursions || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5 * 60 * 1000); // Auto-refresh every 5 minutes
    return () => clearInterval(interval);
  }, [load]);

  if (loading) {
    return <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>Loading incursions...</div>;
  }

  if (incursions.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: '3rem',
        textAlign: 'center',
        color: 'var(--text-secondary)',
      }}>
        No active incursions at this time.
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1rem' }}>
      {incursions.map(inc => (
        <div
          key={inc.constellation_id}
          style={{
            background: 'var(--bg-secondary)',
            border: `1px solid ${STATE_COLORS[inc.state] || 'var(--border-color)'}44`,
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div style={{
            padding: '0.75rem 1rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                {inc.constellation_name}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {inc.region_name}
              </div>
            </div>
            <span style={{
              background: `${STATE_COLORS[inc.state] || '#8b949e'}22`,
              color: STATE_COLORS[inc.state] || '#8b949e',
              padding: '3px 10px',
              borderRadius: 4,
              fontSize: '0.75rem',
              fontWeight: 600,
            }}>
              {STATE_LABELS[inc.state] || inc.state}
            </span>
          </div>

          {/* Body */}
          <div style={{ padding: '0.75rem 1rem' }}>
            {/* Influence bar */}
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Influence</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{(inc.influence * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  width: `${inc.influence * 100}%`,
                  height: '100%',
                  background: STATE_COLORS[inc.state] || '#8b949e',
                  borderRadius: 3,
                  transition: 'width 0.3s',
                }} />
              </div>
            </div>

            {/* Info grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Staging</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {inc.staging_system_name}
                  <span style={{ color: secColor(inc.staging_security), fontSize: '0.75rem', marginLeft: 4 }}>
                    {inc.staging_security.toFixed(1)}
                  </span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Systems</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {inc.system_count} infested
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Security</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500, textTransform: 'capitalize' }}>
                  {inc.security_class}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Boss</div>
                <div style={{ fontSize: '0.85rem', color: inc.has_boss ? '#f85149' : 'var(--text-secondary)', fontWeight: 500 }}>
                  {inc.has_boss ? 'Present' : 'Not spawned'}
                </div>
              </div>
            </div>

            {/* Expand systems */}
            <button
              onClick={() => setExpandedId(expandedId === inc.constellation_id ? null : inc.constellation_id)}
              style={{
                width: '100%',
                background: 'transparent',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                padding: '4px',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                fontSize: '0.75rem',
              }}
            >
              {expandedId === inc.constellation_id ? 'Hide Systems' : 'Show Systems'}
            </button>

            {expandedId === inc.constellation_id && (
              <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {inc.infested_systems.map(sys => (
                  <div key={sys.system_id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '3px 8px',
                    background: sys.system_id === inc.staging_system_id ? 'rgba(248,81,73,0.1)' : 'rgba(255,255,255,0.02)',
                    borderRadius: 3,
                    borderLeft: sys.system_id === inc.staging_system_id ? '2px solid #f85149' : '2px solid transparent',
                  }}>
                    <span style={{
                      fontSize: '0.8rem',
                      color: 'var(--text-primary)',
                      fontWeight: sys.system_id === inc.staging_system_id ? 600 : 400,
                    }}>
                      {sys.system_name}
                      {sys.system_id === inc.staging_system_id && (
                        <span style={{ fontSize: '0.65rem', color: '#f85149', marginLeft: 4 }}>(staging)</span>
                      )}
                    </span>
                    <span style={{ color: secColor(sys.security), fontSize: '0.75rem', fontWeight: 600 }}>
                      {sys.security.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
