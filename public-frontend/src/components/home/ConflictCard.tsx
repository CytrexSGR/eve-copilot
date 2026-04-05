import { memo, useMemo } from 'react';
import { COLORS } from '../../constants';

const DualLineSparkline = memo(function DualLineSparkline({
  kills,
  deaths,
  width = 50,
  height = 16
}: {
  kills: number[];
  deaths: number[];
  width?: number;
  height?: number;
}) {
  const gradientId = useMemo(() => `conflict-${Math.random().toString(36).substring(2, 11)}`, []);

  if (!kills?.length && !deaths?.length) return null;

  const safeKills = kills?.filter(v => isFinite(v)) ?? [];
  const safeDeaths = deaths?.filter(v => isFinite(v)) ?? [];
  const allValues = [...safeKills, ...safeDeaths];
  const max = Math.max(...allValues) || 1;
  const dataLen = Math.max(safeKills.length, safeDeaths.length);

  const getPoints = (data: number[]) => {
    if (data.length < 2) return '';
    return data.map((v, i) => {
      const x = (i / (dataLen - 1)) * width;
      const y = height - (v / max) * (height - 4) - 2;
      return `${x},${y}`;
    }).join(' ');
  };

  const killsPoints = getPoints(safeKills);
  const deathsPoints = getPoints(safeDeaths);

  return (
    <svg width={width} height={height} style={{ display: 'block', flexShrink: 0 }}>
      <defs>
        <linearGradient id={`${gradientId}-k`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={COLORS.positive} stopOpacity="0.2" />
          <stop offset="100%" stopColor={COLORS.positive} stopOpacity="0" />
        </linearGradient>
      </defs>
      {killsPoints && (
        <>
          <polygon points={`0,${height} ${killsPoints} ${width},${height}`} fill={`url(#${gradientId}-k)`} />
          <polyline points={killsPoints} fill="none" stroke={COLORS.positive} strokeWidth="1" />
        </>
      )}
      {deathsPoints && (
        <polyline points={deathsPoints} fill="none" stroke={COLORS.negative} strokeWidth="1" opacity="0.7" />
      )}
    </svg>
  );
});

interface Conflict {
  alliance_1_id: number;
  alliance_1_name: string;
  alliance_1_kills: number;
  alliance_1_isk_destroyed?: number;
  alliance_1_efficiency: number;
  alliance_2_id: number;
  alliance_2_name: string;
  alliance_2_kills: number;
  alliance_2_isk_destroyed?: number;
  alliance_2_efficiency: number;
  kills_series_1?: number[];
  kills_series_2?: number[];
}

interface ConflictCardProps {
  conflict: Conflict;
}

export function ConflictCard({ conflict }: ConflictCardProps) {
  const totalIsk =
    (conflict.alliance_1_isk_destroyed || 0) + (conflict.alliance_2_isk_destroyed || 0);
  const totalKills = conflict.alliance_1_kills + conflict.alliance_2_kills;
  const isk1Pct = totalIsk > 0 ? ((conflict.alliance_1_isk_destroyed || 0) / totalIsk) * 100 : 50;
  const isA1Winning = conflict.alliance_1_efficiency > conflict.alliance_2_efficiency;

  return (
    <div style={{
      padding: '0.3rem 0.5rem',
      background: 'rgba(255, 136, 0, 0.05)',
      borderRadius: '4px',
      borderLeft: '2px solid #ff8800',
    }}>
      {/* Line 1: Logo Name Eff% [===bar===] Eff% Name Logo */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.3rem',
      }}>
        <img
          src={`https://images.evetech.net/alliances/${conflict.alliance_1_id}/logo?size=32`}
          alt="" width={18} height={18}
          style={{ borderRadius: '3px', flexShrink: 0 }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
        <span style={{
          fontSize: '0.7rem', fontWeight: 600,
          color: isA1Winning ? COLORS.positive : 'rgba(255,255,255,0.8)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          minWidth: 0,
        }}>
          {conflict.alliance_1_name}
        </span>
        <span style={{
          fontSize: '0.6rem', fontWeight: 600, fontFamily: 'monospace', flexShrink: 0,
          color: isA1Winning ? COLORS.positive : COLORS.negative,
        }}>
          {conflict.alliance_1_efficiency.toFixed(0)}%
        </span>

        {/* ISK balance bar */}
        <div style={{
          flex: 1, height: '3px', borderRadius: '2px', minWidth: '40px',
          background: 'rgba(255,255,255,0.08)', overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', width: `${isk1Pct}%`,
            background: isA1Winning
              ? `linear-gradient(90deg, ${COLORS.positive}, #00cc6a)`
              : `linear-gradient(90deg, ${COLORS.negative}, #cc3333)`,
          }} />
        </div>

        <span style={{
          fontSize: '0.6rem', fontWeight: 600, fontFamily: 'monospace', flexShrink: 0,
          color: !isA1Winning ? COLORS.positive : COLORS.negative,
        }}>
          {conflict.alliance_2_efficiency.toFixed(0)}%
        </span>
        <span style={{
          fontSize: '0.7rem', fontWeight: 600,
          color: !isA1Winning ? COLORS.positive : 'rgba(255,255,255,0.8)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          minWidth: 0, textAlign: 'right',
        }}>
          {conflict.alliance_2_name}
        </span>
        <img
          src={`https://images.evetech.net/alliances/${conflict.alliance_2_id}/logo?size=32`}
          alt="" width={18} height={18}
          style={{ borderRadius: '3px', flexShrink: 0 }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
      </div>

      {/* Line 2: kills + sparkline */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.5rem',
        marginTop: '0.2rem',
        fontSize: '0.55rem',
        color: 'rgba(255,255,255,0.35)',
      }}>
        <span style={{ fontFamily: 'monospace' }}>
          <span style={{ color: '#ff8800' }}>{totalKills}</span> kills
        </span>
        {(conflict.kills_series_1 || conflict.kills_series_2) && (
          <DualLineSparkline
            kills={conflict.kills_series_1 || []}
            deaths={conflict.kills_series_2 || []}
          />
        )}
      </div>
    </div>
  );
}
