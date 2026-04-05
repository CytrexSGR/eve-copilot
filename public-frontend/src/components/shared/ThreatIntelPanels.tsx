/**
 * Killmail Intelligence Panels — Threat Composition, Capital Radar, Logi Shield Score
 *
 * Used in shared DefensiveView for Corp/Alliance/PowerBloc entities.
 */

import { useState, useEffect } from 'react';
import { intelligenceApi } from '../../services/api/intelligence';
import type {
  ThreatComposition, ThreatEntity, DamageProfile,
  CapitalRadar, LogiScoreEntry,
} from '../../types/intelligence';

// Color constants (match DefensiveView theme)
const DAMAGE_COLORS: Record<string, string> = {
  em: '#58a6ff',
  thermal: '#f85149',
  kinetic: '#8b949e',
  explosive: '#d29922',
};

// ============================================================================
// Panel: Threat Composition
// ============================================================================

export function ThreatPanel({ entityType, entityId, days }: { entityType: string; entityId: number; days: number }) {
  const [data, setData] = useState<ThreatComposition | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    intelligenceApi.getThreats(entityType, entityId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [entityType, entityId, days]);

  if (loading) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>Loading threat composition...</div>;
  if (!data || data.threats.length === 0) return null;

  const maxKills = Math.max(...data.threats.map(t => t.kills_on_us), 1);

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #ff4444' }}>
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem' }}>
        • THREAT COMPOSITION ({data.total_threats} entities)
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', maxHeight: '300px', overflowY: 'auto' }}>
        {data.threats.slice(0, 15).map(threat => (
          <ThreatRow key={threat.attacker_alliance_id} threat={threat} maxKills={maxKills} />
        ))}
      </div>
    </div>
  );
}

function ThreatRow({ threat, maxKills }: { threat: ThreatEntity; maxKills: number }) {
  const pct = (threat.kills_on_us / maxKills) * 100;
  return (
    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', borderLeft: '2px solid #f85149' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <img
            src={`https://images.evetech.net/alliances/${threat.attacker_alliance_id}/logo?size=32`}
            alt=""
            style={{ width: '18px', height: '18px', borderRadius: '2px' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#c9d1d9' }}>{threat.alliance_name}</span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem', fontFamily: 'monospace' }}>
          <span style={{ color: '#f85149' }}>{threat.kills_on_us} kills</span>
          <span style={{ color: '#d29922' }}>{(threat.isk_destroyed / 1e9).toFixed(1)}B</span>
          <span style={{ color: '#8b949e' }}>{threat.ship_diversity} types</span>
        </div>
      </div>
      {/* Kill bar */}
      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '4px', marginBottom: '0.1rem' }}>
        <div style={{ background: '#f85149', height: '100%', width: `${pct}%`, borderRadius: '2px' }} />
      </div>
      {/* Damage profile */}
      {threat.damage_profile && <DamageBar profile={threat.damage_profile} />}
    </div>
  );
}

function DamageBar({ profile }: { profile: DamageProfile }) {
  const total = profile.em + profile.thermal + profile.kinetic + profile.explosive;
  if (total === 0) return null;
  const segments = [
    { type: 'em', value: profile.em, color: DAMAGE_COLORS.em },
    { type: 'thermal', value: profile.thermal, color: DAMAGE_COLORS.thermal },
    { type: 'kinetic', value: profile.kinetic, color: DAMAGE_COLORS.kinetic },
    { type: 'explosive', value: profile.explosive, color: DAMAGE_COLORS.explosive },
  ].filter(s => s.value > 0);

  return (
    <div style={{ display: 'flex', height: '4px', borderRadius: '2px', overflow: 'hidden' }}>
      {segments.map(s => (
        <div key={s.type} style={{ background: s.color, width: `${(s.value / total) * 100}%` }} title={`${s.type}: ${((s.value / total) * 100).toFixed(0)}%`} />
      ))}
    </div>
  );
}

// ============================================================================
// Panel: Capital Radar
// ============================================================================

export function CapitalRadarPanel({ entityType, entityId, days }: { entityType: string; entityId: number; days: number }) {
  const [data, setData] = useState<CapitalRadar | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    intelligenceApi.getCapitalRadar(entityType, entityId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [entityType, entityId, days]);

  if (loading) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>Loading capital radar...</div>;
  if (!data || data.capital_systems.length === 0) return null;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #ff8800' }}>
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem' }}>
        • CAPITAL RADAR ({data.total_capital_systems} systems)
      </div>
      {/* Escalation stats */}
      {data.escalation_stats.escalation_count && data.escalation_stats.escalation_count > 0 && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.3rem', fontSize: '0.6rem' }}>
          <div>
            <span style={{ color: '#8b949e' }}>Avg Escalation: </span>
            <span style={{ color: '#ff8800', fontFamily: 'monospace', fontWeight: 600 }}>
              {data.escalation_stats.avg_escalation_seconds ? `${Math.round(data.escalation_stats.avg_escalation_seconds / 60)}min` : 'N/A'}
            </span>
          </div>
          <div>
            <span style={{ color: '#8b949e' }}>Min: </span>
            <span style={{ color: '#f85149', fontFamily: 'monospace', fontWeight: 600 }}>
              {data.escalation_stats.min_escalation_seconds ? `${Math.round(data.escalation_stats.min_escalation_seconds / 60)}min` : 'N/A'}
            </span>
          </div>
          <div>
            <span style={{ color: '#8b949e' }}>Escalations: </span>
            <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{data.escalation_stats.escalation_count}</span>
          </div>
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', maxHeight: '250px', overflowY: 'auto' }}>
        {data.capital_systems.map((sys, i) => (
          <div key={`${sys.solar_system_id}-${sys.capital_alliance_id}-${i}`} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'rgba(0,0,0,0.2)', padding: '0.2rem 0.4rem', borderRadius: '3px',
            fontSize: '0.6rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', flex: 1 }}>
              <span style={{ fontWeight: 600, color: '#c9d1d9' }}>{sys.system_name}</span>
              <span style={{ color: '#8b949e', fontSize: '0.55rem' }}>{sys.alliance_name}</span>
            </div>
            <div style={{ display: 'flex', gap: '0.4rem', fontFamily: 'monospace' }}>
              <span style={{
                background: sys.capital_class === 'Supercarrier' || sys.capital_class === 'Titan' ? '#ff0000' : '#ff8800',
                color: '#fff', padding: '1px 4px', borderRadius: '2px', fontSize: '0.5rem', fontWeight: 700
              }}>
                {sys.capital_class}
              </span>
              <span style={{ color: '#d29922' }}>{sys.appearances}x</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Panel: Logi Shield Score
// ============================================================================

export function LogiScorePanel({ entityType, entityId, days }: { entityType: string; entityId: number; days: number }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    intelligenceApi.getLogiScores(entityType, entityId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [entityType, entityId, days]);

  if (loading) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>Loading logi scores...</div>;
  if (!data || !data.alliances || data.alliances.length === 0) return null;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #3fb950' }}>
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem' }}>
        • ENEMY LOGI SHIELD SCORES
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', maxHeight: '250px', overflowY: 'auto' }}>
        {data.alliances.map((entry: LogiScoreEntry) => {
          const scoreColor = entry.logi_score >= 70 ? '#f85149' : entry.logi_score >= 40 ? '#d29922' : '#3fb950';
          const label = entry.logi_score >= 70 ? 'STRONG' : entry.logi_score >= 40 ? 'MODERATE' : 'WEAK';
          return (
            <div key={entry.alliance_id} style={{
              display: 'flex', alignItems: 'center', gap: '0.3rem',
              background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '3px'
            }}>
              <img
                src={`https://images.evetech.net/alliances/${entry.alliance_id}/logo?size=32`}
                alt=""
                style={{ width: '16px', height: '16px', borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ flex: 1, fontSize: '0.65rem', color: '#c9d1d9', fontWeight: 600 }}>{entry.alliance_name}</span>
              {/* Score gauge */}
              <div style={{ width: '60px', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${entry.logi_score}%`, background: scoreColor, borderRadius: '3px' }} />
              </div>
              <span style={{
                fontSize: '0.5rem', fontWeight: 700, padding: '1px 4px', borderRadius: '2px',
                background: scoreColor, color: '#fff'
              }}>
                {label}
              </span>
              <span style={{ fontSize: '0.55rem', color: '#8b949e', fontFamily: 'monospace' }}>
                {entry.logi_pilots} logi
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
