/**
 * Hunting Score Board — Ranked system opportunities for hunting operations.
 * Shows systems ranked by hunting score with ADM, kill value, capital umbrella.
 */
import { useState, useEffect } from 'react';
import { intelligenceApi } from '../../services/api/intelligence';
import type { HuntingScores, HuntingSystem } from '../../types/intelligence';

interface HuntingScoreBoardProps {
  regionId?: number;
  days: number;
}

export function HuntingScoreBoard({ regionId, days }: HuntingScoreBoardProps) {
  const [data, setData] = useState<HuntingScores | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    intelligenceApi.getHuntingScores(regionId, days, 50)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [regionId, days]);

  if (loading) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>Loading hunting scores...</div>;
  if (!data || data.systems.length === 0) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>No hunting opportunities found</div>;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #3fb950' }}>
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem' }}>
        • HUNTING OPPORTUNITIES ({data.total_systems_analyzed} analyzed, {data.systems.length} shown)
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', maxHeight: '500px', overflowY: 'auto' }}>
        {data.systems.map((sys, i) => (
          <HuntingSystemRow key={sys.solar_system_id} system={sys} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}

function HuntingSystemRow({ system, rank }: { system: HuntingSystem; rank: number }) {
  const scoreColor = system.score >= 70 ? '#3fb950' : system.score >= 40 ? '#d29922' : '#8b949e';
  const admColor = system.adm_military >= 5 ? '#3fb950' : system.adm_military >= 3 ? '#d29922' : '#f85149';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.3rem',
      background: rank <= 3 ? 'rgba(63,185,80,0.08)' : 'rgba(0,0,0,0.2)',
      padding: '0.25rem 0.4rem', borderRadius: '3px',
      borderLeft: `2px solid ${scoreColor}`
    }}>
      {/* Rank */}
      <span style={{
        fontSize: '0.55rem', fontWeight: 700, color: rank <= 3 ? '#3fb950' : '#8b949e',
        width: '18px', textAlign: 'center', fontFamily: 'monospace'
      }}>
        #{rank}
      </span>
      {/* System name + region */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#c9d1d9' }}>{system.system_name}</div>
        <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>{system.region_name}</div>
      </div>
      {/* Score bar */}
      <div style={{ width: '50px' }}>
        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '3px', height: '6px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${system.score}%`, background: scoreColor, borderRadius: '3px' }} />
        </div>
        <div style={{ fontSize: '0.5rem', textAlign: 'center', color: scoreColor, fontFamily: 'monospace', fontWeight: 700 }}>
          {system.score.toFixed(0)}
        </div>
      </div>
      {/* ADM */}
      <div style={{ textAlign: 'center', width: '35px' }}>
        <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>ADM</div>
        <div style={{ fontSize: '0.6rem', color: admColor, fontFamily: 'monospace', fontWeight: 600 }}>
          {system.adm_military.toFixed(1)}
        </div>
      </div>
      {/* Deaths */}
      <div style={{ textAlign: 'center', width: '35px' }}>
        <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>Deaths</div>
        <div style={{ fontSize: '0.6rem', color: '#f85149', fontFamily: 'monospace' }}>{system.player_deaths}</div>
      </div>
      {/* Avg Value */}
      <div style={{ textAlign: 'center', width: '40px' }}>
        <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>Avg ISK</div>
        <div style={{ fontSize: '0.6rem', color: '#d29922', fontFamily: 'monospace' }}>
          {(system.avg_kill_value / 1e6).toFixed(0)}M
        </div>
      </div>
      {/* Capital umbrella badge */}
      {system.has_capital_umbrella && (
        <span style={{
          fontSize: '0.5rem', fontWeight: 700, background: '#ff0000', color: '#fff',
          padding: '1px 3px', borderRadius: '2px'
        }}>
          CAP
        </span>
      )}
    </div>
  );
}
