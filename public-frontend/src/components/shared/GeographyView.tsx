/**
 * Shared Geography Tab - Activity Map + DOTLAN Integration
 *
 * Unified component for Alliance, Corporation, and PowerBloc entities.
 * Shows DOTLAN-powered live activity, sovereignty defense, territorial changes,
 * alliance power metrics, plus regional distribution, top systems, and home systems.
 */

import { useState, useEffect, useCallback } from 'react';
import type { EntityViewProps, FetcherMap } from './types';
import type { GeographyExtended } from '../../types/geography-dotlan';
import {
  LiveActivityPanel,
  SovDefensePanel,
  TerritorialChangesPanel,
  AlliancePowerPanel,
} from '../corporation/geography';
import { getGeographyExtended as getAllianceGeo } from '../../services/allianceApi';
import { corpApi } from '../../services/corporationApi';

// ============================================================================
// PowerBloc fetcher (days -> minutes conversion)
// ============================================================================

async function fetchPBGeography(leaderId: number, days: number): Promise<GeographyExtended> {
  const minutes = days * 1440;
  const response = await fetch(`/api/powerbloc/${leaderId}/geography/extended?minutes=${minutes}`);
  if (!response.ok) throw new Error(`Failed to fetch geography: ${response.status}`);
  return response.json();
}

// ============================================================================
// Fetcher Map
// ============================================================================

const geographyFetchers: FetcherMap<GeographyExtended> = {
  alliance: (id, days) => getAllianceGeo(id, days),
  corporation: (id, days) => corpApi.getGeographyExtended(id, days),
  powerbloc: fetchPBGeography,
};

// ============================================================================
// Main Component
// ============================================================================

export function GeographyView({ entityType, entityId, days }: EntityViewProps) {
  const [data, setData] = useState<GeographyExtended | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const fetcher = geographyFetchers[entityType];
      const result = await fetcher(entityId, days);
      setData(result);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch extended geography:', err);
      setError('Failed to load geography data');
    } finally {
      setLoading(false);
    }
  }, [entityType, entityId, days]);

  // Initial fetch
  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 10 minutes for live DOTLAN data
  useEffect(() => {
    const interval = setInterval(fetchData, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e' }}>
        Loading geography data...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#f85149' }}>
        {error || 'Failed to load data'}
      </div>
    );
  }

  const hasCriticalCampaigns = data.sov_defense?.critical_count > 0;
  const isCoalition = entityType === 'powerbloc';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {/* DOTLAN: Live Activity Monitor */}
      <SectionPanel title="LIVE ACTIVITY" icon="\u{1F4E1}" refreshRate="1h" borderColor="#14b8a6">
        <LiveActivityPanel data={data.live_activity} />
      </SectionPanel>

      {/* DOTLAN: Sovereignty Defense */}
      <SectionPanel
        title={isCoalition ? 'COALITION SOVEREIGNTY DEFENSE' : 'SOVEREIGNTY DEFENSE'}
        icon="\u{1F6E1}\u{FE0F}"
        refreshRate="10min"
        borderColor={hasCriticalCampaigns ? '#f85149' : '#3fb950'}
        badge={hasCriticalCampaigns ? `${data.sov_defense.critical_count} ALERT` : undefined}
      >
        <SovDefensePanel data={data.sov_defense} />
      </SectionPanel>

      {/* DOTLAN: Territorial Changes + Alliance Power (side by side) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
        <SectionPanel title="TERRITORIAL CHANGES" icon="\u{1F4C8}" refreshRate="2h" borderColor="#a855f7">
          <TerritorialChangesPanel data={data.territorial_changes} />
        </SectionPanel>

        <SectionPanel
          title={isCoalition ? 'COALITION POWER' : 'ALLIANCE POWER'}
          icon="\u{1F451}"
          refreshRate="24h"
          borderColor="#58a6ff"
        >
          <AlliancePowerPanel data={data.alliance_power} />
        </SectionPanel>
      </div>

      {/* zKill Data: Region Distribution + Top Systems */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
        <RegionsPanel regions={data.regions} />
        <TopSystemsPanel systems={data.top_systems} />
      </div>

      {/* zKill Data: Home Systems */}
      <HomeSystemsPanel homeSystems={data.home_systems} isCoalition={isCoalition} />
    </div>
  );
}

// ============================================================================
// Section Panel Wrapper (non-collapsible)
// ============================================================================

function SectionPanel({
  title,
  icon,
  refreshRate,
  borderColor,
  badge,
  children,
}: {
  title: string;
  icon: string;
  refreshRate: string;
  borderColor: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        borderLeft: `2px solid ${borderColor}`,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.3rem 0.5rem',
          background: 'rgba(0,0,0,0.2)',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        <span style={{ fontSize: '0.8rem' }}>{icon}</span>
        <span style={{ fontSize: '0.65rem', fontWeight: 600, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {title}
        </span>
        {badge && (
          <span
            style={{
              padding: '0.1rem 0.3rem',
              borderRadius: '3px',
              fontSize: '0.55rem',
              fontWeight: 700,
              background: 'rgba(248,81,73,0.2)',
              color: '#f85149',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          >
            {badge}
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: '0.5rem', color: '#6e7681' }}>{'\u21BB'} {refreshRate}</span>
      </div>

      {/* Content */}
      <div style={{ padding: '0.4rem' }}>{children}</div>
    </div>
  );
}

// ============================================================================
// zKillboard Panel Components
// ============================================================================

function RegionsPanel({ regions }: { regions: GeographyExtended['regions'] }) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        padding: '0.4rem',
        borderLeft: '2px solid #58a6ff',
        maxHeight: '300px',
        overflowY: 'auto',
      }}
    >
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem', fontWeight: 600 }}>
        {'\u2022'} REGION DISTRIBUTION ({regions.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        {regions.map((r) => (
          <div
            key={r.region_id}
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: '0.2rem 0.35rem',
              borderRadius: '3px',
              fontSize: '0.65rem',
              borderLeft: '2px solid #58a6ff',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ color: '#c9d1d9' }}>{r.region_name}</span>
            <span style={{ display: 'flex', gap: '0.4rem', fontSize: '0.6rem' }}>
              <span style={{ color: '#58a6ff', fontFamily: 'monospace' }}>{r.activity}</span>
              <span style={{ color: '#8b949e' }}>{r.kills}K/{r.deaths}D</span>
              <span style={{ color: (Number(r.efficiency) || 0) >= 50 ? '#3fb950' : '#f85149', fontFamily: 'monospace' }}>
                {(Number(r.efficiency) || 0).toFixed(0)}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TopSystemsPanel({ systems }: { systems: GeographyExtended['top_systems'] }) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        padding: '0.4rem',
        borderLeft: '2px solid #3fb950',
        maxHeight: '300px',
        overflowY: 'auto',
      }}
    >
      <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.3rem', fontWeight: 600 }}>
        {'\u2022'} TOP SYSTEMS ({systems.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        {systems.map((s) => (
          <div
            key={s.system_id}
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: '0.2rem 0.35rem',
              borderRadius: '3px',
              fontSize: '0.65rem',
              borderLeft: '2px solid #3fb950',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>
              <span style={{ fontWeight: 600, color: '#c9d1d9' }}>{s.system_name}</span>
              <span style={{ color: '#6e7681', marginLeft: '0.3rem', fontSize: '0.55rem' }}>{s.region_name}</span>
            </span>
            <span style={{ display: 'flex', gap: '0.4rem', fontSize: '0.6rem' }}>
              <span style={{ color: '#3fb950', fontFamily: 'monospace' }}>{s.activity}</span>
              <span style={{ color: '#8b949e' }}>{s.kills}K/{s.deaths}D</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HomeSystemsPanel({ homeSystems, isCoalition }: { homeSystems: GeographyExtended['home_systems']; isCoalition: boolean }) {
  if (homeSystems.length === 0) {
    return (
      <div
        style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          padding: '0.4rem',
          borderLeft: '2px solid #a855f7',
          textAlign: 'center',
          color: '#8b949e',
          fontSize: '0.65rem',
        }}
      >
        No home systems detected (require 10+ activity & positive K/D)
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        padding: '0.4rem',
        borderLeft: '2px solid #a855f7',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: '#8b949e', fontWeight: 600 }}>
          {'\u2022'} HOME SYSTEMS ({homeSystems.length})
        </span>
        <span style={{ fontSize: '0.5rem', color: '#6e7681' }}>
          <span style={{ color: '#3fb950' }}>{'\u25A0'}</span> {isCoalition ? 'Coalition' : 'Alliance'} Sov
          <span style={{ color: '#a855f7', marginLeft: '0.4rem' }}>{'\u25A0'}</span> Foreign
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.2rem' }}>
        {homeSystems.map((s) => (
          <div
            key={s.system_id}
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: '0.2rem 0.35rem',
              borderRadius: '3px',
              fontSize: '0.65rem',
              borderLeft: `2px solid ${s.owned_by_alliance ? '#3fb950' : '#a855f7'}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>
              {s.owned_by_alliance && <span style={{ marginRight: '0.2rem' }}>{'\u{1F3E0}'}</span>}
              <span style={{ fontWeight: 600, color: s.owned_by_alliance ? '#3fb950' : '#a855f7' }}>{s.system_name}</span>
              <span style={{ color: '#6e7681', marginLeft: '0.3rem', fontSize: '0.55rem' }}>{s.region_name}</span>
            </span>
            <span style={{ color: '#8b949e', fontSize: '0.55rem' }}>{s.kills}K/{s.deaths}D</span>
          </div>
        ))}
      </div>
    </div>
  );
}
