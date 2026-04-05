import { useState } from 'react';
import { fontSize, color, spacing } from '../styles/theme';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { KpiStrip } from '../components/corp/dashboard/KpiStrip';
import { AlertsPanel } from '../components/corp/dashboard/AlertsPanel';
import { TreasuryCard } from '../components/corp/dashboard/TreasuryCard';
import { MilitaryCard } from '../components/corp/dashboard/MilitaryCard';
import { PersonnelCard } from '../components/corp/dashboard/PersonnelCard';
import { DefenseCard } from '../components/corp/dashboard/DefenseCard';
import { InfrastructureCard } from '../components/corp/dashboard/InfrastructureCard';
import { LogisticsCard } from '../components/corp/dashboard/LogisticsCard';
import { BulletinCard } from '../components/corp/dashboard/BulletinCard';
import { useAuth } from '../hooks/useAuth';

const TIME_OPTIONS = [
  { days: 7, label: '7D' },
  { days: 14, label: '14D' },
  { days: 30, label: '30D' },
];

export function CorpDashboard() {
  const [days, setDays] = useState(7);
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  return (
    <div>
      {corpId && (
        <CorpPageHeader
          corpId={corpId}
          title="Command Center"
          subtitle="Strategic overview — treasury, military, personnel, infrastructure, and logistics"
        />
      )}

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
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
          {/* Time selector */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: spacing.xs }}>
            {TIME_OPTIONS.map(opt => (
              <button
                key={opt.days}
                onClick={() => setDays(opt.days)}
                style={{
                  padding: '0.25rem 0.5rem',
                  background: days === opt.days ? 'rgba(0,212,255,0.15)' : 'transparent',
                  border: days === opt.days ? '1px solid #00d4ff44' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  fontSize: fontSize.tiny,
                  fontWeight: 600,
                  color: days === opt.days ? color.accentCyan : 'rgba(255,255,255,0.4)',
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* KPI Strip */}
          <KpiStrip corpId={corpId} days={days} />

          {/* Alerts */}
          <AlertsPanel corpId={corpId} />

          {/* Section Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
            gap: spacing.lg,
          }}>
            <TreasuryCard corpId={corpId} days={days} />
            <MilitaryCard corpId={corpId} days={days} />
            <PersonnelCard corpId={corpId} />
            <DefenseCard corpId={corpId} />
            <InfrastructureCard />
            <LogisticsCard corpId={corpId} />
            <BulletinCard corpId={corpId} />
          </div>
        </div>
      )}
    </div>
  );
}
