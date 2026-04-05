import { useState } from 'react';
import { TierGate } from '../components/TierGate';
import { ListManager } from '../components/shopping/ListManager';
import { FreightCalculator } from '../components/shopping/FreightCalculator';

type ShopTab = 'lists' | 'freight';

export function Shopping() {
  const [activeTab, setActiveTab] = useState<ShopTab>('lists');

  const tabs: { id: ShopTab; label: string; color: string }[] = [
    { id: 'lists', label: 'Shopping Lists', color: '#3fb950' },
    { id: 'freight', label: 'Freight Calculator', color: '#d29922' },
  ];

  return (
    <TierGate requiredTier="pilot" showPreview={true}>
      <div>
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ fontSize: '1.5rem', margin: 0 }}>Shopping</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Manage shopping lists, compare prices, and calculate freight costs
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

        {activeTab === 'lists' && <ListManager />}
        {activeTab === 'freight' && <FreightCalculator />}
      </div>
    </TierGate>
  );
}
