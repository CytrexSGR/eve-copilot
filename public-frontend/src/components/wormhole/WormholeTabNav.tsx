import { WORMHOLE_TAB_CONFIG } from '../../constants/wormhole';
import type { WormholeTabId } from '../../types/wormhole';

interface WormholeTabNavProps {
  activeTab: WormholeTabId;
  onTabChange: (tab: WormholeTabId) => void;
}

export function WormholeTabNav({ activeTab, onTabChange }: WormholeTabNavProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap: '0.5rem',
        padding: '0.75rem',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        marginTop: '1rem',
      }}
    >
      {WORMHOLE_TAB_CONFIG.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1rem',
              background: isActive ? `${tab.color}22` : 'transparent',
              border: 'none',
              borderBottom: isActive ? `2px solid ${tab.color}` : '2px solid transparent',
              borderRadius: '6px 6px 0 0',
              color: isActive ? tab.color : 'rgba(255,255,255,0.4)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              fontSize: '0.9rem',
              fontWeight: 500,
            }}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {isActive && (
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: tab.color,
                  boxShadow: `0 0 8px ${tab.color}`,
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
