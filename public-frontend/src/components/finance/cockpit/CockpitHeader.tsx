import { useState, useEffect } from 'react';
import { fontSize, color, spacing } from '../../../styles/theme';
import { formatIsk } from '../../../types/finance';
import { walletApi } from '../../../services/api/finance';
import { corpApi } from '../../../services/corporationApi';

interface CockpitHeaderProps {
  corpId: number;
  days: number;
}

interface CorpEsiInfo {
  name: string;
  ticker: string;
}

const nameCache: Record<number, CorpEsiInfo> = {};

export function CockpitHeader({ corpId, days }: CockpitHeaderProps) {
  const [balance, setBalance] = useState<number | null>(null);
  const [kills, setKills] = useState(0);
  const [deaths, setDeaths] = useState(0);
  const [efficiency, setEfficiency] = useState(0);
  const [corpInfo, setCorpInfo] = useState<CorpEsiInfo | null>(nameCache[corpId] || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (nameCache[corpId]) {
      setCorpInfo(nameCache[corpId]);
    } else {
      fetch(`https://esi.evetech.net/latest/corporations/${corpId}/`)
        .then(r => r.json())
        .then(data => {
          const info = { name: data.name || `Corp ${corpId}`, ticker: data.ticker || '???' };
          nameCache[corpId] = info;
          setCorpInfo(info);
        })
        .catch(() => {});
    }
  }, [corpId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      walletApi.getBalance(corpId),
      corpApi.getOffensiveStats(corpId, days),
    ]).then(([balanceResult, offensiveResult]) => {
      if (cancelled) return;

      if (balanceResult.status === 'fulfilled') {
        setBalance(balanceResult.value.balance);
      }

      if (offensiveResult.status === 'fulfilled') {
        const summary = offensiveResult.value.summary;
        const k = summary.total_kills ?? 0;
        const kdRatio = summary.kd_ratio ?? 0;
        const d = kdRatio > 0 ? Math.round(k / kdRatio) : 0;
        setKills(k);
        setDeaths(d);
        setEfficiency(summary.efficiency ?? 0);
      }

      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  const efficiencyColor =
    efficiency >= 70 ? color.killGreen :
    efficiency >= 50 ? color.warningYellow :
    color.lossRed;

  const kdDisplay =
    deaths > 0 ? (kills / deaths).toFixed(2) :
    kills > 0 ? '\u221E' :
    '0.00';

  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: spacing.lg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: color.textSecondary,
        fontSize: fontSize.base,
      }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.lg,
      display: 'flex',
      alignItems: 'center',
      gap: spacing.lg,
    }}>
      {/* Corp Logo */}
      <img
        src={`https://images.evetech.net/corporations/${corpId}/logo?size=64`}
        alt="Corp Logo"
        style={{ width: 48, height: 48, borderRadius: '4px' }}
      />

      {/* Corp Name */}
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: fontSize.tiny,
          color: color.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          Corporation
        </div>
        <div style={{
          fontSize: fontSize.lg,
          fontWeight: 700,
          color: color.textPrimary,
        }}>
          {corpInfo?.name || '...'}
          {corpInfo?.ticker && (
            <span style={{ fontSize: fontSize.xs, color: color.textSecondary, marginLeft: spacing.xs, fontWeight: 600 }}>
              [{corpInfo.ticker}]
            </span>
          )}
        </div>
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Wallet Balance */}
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontSize: fontSize.tiny,
          color: color.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          Wallet Balance
        </div>
        <div style={{
          fontSize: fontSize.lg,
          fontFamily: 'monospace',
          fontWeight: 700,
          color: color.killGreen,
        }}>
          {balance !== null ? formatIsk(balance) : '--'}
        </div>
      </div>

      {/* ISK Efficiency */}
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontSize: fontSize.tiny,
          color: color.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          ISK Efficiency
        </div>
        <div style={{
          fontSize: fontSize.lg,
          fontFamily: 'monospace',
          fontWeight: 700,
          color: efficiencyColor,
        }}>
          {isFinite(efficiency) ? efficiency.toFixed(1) : '0.0'}%
        </div>
      </div>

      {/* K/D Ratio */}
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontSize: fontSize.tiny,
          color: color.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          K/D Ratio
        </div>
        <div style={{
          fontSize: fontSize.lg,
          fontFamily: 'monospace',
          fontWeight: 700,
          color: color.textPrimary,
        }}>
          {kills}/{deaths}
          <span style={{
            fontSize: fontSize.xs,
            color: color.textSecondary,
            marginLeft: spacing.xs,
          }}>
            ({kdDisplay})
          </span>
        </div>
      </div>
    </div>
  );
}
