/**
 * Corporation Detail Page
 *
 * Comprehensive intelligence view for individual corporations with 8 tabs:
 * - Overview: Complete overview (stats, ships, regions)
 * - Offensive: Kill intelligence (victims, high-value kills)
 * - Defensive: Loss analysis (threats, vulnerabilities)
 * - Capitals: Capital fleet strength
 * - Pilots: Member statistics
 * - Geography: Operating areas
 * - Activity: Timeline and trends
 * - Hunting: Intelligence command perspective (where/when to find them)
 */

import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { corpApi } from '../services/corporationApi';
import type { CorporationBasicInfo } from '../types/corporation';
import { formatISKCompact } from '../utils/format';
import { ModuleGate } from '../components/ModuleGate';
import { AllianceLink } from '../components/AllianceLink';

// Tab components
import {
  OverviewView,
  HuntingView,
  PilotsView,
  CorporationWormholeView,
} from '../components/corporation';
import { OffensiveView } from '../components/shared/OffensiveView';
import { DefensiveView } from '../components/shared/DefensiveView';
import { CapitalsView } from '../components/shared/CapitalsView';
import { GeographyView } from '../components/shared/GeographyView';
import { LiveMapView } from '../components/shared/LiveMapView';

type TabType = 'overview' | 'offensive' | 'defensive' | 'capitals' | 'pilots' | 'geography' | 'livemap' | 'wormhole' | 'hunting';

const TABS = [
  { id: 'overview' as const, label: 'Overview', icon: '📊' },
  { id: 'offensive' as const, label: 'Offensive', icon: '⚔️' },
  { id: 'defensive' as const, label: 'Defensive', icon: '🛡️' },
  { id: 'capitals' as const, label: 'Capitals', icon: '🚀' },
  { id: 'pilots' as const, label: 'Pilots', icon: '👥' },
  { id: 'geography' as const, label: 'Geography', icon: '🌍' },
  { id: 'livemap' as const, label: 'Live Map', icon: '🗺️' },
  { id: 'wormhole' as const, label: 'Wormhole', icon: '🌀' },
  { id: 'hunting' as const, label: 'Hunting', icon: '🎯' },
];

const TIME_OPTIONS = [
  { label: '7D', days: 7 },
  { label: '14D', days: 14 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
];

export function CorporationDetail() {
  const { corpId } = useParams<{ corpId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<CorporationBasicInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  const currentTab = (searchParams.get('tab') as TabType) || 'overview';

  useEffect(() => {
    if (!corpId) return;
    setLoading(true);
    setError(null);
    corpApi
      .getBasicInfo(parseInt(corpId), days)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [corpId, days]);

  const setTab = (tab: TabType) => {
    setSearchParams({ tab });
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e' }}>
        Loading corporation intelligence...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#f85149' }}>
        Error: {error || 'Corporation not found'}
      </div>
    );
  }

  // Threat level based on ISK efficiency
  const threatLevel = data.isk_efficiency < 40 ? 'CRITICAL' : data.isk_efficiency < 50 ? 'HIGH' : data.isk_efficiency < 60 ? 'MEDIUM' : 'LOW';
  const threatColor = threatLevel === 'CRITICAL' ? '#ff0000' : threatLevel === 'HIGH' ? '#ff6600' : threatLevel === 'MEDIUM' ? '#ffcc00' : '#3fb950';

  return (
    <div style={{ padding: '0.5rem', zoom: 1.1 }}>
      {/* HEADER BOX - Alliance Style */}
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
            src={`https://images.evetech.net/corporations/${data.corporation_id}/logo?size=64`}
            alt=""
            style={{ width: 40, height: 40, borderRadius: 6 }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
              {data.corporation_name}
            </h1>
            {data.ticker && (
              <span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 400, fontSize: '1rem' }}>
                [{data.ticker}]
              </span>
            )}
          </div>
          {data.alliance_id && data.alliance_name && (
            <div style={{ marginLeft: '0.25rem', paddingLeft: '0.75rem', borderLeft: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center' }}>
              <AllianceLink
                allianceId={data.alliance_id}
                name={data.alliance_name}
                showLogo
                logoSize={28}
                style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', gap: '0.4rem' }}
              />
            </div>
          )}

          {/* Inline Stats - ISK & Kill Metrics */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginLeft: 'auto' }}>
            {/* ISK Metrics */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>ISK</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: data.net_isk >= 0 ? '#3fb950' : '#f85149', fontFamily: 'monospace' }}>
                {data.net_isk >= 0 ? '+' : ''}{formatISKCompact(data.net_isk)}
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>•</span>
              <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}>
                {formatISKCompact(data.isk_destroyed)}/<span style={{ color: 'rgba(255,255,255,0.4)' }}>{formatISKCompact(data.isk_lost)}</span>
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>•</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
                {data.isk_efficiency.toFixed(1)}%
              </span>
            </div>

            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.2)' }}>|</span>

            {/* Kill Metrics */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Kills</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: data.kill_balance >= 0 ? '#3fb950' : '#f85149', fontFamily: 'monospace' }}>
                {data.kill_balance >= 0 ? '+' : ''}{data.kill_balance}
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>•</span>
              <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}>
                {data.kills.toLocaleString()}/<span style={{ color: 'rgba(255,255,255,0.4)' }}>{data.deaths.toLocaleString()}</span>
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>•</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#58a6ff', fontFamily: 'monospace' }}>
                {data.kill_efficiency.toFixed(1)}%
              </span>
            </div>

            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.2)' }}>|</span>

            {/* Status Badge */}
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
                <div style={{ width: `${data.isk_efficiency}%`, height: '100%', background: threatColor }} />
              </div>
            </div>
          </div>

          {/* zKill Link */}
          <a
            href={`https://zkillboard.com/corporation/${data.corporation_id}/`}
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

        {/* Sub-header Row: Intel + Peak + Trend + Timeframe */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>📊</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)' }}>Corporation Intel</span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              Peak <span style={{ color: '#ffcc00', fontWeight: 600 }}>{data.peak_hour}:00</span>
            </span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>|</span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
              Trend <span style={{ color: data.trend_pct >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                {data.trend_pct >= 0 ? '↑' : '↓'}{Math.abs(data.trend_pct).toFixed(1)}%
              </span>
            </span>
          </div>
          <div style={{ flex: 1 }} />
          {/* Timeframe Switcher */}
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            {TIME_OPTIONS.map((option) => (
              <button
                key={option.days}
                onClick={() => setDays(option.days)}
                style={{
                  padding: '0.15rem 0.4rem',
                  background: days === option.days ? 'rgba(88,166,255,0.2)' : 'rgba(0,0,0,0.2)',
                  border: days === option.days ? '1px solid #58a6ff' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '3px',
                  fontSize: '0.6rem',
                  cursor: 'pointer',
                  color: days === option.days ? '#58a6ff' : '#8b949e',
                  fontWeight: days === option.days ? 600 : 400,
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* TAB NAVIGATION */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            style={{
              padding: '0.5rem 0.75rem',
              background: currentTab === tab.id ? 'rgba(88,166,255,0.2)' : 'rgba(0,0,0,0.3)',
              border: currentTab === tab.id ? '1px solid #58a6ff' : '1px solid rgba(255,255,255,0.1)',
              borderRadius: '6px',
              fontSize: '0.8rem',
              cursor: 'pointer',
              color: '#c9d1d9',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT — Overview is free, all other tabs require corp_intel */}
      {currentTab === 'overview' && <OverviewView corpId={data.corporation_id} days={days} />}
      {currentTab === 'offensive' && (
        <ModuleGate module="corp_intel">
          <OffensiveView entityType="corporation" entityId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'defensive' && (
        <ModuleGate module="corp_intel">
          <DefensiveView entityType="corporation" entityId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'capitals' && (
        <ModuleGate module="corp_intel">
          <CapitalsView entityType="corporation" entityId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'pilots' && (
        <ModuleGate module="corp_intel">
          <PilotsView corpId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'geography' && (
        <ModuleGate module="corp_intel">
          <GeographyView entityType="corporation" entityId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'livemap' && (
        <ModuleGate module="corp_intel">
          <LiveMapView entityType="corporation" entityId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'wormhole' && (
        <ModuleGate module="corp_intel">
          <CorporationWormholeView corpId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
      {currentTab === 'hunting' && (
        <ModuleGate module="corp_intel">
          <HuntingView corpId={data.corporation_id} days={days} />
        </ModuleGate>
      )}
    </div>
  );
}

