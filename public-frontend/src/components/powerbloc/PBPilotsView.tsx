/**
 * PBPilotsView - PowerBloc Capsuleer Intelligence
 *
 * Layout:
 * ┌─────────────────────── SUMMARY STATS ──────────────────────┐
 * ├──────────────────────┬──────────────────────────────────────┤
 * │ ALLIANCE RANKINGS    │ TOP CAPSULEERS                       │
 * │ (click to filter)    │ (scrollable list)                    │
 * ├──────────────────────┴──────────────────────────────────────┤
 * │ CORP RANKINGS (full width, clickable)                       │
 * ├────────────────────────────────────────────────────────────┤
 * │ CORP PILOT INTEL (PilotsView for selected corp)            │
 * └────────────────────────────────────────────────────────────┘
 */

import { useState, useEffect } from 'react';
import { powerblocApi } from '../../services/api/powerbloc';
import { PilotsView } from '../corporation/PilotsView';

interface PBPilotsViewProps {
  leaderId: number;
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

export function PBPilotsView({ leaderId, days }: PBPilotsViewProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAlliance, setSelectedAlliance] = useState<any>(null);
  const [selectedCorp, setSelectedCorp] = useState<any>(null);

  useEffect(() => {
    setLoading(true);
    powerblocApi.getCapsuleers(leaderId, days)
      .then(setData)
      .catch(err => console.error('PB capsuleer data error:', err))
      .finally(() => setLoading(false));
  }, [leaderId, days]);

  if (loading) {
    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
          {[1, 2].map(i => (
            <div key={i} className="skeleton" style={{ height: '300px', borderRadius: '6px' }} />
          ))}
        </div>
        <div className="skeleton" style={{ height: '200px', borderRadius: '6px' }} />
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{
        background: 'rgba(248,81,73,0.2)',
        border: '1px solid #f85149',
        borderRadius: '8px',
        padding: '2rem',
        textAlign: 'center',
      }}>
        <h3 style={{ color: '#f85149', margin: 0 }}>Failed to load capsuleer data</h3>
      </div>
    );
  }

  const displayedPilots = selectedAlliance
    ? data.top_pilots.filter((p: any) => p.alliance_id === selectedAlliance.alliance_id)
    : data.top_pilots;

  const displayedCorps = selectedAlliance
    ? data.corp_rankings.filter((_: any) => {
        // Since we don't have alliance_id on corps directly, show all when alliance selected
        return true;
      })
    : data.corp_rankings;

  return (
    <div>
      {/* Summary Stats */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <StatBadge label="ACTIVE PILOTS" value={(data.summary.active_pilots || 0).toLocaleString()} color="#3fb950" />
        <StatBadge label="KILLS" value={(data.summary.total_kills || 0).toLocaleString()} color="#3fb950" />
        <StatBadge label="DEATHS" value={(data.summary.total_deaths || 0).toLocaleString()} color="#f85149" />
        <StatBadge label="EFFICIENCY" value={`${(data.summary.efficiency || 0).toFixed(1)}%`} color="#ffcc00" />
        <StatBadge label="ALLIANCES" value={(data.alliance_rankings?.length || 0).toString()} color="#58a6ff" />
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

      {/* PowerBloc-wide Pilot Intelligence */}
      <div style={{ marginBottom: '0.75rem' }}>
        <PilotsView leaderId={leaderId} days={days} />
      </div>

      {/* Top Row: Alliance Rankings + Capsuleers */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
        {/* Alliance Rankings */}
        <div style={cardStyle}>
          <div style={headerStyle}>
            <span style={{ fontSize: '0.8rem' }}>🏛️</span>
            <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>ALLIANCE RANKINGS</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
              {data.alliance_rankings?.length || 0} alliances
            </span>
          </div>
          <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {(data.alliance_rankings || []).map((alliance: any, idx: number) => (
              <AllianceRow
                key={alliance.alliance_id}
                alliance={alliance}
                rank={idx + 1}
                isSelected={selectedAlliance?.alliance_id === alliance.alliance_id}
                onClick={() => setSelectedAlliance(
                  selectedAlliance?.alliance_id === alliance.alliance_id ? null : alliance
                )}
              />
            ))}
          </div>
        </div>

        {/* Top Capsuleers */}
        <div style={cardStyle}>
          <div style={headerStyle}>
            <span style={{ fontSize: '0.8rem' }}>👤</span>
            <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>TOP CAPSULEERS</span>
            {selectedAlliance && (
              <span style={{
                fontSize: '0.6rem',
                background: 'rgba(88,166,255,0.2)',
                border: '1px solid #58a6ff',
                borderRadius: '3px',
                padding: '1px 4px',
                color: '#58a6ff',
              }}>
                [{selectedAlliance.ticker}]
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
              displayedPilots.map((pilot: any, idx: number) => (
                <PilotRow key={pilot.character_id} pilot={pilot} rank={idx + 1} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Corp Rankings */}
      <div style={{ ...cardStyle, marginBottom: '0.75rem' }}>
        <div style={headerStyle}>
          <span style={{ fontSize: '0.8rem' }}>🏢</span>
          <span style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>CORP RANKINGS</span>
          {selectedCorp && (
            <span style={{
              fontSize: '0.6rem',
              background: 'rgba(88,166,255,0.2)',
              border: '1px solid #58a6ff',
              borderRadius: '3px',
              padding: '1px 4px',
              color: '#58a6ff',
              cursor: 'pointer',
            }}
            onClick={() => setSelectedCorp(null)}
            >
              [{selectedCorp.ticker}] ✕
            </span>
          )}
          <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
            {displayedCorps.length} corps — click for pilot intel
          </span>
        </div>
        <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
          {displayedCorps.map((corp: any, idx: number) => (
            <CorpRow
              key={corp.corp_id}
              corp={corp}
              rank={idx + 1}
              isSelected={selectedCorp?.corp_id === corp.corp_id}
              onClick={() => setSelectedCorp(
                selectedCorp?.corp_id === corp.corp_id ? null : corp
              )}
            />
          ))}
        </div>
      </div>

      {/* Corp Pilot Intel */}
      {selectedCorp && (
        <div>
          <div style={{ ...cardStyle, padding: '0.5rem 0.75rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <img
              src={`https://images.evetech.net/corporations/${selectedCorp.corp_id}/logo?size=32`}
              alt=""
              style={{ width: 24, height: 24, borderRadius: 3 }}
              onError={(e: any) => { e.currentTarget.style.display = 'none'; }}
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
      )}
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

function AllianceRow({ alliance, rank, isSelected, onClick }: {
  alliance: any;
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
        src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=32`}
        alt=""
        style={{ width: 22, height: 22, borderRadius: 3 }}
        onError={(e: any) => { e.currentTarget.style.display = 'none'; }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {alliance.alliance_name}
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          [{alliance.ticker}] • {alliance.pilots} pilots
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#3fb950', fontFamily: 'monospace' }}>
          {alliance.kills.toLocaleString()} <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)', fontWeight: 400 }}>kills</span>
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>{alliance.efficiency.toFixed(0)}%</div>
      </div>
    </div>
  );
}

function CorpRow({ corp, rank, isSelected, onClick }: {
  corp: any;
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
        src={`https://images.evetech.net/corporations/${corp.corp_id}/logo?size=32`}
        alt=""
        style={{ width: 22, height: 22, borderRadius: 3 }}
        onError={(e: any) => { e.currentTarget.style.display = 'none'; }}
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
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          {corp.deaths} deaths • {corp.efficiency.toFixed(0)}%
        </div>
      </div>
    </div>
  );
}

function PilotRow({ pilot, rank }: { pilot: any; rank: number }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.4rem',
        marginBottom: '0.2rem',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid transparent',
        borderLeft: '3px solid rgba(255,255,255,0.1)',
        borderRadius: '4px',
      }}
    >
      <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', width: '14px' }}>#{rank}</span>
      <img
        src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
        alt=""
        style={{ width: 22, height: 22, borderRadius: 3 }}
        onError={(e: any) => { e.currentTarget.style.display = 'none'; }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {pilot.character_name}
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          [{pilot.ticker || '???'}] • {pilot.final_blows || 0} FB
          <span style={{ marginLeft: '0.3rem', color: 'rgba(255,255,255,0.3)' }}>
            {pilot.alliance_name}
          </span>
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

export default PBPilotsView;
