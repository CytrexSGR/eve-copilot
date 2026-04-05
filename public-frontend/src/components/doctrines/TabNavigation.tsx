import { memo } from 'react';
import { Activity, Users, TrendingUp } from 'lucide-react';

export type DoctrineTab = 'live-ops' | 'intel' | 'trends';

interface TabNavigationProps {
  activeTab: DoctrineTab;
  onTabChange: (tab: DoctrineTab) => void;
}

const TABS: { id: DoctrineTab; label: string; icon: typeof Activity; color: string }[] = [
  { id: 'live-ops', label: 'Live Ops', icon: Activity, color: '#ff4444' },
  { id: 'intel', label: 'Intel', icon: Users, color: '#58a6ff' },
  { id: 'trends', label: 'Trends', icon: TrendingUp, color: '#00ff88' },
];

export const TabNavigation = memo(function TabNavigation({
  activeTab,
  onTabChange
}: TabNavigationProps) {
  return (
    <div style={{
      display: 'flex',
      gap: '0.25rem',
      padding: '0.35rem 0.5rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.05)',
      marginBottom: '1rem'
    }}>
      {TABS.map(({ id, label, icon: Icon, color }) => {
        const isActive = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 1rem',
              fontSize: '0.8rem',
              fontWeight: 700,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              textTransform: 'uppercase',
              letterSpacing: '0.03em',
              background: isActive ? `${color}22` : 'transparent',
              color: isActive ? color : 'rgba(255,255,255,0.5)',
              borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent'
            }}
          >
            <Icon size={16} />
            {label}
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
});
