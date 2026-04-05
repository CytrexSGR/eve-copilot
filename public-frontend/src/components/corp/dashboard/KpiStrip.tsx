import { useState, useEffect } from 'react';
import { walletApi } from '../../../services/api/finance';
import { corpApi } from '../../../services/corporationApi';
import { formatIsk } from '../../../types/finance';
import { fontSize, color } from '../../../styles/theme';
import type { OffensiveStats } from '../../../types/corporation';
import type { WalletBalance } from '../../../types/finance';

interface KpiStripProps {
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

interface TileConfig {
  label: string;
  value: string;
  color: string;
}

function getEfficiencyColor(eff: number): string {
  if (eff >= 70) return '#3fb950';
  if (eff >= 50) return '#d29922';
  return '#f85149';
}

function getKdColor(kd: number): string {
  if (kd >= 2) return '#3fb950';
  if (kd >= 1) return '#d29922';
  return '#f85149';
}

export function KpiStrip({ corpId, days }: KpiStripProps) {
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState<WalletBalance | null>(null);
  const [offensive, setOffensive] = useState<OffensiveStats | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      walletApi.getBalance(corpId),
      corpApi.getOffensiveStats(corpId, days),
    ]).then(([balanceResult, offensiveResult]) => {
      if (cancelled) return;
      if (balanceResult.status === 'fulfilled') setBalance(balanceResult.value);
      if (offensiveResult.status === 'fulfilled') setOffensive(offensiveResult.value);
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            style={{
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '6px',
              padding: '0.5rem 0.75rem',
              minWidth: '110px',
              flex: '1 1 0',
              height: '48px',
              animation: 'kpi-pulse 1.5s ease-in-out infinite',
            }}
          />
        ))}
        <style>{`
          @keyframes kpi-pulse {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 0.7; }
          }
        `}</style>
      </div>
    );
  }

  const summary = offensive?.summary;

  // Derive total_deaths from kd_ratio
  const totalKills = summary?.total_kills ?? 0;
  const kdRatio = summary?.kd_ratio ?? 0;
  const totalDeaths = kdRatio > 0 ? Math.round(totalKills / kdRatio) : 0;

  // Parse ISK destroyed from formatted string, derive ISK lost from efficiency
  const iskDestroyedRaw = summary ? parseIskString(summary.isk_destroyed) : 0;
  const efficiency = summary?.efficiency ?? 0;
  const iskLostRaw = efficiency > 0 && efficiency < 100
    ? iskDestroyedRaw * (100 - efficiency) / efficiency
    : 0;

  const tiles: TileConfig[] = [
    {
      label: 'Wallet',
      value: balance ? formatIsk(balance.balance) : '---',
      color: color.killGreen,
    },
    {
      label: 'Net Income',
      value: '\u2014',
      color: color.textSecondary,
    },
    {
      label: 'ISK Efficiency',
      value: summary ? `${summary.efficiency.toFixed(1)}%` : '---',
      color: summary ? getEfficiencyColor(summary.efficiency) : color.textSecondary,
    },
    {
      label: 'K/D Ratio',
      value: summary
        ? (totalDeaths === 0 ? '\u221E' : kdRatio.toFixed(2))
        : '---',
      color: summary ? getKdColor(kdRatio) : color.textSecondary,
    },
    {
      label: 'Kills',
      value: summary ? totalKills.toLocaleString() : '---',
      color: color.killGreen,
    },
    {
      label: 'Losses',
      value: summary ? totalDeaths.toLocaleString() : '---',
      color: color.lossRed,
    },
    {
      label: 'ISK Destroyed',
      value: iskDestroyedRaw > 0 ? formatIsk(iskDestroyedRaw) : (summary ? summary.isk_destroyed : '---'),
      color: color.killGreen,
    },
    {
      label: 'ISK Lost',
      value: iskLostRaw > 0 ? formatIsk(iskLostRaw) : '---',
      color: color.lossRed,
    },
  ];

  return (
    <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto' }}>
      {tiles.map((tile) => (
        <div
          key={tile.label}
          style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '6px',
            padding: '0.5rem 0.75rem',
            minWidth: '110px',
            flex: '1 1 0',
          }}
        >
          <div
            style={{
              fontSize: fontSize.tiny,
              color: color.textSecondary,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '0.25rem',
            }}
          >
            {tile.label}
          </div>
          <div
            style={{
              fontSize: fontSize.base,
              fontFamily: 'monospace',
              fontWeight: 700,
              color: tile.color,
            }}
          >
            {tile.value}
          </div>
        </div>
      ))}
    </div>
  );
}
