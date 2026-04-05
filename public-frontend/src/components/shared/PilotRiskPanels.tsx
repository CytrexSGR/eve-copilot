/**
 * Pilot Risk Intelligence Panels — AWOX Risk + Corp Health Dashboard
 *
 * Used in PilotsView for Corporation entities.
 */
import { useState, useEffect } from 'react';
import { intelligenceApi } from '../../services/api/intelligence';
import type { PilotRiskData, PilotRiskEntry, CorpHealth } from '../../types/intelligence';

// ============================================================================
// AWOX Risk Panel
// ============================================================================

interface AWOXRiskPanelProps {
  corpId: number;
  days: number;
}

export function AWOXRiskPanel({ corpId, days }: AWOXRiskPanelProps) {
  const [data, setData] = useState<PilotRiskData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    intelligenceApi.getPilotRisk(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>Loading pilot risk...</div>;
  if (!data) return null;

  const { summary, pilots } = data;
  const atRiskPilots = pilots.filter(p => p.awox_count > 0 || p.performance_category === 'LIABILITY');

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #f85149' }}>
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem' }}>
        • PILOT RISK ASSESSMENT ({summary.total_analyzed} pilots)
      </div>
      {/* Summary badges */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
        <CategoryBadge label="Normal" count={summary.normal} color="#3fb950" />
        <CategoryBadge label="Trainable" count={summary.trainable} color="#d29922" />
        <CategoryBadge label="Liability" count={summary.liability} color="#f85149" />
        {summary.at_risk_awox > 0 && <CategoryBadge label="AWOX Risk" count={summary.at_risk_awox} color="#ff0000" />}
      </div>
      {/* At-risk pilot list */}
      {atRiskPilots.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', maxHeight: '200px', overflowY: 'auto' }}>
          {atRiskPilots.slice(0, 20).map(pilot => (
            <PilotRiskRow key={pilot.character_id} pilot={pilot} />
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.2rem',
      background: `${color}15`, border: `1px solid ${color}40`,
      padding: '0.15rem 0.4rem', borderRadius: '4px'
    }}>
      <span style={{ fontSize: '0.55rem', color }}>{label}</span>
      <span style={{ fontSize: '0.65rem', fontWeight: 700, color, fontFamily: 'monospace' }}>{count}</span>
    </div>
  );
}

function PilotRiskRow({ pilot }: { pilot: PilotRiskEntry }) {
  const catColor = pilot.performance_category === 'LIABILITY' ? '#f85149'
    : pilot.performance_category === 'TRAINABLE' ? '#d29922' : '#3fb950';

  return (
    <a
      href={`https://zkillboard.com/character/${pilot.character_id}/`}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'flex', alignItems: 'center', gap: '0.3rem',
        background: pilot.awox_count > 0 ? 'rgba(255,0,0,0.1)' : 'rgba(0,0,0,0.2)',
        padding: '0.2rem 0.4rem', borderRadius: '3px',
        textDecoration: 'none', color: 'inherit',
        borderLeft: `2px solid ${pilot.awox_count > 0 ? '#ff0000' : catColor}`
      }}
    >
      <img
        src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
        alt=""
        style={{ width: '18px', height: '18px', borderRadius: '2px' }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.6rem', color: '#c9d1d9' }}>ID: {pilot.character_id}</div>
      </div>
      <span style={{
        fontSize: '0.5rem', fontWeight: 700, padding: '1px 4px', borderRadius: '2px',
        background: catColor, color: '#fff'
      }}>
        {pilot.performance_category}
      </span>
      <div style={{ fontSize: '0.55rem', fontFamily: 'monospace', color: '#8b949e' }}>
        {pilot.kills}K/{pilot.deaths}D
      </div>
      <div style={{ fontSize: '0.55rem', fontFamily: 'monospace', color: '#d29922' }}>
        {pilot.efficiency.toFixed(0)}%
      </div>
      {pilot.awox_count > 0 && (
        <span style={{ fontSize: '0.5rem', fontWeight: 700, background: '#ff0000', color: '#fff', padding: '1px 3px', borderRadius: '2px' }}>
          AWOX {pilot.awox_count}
        </span>
      )}
    </a>
  );
}

// ============================================================================
// Corp Health Dashboard
// ============================================================================

interface CorpHealthDashboardProps {
  corpId: number;
  days: number;
}

export function CorpHealthDashboard({ corpId, days }: CorpHealthDashboardProps) {
  const [data, setData] = useState<CorpHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    intelligenceApi.getCorpHealth(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) return <div style={{ padding: '1rem', textAlign: 'center', color: '#8b949e', fontSize: '0.65rem' }}>Loading corp health...</div>;
  if (!data) return null;

  const activityColor = data.activity_rate >= 30 ? '#3fb950' : data.activity_rate >= 15 ? '#d29922' : '#f85149';
  const effColor = data.isk_efficiency >= 60 ? '#3fb950' : data.isk_efficiency >= 40 ? '#d29922' : '#f85149';

  // Simple sparkline for member trend
  const trendValues = data.member_trend.map(t => t.count);
  const trendMin = Math.min(...trendValues, 0);
  const trendMax = Math.max(...trendValues, 1);
  const trendRange = trendMax - trendMin || 1;
  const sparkWidth = 120;
  const sparkHeight = 24;
  const sparkPoints = trendValues.map((v, i) => ({
    x: (i / Math.max(trendValues.length - 1, 1)) * sparkWidth,
    y: sparkHeight - ((v - trendMin) / trendRange) * sparkHeight
  }));
  const sparkPath = sparkPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #58a6ff' }}>
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem' }}>
        • CORP HEALTH DASHBOARD
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {/* Members */}
        <div>
          <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>Members</div>
          <div style={{ fontSize: '0.85rem', color: '#c9d1d9', fontFamily: 'monospace', fontWeight: 700 }}>{data.member_count}</div>
        </div>
        {/* Active */}
        <div>
          <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>Active</div>
          <div style={{ fontSize: '0.85rem', color: activityColor, fontFamily: 'monospace', fontWeight: 700 }}>{data.active_pilots}</div>
        </div>
        {/* Activity Rate */}
        <div>
          <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>Activity %</div>
          <div style={{ fontSize: '0.85rem', color: activityColor, fontFamily: 'monospace', fontWeight: 700 }}>{data.activity_rate}%</div>
        </div>
        {/* ISK Efficiency */}
        <div>
          <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>ISK Eff</div>
          <div style={{ fontSize: '0.85rem', color: effColor, fontFamily: 'monospace', fontWeight: 700 }}>{data.isk_efficiency}%</div>
        </div>
        {/* ISK Killed */}
        <div>
          <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>ISK Killed</div>
          <div style={{ fontSize: '0.7rem', color: '#3fb950', fontFamily: 'monospace' }}>{(data.isk_killed / 1e9).toFixed(1)}B</div>
        </div>
        {/* ISK Lost */}
        <div>
          <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>ISK Lost</div>
          <div style={{ fontSize: '0.7rem', color: '#f85149', fontFamily: 'monospace' }}>{(data.isk_lost / 1e9).toFixed(1)}B</div>
        </div>
        {/* Member Trend Sparkline */}
        {trendValues.length > 2 && (
          <div>
            <div style={{ fontSize: '0.5rem', color: '#8b949e' }}>Member Trend</div>
            <svg width={sparkWidth} height={sparkHeight} style={{ display: 'block' }}>
              <path d={sparkPath} fill="none" stroke="#58a6ff" strokeWidth="1.5" />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}
