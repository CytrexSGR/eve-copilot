export type MarketTab = 'prices' | 'history' | 'arbitrage' | 'opportunities' | 'portfolio';

interface TabDef {
  id: MarketTab;
  label: string;
  icon: string;
  color: string;
  requiresItem?: boolean;
}

const MARKET_TABS: TabDef[] = [
  { id: 'prices', label: 'Prices', icon: '💰', color: '#3fb950', requiresItem: true },
  { id: 'history', label: 'Order Book', icon: '📈', color: '#00d4ff', requiresItem: true },
  { id: 'arbitrage', label: 'Arbitrage', icon: '🔄', color: '#ffcc00' },
  { id: 'opportunities', label: 'Opportunities', icon: '🎯', color: '#ff8800' },
  { id: 'portfolio', label: 'Portfolio', icon: '📊', color: '#a855f7' },
];

interface Props {
  activeTab: MarketTab;
  onTabChange: (tab: MarketTab) => void;
  hasSelectedItem: boolean;
}

export function MarketTabNavigation({ activeTab, onTabChange, hasSelectedItem }: Props) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.25rem',
      padding: '0.35rem 0.5rem', background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)',
      height: '42px', boxSizing: 'border-box', marginBottom: '0.75rem',
    }}>
      {MARKET_TABS.map(tab => {
        const isActive = activeTab === tab.id;
        const isDisabled = tab.requiresItem && !hasSelectedItem;
        return (
          <button
            key={tab.id}
            onClick={() => !isDisabled && onTabChange(tab.id)}
            disabled={isDisabled}
            style={{
              padding: '0.35rem 0.6rem', fontSize: '0.75rem', fontWeight: 700,
              border: 'none', borderRadius: '4px', cursor: isDisabled ? 'not-allowed' : 'pointer',
              background: isActive ? `${tab.color}22` : 'transparent',
              color: isActive ? tab.color : isDisabled ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.4)',
              borderBottom: isActive ? `2px solid ${tab.color}` : '2px solid transparent',
              textTransform: 'uppercase', letterSpacing: '0.03em',
              display: 'flex', alignItems: 'center', gap: '0.3rem',
              opacity: isDisabled ? 0.4 : 1,
            }}
          >
            <span style={{ opacity: isActive ? 1 : 0.6 }}>{tab.icon}</span>
            {tab.label}
            {isActive && (
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: tab.color, boxShadow: `0 0 8px ${tab.color}`,
              }} />
            )}
          </button>
        );
      })}
    </div>
  );
}
