const FEATURES = [
  {
    icon: '/warfare-intel-logo.png',
    title: 'Warfare Intelligence',
    description: 'Real-time battle reports, coalition tracking, fleet doctrine analysis, and capital movement alerts across all of nullsec.',
    color: '#f85149',
  },
  {
    icon: '/war-economy-logo.png',
    title: 'Economic Warfare',
    description: 'Market manipulation detection, fuel trend analysis, trade route optimization, and arbitrage discovery across 5 trade hubs.',
    color: '#d29922',
  },
  {
    icon: '/wormhole-intel-logo.png',
    title: 'Wormhole Intel',
    description: 'J-Space scanning intel, chain mapping data, wormhole resident tracking, and Thera route calculation.',
    color: '#a855f7',
  },
  {
    title: 'Fleet & Corp Tools',
    description: 'SRP management, fleet PAP tracking, D-Scan parser, local scan analysis, structure timers, and HR recruitment pipeline.',
    color: '#00d4ff',
  },
  {
    title: 'Market & Production',
    description: 'Live market data for 16K+ items, production calculators with ME/TE optimization, invention cost analysis, and buyback programs.',
    color: '#3fb950',
  },
  {
    title: 'Character Management',
    description: 'Multi-character dashboard with skill queues, asset valuation, industry jobs tracking, and wallet analysis.',
    color: '#58a6ff',
  },
];

export function LandingFeatures() {
  return (
    <div style={{ marginBottom: '2rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.4rem' }}>
          One Platform. Total Awareness.
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Everything you need to make informed decisions in New Eden.
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem',
      }}>
        {FEATURES.map(feat => (
          <div key={feat.title} style={{
            background: 'var(--bg-secondary)',
            border: `1px solid ${feat.color}22`,
            borderRadius: '8px',
            padding: '1.25rem',
            transition: 'border-color 0.2s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem' }}>
              {feat.icon && (
                <img src={feat.icon} alt="" style={{ width: 22, height: 22, objectFit: 'contain' }} />
              )}
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: feat.color }}>{feat.title}</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              {feat.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
