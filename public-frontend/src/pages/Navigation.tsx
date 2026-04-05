import { useState } from 'react';
import { TierGate } from '../components/TierGate';
import { JumpPlanner } from '../components/navigation/JumpPlanner';
import { TheraRouterTab } from '../components/wormhole/TheraRouterTab';

type NavTab = 'jump-planner' | 'thera-router';

export function Navigation() {
  const [activeTab, setActiveTab] = useState<NavTab>('jump-planner');

  const tabs: { id: NavTab; label: string; color: string }[] = [
    { id: 'jump-planner', label: 'Jump Planner', color: '#00d4ff' },
    { id: 'thera-router', label: 'Thera Router', color: '#ff8800' },
  ];

  return (
    <TierGate requiredTier="pilot" showPreview={true}>
      <div>
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ fontSize: '1.5rem', margin: 0 }}>Navigation</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Capital jump planning and wormhole routing
          </p>
        </div>

        <div style={{
          display: 'flex',
          gap: '0.5rem',
          marginBottom: '1.5rem',
          borderBottom: '1px solid var(--border-color)',
          paddingBottom: '0.5rem',
        }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? `${tab.color}15` : 'transparent',
                border: activeTab === tab.id ? `1px solid ${tab.color}44` : '1px solid transparent',
                color: activeTab === tab.id ? tab.color : 'var(--text-secondary)',
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: activeTab === tab.id ? 600 : 400,
                transition: 'all 0.2s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'jump-planner' && <JumpPlanner />}
        {activeTab === 'thera-router' && <TheraRouterTab />}
      </div>
    </TierGate>
  );
}
