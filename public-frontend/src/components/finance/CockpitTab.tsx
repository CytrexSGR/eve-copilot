import { useState } from 'react';
import { fontSize, color, spacing } from '../../styles/theme';
import { TIME_OPTIONS } from '../../types/cockpit';
import { CockpitHeader } from './cockpit/CockpitHeader';
import { FinanceSection } from './cockpit/FinanceSection';
import { MilitarySection } from './cockpit/MilitarySection';
import { PersonnelSection } from './cockpit/PersonnelSection';
import { ProductionSection } from './cockpit/ProductionSection';

interface CockpitTabProps {
  corpId: number;
}

export function CockpitTab({ corpId }: CockpitTabProps) {
  const [days, setDays] = useState(7);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
      <CockpitHeader corpId={corpId} days={days} />

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

      <FinanceSection corpId={corpId} days={days} />
      <MilitarySection corpId={corpId} days={days} />
      <PersonnelSection corpId={corpId} days={days} />
      <ProductionSection corpId={corpId} days={days} />
    </div>
  );
}
