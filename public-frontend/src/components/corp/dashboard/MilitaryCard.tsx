import { useState, useEffect } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { corpApi } from '../../../services/corporationApi';
import { formatIsk } from '../../../types/finance';
import { SectionCard } from './SectionCard';
import type { OffensiveStats } from '../../../types/corporation';

interface MilitaryCardProps {
  corpId: number;
  days: number;
}

/** Parse a pre-formatted ISK string (e.g. "123.45B ISK") back to a raw number. */
function parseIskString(s: string): number {
  const cleaned = s.replace(/,/g, '').replace(/\s*ISK\s*/i, '').trim();
  const match = cleaned.match(/^(-?[\d.]+)\s*([BKMGT]?)$/i);
  if (!match) return 0;
  const num = parseFloat(match[1]);
  const suffix = match[2].toUpperCase();
  const multipliers: Record<string, number> = { '': 1, K: 1e3, M: 1e6, B: 1e9, T: 1e12 };
  return num * (multipliers[suffix] ?? 1);
}

function getEfficiencyColor(eff: number): string {
  if (eff >= 70) return '#3fb950';
  if (eff >= 50) return '#d29922';
  return '#f85149';
}

export function MilitaryCard({ corpId, days }: MilitaryCardProps) {
  const [stats, setStats] = useState<OffensiveStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    corpApi.getOffensiveStats(corpId, days).then(data => {
      if (cancelled) return;
      setStats(data);
      setLoading(false);
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  const summary = stats?.summary;
  const totalKills = summary?.total_kills ?? 0;
  const kdRatio = summary?.kd_ratio ?? 0;
  const totalDeaths = kdRatio > 0 ? Math.round(totalKills / kdRatio) : 0;
  const efficiency = summary?.efficiency ?? 0;
  const effColor = getEfficiencyColor(efficiency);

  // Parse ISK destroyed from formatted string, derive ISK lost from efficiency
  const iskDestroyed = summary ? parseIskString(summary.isk_destroyed) : 0;
  const iskLost = efficiency > 0 && efficiency < 100
    ? iskDestroyed * (100 - efficiency) / efficiency
    : 0;

  return (
    <SectionCard
      title="Military"
      borderColor="#f85149"
      linkTo="/corp/fleet"
      loading={loading}
    >
      {/* Kill / Death line */}
      <div style={{
        fontSize: fontSize.base,
        fontFamily: 'monospace',
        fontWeight: 700,
      }}>
        <span style={{ color: color.killGreen }}>
          {totalKills.toLocaleString()}
        </span>
        <span style={{ color: color.textSecondary }}> / </span>
        <span style={{ color: color.lossRed }}>
          {totalDeaths.toLocaleString()}
        </span>
      </div>

      {/* ISK Efficiency bar */}
      <div
        style={{
          background: 'rgba(255,255,255,0.1)',
          height: '6px',
          borderRadius: '3px',
          margin: '0.25rem 0',
        }}
      >
        <div
          style={{
            width: `${Math.min(efficiency, 100)}%`,
            background: effColor,
            height: '100%',
            borderRadius: '3px',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      <div style={{
        fontSize: fontSize.tiny,
        color: effColor,
      }}>
        {efficiency.toFixed(1)}% ISK Efficiency
      </div>

      {/* ISK Values */}
      <div style={{
        fontSize: fontSize.tiny,
        fontFamily: 'monospace',
        color: color.killGreen,
        marginTop: '0.15rem',
      }}>
        Destroyed: {iskDestroyed > 0 ? formatIsk(iskDestroyed) : '--'}
      </div>
      <div style={{
        fontSize: fontSize.tiny,
        fontFamily: 'monospace',
        color: color.lossRed,
      }}>
        Lost: {iskLost > 0 ? formatIsk(iskLost) : '--'}
      </div>
    </SectionCard>
  );
}
