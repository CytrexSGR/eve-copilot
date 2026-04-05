import { useState } from 'react';
import { vettingApi } from '../../services/api/hr';
import type { VettingReport } from '../../types/hr';
import { getRiskColor, getRiskLabel } from '../../types/hr';

const FLAG_LABELS: Record<string, string> = {
  red_list_hit: 'Red List Hit',
  wallet_suspicious: 'Wallet Suspicious',
  skill_injection_detected: 'Skill Injection',
  corp_hopping: 'Corp Hopping',
  short_tenure: 'Short Tenure',
};

const FLAG_COLORS: Record<string, string> = {
  red_list_hit: '#f85149',
  wallet_suspicious: '#d29922',
  skill_injection_detected: '#00d4ff',
  corp_hopping: '#d29922',
  short_tenure: '#ff8800',
};

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

export function VettingTab({ corpId: _corpId }: { corpId: number }) {
  const [characterId, setCharacterId] = useState('');
  const [report, setReport] = useState<VettingReport | null>(null);
  const [history, setHistory] = useState<VettingReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunVetting = async () => {
    const id = Number(characterId);
    if (!id) { setError('Enter a valid character ID'); return; }
    setLoading(true);
    setError(null);
    try {
      const result = await vettingApi.runCheck({
        character_id: id, check_contacts: true, check_wallet: true, check_skills: true,
      });
      setReport(result);
      const hist = await vettingApi.getHistory(id);
      setHistory(hist);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Vetting check failed';
      setError(msg);
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  const activeFlags = report ? Object.entries(report.flags).filter(([, v]) => v) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Search */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', padding: '1rem',
        display: 'flex', gap: '0.75rem', alignItems: 'center',
      }}>
        <input
          type="number"
          value={characterId}
          onChange={e => setCharacterId(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleRunVetting()}
          placeholder="Character ID"
          style={{
            flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
            borderRadius: '4px', color: '#fff', padding: '0.5rem 0.75rem',
            fontSize: '0.85rem', fontFamily: 'monospace', outline: 'none',
          }}
        />
        <button
          onClick={handleRunVetting}
          disabled={loading}
          style={{
            background: loading ? 'rgba(255,255,255,0.05)' : 'rgba(63,185,80,0.15)',
            border: '1px solid rgba(63,185,80,0.3)', borderRadius: '6px',
            color: loading ? 'rgba(255,255,255,0.3)' : '#3fb950',
            padding: '0.5rem 1.25rem', fontSize: '0.85rem', fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Running...' : 'Run Vetting'}
        </button>
      </div>

      {error && (
        <div style={{
          background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
          borderRadius: '6px', padding: '0.75rem 1rem', color: '#f85149', fontSize: '0.85rem',
        }}>
          {error}
        </div>
      )}

      {/* Report */}
      {report && (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '1.25rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'rgba(255,255,255,0.4)' }}>
              Vetting Report — {report.character_name}
            </div>
            <span style={{
              padding: '4px 12px', borderRadius: '4px', fontFamily: 'monospace',
              fontSize: '0.85rem', fontWeight: 700,
              background: `${getRiskColor(report.risk_score)}22`,
              color: getRiskColor(report.risk_score),
              border: `1px solid ${getRiskColor(report.risk_score)}55`,
            }}>
              {report.risk_score} — {getRiskLabel(report.risk_score)}
            </span>
          </div>

          {/* Flags */}
          {activeFlags.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
              {activeFlags.map(([key]) => (
                <span key={key} style={{
                  padding: '3px 8px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 700,
                  background: `${FLAG_COLORS[key] || '#8b949e'}22`,
                  color: FLAG_COLORS[key] || '#8b949e',
                  border: `1px solid ${FLAG_COLORS[key] || '#8b949e'}44`,
                }}>
                  {FLAG_LABELS[key] || key}
                </span>
              ))}
            </div>
          )}

          {/* Red List Hits */}
          {report.red_list_hits.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', fontWeight: 600 }}>Red List Hits</div>
              {report.red_list_hits.map((hit, i) => (
                <div key={i} style={{
                  display: 'grid', gridTemplateColumns: '100px 60px 1fr', gap: '0.5rem',
                  padding: '0.4rem 0', fontSize: '0.8rem', borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <span style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>{hit.entity_id}</span>
                  <span style={{ color: '#f85149', fontWeight: 700 }}>Sev {hit.severity}</span>
                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{hit.reason}</span>
                </div>
              ))}
            </div>
          )}

          {/* Wallet Flags */}
          {report.wallet_flags.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', fontWeight: 600 }}>Wallet Flags</div>
              {report.wallet_flags.map((f, i) => (
                <div key={i} style={{
                  display: 'grid', gridTemplateColumns: '1fr 120px 80px', gap: '0.5rem',
                  padding: '0.4rem 0', fontSize: '0.8rem', borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{f.type}</span>
                  <span style={{ fontFamily: 'monospace', textAlign: 'right', color: '#3fb950' }}>{f.amount.toLocaleString()} ISK</span>
                  <span style={{ textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{f.direction}</span>
                </div>
              ))}
            </div>
          )}

          {/* Skill Flags */}
          {report.skill_flags.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', fontWeight: 600 }}>Skill Flags</div>
              {report.skill_flags.map((f, i) => (
                <div key={i} style={{
                  display: 'grid', gridTemplateColumns: '140px 1fr', gap: '0.5rem',
                  padding: '0.4rem 0', fontSize: '0.8rem', borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <span style={{ color: '#00d4ff' }}>{f.type}</span>
                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{f.details}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', overflow: 'hidden',
        }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '140px 80px 1fr', gap: '0.5rem',
            padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
            fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.45)',
          }}>
            <span>Date</span><span>Score</span><span>Flags</span>
          </div>
          {history.map((h, i) => (
            <div key={h.id ?? i} style={{
              display: 'grid', gridTemplateColumns: '140px 80px 1fr', gap: '0.5rem',
              padding: '0.5rem 1rem', fontSize: '0.8rem',
              background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
              borderBottom: '1px solid rgba(255,255,255,0.03)',
            }}>
              <span style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'rgba(255,255,255,0.55)' }}>
                {formatDate(h.checked_at)}
              </span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: getRiskColor(h.risk_score) }}>
                {h.risk_score}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.78rem' }}>
                {Object.entries(h.flags).filter(([, v]) => v).map(([k]) => FLAG_LABELS[k] || k).join(', ') || '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
