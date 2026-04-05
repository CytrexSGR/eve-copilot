import { TABS, TAB_COLORS } from '../../constants/battleReport';
import type { TabId } from '../../constants/battleReport';

interface TabNavigationProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.35rem 0.5rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.05)',
      height: '42px',
      boxSizing: 'border-box',
    }}>
      {TABS.map(tab => {
        const color = TAB_COLORS[tab.id];
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              padding: '0.35rem 0.6rem',
              fontSize: '0.75rem',
              fontWeight: 700,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              background: isActive ? `${color}22` : 'transparent',
              color: isActive ? color : 'rgba(255,255,255,0.4)',
              borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
              textTransform: 'uppercase',
              letterSpacing: '0.03em',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem'
            }}
          >
            <span style={{ opacity: isActive ? 1 : 0.6 }}>{tab.icon}</span>
            {tab.label}
            {isActive && (
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: color,
                boxShadow: `0 0 8px ${color}`
              }} />
            )}
          </button>
        );
      })}
    </div>
  );
}
