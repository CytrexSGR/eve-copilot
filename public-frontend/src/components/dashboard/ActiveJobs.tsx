import { usePilotIntel } from '../../hooks/usePilotIntel';
import { formatISK } from '../../utils/format';
import { ACTIVITY_NAMES, ACTIVITY_COLORS } from '../../types/character';

function timeRemaining(endDate: string): string {
  const ms = new Date(endDate).getTime() - Date.now();
  if (ms <= 0) return 'Done';
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function ActiveJobs() {
  const { profile, derived } = usePilotIntel();

  // Collect all active jobs from all characters
  const allJobs = profile.characters.flatMap(char =>
    (char.industry?.jobs ?? [])
      .filter(j => j.status === 'active')
      .map(j => ({ ...j, characterName: char.character_name }))
  ).sort((a, b) => {
    if (!a.end_date) return 1;
    if (!b.end_date) return -1;
    return new Date(a.end_date).getTime() - new Date(b.end_date).getTime();
  });

  const orders = profile.orders;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
      {/* Industry Jobs */}
      <div style={{
        background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '8px', padding: '0.65rem',
      }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '0.4rem' }}>
          Industry ({derived.activeIndustryJobs} active)
        </div>
        {allJobs.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.75rem', padding: '0.5rem 0' }}>No active jobs</div>
        ) : allJobs.slice(0, 6).map(job => (
          <div key={job.job_id} style={{
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            padding: '0.3rem 0', borderBottom: '1px solid rgba(255,255,255,0.03)',
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
              background: ACTIVITY_COLORS[job.activity_id] || '#8b949e',
            }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {job.product_type_name || job.blueprint_type_name}
              </div>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>
                {ACTIVITY_NAMES[job.activity_id] || 'Unknown'} x{job.runs} — {job.characterName}
              </div>
            </div>
            <span style={{
              fontSize: '0.7rem', fontFamily: 'monospace', fontWeight: 600, flexShrink: 0,
              color: job.end_date && (new Date(job.end_date).getTime() - Date.now() < 3600000) ? '#3fb950' : '#00d4ff',
            }}>
              {job.end_date ? timeRemaining(job.end_date) : '\u2014'}
            </span>
          </div>
        ))}
      </div>

      {/* Orders Summary */}
      <div style={{
        background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '8px', padding: '0.65rem',
      }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '0.4rem' }}>
          Market Orders
        </div>
        {orders?.summary ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginBottom: '0.5rem' }}>
              <div style={{ background: 'rgba(63,185,80,0.08)', borderRadius: '4px', padding: '0.4rem' }}>
                <div style={{ fontSize: '0.6rem', color: '#3fb950' }}>SELL</div>
                <div style={{ fontSize: '0.85rem', fontFamily: 'monospace', fontWeight: 700 }}>{orders.summary.total_sell_orders}</div>
                <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>{formatISK(orders.summary.total_isk_in_sell_orders)}</div>
              </div>
              <div style={{ background: 'rgba(0,212,255,0.08)', borderRadius: '4px', padding: '0.4rem' }}>
                <div style={{ fontSize: '0.6rem', color: '#00d4ff' }}>BUY</div>
                <div style={{ fontSize: '0.85rem', fontFamily: 'monospace', fontWeight: 700 }}>{orders.summary.total_buy_orders}</div>
                <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>{formatISK(orders.summary.total_isk_in_buy_orders)}</div>
              </div>
            </div>
            {derived.outbidCount > 0 && (
              <div style={{
                background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.25)',
                borderRadius: '4px', padding: '0.35rem 0.5rem',
                display: 'flex', alignItems: 'center', gap: '0.3rem',
              }}>
                <span style={{ fontSize: '0.7rem', color: '#f85149', fontWeight: 700 }}>{derived.outbidCount}</span>
                <span style={{ fontSize: '0.65rem', color: '#f85149' }}>orders outbid</span>
              </div>
            )}
          </>
        ) : (
          <div style={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.75rem', padding: '0.5rem 0' }}>No order data</div>
        )}
      </div>
    </div>
  );
}
