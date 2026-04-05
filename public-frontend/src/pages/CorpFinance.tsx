import { useState } from 'react';
import { CockpitTab } from '../components/finance/CockpitTab';
import { WalletTab } from '../components/finance/WalletTab';
import { ReportsTab } from '../components/finance/ReportsTab';
import { MiningTaxTab } from '../components/finance/MiningTaxTab';
import { BuybackTab } from '../components/finance/BuybackTab';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { useAuth } from '../hooks/useAuth';

type FinanceTab = 'cockpit' | 'wallet' | 'reports' | 'mining' | 'buyback';

export function CorpFinance() {
  const [activeTab, setActiveTab] = useState<FinanceTab>('cockpit');
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  const tabs: { id: FinanceTab; label: string; color: string }[] = [
    { id: 'cockpit', label: 'Cockpit', color: '#00d4ff' },
    { id: 'wallet', label: 'Wallet', color: '#3fb950' },
    { id: 'reports', label: 'Reports', color: '#00d4ff' },
    { id: 'mining', label: 'Mining Tax', color: '#d29922' },
    { id: 'buyback', label: 'Buyback', color: '#ff8800' },
  ];

  return (
    <div>
        {corpId && <CorpPageHeader corpId={corpId} title="Finance" subtitle="Wallet, reports, mining tax, and buyback management" />}

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

            {activeTab === 'cockpit' && <CockpitTab corpId={corpId} />}
            {activeTab === 'wallet' && <WalletTab corpId={corpId} />}
            {activeTab === 'reports' && <ReportsTab corpId={corpId} />}
            {activeTab === 'mining' && <MiningTaxTab corpId={corpId} />}
            {activeTab === 'buyback' && <BuybackTab corpId={corpId} />}
          </>
        )}
    </div>
  );
}
