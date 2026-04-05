import { useState } from 'react';
import { VettingTab } from '../components/hr/VettingTab';
import { RedListTab } from '../components/hr/RedListTab';
import { ActivityTab } from '../components/hr/ActivityTab';
import { ApplicationsTab } from '../components/hr/ApplicationsTab';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { useAuth } from '../hooks/useAuth';

type HrTab = 'vetting' | 'redlist' | 'activity' | 'applications';

export function CorpHR() {
  const [activeTab, setActiveTab] = useState<HrTab>('vetting');
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  const tabs: { id: HrTab; label: string; color: string }[] = [
    { id: 'vetting', label: 'Vetting', color: '#00d4ff' },
    { id: 'redlist', label: 'Red List', color: '#f85149' },
    { id: 'activity', label: 'Activity', color: '#3fb950' },
    { id: 'applications', label: 'Applications', color: '#a855f7' },
  ];

  return (
    <div>
        {corpId && <CorpPageHeader corpId={corpId} title="HR & Recruitment" subtitle="Character vetting, red list management, activity tracking, and recruitment" />}

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

            {activeTab === 'vetting' && <VettingTab corpId={corpId} />}
            {activeTab === 'redlist' && <RedListTab corpId={corpId} />}
            {activeTab === 'activity' && <ActivityTab corpId={corpId} />}
            {activeTab === 'applications' && <ApplicationsTab corpId={corpId} />}
          </>
        )}
    </div>
  );
}
