import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { reportsApi } from '../services/api';
import type { PowerBlocComplete } from '../types/powerbloc';
import { formatISKCompact } from '../utils/format';
import { ModuleGate } from '../components/ModuleGate';
import { Sparkline } from '../components/alliance';
import {
  PBDetailsView,
  PBWormholeView,
  PBAlliancesView, PBPilotsView, PBHuntingView,
} from '../components/powerbloc';
import { OffensiveView } from '../components/shared/OffensiveView';
import { DefensiveView } from '../components/shared/DefensiveView';
import { CapitalsView } from '../components/shared/CapitalsView';
import { GeographyView } from '../components/shared/GeographyView';
import { LiveMapView } from '../components/shared/LiveMapView';

type TabType = 'overview' | 'offensive' | 'defensive' | 'capitals' | 'alliances' | 'pilots' | 'geography' | 'livemap' | 'wormhole' | 'hunting';

const TABS: { id: TabType; label: string; emoji: string }[] = [
  { id: 'overview', label: 'OVERVIEW', emoji: '📊' },
  { id: 'offensive', label: 'OFFENSIVE', emoji: '⚔️' },
  { id: 'defensive', label: 'DEFENSIVE', emoji: '🛡️' },
  { id: 'capitals', label: 'CAPITALS', emoji: '🚀' },
  { id: 'alliances', label: 'ALLIANCES', emoji: '👥' },
  { id: 'pilots', label: 'PILOTS', emoji: '🎯' },
  { id: 'geography', label: 'GEOGRAPHY', emoji: '🌍' },
  { id: 'livemap', label: 'LIVE MAP', emoji: '🗺️' },
  { id: 'wormhole', label: 'WORMHOLE', emoji: '🌀' },
  { id: 'hunting', label: 'HUNTING', emoji: '🔍' },
];

const TIME_OPTIONS = [
  { label: '24H', days: 1 },
  { label: '7D', days: 7 },
  { label: '14D', days: 14 },
  { label: '30D', days: 30 },
];

export function PowerBlocDetail() {
  const { leaderAllianceId } = useParams<{ leaderAllianceId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<PowerBlocComplete | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  const currentTab = (searchParams.get('tab') as TabType) || 'overview';

  const leaderId = leaderAllianceId ? parseInt(leaderAllianceId) : 0;

  // Load base data (header + members) - uses minutes param
  useEffect(() => {
    if (!leaderId) return;
    setLoading(true);
    setError(null);
    reportsApi.getPowerBlocDetail(leaderId, days * 1440)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [leaderId, days]);

  const setTab = (tab: TabType) => {
    setSearchParams({ tab });
  };

  if (loading) {
    return (
      <div style={{ padding: '1rem', zoom: 1.1 }}>
        <div className="skeleton" style={{ height: '120px', marginBottom: '1rem', borderRadius: '8px' }} />
        <div className="skeleton" style={{ height: '400px', borderRadius: '8px' }} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{
        background: 'rgba(248,81,73,0.2)',
        border: '1px solid #f85149',
        borderRadius: '8px',
        padding: '2rem',
        textAlign: 'center',
        zoom: 1.1,
      }}>
        <h2 style={{ color: '#f85149', margin: '0 0 0.5rem 0' }}>Failed to load power bloc data</h2>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0 }}>{error || 'Unknown error'}</p>
      </div>
    );
  }

  const { header } = data;
  const dailyNetIsk = data.combat.daily_activity.map(d => (d.isk_destroyed || 0) - (d.isk_lost || 0));
  const threatLevel = header.efficiency < 40 ? 'CRITICAL' : header.efficiency < 50 ? 'HIGH' : header.efficiency < 60 ? 'MEDIUM' : 'LOW';
  const threatColor = threatLevel === 'CRITICAL' ? '#ff0000' : threatLevel === 'HIGH' ? '#ff6600' : threatLevel === 'MEDIUM' ? '#ffcc00' : '#3fb950';

  return (
    <div style={{ padding: '0.5rem', zoom: 1.1 }}>
      {/* HEADER BOX */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: '0.75rem 1rem',
        marginBottom: '0.75rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <img
            src={`https://images.evetech.net/alliances/${data.leader_alliance_id}/logo?size=64`}
            alt=""
            loading="lazy"
            style={{ width: 40, height: 40, borderRadius: 6 }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#a855f7' }}>
              {data.coalition_name}
            </h1>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 400, fontSize: '0.85rem' }}>
              {data.member_count} alliances
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginLeft: 'auto' }}>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: header.net_isk >= 0 ? '#3fb950' : '#f85149', fontFamily: 'monospace' }}>
                {formatISKCompact(Math.abs(header.net_isk))}
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem', textTransform: 'uppercase' }}>
                {header.net_isk >= 0 ? 'profit' : 'loss'}
              </span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
                {(header.isk_efficiency ?? header.efficiency)?.toFixed(1)}
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem', textTransform: 'uppercase' }}>%isk</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
                {(header.kill_efficiency ?? 0).toFixed(1)}
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem', textTransform: 'uppercase' }}>%k/d</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'monospace' }}>
                <span style={{ color: '#3fb950' }}>{header.kills?.toLocaleString()}</span>
                <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
                <span style={{ color: '#f85149' }}>{header.deaths?.toLocaleString()}</span>
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem', textTransform: 'uppercase' }}>k/d</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Status</span>
              <span style={{
                fontSize: '0.6rem',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: '3px',
                background: threatColor,
                color: threatLevel === 'LOW' ? '#000' : '#fff',
              }}>
                {threatLevel}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)' }}>Power Bloc Intel</span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              Peak <span style={{ color: '#ffcc00', fontWeight: 600 }}>{header.peak_hour}:00</span>
            </span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              <span style={{ color: '#a855f7', fontWeight: 600 }}>{data.total_pilots?.toLocaleString()}</span> pilots
            </span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              <span style={{ color: '#3fb950', fontWeight: 600 }}>{data.active_pilots?.toLocaleString()}</span> active
            </span>
          </div>
          <div style={{ flex: 1 }} />
          <Sparkline data={dailyNetIsk} width={200} height={24} />
        </div>
      </div>

      {/* TABS + TIME SELECTOR */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.75rem',
        flexWrap: 'wrap',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.35rem 0.6rem',
              background: currentTab === tab.id ? 'rgba(168,85,247,0.2)' : 'transparent',
              border: currentTab === tab.id ? '1px solid #a855f7' : '1px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.7rem',
              fontWeight: 600,
              color: currentTab === tab.id ? '#a855f7' : 'rgba(255,255,255,0.5)',
              textTransform: 'uppercase',
            }}
          >
            {currentTab === tab.id && <span style={{ color: '#a855f7' }}>✕</span>}
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        ))}

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          {TIME_OPTIONS.map(opt => (
            <button
              key={opt.days}
              onClick={() => setDays(opt.days)}
              style={{
                padding: '0.25rem 0.5rem',
                background: days === opt.days ? 'rgba(168,85,247,0.2)' : 'transparent',
                border: days === opt.days ? '1px solid #a855f7' : '1px solid rgba(255,255,255,0.1)',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '0.65rem',
                fontWeight: 600,
                color: days === opt.days ? '#a855f7' : 'rgba(255,255,255,0.4)',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content — Overview is free, all other tabs require powerbloc_intel */}
      {currentTab === 'overview' && <PBDetailsView leaderId={leaderId} days={days} />}
      {currentTab === 'offensive' && (
        <ModuleGate module="powerbloc_intel">
          <OffensiveView entityType="powerbloc" entityId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'defensive' && (
        <ModuleGate module="powerbloc_intel">
          <DefensiveView entityType="powerbloc" entityId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'capitals' && (
        <ModuleGate module="powerbloc_intel">
          <CapitalsView entityType="powerbloc" entityId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'geography' && (
        <ModuleGate module="powerbloc_intel">
          <GeographyView entityType="powerbloc" entityId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'livemap' && (
        <ModuleGate module="powerbloc_intel">
          <LiveMapView entityType="powerbloc" entityId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'wormhole' && (
        <ModuleGate module="powerbloc_intel">
          <PBWormholeView leaderId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'alliances' && (
        <ModuleGate module="powerbloc_intel">
          <PBAlliancesView leaderId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'pilots' && (
        <ModuleGate module="powerbloc_intel">
          <PBPilotsView leaderId={leaderId} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'hunting' && (
        <ModuleGate module="powerbloc_intel">
          <PBHuntingView leaderId={leaderId} days={days} />
        </ModuleGate>
      )}
    </div>
  );
}

export default PowerBlocDetail;
