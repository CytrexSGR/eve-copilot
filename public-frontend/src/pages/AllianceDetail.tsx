import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { allianceApi, type SovThreatsResponse } from '../services/allianceApi';
import type { AllianceComplete } from '../types/alliance';
import { formatISKCompact } from '../utils/format';
import { ModuleGate } from '../components/ModuleGate';
import {
  HuntingView,
  OverviewView,
  WormholeView,
  CapsuleersView,
  CorpsView,
  Sparkline,
  type AllianceWormholeEmpire,
} from '../components/alliance';
import { OffensiveView } from '../components/shared/OffensiveView';
import { DefensiveView } from '../components/shared/DefensiveView';
import { CapitalsView } from '../components/shared/CapitalsView';
import { GeographyView } from '../components/shared/GeographyView';
import { LiveMapView } from '../components/shared/LiveMapView';


type TabType = 'hunting' | 'details' | 'offensive' | 'defensive' | 'capitals' | 'geography' | 'livemap' | 'wormhole' | 'capsuleer' | 'corps';

const TIME_OPTIONS = [
  { label: '24H', days: 1 },
  { label: '7D', days: 7 },
  { label: '14D', days: 14 },
  { label: '30D', days: 30 },
];

export function AllianceDetail() {
  const { allianceId } = useParams<{ allianceId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<AllianceComplete | null>(null);
  const [wormholeIntel, setWormholeIntel] = useState<AllianceWormholeEmpire | null>(null);
  const [sovThreats, setSovThreats] = useState<SovThreatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [wormholeLoading, setWormholeLoading] = useState(false);
  const [sovThreatsLoading, setSovThreatsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  const currentTab = (searchParams.get('tab') as TabType) || 'details';

  useEffect(() => {
    if (!allianceId) return;
    setLoading(true);
    setError(null);
    allianceApi.getComplete(parseInt(allianceId), days)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  useEffect(() => {
    if (!allianceId || currentTab !== 'wormhole') return;
    setWormholeLoading(true);
    setSovThreatsLoading(true);

    // Fetch both WH empire and SOV threats in parallel
    Promise.all([
      allianceApi.getWormholeIntel(parseInt(allianceId), days)
        .then(setWormholeIntel)
        .catch((err: Error) => console.error('Wormhole intel error:', err))
        .finally(() => setWormholeLoading(false)),
      allianceApi.getSovThreats(parseInt(allianceId))
        .then(setSovThreats)
        .catch((err: Error) => console.error('SOV threats error:', err))
        .finally(() => setSovThreatsLoading(false)),
    ]);
  }, [allianceId, currentTab, days]);

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
        <h2 style={{ color: '#f85149', margin: '0 0 0.5rem 0' }}>Failed to load alliance data</h2>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0 }}>{error || 'Unknown error'}</p>
      </div>
    );
  }

  const { alliance_info, header, combat } = data;
  const dailyNetIsk = combat.kills_activity.daily_activity.map(d => d.isk_destroyed - d.isk_lost);

  // Determine threat level based on efficiency
  const threatLevel = header.efficiency < 40 ? 'CRITICAL' : header.efficiency < 50 ? 'HIGH' : header.efficiency < 60 ? 'MEDIUM' : 'LOW';
  const threatColor = threatLevel === 'CRITICAL' ? '#ff0000' : threatLevel === 'HIGH' ? '#ff6600' : threatLevel === 'MEDIUM' ? '#ffcc00' : '#3fb950';

  return (
    <div style={{ padding: '0.5rem', zoom: 1.1 }}>
      {/* HEADER BOX - Battle Report Style */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: '0.75rem 1rem',
        marginBottom: '0.75rem',
      }}>
        {/* Top Row: Logo + Title + Stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <img
            src={allianceApi.getLogoUrl(data.alliance_id, 64)}
            alt=""
            style={{ width: 40, height: 40, borderRadius: 6 }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
              {alliance_info.name}
            </h1>
            <span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 400, fontSize: '1rem' }}>
              [{alliance_info.ticker}]
            </span>
          </div>

          {/* Inline Stats */}
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

            {/* Threat Level Badge */}
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
              <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${header.efficiency || 0}%`, height: '100%', background: threatColor }} />
              </div>
            </div>
          </div>

          {/* zKill Link */}
          <a
            href={allianceApi.getZkillUrl(data.alliance_id)}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: '0.25rem 0.5rem',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              fontSize: '0.65rem',
              textDecoration: 'none',
              color: 'rgba(255,255,255,0.6)',
            }}
          >
            zKill →
          </a>
        </div>

        {/* Sub-header Row: Sparkline + Additional Stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>📊</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)' }}>Alliance Intel</span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              Peak <span style={{ color: '#ffcc00', fontWeight: 600 }}>{header.peak_hour}:00</span>
            </span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              Trend <span style={{ color: header.trend_pct >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                {header.trend_pct >= 0 ? '↑' : '↓'}{Math.abs(header.trend_pct || 0).toFixed(1)}%
              </span>
            </span>
          </div>
          <div style={{ flex: 1 }} />
          <Sparkline data={dailyNetIsk} width={200} height={24} />
        </div>
      </div>

      {/* TABS + TIME SELECTOR - Battle Report Style */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.75rem',
        flexWrap: 'wrap',
      }}>
        {/* Tab Buttons */}
        {([
          { id: 'details', label: 'OVERVIEW', emoji: '📊' },
          { id: 'offensive', label: 'OFFENSIVE', emoji: '⚔️' },
          { id: 'defensive', label: 'DEFENSIVE', emoji: '🛡️' },
          { id: 'capitals', label: 'CAPITALS', emoji: '🚀' },
          { id: 'corps', label: 'CORPS', emoji: '🏢' },
          { id: 'capsuleer', label: 'PILOTS', emoji: '👤' },
          { id: 'geography', label: 'GEOGRAPHY', emoji: '🌍' },
          { id: 'livemap', label: 'LIVE MAP', emoji: '🗺️' },
          { id: 'wormhole', label: 'WORMHOLE', emoji: '🌀' },
          { id: 'hunting', label: 'HUNTING', emoji: '🎯' },
        ] as { id: TabType; label: string; emoji: string }[]).map(tab => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.35rem 0.6rem',
              background: currentTab === tab.id ? 'rgba(88,166,255,0.2)' : 'transparent',
              border: currentTab === tab.id ? '1px solid #58a6ff' : '1px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.7rem',
              fontWeight: 600,
              color: currentTab === tab.id ? '#58a6ff' : 'rgba(255,255,255,0.5)',
              textTransform: 'uppercase',
            }}
          >
            {currentTab === tab.id && <span style={{ color: '#58a6ff' }}>✕</span>}
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        ))}

        {/* Stat Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginLeft: '0.5rem' }}>
          <span style={{
            padding: '0.2rem 0.4rem',
            background: 'rgba(63,185,80,0.15)',
            border: '1px solid rgba(63,185,80,0.3)',
            borderRadius: '3px',
            fontSize: '0.6rem',
            fontWeight: 600,
          }}>
            <span style={{ color: '#3fb950' }}>{header.kills?.toLocaleString()}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.2rem' }}>KILLS</span>
          </span>
          <span style={{
            padding: '0.2rem 0.4rem',
            background: 'rgba(255,204,0,0.15)',
            border: '1px solid rgba(255,204,0,0.3)',
            borderRadius: '3px',
            fontSize: '0.6rem',
            fontWeight: 600,
          }}>
            <span style={{ color: '#ffcc00' }}>{formatISKCompact(combat.summary?.isk_destroyed || 0)}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.2rem' }}>ISK</span>
          </span>
          <span style={{
            padding: '0.2rem 0.4rem',
            background: 'rgba(168,85,247,0.15)',
            border: '1px solid rgba(168,85,247,0.3)',
            borderRadius: '3px',
            fontSize: '0.6rem',
            fontWeight: 600,
          }}>
            <span style={{ color: '#a855f7' }}>{data.sovereignty?.count || 0}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.2rem' }}>SOV</span>
          </span>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Time Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          {TIME_OPTIONS.map(opt => (
            <button
              key={opt.days}
              onClick={() => setDays(opt.days)}
              style={{
                padding: '0.25rem 0.5rem',
                background: days === opt.days ? 'rgba(88,166,255,0.2)' : 'transparent',
                border: days === opt.days ? '1px solid #58a6ff' : '1px solid rgba(255,255,255,0.1)',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '0.65rem',
                fontWeight: 600,
                color: days === opt.days ? '#58a6ff' : 'rgba(255,255,255,0.4)',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content — Overview is free, all other tabs require alliance_intel */}
      {currentTab === 'details' && <OverviewView allianceId={data.alliance_id} days={days} data={data} />}
      {currentTab === 'hunting' && (
        <ModuleGate module="alliance_intel">
          <HuntingView allianceId={data.alliance_id} allianceName={alliance_info.name} />
        </ModuleGate>
      )}
      {currentTab === 'offensive' && (
        <ModuleGate module="alliance_intel">
          <OffensiveView entityType="alliance" entityId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'defensive' && (
        <ModuleGate module="alliance_intel">
          <DefensiveView entityType="alliance" entityId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'capitals' && (
        <ModuleGate module="alliance_intel">
          <CapitalsView entityType="alliance" entityId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'geography' && (
        <ModuleGate module="alliance_intel">
          <GeographyView entityType="alliance" entityId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'livemap' && (
        <ModuleGate module="alliance_intel">
          <LiveMapView entityType="alliance" entityId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'wormhole' && (
        <ModuleGate module="alliance_intel">
          <WormholeView intel={wormholeIntel} loading={wormholeLoading} sovThreats={sovThreats} sovThreatsLoading={sovThreatsLoading} />
        </ModuleGate>
      )}
      {currentTab === 'capsuleer' && (
        <ModuleGate module="alliance_intel">
          <CapsuleersView allianceId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'corps' && (
        <ModuleGate module="alliance_intel">
          <CorpsView allianceId={data.alliance_id} days={days} />
        </ModuleGate>
      )}
    </div>
  );
}

export default AllianceDetail;
