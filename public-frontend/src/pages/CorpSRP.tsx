import { useState } from 'react';
import { SrpRequestsTab } from '../components/srp/SrpRequestsTab';
import { DoctrinesTab } from '../components/srp/DoctrinesTab';
import { SrpStatsTab } from '../components/srp/SrpStatsTab';
import { SrpConfigTab } from '../components/srp/SrpConfigTab';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { useAuth } from '../hooks/useAuth';

type SrpTab = 'requests' | 'doctrines' | 'stats' | 'config';

export function CorpSRP() {
  const [activeTab, setActiveTab] = useState<SrpTab>('requests');
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  const tabs: { id: SrpTab; label: string; color: string }[] = [
    { id: 'requests', label: 'SRP Requests', color: '#f85149' },
    { id: 'doctrines', label: 'Doctrines', color: '#00d4ff' },
    { id: 'stats', label: 'Statistics', color: '#3fb950' },
    { id: 'config', label: 'Config', color: '#d29922' },
  ];

  return (
    <div>
        {corpId && <CorpPageHeader corpId={corpId} title="SRP" subtitle="Ship Replacement Program — requests, doctrine management, and payouts" />}

        {!corpId ? (
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '2rem',
            textAlign: 'center',
            color: 'var(--text-secondary)',
          }}>
            No corporation found. Please ensure your character is in a corporation.
          </div>
        ) : (
          <>
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

            {activeTab === 'requests' && <SrpRequestsTab corpId={corpId} />}
            {activeTab === 'doctrines' && <DoctrinesTab corpId={corpId} />}
            {activeTab === 'stats' && <SrpStatsTab corpId={corpId} />}
            {activeTab === 'config' && <SrpConfigTab corpId={corpId} />}
          </>
        )}
    </div>
  );
}
