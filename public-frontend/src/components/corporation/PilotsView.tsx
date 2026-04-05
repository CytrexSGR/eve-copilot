/**
 * Pilot Intelligence - Comprehensive Pilot Analysis
 *
 * Provides detailed member analysis: morale, engagement, combat style, risk profile
 * Works at 3 levels: Corporation, Alliance, or PowerBloc (coalition)
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../services/corporationApi';
import { AWOXRiskPanel, CorpHealthDashboard } from '../shared/PilotRiskPanels';
import type { PilotIntel, PilotDetail, ActivePilotsTimelinePoint, MemberCountPoint } from '../../types/corporation';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface PilotsViewProps {
  corpId?: number;
  allianceId?: number;
  leaderId?: number;
  days: number;
}

export function PilotsView({ corpId, allianceId, leaderId, days }: PilotsViewProps) {
  const [data, setData] = useState<PilotIntel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setData(null);

    let fetchPromise: Promise<any>;
    if (corpId) {
      fetchPromise = corpApi.getPilotIntel(corpId, days);
    } else if (allianceId) {
      fetchPromise = fetch(`${API_BASE}/api/intelligence/fast/${allianceId}/pilot-intel?days=${days}`)
        .then(r => { if (!r.ok) throw new Error('Failed'); return r.json(); });
    } else if (leaderId) {
      fetchPromise = fetch(`${API_BASE}/api/powerbloc/${leaderId}/pilot-intel?days=${days}`)
        .then(r => { if (!r.ok) throw new Error('Failed'); return r.json(); });
    } else {
      setLoading(false);
      return;
    }

    fetchPromise
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, allianceId, leaderId, days]);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e' }}>Loading...</div>;
  if (!data) return <div style={{ padding: '2rem', textAlign: 'center', color: '#f85149' }}>Failed to load pilot intel</div>;

  const { fleet_overview, pilots, timeline, active_pilots_timeline } = data;

  // Categorize pilots
  const elitePilots = pilots
    .filter(p => p.morale_score >= 60 && p.efficiency >= 50)
    .sort((a, b) => b.morale_score - a.morale_score)
    .slice(0, 20);

  const strugglingPilots = pilots
    .filter(p => p.deaths > p.kills || p.morale_score < 40 || p.expensive_losses >= 2)
    .sort((a, b) => {
      const aRisk = (a.deaths - a.kills) + a.expensive_losses * 5 + (100 - a.morale_score);
      const bRisk = (b.deaths - b.kills) + b.expensive_losses * 5 + (100 - b.morale_score);
      return bRisk - aRisk;
    })
    .slice(0, 15);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
      {/* Row 1: Fleet Overview (Full Width) */}
      <div style={{ gridColumn: '1 / -1' }}>
        <FleetOverviewPanel overview={fleet_overview} activePilotsTimeline={active_pilots_timeline} memberCountHistory={data?.member_count_history} />
      </div>

      {/* Row 2: Elite | Struggling | Activity Trends */}
      <ElitePilotsPanel pilots={elitePilots} />
      <StrugglingPilotsPanel pilots={strugglingPilots} />
      <ActivityTrendsPanel pilots={pilots} timeline={timeline} />

      {/* Row 3: Combat Styles (spans 2) | Engagement Profile */}
      <div style={{ gridColumn: 'span 2' }}>
        <CombatStylesPanel pilots={pilots.slice(0, 25)} />
      </div>
      <EngagementProfilePanel pilots={pilots.slice(0, 30)} />

      {/* Row 4: Killmail Intelligence — AWOX Risk + Corp Health (Full Width) */}
      {corpId && (
        <>
          <div style={{ gridColumn: '1 / -1' }}>
            <CorpHealthDashboard corpId={corpId} days={days} />
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <AWOXRiskPanel corpId={corpId} days={days} />
          </div>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Panel 1: Fleet Overview
// ============================================================================
function FleetOverviewPanel({ overview, activePilotsTimeline, memberCountHistory }: { overview: PilotIntel['fleet_overview']; activePilotsTimeline?: ActivePilotsTimelinePoint[]; memberCountHistory?: MemberCountPoint[] }) {
  const getMoraleColor = (score: number) => {
    if (score >= 70) return '#3fb950';
    if (score >= 50) return '#ffcc00';
    return '#f85149';
  };

  // Morale diagnostic (Recommendation #6)
  type DiagnosticType = 'success' | 'info' | 'warning' | 'critical';
  const getMoraleDiagnostic = (): { type: DiagnosticType; message: string } => {
    if (overview.avg_morale >= 70) {
      return { type: 'success', message: '✅ Fleet morale is excellent! Pilots are engaged and performing well.' };
    }
    if (overview.avg_morale >= 50) {
      return { type: 'info', message: '📊 Fleet morale is solid. Monitor trend for early warning of issues.' };
    }
    if (overview.avg_morale >= 30) {
      return { type: 'warning', message: '⚠️ Low morale detected. Check: Pilot activity consistency, combat efficiency, recent activity trend. Consider: improved pings, better content, burnout assessment.' };
    }
    return { type: 'critical', message: '🔴 Critical morale issue! Investigate: Low engagement, high death rates, declining activity. Action: Review doctrine, improve training, check pilot burnout.' };
  };

  const diagnostic = getMoraleDiagnostic();
  const diagnosticColors: Record<DiagnosticType, string> = {
    success: '#238636',
    info: '#1f6feb',
    warning: '#9e6a03',
    critical: '#da3633'
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #58a6ff', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', fontWeight: 600, letterSpacing: '0.5px' }}>FLEET</span>
        <InlineStat label="Pilots" value={overview.total_pilots} />
        <InlineStat label="7d Active" value={overview.active_7d} />
        <InlineStat label="Elite" value={overview.elite_count} color="#3fb950" />
        <InlineStat label="Avg Eng." value={overview.avg_activity.toFixed(1)} />
        <InlineStat label="Daily Active" value={(overview.avg_daily_active ?? 0).toFixed(1)} color="#58a6ff" />
        <InlineStat label="Participation" value={`${overview.avg_participation.toFixed(1)}%`} />
        <span title="Morale Formula: Activity Consistency (30%) + Efficiency (40%) + Trend Factor (30%). ≥70 Elite, 50-69 Solid, 30-49 Struggling, <30 Problem" style={{ cursor: 'help' }}>
          <InlineStat label="Morale" value={overview.avg_morale.toFixed(1)} color={getMoraleColor(overview.avg_morale)} />
        </span>
        {overview.member_count_change != null && (
          <InlineStat
            label="Members"
            value={`${overview.member_count_change >= 0 ? '+' : ''}${overview.member_count_change} (${(overview.member_count_change_pct ?? 0) >= 0 ? '+' : ''}${(overview.member_count_change_pct ?? 0).toFixed(1)}%)`}
            color={overview.member_count_change > 0 ? '#3fb950' : overview.member_count_change < 0 ? '#f85149' : '#8b949e'}
          />
        )}
      </div>

      {/* Morale Diagnostic (Recommendation #6) */}
      <div style={{
        marginTop: '0.5rem',
        padding: '0.4rem',
        background: `rgba(${diagnostic.type === 'success' ? '35,134,54' : diagnostic.type === 'info' ? '31,111,235' : diagnostic.type === 'warning' ? '158,106,3' : '218,54,51'},0.15)`,
        borderLeft: `2px solid ${diagnosticColors[diagnostic.type]}`,
        borderRadius: '4px',
        fontSize: '0.65rem',
        color: '#c9d1d9'
      }}>
        {diagnostic.message}
      </div>

      {/* Active Pilots Timeline Chart */}
      {activePilotsTimeline && activePilotsTimeline.length > 1 && (
        <ActivePilotsChart timeline={activePilotsTimeline} />
      )}

      {/* Member Count History Chart */}
      {memberCountHistory && memberCountHistory.length > 1 && (
        <MemberCountChart history={memberCountHistory} />
      )}
    </div>
  );
}

function ActivePilotsChart({ timeline }: { timeline: ActivePilotsTimelinePoint[] }) {
  const hasCumulative = timeline.some(d => d.cumulative != null);
  const values = timeline.map(d => d.active_pilots);
  const cumValues = hasCumulative ? timeline.map(d => d.cumulative ?? 0) : [];
  const maxActive = Math.max(...values, 1);
  const maxCum = hasCumulative ? Math.max(...cumValues, 1) : 0;

  // Left Y-axis: active pilots
  const yAxisMax = Math.max(Math.ceil(maxActive / 10) * 10, 10);
  const yStep = Math.max(Math.ceil(yAxisMax / 4), 1);
  const yLabels: number[] = [];
  for (let i = 0; i <= yAxisMax; i += yStep) yLabels.push(i);

  // Right Y-axis: cumulative
  const yAxisMaxR = hasCumulative ? Math.max(Math.ceil(maxCum / 10) * 10, 10) : yAxisMax;

  const chartWidth = 900;
  const chartHeight = 100;
  const pad = { top: 5, right: hasCumulative ? 35 : 10, bottom: 20, left: 35 };
  const dw = chartWidth - pad.left - pad.right;
  const dh = chartHeight - pad.top - pad.bottom;

  const points = values.map((v, i) => ({
    x: pad.left + (i / Math.max(values.length - 1, 1)) * dw,
    y: pad.top + dh - (v / yAxisMax) * dh
  }));
  const cumPoints = hasCumulative ? cumValues.map((v, i) => ({
    x: pad.left + (i / Math.max(cumValues.length - 1, 1)) * dw,
    y: pad.top + dh - (v / yAxisMaxR) * dh
  })) : [];

  const lineD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaD = lineD + ` L ${points[points.length - 1].x.toFixed(1)},${(pad.top + dh).toFixed(1)} L ${points[0].x.toFixed(1)},${(pad.top + dh).toFixed(1)} Z`;
  const cumLineD = hasCumulative ? cumPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') : '';

  const maxXLabels = 10;
  const step = Math.ceil(timeline.length / maxXLabels);
  const xIndices = timeline.map((_, i) => i).filter((_, idx) => idx % step === 0);
  if (xIndices[xIndices.length - 1] !== timeline.length - 1) xIndices.push(timeline.length - 1);

  // Sample "+N new" labels to avoid overlap
  const newStep = Math.max(1, Math.ceil(timeline.length / 15));

  return (
    <div style={{ marginTop: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
        <div style={{ fontSize: '0.6rem', textTransform: 'uppercase', color: '#8b949e' }}>
          Active Pilots Trend ({timeline.length} days)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.55rem', color: '#8b949e' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
            <span style={{ width: '10px', height: '2px', background: '#58a6ff', display: 'inline-block' }} /> Daily Active
          </span>
          {hasCumulative && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
              <span style={{ width: '10px', height: '2px', background: '#3fb950', display: 'inline-block', borderTop: '1px dashed #3fb950' }} /> Cumulative Unique
            </span>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <svg width={chartWidth} height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={{ display: 'block', width: '100%', height: 'auto' }}>
          {/* Y-axis grid + labels (left) */}
          {yLabels.map((value, i) => {
            const y = pad.top + dh - (value / yAxisMax) * dh;
            return (
              <g key={i}>
                <line x1={pad.left} y1={y} x2={chartWidth - pad.right} y2={y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                <text x={pad.left - 4} y={y + 3} textAnchor="end" fontSize="8" fill="#6e7681" fontFamily="monospace">{value}</text>
              </g>
            );
          })}
          {/* Right Y-axis labels (cumulative) */}
          {hasCumulative && [0, Math.round(yAxisMaxR / 2), yAxisMaxR].map((value, i) => {
            const y = pad.top + dh - (value / yAxisMaxR) * dh;
            return (
              <text key={`r${i}`} x={chartWidth - pad.right + 4} y={y + 3} textAnchor="start" fontSize="8" fill="#3fb950" fontFamily="monospace">{value}</text>
            );
          })}
          {/* X-axis labels */}
          {xIndices.map(i => {
            const d = new Date(timeline[i]?.day || '');
            return (
              <text key={i} x={points[i]?.x || 0} y={chartHeight - 3} textAnchor="middle" fontSize="8" fill="#6e7681" fontFamily="monospace">
                {`${d.getMonth() + 1}/${d.getDate()}`}
              </text>
            );
          })}
          {/* Area fill (daily active) */}
          <path d={areaD} fill="rgba(88,166,255,0.08)" />
          {/* Line (daily active) */}
          <path d={lineD} fill="none" stroke="#58a6ff" strokeWidth="2" />
          {/* Cumulative line (dashed green) */}
          {hasCumulative && cumLineD && (
            <path d={cumLineD} fill="none" stroke="#3fb950" strokeWidth="1.5" strokeDasharray="4 2" />
          )}
          {/* Dots + "+N new" labels (sampled) */}
          {points.map((p, i) => {
            const showLabel = hasCumulative && i % newStep === 0 && (timeline[i]?.new_pilots ?? 0) > 0;
            return (
              <g key={i}>
                {i % Math.max(1, Math.floor(points.length / 30)) === 0 && (
                  <circle cx={p.x} cy={p.y} r="2" fill="#58a6ff" />
                )}
                {showLabel && (
                  <text x={p.x} y={p.y - 5} textAnchor="middle" fontSize="7" fill="#3fb950" fontFamily="monospace">
                    +{timeline[i].new_pilots}
                  </text>
                )}
              </g>
            );
          })}
          {/* Final cumulative total label */}
          {hasCumulative && cumPoints.length > 0 && (
            <text x={cumPoints[cumPoints.length - 1].x + 3} y={cumPoints[cumPoints.length - 1].y + 3} textAnchor="start" fontSize="8" fontWeight="bold" fill="#3fb950" fontFamily="monospace">
              ={cumValues[cumValues.length - 1]}
            </text>
          )}
        </svg>
      </div>
    </div>
  );
}

function MemberCountChart({ history }: { history: MemberCountPoint[] }) {
  const values = history.map(d => d.member_count);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values, minVal + 1);

  // Y-axis range with padding
  const range = maxVal - minVal;
  const yMin = Math.max(0, Math.floor(minVal - range * 0.1));
  const yMax = Math.ceil(maxVal + range * 0.1);
  const yRange = yMax - yMin || 1;

  const yStep = Math.max(Math.ceil(yRange / 4), 1);
  const yLabels: number[] = [];
  for (let i = yMin; i <= yMax; i += yStep) yLabels.push(i);
  if (yLabels[yLabels.length - 1] < yMax) yLabels.push(yMax);

  const chartWidth = 900;
  const chartHeight = 100;
  const pad = { top: 5, right: 10, bottom: 20, left: 40 };
  const dw = chartWidth - pad.left - pad.right;
  const dh = chartHeight - pad.top - pad.bottom;

  const points = values.map((v, i) => ({
    x: pad.left + (i / Math.max(values.length - 1, 1)) * dw,
    y: pad.top + dh - ((v - yMin) / yRange) * dh
  }));

  const lineD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaD = lineD + ` L ${points[points.length - 1].x.toFixed(1)},${(pad.top + dh).toFixed(1)} L ${points[0].x.toFixed(1)},${(pad.top + dh).toFixed(1)} Z`;

  const maxXLabels = 10;
  const step = Math.ceil(history.length / maxXLabels);
  const xIndices = history.map((_, i) => i).filter((_, idx) => idx % step === 0);
  if (xIndices[xIndices.length - 1] !== history.length - 1) xIndices.push(history.length - 1);

  // Delta label
  const delta = values[values.length - 1] - values[0];
  const deltaColor = delta > 0 ? '#3fb950' : delta < 0 ? '#f85149' : '#8b949e';

  return (
    <div style={{ marginTop: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
        <div style={{ fontSize: '0.6rem', textTransform: 'uppercase', color: '#8b949e' }}>
          Corp Membership Trend ({history.length} days)
        </div>
        <div style={{ fontSize: '0.55rem', color: deltaColor, fontWeight: 'bold' }}>
          {delta > 0 ? '+' : ''}{delta} members
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <svg width={chartWidth} height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={{ display: 'block', width: '100%', height: 'auto' }}>
          {/* Y-axis grid + labels */}
          {yLabels.map((value, i) => {
            const y = pad.top + dh - ((value - yMin) / yRange) * dh;
            return (
              <g key={i}>
                <line x1={pad.left} y1={y} x2={chartWidth - pad.right} y2={y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                <text x={pad.left - 4} y={y + 3} textAnchor="end" fontSize="8" fill="#6e7681" fontFamily="monospace">{value}</text>
              </g>
            );
          })}
          {/* X-axis labels */}
          {xIndices.map(i => {
            const d = new Date(history[i]?.date || '');
            return (
              <text key={i} x={points[i]?.x || 0} y={chartHeight - 3} textAnchor="middle" fontSize="8" fill="#6e7681" fontFamily="monospace">
                {`${d.getMonth() + 1}/${d.getDate()}`}
              </text>
            );
          })}
          {/* Area fill */}
          <path d={areaD} fill="rgba(255,136,0,0.08)" />
          {/* Line */}
          <path d={lineD} fill="none" stroke="#ff8800" strokeWidth="2" />
          {/* Dots */}
          {points.map((p, i) => (
            i % Math.max(1, Math.floor(points.length / 30)) === 0 ? (
              <circle key={i} cx={p.x} cy={p.y} r="2" fill="#ff8800" />
            ) : null
          ))}
          {/* End value label */}
          <text x={points[points.length - 1].x + 4} y={points[points.length - 1].y + 3} textAnchor="start" fontSize="8" fontWeight="bold" fill="#ff8800" fontFamily="monospace">
            {values[values.length - 1]}
          </text>
        </svg>
      </div>
    </div>
  );
}

function InlineStat({ label, value, color = '#c9d1d9' }: { label: string; value: string | number; color?: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '0.2rem' }}>
      <span style={{ fontSize: '0.6rem', color: '#8b949e' }}>{label}</span>
      <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color }}>{value}</span>
    </span>
  );
}

// ============================================================================
// Panel 2: Elite Pilots
// ============================================================================
function ElitePilotsPanel({ pilots }: { pilots: PilotDetail[] }) {
  const getMoraleColor = (score: number) => {
    if (score >= 70) return '#3fb950';
    if (score >= 50) return '#ffcc00';
    return '#f85149';
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #3fb950', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.4rem' }}>• ELITE PILOTS ({pilots.length})</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {pilots.map((p) => (
          <div key={p.character_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem', borderLeft: `2px solid ${getMoraleColor(p.morale_score)}` }}>
            {/* Line 1: Portrait + Name + Morale Badge */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.15rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <img src={`https://images.evetech.net/characters/${p.character_id}/portrait?size=32`} alt={p.character_name || 'Unknown'} style={{ width: '20px', height: '20px', borderRadius: '3px' }} />
                <span style={{ color: '#c9d1d9', fontWeight: 'bold' }}>{p.character_name || 'Unknown'}</span>
              </div>
              <span style={{ background: getMoraleColor(p.morale_score), color: '#000', padding: '0.1rem 0.3rem', borderRadius: '3px', fontSize: '0.65rem', fontWeight: 'bold' }}>
                {p.morale_score.toFixed(0)}
              </span>
            </div>
            {/* Line 2: K/D + Efficiency + ISK */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#8b949e', marginBottom: '0.15rem' }}>
              <span>{p.kills}K/{p.deaths}D ({p.kd_ratio.toFixed(1)})</span>
              <span style={{ color: p.efficiency >= 70 ? '#3fb950' : p.efficiency >= 50 ? '#ffcc00' : '#f85149' }}>
                {p.efficiency.toFixed(1)}% eff
              </span>
              <span>{(p.isk_killed / 1e9).toFixed(1)}B killed</span>
            </div>
            {/* Line 3: Combat Style Indicators */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#6e7681' }}>
              <span>{p.solo_kills > 0 ? `⚔️ ${p.solo_kills} solo` : ''}</span>
              <span>{p.fleet_participation_pct.toFixed(0)}% fleet</span>
              <span>{p.primary_ship_class}</span>
              {p.capital_usage && <span style={{ color: '#ff0000' }}>♦ CAP</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 3: Struggling Pilots
// ============================================================================
function StrugglingPilotsPanel({ pilots }: { pilots: PilotDetail[] }) {
  const getRiskFlags = (p: PilotDetail) => {
    const flags: string[] = [];
    if (p.deaths > p.kills * 2) flags.push('🔴 High Deaths');
    if (p.expensive_losses >= 2) flags.push('💰 Expensive Losses');
    if (p.morale_score < 30) flags.push('📉 Low Morale');
    if (p.activity_7d === 0) flags.push('💤 Inactive');
    return flags.join(' ');
  };

  const daysSinceActive = (lastActive: string | null) => {
    if (!lastActive) return 'Never';
    const diff = Date.now() - new Date(lastActive).getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days === 0) return 'Today';
    if (days === 1) return '1 day';
    return `${days} days`;
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #f85149', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.4rem' }}>• STRUGGLING PILOTS ({pilots.length})</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {pilots.map((p) => (
          <div key={p.character_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem', borderLeft: '2px solid #f85149' }}>
            {/* Line 1: Portrait + Name + Risk Flags */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.15rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <img src={`https://images.evetech.net/characters/${p.character_id}/portrait?size=32`} alt={p.character_name || 'Unknown'} style={{ width: '20px', height: '20px', borderRadius: '3px' }} />
                <span style={{ color: '#c9d1d9' }}>{p.character_name || 'Unknown'}</span>
              </div>
              <span style={{ fontSize: '0.6rem', color: '#f85149' }}>{getRiskFlags(p)}</span>
            </div>
            {/* Line 2: K/D + Losses + Last Active */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#8b949e', marginBottom: '0.15rem' }}>
              <span>{p.kills}K/{p.deaths}D</span>
              <span style={{ color: '#f85149' }}>{p.expensive_losses > 0 ? `${p.expensive_losses} >1B` : ''}</span>
              <span>{daysSinceActive(p.last_active)} ago</span>
            </div>
            {/* Line 3: Death Analysis */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#6e7681' }}>
              <span>{p.solo_deaths > 0 ? `${p.solo_deaths} solo deaths` : ''}</span>
              <span>{(p.avg_loss_value / 1e6).toFixed(0)}M avg loss</span>
              <span>{p.efficiency.toFixed(1)}% eff</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 4: Activity Trends
// ============================================================================
function ActivityTrendsPanel({ pilots, timeline }: { pilots: PilotDetail[]; timeline: Record<number, { day: string; kills: number }[]> }) {
  const generateSparkline = (charId: number) => {
    const data = timeline[charId] || [];
    if (data.length === 0) return '▁▁▁▁▁▁▁▁';

    // Get last 15 days
    const last15 = data.slice(-15);
    const max = Math.max(...last15.map(d => d.kills), 1);

    const chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
    return last15.map(d => {
      const normalized = d.kills / max;
      const index = Math.min(Math.floor(normalized * chars.length), chars.length - 1);
      return chars[index];
    }).join('');
  };

  const getTrendIndicator = (p: PilotDetail) => {
    if (p.activity_prev_7d === 0) return '⬆️';
    const change = ((p.activity_7d - p.activity_prev_7d) / p.activity_prev_7d) * 100;
    if (change > 15) return '⬆️';
    if (change < -15) return '⬇️';
    return '→';
  };

  const getTrendColor = (p: PilotDetail) => {
    if (p.activity_prev_7d === 0) return '#3fb950';
    const change = ((p.activity_7d - p.activity_prev_7d) / p.activity_prev_7d) * 100;
    if (change > 15) return '#3fb950';
    if (change < -15) return '#f85149';
    return '#58a6ff';
  };

  const activePilots = pilots.filter(p => p.activity_7d > 0 || p.activity_prev_7d > 0).slice(0, 30);

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #a855f7', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.4rem' }}>• ACTIVITY TRENDS ({activePilots.length})</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {activePilots.map((p) => (
          <div key={p.character_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem', borderLeft: `2px solid ${getTrendColor(p)}` }}>
            {/* Line 1: Portrait + Name + Trend */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.15rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <img src={`https://images.evetech.net/characters/${p.character_id}/portrait?size=32`} alt={p.character_name || 'Unknown'} style={{ width: '20px', height: '20px', borderRadius: '3px' }} />
                <span style={{ color: '#c9d1d9' }}>{p.character_name || 'Unknown'}</span>
              </div>
              <span style={{ fontSize: '0.9rem' }}>{getTrendIndicator(p)}</span>
            </div>
            {/* Line 2: Sparkline + Activity Comparison */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.65rem', marginBottom: '0.1rem' }}>
              <span style={{ fontFamily: 'monospace', fontSize: '1rem', letterSpacing: '0.1rem', color: getTrendColor(p) }}>
                {generateSparkline(p.character_id)}
              </span>
              <span style={{ color: '#8b949e' }}>
                7d: {p.activity_7d} → {p.activity_prev_7d}
              </span>
            </div>
            {/* Line 3: Stats */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#6e7681' }}>
              <span>{p.active_days}d active</span>
              <span>{(p.kills / p.active_days).toFixed(1)} kills/day</span>
              <span>{p.morale_score.toFixed(0)} morale</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 5: Combat Styles
// ============================================================================
function CombatStylesPanel({ pilots }: { pilots: PilotDetail[] }) {
  const getShipClassColor = (shipClass: string) => {
    const lower = shipClass.toLowerCase();
    if (lower.includes('frigate')) return '#3fb950';
    if (lower.includes('destroyer')) return '#58a6ff';
    if (lower.includes('cruiser')) return '#a855f7';
    if (lower.includes('battlecruiser')) return '#ff8800';
    if (lower.includes('battleship')) return '#ff4444';
    if (lower.includes('carrier') || lower.includes('dread') || lower.includes('titan') || lower.includes('super')) return '#ff0000';
    return '#8b949e';
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #ff8800', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.4rem' }}>• COMBAT STYLES ({pilots.length})</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {pilots.map((p) => {
          const totalKills = p.kills;
          const soloWidth = totalKills > 0 ? (p.solo_kills / totalKills) * 100 : 0;
          const fleetWidth = totalKills > 0 ? (p.fleet_kills / totalKills) * 100 : 0;

          return (
            <div key={p.character_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem', borderLeft: `2px solid ${getShipClassColor(p.primary_ship_class)}` }}>
              {/* Line 1: Portrait + Name + Ship Class */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.15rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <img src={`https://images.evetech.net/characters/${p.character_id}/portrait?size=32`} alt={p.character_name || 'Unknown'} style={{ width: '20px', height: '20px', borderRadius: '3px' }} />
                  <span style={{ color: '#c9d1d9' }}>{p.character_name || 'Unknown'}</span>
                </div>
                <span style={{ color: getShipClassColor(p.primary_ship_class), fontSize: '0.65rem', fontWeight: 'bold' }}>
                  {p.primary_ship_class}
                </span>
              </div>
              {/* Line 2: Solo vs Fleet Bar */}
              <div style={{ display: 'flex', gap: '0.2rem', marginBottom: '0.15rem' }}>
                <div style={{ flex: soloWidth, background: '#f85149', height: '6px', borderRadius: '2px' }} />
                <div style={{ flex: fleetWidth, background: '#3fb950', height: '6px', borderRadius: '2px' }} />
                <div style={{ flex: Math.max(100 - soloWidth - fleetWidth, 0), background: 'rgba(139, 148, 158, 0.3)', height: '6px', borderRadius: '2px' }} />
              </div>
              {/* Line 3: Stats */}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: '#6e7681' }}>
                <span style={{ color: '#f85149' }}>{p.solo_kills} solo</span>
                <span style={{ color: '#3fb950' }}>{p.fleet_kills} fleet</span>
                <span>{p.ship_diversity} ships</span>
                <span>⌀{p.avg_fleet_size.toFixed(1)} size</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 6: Engagement Profile
// ============================================================================
function EngagementProfilePanel({ pilots }: { pilots: PilotDetail[] }) {
  const engagementColors = {
    solo: '#f85149',
    small: '#ff8800',
    medium: '#ffcc00',
    large: '#3fb950',
    fleet: '#58a6ff',
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', borderLeft: '2px solid #10b981', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.4rem' }}>• ENGAGEMENT PROFILE ({pilots.length})</div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '0.4rem', fontSize: '0.65rem', color: '#8b949e', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <div style={{ width: '12px', height: '6px', background: engagementColors.solo, borderRadius: '2px' }} />
          <span>Solo (≤3)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <div style={{ width: '12px', height: '6px', background: engagementColors.medium, borderRadius: '2px' }} />
          <span>Small/Medium (4-30)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <div style={{ width: '12px', height: '6px', background: engagementColors.fleet, borderRadius: '2px' }} />
          <span>Fleet (31+)</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {pilots.map((p) => {
          const totalKills = p.kills;
          const soloKills = p.solo_kills;
          const fleetKills = p.fleet_kills;
          const otherKills = totalKills - soloKills - fleetKills;

          const soloWidth = totalKills > 0 ? (soloKills / totalKills) * 100 : 0;
          const fleetWidth = totalKills > 0 ? (fleetKills / totalKills) * 100 : 0;
          const otherWidth = totalKills > 0 ? (otherKills / totalKills) * 100 : 0;

          return (
            <div key={p.character_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <img src={`https://images.evetech.net/characters/${p.character_id}/portrait?size=32`} alt={p.character_name || 'Unknown'} style={{ width: '18px', height: '18px', borderRadius: '2px' }} />
                  <span style={{ color: '#c9d1d9', fontSize: '0.7rem' }}>{p.character_name || 'Unknown'}</span>
                </div>
                <span style={{ fontSize: '0.65rem', color: '#8b949e' }}>
                  {totalKills} kills • {p.efficiency.toFixed(0)}% eff
                </span>
              </div>
              <div style={{ display: 'flex', gap: '1px', height: '8px', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ flex: soloWidth, background: engagementColors.solo }} title={`Solo: ${soloKills}`} />
                <div style={{ flex: otherWidth, background: engagementColors.medium }} title={`Small/Medium: ${otherKills}`} />
                <div style={{ flex: fleetWidth, background: engagementColors.fleet }} title={`Fleet: ${fleetKills}`} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
