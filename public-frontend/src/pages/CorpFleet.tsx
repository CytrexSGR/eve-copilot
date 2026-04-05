import { useState } from 'react';
import { OperationsTab } from '../components/fleet/OperationsTab';
import { PapStatsTab } from '../components/fleet/PapStatsTab';
import { OpsCalendar } from '../components/fleet/OpsCalendar';
import { NotificationConfig } from '../components/fleet/NotificationConfig';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { useAuth } from '../hooks/useAuth';

type FleetTab = 'operations' | 'pap' | 'calendar' | 'notifications';

export function CorpFleet() {
  const [activeTab, setActiveTab] = useState<FleetTab>('operations');
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  const tabs: { id: FleetTab; label: string; color: string }[] = [
    { id: 'operations', label: 'Operations', color: '#f85149' },
    { id: 'calendar', label: 'Calendar', color: '#58a6ff' },
    { id: 'pap', label: 'PAP Stats', color: '#3fb950' },
    { id: 'notifications', label: 'Notifications', color: '#d2a8ff' },
  ];

  return (
    <div>
        {corpId && <CorpPageHeader corpId={corpId} title="Fleet Ops" subtitle="Fleet management, participation tracking, and PAP reports" />}

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

            {activeTab === 'operations' && <OperationsTab corpId={corpId} />}
            {activeTab === 'calendar' && <OpsCalendar corpId={corpId} />}
            {activeTab === 'pap' && <PapStatsTab corpId={corpId} />}
            {activeTab === 'notifications' && <NotificationConfig />}
          </>
        )}
    </div>
  );
}
