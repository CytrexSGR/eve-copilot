import { useState, useEffect } from 'react';
import { srpApi } from '../../services/api/srp';
import type { SrpRequest } from '../../types/srp';
import { SRP_STATUS_COLORS, formatIsk } from '../../types/srp';

export function SrpStatsTab({ corpId }: { corpId: number }) {
  const [requests, setRequests] = useState<SrpRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    srpApi.getRequests(corpId, { limit: 200 })
      .then(setRequests)
      .catch(err => console.error('Failed to load SRP stats:', err))
      .finally(() => setLoading(false));
  }, [corpId]);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>;
  }

  // Compute stats
  const total = requests.length;
  const byStatus: Record<string, SrpRequest[]> = {};
  for (const r of requests) {
    if (!byStatus[r.status]) byStatus[r.status] = [];
    byStatus[r.status].push(r);
  }

  const totalPayout = requests.reduce((sum, r) => sum + r.payout_amount, 0);
  const paidPayout = (byStatus['paid'] || []).reduce((sum, r) => sum + r.payout_amount, 0);
  const approvedPayout = (byStatus['approved'] || []).reduce((sum, r) => sum + r.payout_amount, 0);

  const avgPayout = total > 0 ? totalPayout / total : 0;
  const avgMatchScore = total > 0 ? requests.reduce((sum, r) => sum + r.match_score, 0) / total : 0;

  // Top ships
  const shipCounts: Record<string, { count: number; totalIsk: number }> = {};
  for (const r of requests) {
    const key = r.ship_name || `Type ${r.ship_type_id}`;
    if (!shipCounts[key]) shipCounts[key] = { count: 0, totalIsk: 0 };
    shipCounts[key].count++;
    shipCounts[key].totalIsk += r.payout_amount;
  }
  const topShips = Object.entries(shipCounts)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 10);

  // Top claimants
  const claimantCounts: Record<string, { count: number; totalIsk: number }> = {};
  for (const r of requests) {
    const key = r.character_name || `ID ${r.character_id}`;
    if (!claimantCounts[key]) claimantCounts[key] = { count: 0, totalIsk: 0 };
    claimantCounts[key].count++;
    claimantCounts[key].totalIsk += r.payout_amount;
  }
  const topClaimants = Object.entries(claimantCounts)
    .sort((a, b) => b[1].totalIsk - a[1].totalIsk)
    .slice(0, 10);

  const statCardStyle = {
    background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
    borderRadius: '8px', padding: '1rem',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem' }}>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Total Requests</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace' }}>{total}</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Total Payout</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: '#3fb950' }}>{formatIsk(totalPayout)}</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Avg Payout</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: '#00d4ff' }}>{formatIsk(avgPayout)}</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Avg Match</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: '#d29922' }}>{(avgMatchScore * 100).toFixed(0)}%</div>
        </div>
      </div>

      {/* Status breakdown */}
      <div style={statCardStyle}>
        <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Status Breakdown</div>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {['pending', 'approved', 'rejected', 'paid'].map(status => {
            const count = (byStatus[status] || []).length;
            const pct = total > 0 ? (count / total * 100).toFixed(0) : '0';
            const color = SRP_STATUS_COLORS[status] || '#8b949e';
            return (
              <div key={status} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                  width: '8px', height: '8px', borderRadius: '2px', background: color,
                }} />
                <span style={{ fontSize: '0.85rem', textTransform: 'capitalize' }}>{status}</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color }}>{count}</span>
                <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)' }}>({pct}%)</span>
              </div>
            );
          })}
        </div>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem', fontSize: '0.8rem' }}>
          <span>Paid: <span style={{ fontFamily: 'monospace', color: '#00d4ff' }}>{formatIsk(paidPayout)}</span></span>
          <span>Pending Payout: <span style={{ fontFamily: 'monospace', color: '#d29922' }}>{formatIsk(approvedPayout)}</span></span>
        </div>
      </div>

      {/* Two columns: Top Ships + Top Claimants */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        {/* Top Ships */}
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Top Ships Lost</div>
          {topShips.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>No data</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {topShips.map(([ship, data], i) => (
                <div key={ship} style={{
                  display: 'grid', gridTemplateColumns: '20px 1fr 50px 80px',
                  gap: '0.5rem', padding: '0.3rem 0', fontSize: '0.8rem', alignItems: 'center',
                  borderBottom: i < topShips.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', fontSize: '0.7rem' }}>#{i + 1}</span>
                  <span style={{ color: 'rgba(255,255,255,0.8)' }}>{ship}</span>
                  <span style={{ fontFamily: 'monospace', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{data.count}x</span>
                  <span style={{ fontFamily: 'monospace', textAlign: 'right', color: '#3fb950', fontSize: '0.78rem' }}>{formatIsk(data.totalIsk)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Claimants */}
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Top Claimants</div>
          {topClaimants.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>No data</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {topClaimants.map(([name, data], i) => (
                <div key={name} style={{
                  display: 'grid', gridTemplateColumns: '20px 1fr 50px 80px',
                  gap: '0.5rem', padding: '0.3rem 0', fontSize: '0.8rem', alignItems: 'center',
                  borderBottom: i < topClaimants.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', fontSize: '0.7rem' }}>#{i + 1}</span>
                  <span style={{ color: 'rgba(255,255,255,0.8)' }}>{name}</span>
                  <span style={{ fontFamily: 'monospace', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{data.count}x</span>
                  <span style={{ fontFamily: 'monospace', textAlign: 'right', color: '#3fb950', fontSize: '0.78rem' }}>{formatIsk(data.totalIsk)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
