import { useState } from 'react';
import { ContractsTab } from '../components/corptools/ContractsTab';
import { DiscordTab } from '../components/corptools/DiscordTab';
import { MoonMiningTab } from '../components/corptools/MoonMiningTab';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { useAuth } from '../hooks/useAuth';

type ToolsTab = 'contracts' | 'discord' | 'moon-mining';

export function CorpTools() {
  const [activeTab, setActiveTab] = useState<ToolsTab>('contracts');
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  const tabs: { id: ToolsTab; label: string; color: string }[] = [
    { id: 'contracts', label: 'Contracts', color: '#00d4ff' },
    { id: 'discord', label: 'Discord', color: '#a855f7' },
    { id: 'moon-mining', label: 'Moon Mining', color: '#d29922' },
  ];

  return (
    <div>
        {corpId && <CorpPageHeader corpId={corpId} title="Corp Tools" subtitle="Contract tracking, Discord webhooks, and corp management utilities" />}

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

            {activeTab === 'contracts' && <ContractsTab corpId={corpId} />}
            {activeTab === 'discord' && <DiscordTab />}
            {activeTab === 'moon-mining' && corpId && <MoonMiningTab corpId={corpId} />}
          </>
        )}
    </div>
  );
}
