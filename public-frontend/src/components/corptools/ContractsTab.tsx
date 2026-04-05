import { useState, useEffect } from 'react';
import { contractsApi } from '../../services/api/corptools';
import type { CorpContract, ContractSummary, ContractStatsResponse, ContractChange } from '../../types/corptools';
import { CONTRACT_STATUS_COLORS, formatIsk } from '../../types/corptools';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

type ContractTypeFilter = 'all' | 'courier' | 'item_exchange' | 'auction';

export function ContractsTab({ corpId }: { corpId: number }) {
  const [contracts, setContracts] = useState<CorpContract[]>([]);
  const [summary, setSummary] = useState<ContractSummary | null>(null);
  const [stats, setStats] = useState<ContractStatsResponse | null>(null);
  const [changes, setChanges] = useState<ContractChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<ContractTypeFilter>('all');

  useEffect(() => {
    setLoading(true);
    const typeParam = typeFilter === 'all' ? undefined : typeFilter;
    Promise.all([
      contractsApi.getActive(corpId, typeParam),
      contractsApi.getStats(corpId, 30),
      contractsApi.getChanges(corpId, 24),
    ])
      .then(([activeRes, statsRes, changesRes]) => {
        setContracts(activeRes?.contracts ?? []);
        setSummary(activeRes?.summary ?? null);
        setStats(statsRes ?? null);
        setChanges(changesRes?.changes ?? []);
      })
      .catch(err => console.error('Failed to load contracts:', err))
      .finally(() => setLoading(false));
  }, [corpId, typeFilter]);

  const statCardStyle = {
    background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
    borderRadius: '8px', padding: '0.75rem 1rem',
  };

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Summary */}
      {summary && (
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={statCardStyle}>
            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Outstanding</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'monospace', color: '#d29922' }}>{summary.outstanding}</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>In Progress</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'monospace', color: '#00d4ff' }}>{summary.inProgress}</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Total Active</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'monospace' }}>{summary.total}</div>
          </div>
          {stats && stats.completionRates && stats.completionRates.length > 0 && (
            <div style={statCardStyle}>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Completion (30d)</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'monospace', color: '#3fb950' }}>
                {stats.completionRates.reduce((sum, r) => sum + r.completionRate, 0) / Math.max(stats.completionRates.length, 1) | 0}%
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filter */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {(['all', 'courier', 'item_exchange', 'auction'] as ContractTypeFilter[]).map(f => (
          <button key={f} onClick={() => setTypeFilter(f)} style={{
            background: typeFilter === f ? 'rgba(255,255,255,0.08)' : 'transparent',
            border: typeFilter === f ? '1px solid var(--border-color)' : '1px solid transparent',
            color: typeFilter === f ? '#fff' : 'var(--text-secondary)',
            padding: '0.4rem 0.75rem', borderRadius: '6px', cursor: 'pointer',
            fontSize: '0.8rem', fontWeight: typeFilter === f ? 600 : 400, textTransform: 'capitalize',
          }}>
            {f === 'item_exchange' ? 'Item Exchange' : f}
          </button>
        ))}
      </div>

      {/* Contracts table */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '80px 90px 1.5fr 90px 90px 90px 120px',
          gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Type</span><span>Status</span><span>Title</span>
          <span style={{ textAlign: 'right' }}>Price</span>
          <span style={{ textAlign: 'right' }}>Reward</span>
          <span style={{ textAlign: 'right' }}>Volume</span>
          <span>Issued</span>
        </div>

        {contracts.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No active contracts</div>
        ) : (
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {contracts.map((c, idx) => {
              const statusColor = CONTRACT_STATUS_COLORS[c.status] || '#8b949e';
              return (
                <div key={c.contractId} style={{
                  display: 'grid', gridTemplateColumns: '80px 90px 1.5fr 90px 90px 90px 120px',
                  gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem',
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                }}>
                  <span style={{
                    fontSize: '0.7rem', textTransform: 'capitalize',
                    color: 'rgba(255,255,255,0.6)',
                  }}>{c.type.replace('_', ' ')}</span>
                  <span style={{
                    padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                    background: `${statusColor}22`, color: statusColor, textTransform: 'capitalize', textAlign: 'center',
                  }}>{c.status.replace('_', ' ')}</span>
                  <span style={{ color: 'rgba(255,255,255,0.7)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {c.title || '—'}
                  </span>
                  <span style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.78rem', color: c.price ? '#3fb950' : 'rgba(255,255,255,0.3)' }}>
                    {c.price ? formatIsk(c.price) : '—'}
                  </span>
                  <span style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.78rem', color: c.reward ? '#d29922' : 'rgba(255,255,255,0.3)' }}>
                    {c.reward ? formatIsk(c.reward) : '—'}
                  </span>
                  <span style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.78rem', color: 'rgba(255,255,255,0.5)' }}>
                    {c.volume != null ? `${(c.volume / 1000).toFixed(1)}K m³` : '—'}
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)' }}>
                    {formatDate(c.dateIssued)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent changes */}
      {changes.length > 0 && (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '1rem',
        }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>Recent Changes (24h)</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', maxHeight: '200px', overflowY: 'auto' }}>
            {changes.slice(0, 20).map((ch, i) => {
              const oldColor = CONTRACT_STATUS_COLORS[ch.oldStatus] || '#8b949e';
              const newColor = CONTRACT_STATUS_COLORS[ch.newStatus] || '#8b949e';
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem',
                  padding: '0.3rem 0', borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', minWidth: '100px' }}>
                    {formatDate(ch.changedAt)}
                  </span>
                  <span style={{ textTransform: 'capitalize', color: 'rgba(255,255,255,0.5)' }}>{ch.type.replace('_', ' ')}</span>
                  <span style={{ color: oldColor, textTransform: 'capitalize' }}>{ch.oldStatus.replace('_', ' ')}</span>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>→</span>
                  <span style={{ color: newColor, fontWeight: 600, textTransform: 'capitalize' }}>{ch.newStatus.replace('_', ' ')}</span>
                  {ch.price != null && (
                    <span style={{ fontFamily: 'monospace', color: '#3fb950', marginLeft: 'auto' }}>{formatIsk(ch.price)}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Completion rates */}
      {stats && stats.completionRates && stats.completionRates.length > 0 && (
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>Completion Rates (30d)</div>
          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
            {stats.completionRates.map(rate => (
              <div key={rate.type} style={{ minWidth: '120px' }}>
                <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', textTransform: 'capitalize', marginBottom: '0.25rem' }}>
                  {rate.type.replace('_', ' ')}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
                  <span style={{
                    fontSize: '1.25rem', fontWeight: 700, fontFamily: 'monospace',
                    color: rate.completionRate >= 80 ? '#3fb950' : rate.completionRate >= 50 ? '#d29922' : '#f85149',
                  }}>
                    {rate.completionRate.toFixed(0)}%
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)' }}>
                    ({rate.completed}/{rate.total})
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
