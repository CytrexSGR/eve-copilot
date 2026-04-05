import { usePilotIntel } from '../../hooks/usePilotIntel';
import { formatISK } from '../../utils/format';

export function WealthSummaryBar() {
  const { derived } = usePilotIntel();
  const { totalWallet, totalSellOrderValue, totalBuyEscrow, totalNetWorth } = derived;

  const segments = [
    { label: 'Wallet', value: totalWallet, color: '#3fb950' },
    { label: 'Sell Orders', value: totalSellOrderValue, color: '#00d4ff' },
    { label: 'Buy Escrow', value: totalBuyEscrow, color: '#ff8800' },
  ];

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '8px', padding: '0.75rem 1rem', marginBottom: '0.75rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>
          Net Worth
        </span>
        <span style={{ fontSize: '1.3rem', fontFamily: 'monospace', fontWeight: 700, color: '#3fb950' }}>
          {formatISK(totalNetWorth)}
        </span>
      </div>
      {/* Bar */}
      <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden', display: 'flex' }}>
        {segments.map(s => {
          const pct = totalNetWorth > 0 ? (s.value / totalNetWorth) * 100 : 0;
          return pct > 0 ? (
            <div key={s.label} style={{ width: `${pct}%`, background: s.color, height: '100%' }} />
          ) : null;
        })}
      </div>
      {/* Legend */}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '0.4rem' }}>
        {segments.map(s => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)' }}>{s.label}</span>
            <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: s.color, fontWeight: 600 }}>{formatISK(s.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
