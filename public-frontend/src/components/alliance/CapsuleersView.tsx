/**
 * CapsuleersView - Alliance player statistics with skill estimates
 *
 * Layout:
 * ┌─────────────────────────────┬─────────────────────────────┐
 * │ 🏢 CORP RANKINGS            │ 👤 TOP CAPSULEERS           │
 * │ (scrollable list)           │ (scrollable list)           │
 * └─────────────────────────────┴─────────────────────────────┘
 * ┌───────────────────────────────────────────────────────────┐
 * │ 📋 PILOT DETAIL (large panel when selected)               │
 * │ Portrait | Stats Grid | Ships | Activity | Skills         │
 * └───────────────────────────────────────────────────────────┘
 */

import { useState, useEffect } from 'react';
import {
  allianceApi,
  type CapsuleersResponse,
  type CapsuleerCorpStats,
  type CapsuleerPilotStats,
  type CapsuleerDetailResponse,
  getSurvivalTrainer,
  type SurvivalTrainerResponse,
} from '../../services/allianceApi';
import { formatISKCompact } from '../../utils/format';
import { PilotsView } from '../corporation/PilotsView';

interface CapsuleersViewProps {
  allianceId: number;
  days: number;
}

const cardStyle = {
  background: 'rgba(0,0,0,0.3)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '6px',
  padding: '0.75rem',
};

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
  marginBottom: '0.75rem',
  paddingBottom: '0.5rem',
  borderBottom: '1px solid rgba(255,255,255,0.1)',
};

export function CapsuleersView({ allianceId, days }: CapsuleersViewProps) {
  const [data, setData] = useState<CapsuleersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCorp, setSelectedCorp] = useState<CapsuleerCorpStats | null>(null);
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null);
  const [selectedCharName, setSelectedCharName] = useState<string>('');
  const [pilotDetail, setPilotDetail] = useState<CapsuleerDetailResponse | null>(null);
  const [pilotLoading, setPilotLoading] = useState(false);
  const [survivalData, setSurvivalData] = useState<SurvivalTrainerResponse | null>(null);

  const selectPilot = (charId: number | null, charName?: string) => {
    if (charId === selectedCharId) {
      setSelectedCharId(null);
      setSelectedCharName('');
    } else {
      setSelectedCharId(charId);
      setSelectedCharName(charName || '');
    }
  };

  useEffect(() => {
    setLoading(true);
    allianceApi.getCapsuleers(allianceId, days)
      .then(setData)
      .catch(err => console.error('Capsuleer data error:', err))
      .finally(() => setLoading(false));
    // Fetch survival trainer in background
    getSurvivalTrainer(allianceId, days).then(setSurvivalData).catch(() => {});
  }, [allianceId, days]);

  useEffect(() => {
    if (!selectedCharId) {
      setPilotDetail(null);
      return;
    }
    setPilotLoading(true);
    allianceApi.getCapsuleerDetail(allianceId, selectedCharId, days)
      .then(setPilotDetail)
      .catch(err => console.error('Pilot detail error:', err))
      .finally(() => setPilotLoading(false));
  }, [allianceId, selectedCharId, days]);

  if (loading) {
    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
          {[1, 2].map(i => (
            <div key={i} className="skeleton" style={{ height: '300px', borderRadius: '6px' }} />
          ))}
        </div>
        <div className="skeleton" style={{ height: '250px', borderRadius: '6px' }} />
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div style={{
        background: 'rgba(248,81,73,0.2)',
        border: '1px solid #f85149',
        borderRadius: '8px',
        padding: '2rem',
        textAlign: 'center',
      }}>
        <h3 style={{ color: '#f85149', margin: 0 }}>Failed to load capsuleer data</h3>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: '0.5rem 0 0' }}>{data?.error || 'Unknown error'}</p>
      </div>
    );
  }

  const displayedPilots = selectedCorp
    ? data.top_pilots.filter(p => p.corp_id === selectedCorp.corp_id)
    : data.top_pilots;

  return (
    <div>
      {/* Alliance-wide Pilot Intelligence */}
      <div style={{ marginBottom: '0.75rem' }}>
        <PilotsView allianceId={allianceId} days={days} />
      </div>

      {/* Summary Stats */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <StatBadge label="ACTIVE PILOTS" value={data.summary.active_pilots.toLocaleString()} color="#3fb950" />
        <StatBadge label="KILLS" value={data.summary.total_kills.toLocaleString()} color="#3fb950" />
        <StatBadge label="DEATHS" value={data.summary.total_deaths.toLocaleString()} color="#f85149" />
        <StatBadge label="EFFICIENCY" value={`${data.summary.efficiency.toFixed(1)}%`} color="#ffcc00" />
        <StatBadge label="CORPS" value={data.corps.length.toString()} color="#58a6ff" />
        <StatBadge
          label="POD SURVIVAL"
          value={`${(data.summary.pod_survival_rate ?? 0).toFixed(1)}%`}
          color={
            (data.summary.pod_survival_rate ?? 0) >= 70 ? '#3fb950'
              : (data.summary.pod_survival_rate ?? 0) >= 40 ? '#ffcc00'
              : '#f85149'
          }
        />
        <StatBadge label="POD LOSSES" value={(data.summary.pod_deaths ?? 0).toLocaleString()} color="#f85149" />
      </div>

      {/* Top Row: Corps + Capsuleers */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
        {/* Corps */}
        <div style={cardStyle}>
          <div style={headerStyle}>
            <span style={{ fontSize: '0.8rem' }}>🏢</span>
            <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>CORP RANKINGS</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
              {data.corps.length} corps
            </span>
          </div>
          <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {data.corps.map((corp, idx) => (
              <CorpRow
                key={corp.corp_id}
                corp={corp}
                rank={idx + 1}
                isSelected={selectedCorp?.corp_id === corp.corp_id}
                onClick={() => setSelectedCorp(selectedCorp?.corp_id === corp.corp_id ? null : corp)}
              />
            ))}
          </div>
        </div>

        {/* Capsuleers */}
        <div style={cardStyle}>
          <div style={headerStyle}>
            <span style={{ fontSize: '0.8rem' }}>👤</span>
            <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>TOP CAPSULEERS</span>
            {selectedCorp && (
              <span style={{
                fontSize: '0.6rem',
                background: 'rgba(88,166,255,0.2)',
                border: '1px solid #58a6ff',
                borderRadius: '3px',
                padding: '1px 4px',
                color: '#58a6ff',
              }}>
                [{selectedCorp.ticker}]
              </span>
            )}
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
              {displayedPilots.length} pilots
            </span>
          </div>
          <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {displayedPilots.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'rgba(255,255,255,0.4)' }}>
                No pilots found
              </div>
            ) : (
              displayedPilots.map((pilot, idx) => (
                <PilotRow
                  key={pilot.character_id}
                  pilot={pilot}
                  rank={idx + 1}
                  isSelected={selectedCharId === pilot.character_id}
                  onClick={() => selectPilot(pilot.character_id, pilot.character_name)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Survival Trainer */}
      {survivalData && survivalData.pilots && survivalData.pilots.length > 0 && (
        <SurvivalTrainerPanel data={survivalData} selectedCharId={selectedCharId} onSelectPilot={selectPilot} />
      )}

      {/* Corp Pilot Intel — show when corp selected */}
      {selectedCorp ? (
        <div style={{ marginTop: '0.25rem' }}>
          <div style={{ ...cardStyle, padding: '0.5rem 0.75rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <img
              src={allianceApi.getCorpLogoUrl(selectedCorp.corp_id, 32)}
              alt=""
              style={{ width: 24, height: 24, borderRadius: 3 }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <span style={{ fontWeight: 600, fontSize: '0.8rem', color: '#fff' }}>
              {selectedCorp.corp_name}
            </span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              [{selectedCorp.ticker}] — Pilot Intelligence
            </span>
          </div>
          <PilotsView corpId={selectedCorp.corp_id} days={days} />
        </div>
      ) : (
        /* Bottom: Large Pilot Detail Panel — show when no corp selected */
        <div style={cardStyle}>
          <div style={headerStyle}>
            <span style={{ fontSize: '0.8rem' }}>📋</span>
            <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>PILOT INTELLIGENCE</span>
            {selectedCharName && (
              <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
                {selectedCharName}
              </span>
            )}
          </div>
          {pilotLoading ? (
            <div className="skeleton" style={{ height: '200px', borderRadius: '4px' }} />
          ) : selectedCharId && pilotDetail ? (
            <PilotDetailPanel pilot={pilotDetail} />
          ) : (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              color: 'rgba(255,255,255,0.4)',
            }}>
              <span style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>👤</span>
              <span style={{ fontSize: '0.75rem' }}>Select a corp to view pilot intel, or click a pilot for individual details</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SurvivalTrainerPanel({ data, selectedCharId, onSelectPilot }: {
  data: SurvivalTrainerResponse;
  selectedCharId: number | null;
  onSelectPilot: (charId: number | null, charName?: string) => void;
}) {
  const riskColors: Record<string, string> = {
    critical: '#ff0000',
    at_risk: '#ff6600',
    good: '#3fb950',
  };

  const riskLabels: Record<string, string> = {
    critical: 'CRITICAL',
    at_risk: 'AT RISK',
    good: 'GOOD',
  };

  return (
    <div style={{ ...cardStyle, marginBottom: '0.75rem' }}>
      <div style={headerStyle}>
        <span style={{ fontSize: '0.8rem' }}>🛡️</span>
        <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>SURVIVAL TRAINER</span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
          {data.summary.pilots_analyzed} analyzed
        </span>
        <span style={{
          fontSize: '0.55rem',
          fontWeight: 700,
          color: '#fff',
          background: data.summary.critical_pilots > 0 ? '#ff0000' : data.summary.at_risk_pilots > 0 ? '#ff6600' : '#3fb950',
          padding: '1px 5px',
          borderRadius: '3px',
        }}>
          {data.summary.critical_pilots} CRITICAL • {data.summary.at_risk_pilots} AT RISK
        </span>
      </div>

      {/* Summary Stats */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.5rem', fontSize: '0.65rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Alliance Survival: </span>
          <span style={{
            fontWeight: 700,
            fontFamily: 'monospace',
            color: data.summary.alliance_survival_rate >= 70 ? '#3fb950' : data.summary.alliance_survival_rate >= 40 ? '#ffcc00' : '#f85149',
          }}>
            {data.summary.alliance_survival_rate.toFixed(1)}%
          </span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Pod ISK Wasted: </span>
          <span style={{ fontWeight: 700, fontFamily: 'monospace', color: '#f85149' }}>
            {formatISKCompact(data.summary.total_pod_isk_wasted)}
          </span>
        </div>
      </div>

      {/* Pilot List */}
      <div style={{ maxHeight: '240px', overflowY: 'auto' }}>
        {data.pilots.map(pilot => {
          const isSelected = selectedCharId === pilot.character_id;
          return (
            <div
              key={pilot.character_id}
              onClick={() => onSelectPilot(pilot.character_id, pilot.character_name)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.35rem 0.4rem',
                marginBottom: '0.15rem',
                background: isSelected
                  ? 'rgba(168,85,247,0.15)'
                  : pilot.risk_level === 'critical' ? 'rgba(255,0,0,0.08)'
                  : pilot.risk_level === 'at_risk' ? 'rgba(255,102,0,0.06)'
                  : 'rgba(255,255,255,0.02)',
                border: isSelected ? '1px solid rgba(168,85,247,0.4)' : '1px solid transparent',
                borderLeft: isSelected ? '3px solid #a855f7' : `2px solid ${riskColors[pilot.risk_level] || '#888'}`,
                borderRadius: '3px',
                cursor: 'pointer',
              }}
            >
              <span style={{
                fontSize: '0.5rem',
                fontWeight: 700,
                color: '#fff',
                background: riskColors[pilot.risk_level] || '#888',
                padding: '1px 4px',
                borderRadius: '2px',
                flexShrink: 0,
                minWidth: '48px',
                textAlign: 'center',
              }}>
                {riskLabels[pilot.risk_level] || pilot.risk_level}
              </span>
              <img
                src={allianceApi.getCharacterPortraitUrl(pilot.character_id, 32)}
                alt=""
                style={{ width: 20, height: 20, borderRadius: 2 }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ fontSize: '0.7rem', color: '#58a6ff', fontWeight: 600, minWidth: '100px' }}>
                {pilot.character_name}
              </span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
                [{pilot.ticker}]
              </span>
              <span style={{ fontSize: '0.65rem', fontFamily: 'monospace', color: '#f85149' }}>
                {pilot.pod_deaths} pods
              </span>
              <span style={{ fontSize: '0.65rem', fontFamily: 'monospace', color: '#f85149' }}>
                {formatISKCompact(pilot.pod_isk_lost)}
              </span>
              <span style={{
                fontSize: '0.65rem',
                fontFamily: 'monospace',
                color: pilot.survival_rate >= 70 ? '#3fb950' : pilot.survival_rate >= 40 ? '#ffcc00' : '#f85149',
              }}>
                {pilot.survival_rate.toFixed(0)}% surv
              </span>
              <span style={{
                flex: 1,
                fontSize: '0.55rem',
                color: 'rgba(255,255,255,0.5)',
                fontStyle: 'italic',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {pilot.training_tip}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatBadge({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      padding: '0.3rem 0.5rem',
      background: `${color}15`,
      border: `1px solid ${color}30`,
      borderRadius: '4px',
    }}>
      <span style={{ color, fontWeight: 700, fontFamily: 'monospace', fontSize: '0.85rem' }}>{value}</span>
      <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem', marginLeft: '0.3rem' }}>{label}</span>
    </div>
  );
}

function CorpRow({ corp, rank, isSelected, onClick }: {
  corp: CapsuleerCorpStats;
  rank: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.4rem',
        marginBottom: '0.2rem',
        background: isSelected ? 'rgba(88,166,255,0.15)' : 'rgba(255,255,255,0.02)',
        border: isSelected ? '1px solid rgba(88,166,255,0.4)' : '1px solid transparent',
        borderLeft: `3px solid ${isSelected ? '#58a6ff' : 'rgba(255,255,255,0.1)'}`,
        borderRadius: '4px',
        cursor: 'pointer',
      }}
    >
      <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', width: '14px' }}>#{rank}</span>
      <img
        src={allianceApi.getCorpLogoUrl(corp.corp_id, 32)}
        alt=""
        style={{ width: 22, height: 22, borderRadius: 3 }}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {corp.corp_name}
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          [{corp.ticker}] • {corp.active_pilots} pilots
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#3fb950', fontFamily: 'monospace' }}>
          {corp.kills.toLocaleString()} <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)', fontWeight: 400 }}>kills</span>
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>{corp.efficiency.toFixed(0)}%</div>
      </div>
    </div>
  );
}

function PilotRow({ pilot, rank, isSelected, onClick }: {
  pilot: CapsuleerPilotStats;
  rank: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.4rem',
        marginBottom: '0.2rem',
        background: isSelected ? 'rgba(168,85,247,0.15)' : 'rgba(255,255,255,0.02)',
        border: isSelected ? '1px solid rgba(168,85,247,0.4)' : '1px solid transparent',
        borderLeft: `3px solid ${isSelected ? '#a855f7' : 'rgba(255,255,255,0.1)'}`,
        borderRadius: '4px',
        cursor: 'pointer',
      }}
    >
      <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', width: '14px' }}>#{rank}</span>
      <img
        src={allianceApi.getCharacterPortraitUrl(pilot.character_id, 32)}
        alt=""
        style={{ width: 22, height: 22, borderRadius: 3 }}
        onError={(e) => { e.currentTarget.style.display = 'none'; }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {pilot.character_name}
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          [{pilot.ticker}] • {pilot.final_blows} FB
          {pilot.min_sp > 0 && <span style={{ color: '#a855f7' }}> • {formatSP(pilot.min_sp)}</span>}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#3fb950', fontFamily: 'monospace' }}>
          {pilot.kills.toLocaleString()} <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)', fontWeight: 400 }}>kills</span>
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>{pilot.efficiency.toFixed(0)}%</div>
      </div>
    </div>
  );
}

function PilotDetailPanel({ pilot }: { pilot: CapsuleerDetailResponse }) {
  const maxShipUses = Math.max(...pilot.top_ships.map(s => s.uses), 1);
  const skillBreakdown = pilot.skill_estimate?.skill_breakdown || {};
  const sortedSkills = Object.entries(skillBreakdown)
    .sort(([, a], [, b]) => b.sp - a.sp)
    .slice(0, 10);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 1fr 1fr', gap: '1rem' }}>
      {/* Column 1: Portrait + Basic Info */}
      <div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '0.75rem' }}>
          <img
            src={allianceApi.getCharacterPortraitUrl(pilot.character_id, 256)}
            alt=""
            style={{ width: 120, height: 120, borderRadius: 8, marginBottom: '0.5rem' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', textAlign: 'center' }}>{pilot.character_name}</div>
          <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', textAlign: 'center' }}>
            {pilot.corp_name} [{pilot.ticker}]
          </div>
          <a
            href={allianceApi.getCharacterZkillUrl(pilot.character_id)}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: '0.65rem', color: '#58a6ff', textDecoration: 'none', marginTop: '0.25rem' }}
          >
            zKillboard →
          </a>
        </div>

        {/* Combat Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem' }}>
          <MiniStat label="KILLS" value={pilot.stats.kills.toLocaleString()} color="#3fb950" />
          <MiniStat label="DEATHS" value={pilot.stats.deaths.toLocaleString()} color="#f85149" />
          <MiniStat label="FINAL BLOWS" value={pilot.stats.final_blows.toLocaleString()} color="#58a6ff" />
          <MiniStat label="EFFICIENCY" value={`${pilot.stats.efficiency.toFixed(0)}%`} color="#ffcc00" />
          <MiniStat label="AVG DMG" value={formatDamage(pilot.stats.avg_damage)} color="#a855f7" />
          <MiniStat label="SOLO" value={pilot.stats.solo_kills.toString()} color="#ff6600" />
        </div>
      </div>

      {/* Column 2: Ships + Activity */}
      <div>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>🚀 SHIPS FLOWN</div>
        {pilot.top_ships.map(ship => (
          <div key={ship.ship_type_id} style={{ marginBottom: '0.3rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', marginBottom: '2px' }}>
              <span style={{ color: 'rgba(255,255,255,0.8)' }}>{ship.ship_name}</span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>{ship.uses}x ({ship.percentage.toFixed(0)}%)</span>
            </div>
            <div style={{ height: '3px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
              <div style={{ width: `${(ship.uses / maxShipUses) * 100}%`, height: '100%', background: '#58a6ff', borderRadius: '2px' }} />
            </div>
          </div>
        ))}

        {pilot.activity && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>🕐 ACTIVITY</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.3rem', fontSize: '0.65rem' }}>
              <div><span style={{ color: 'rgba(255,255,255,0.4)' }}>Peak Hour:</span> <span style={{ color: '#ffcc00' }}>{pilot.activity.peak_hour}:00</span></div>
              <div><span style={{ color: 'rgba(255,255,255,0.4)' }}>Peak Day:</span> <span style={{ color: '#ffcc00' }}>{pilot.activity.peak_day}</span></div>
              <div><span style={{ color: 'rgba(255,255,255,0.4)' }}>TZ:</span> <span style={{ color: getTZColor(pilot.activity.timezone) }}>{pilot.activity.timezone}</span></div>
              <div><span style={{ color: 'rgba(255,255,255,0.4)' }}>Active:</span> <span style={{ color: '#fff' }}>{pilot.activity.active_days}d</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Column 3: Top Victims */}
      <div>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>💀 TOP VICTIMS</div>
        {pilot.top_victims.length === 0 ? (
          <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>No victim data</div>
        ) : (
          pilot.top_victims.map(victim => (
            <div
              key={victim.alliance_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.3rem',
                background: 'rgba(248,81,73,0.1)',
                borderRadius: '3px',
                marginBottom: '0.2rem',
              }}
            >
              <img
                src={allianceApi.getLogoUrl(victim.alliance_id, 32)}
                alt=""
                style={{ width: 18, height: 18, borderRadius: 2 }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ flex: 1, fontSize: '0.65rem', color: 'rgba(255,255,255,0.8)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {victim.alliance_name}
              </span>
              <span style={{ fontSize: '0.65rem', color: '#f85149', fontFamily: 'monospace' }}>{victim.kills}</span>
            </div>
          ))
        )}

        {/* ISK Stats */}
        <div style={{ marginTop: '1rem' }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>💰 ISK</div>
          <div style={{ fontSize: '0.65rem' }}>
            <div><span style={{ color: 'rgba(255,255,255,0.4)' }}>Destroyed:</span> <span style={{ color: '#3fb950' }}>{formatISKCompact(pilot.stats.isk_destroyed)}</span></div>
            <div><span style={{ color: 'rgba(255,255,255,0.4)' }}>Lost:</span> <span style={{ color: '#f85149' }}>{formatISKCompact(pilot.stats.isk_lost)}</span></div>
          </div>
        </div>
      </div>

      {/* Column 4: Skill Estimate */}
      <div>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>
          🧠 SKILL ESTIMATE
          {pilot.skill_estimate && (
            <span style={{ fontSize: '0.9rem', color: '#a855f7', marginLeft: '0.5rem', fontFamily: 'monospace' }}>
              {formatSP(pilot.skill_estimate.min_sp)}
            </span>
          )}
        </div>
        {!pilot.skill_estimate ? (
          <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
            Skill analysis not yet calculated
          </div>
        ) : (
          <>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.5rem' }}>
              Based on {pilot.skill_estimate.ships_analyzed} ships, {pilot.skill_estimate.modules_analyzed} modules
            </div>
            <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
              {sortedSkills.map(([name, data]) => (
                <div key={name} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.2rem 0.3rem',
                  marginBottom: '0.15rem',
                  background: 'rgba(168,85,247,0.1)',
                  borderRadius: '2px',
                  fontSize: '0.6rem',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{name}</span>
                  <span>
                    <span style={{ color: '#a855f7' }}>L{data.level}</span>
                    <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.3rem' }}>{formatSP(data.sp)}</span>
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.05)',
      borderRadius: '3px',
      padding: '0.25rem',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: '0.8rem', fontWeight: 700, color, fontFamily: 'monospace' }}>{value}</div>
      <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>{label}</div>
    </div>
  );
}

function formatSP(sp: number): string {
  if (sp >= 1000000) return `${(sp / 1000000).toFixed(1)}M SP`;
  if (sp >= 1000) return `${(sp / 1000).toFixed(0)}K SP`;
  return `${sp} SP`;
}

function formatDamage(damage: number): string {
  if (damage >= 1000000000) return `${(damage / 1000000000).toFixed(1)}B`;
  if (damage >= 1000000) return `${(damage / 1000000).toFixed(1)}M`;
  if (damage >= 1000) return `${(damage / 1000).toFixed(1)}K`;
  return damage.toString();
}

function getTZColor(tz: string): string {
  switch (tz) {
    case 'EU': return '#3fb950';
    case 'US': return '#58a6ff';
    case 'AU': return '#a855f7';
    default: return '#fff';
  }
}

export default CapsuleersView;
