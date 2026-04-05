import { useState } from 'react';
import { TierGate } from '../components/TierGate';
import { DScanParser } from '../components/intel/DScanParser';
import { LocalScan } from '../components/intel/LocalScan';
import { Notifications } from '../components/intel/Notifications';
import { IncursionsTab } from '../components/intel/IncursionsTab';

type IntelTab = 'dscan' | 'local' | 'notifications' | 'incursions';

export function Intel() {
  const [activeTab, setActiveTab] = useState<IntelTab>('dscan');

  const tabs: { id: IntelTab; label: string; color: string }[] = [
    { id: 'dscan', label: 'D-Scan Parser', color: '#f85149' },
    { id: 'local', label: 'Local Scan', color: '#d29922' },
    { id: 'notifications', label: 'Notifications', color: '#00d4ff' },
    { id: 'incursions', label: 'Incursions', color: '#3fb950' },
  ];

  return (
    <TierGate requiredTier="pilot" showPreview={true}>
      <div>
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ fontSize: '1.5rem', margin: 0 }}>Intel Tools</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Tactical intelligence — paste D-Scan or Local to analyze threats
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

        {activeTab === 'dscan' && <DScanParser />}
        {activeTab === 'local' && <LocalScan />}
        {activeTab === 'notifications' && <Notifications />}
        {activeTab === 'incursions' && <IncursionsTab />}
      </div>
    </TierGate>
  );
}
