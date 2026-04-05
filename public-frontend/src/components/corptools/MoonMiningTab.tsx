import { useState, useEffect, useMemo } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StructurePerformance {
  observer_id: number;
  total_isk: number;
  isk_per_day: number;
  unique_miners: number;
  active_days: number;
}

interface OreBreakdown {
  rarity: string;
  isk_value: number;
  percentage: number;
}

interface Performance {
  corporation_id: number;
  period_days: number;
  total_isk_mined: number;
  isk_per_day: number;
  structure_performance: StructurePerformance[];
  ore_breakdown: OreBreakdown[];
}

interface Observer {
  observer_id: number;
  observer_type: string;
  last_updated: string | null;
}

interface Extraction {
  structure_id: number;
  moon_id: number;
  extraction_start_time: string;
  chunk_arrival_time: string;
  natural_decay_time: string;
  status: 'active' | 'ready' | 'expired';
}

interface TaxEntry {
  character_id: number;
  total_mined_quantity: number;
  total_isk_value: number;
  total_tax: number;
}

interface DashboardData {
  corporation_id: number;
  days: number;
  observers: Observer[];
  performance: Performance;
  extractions: Extraction[];
  tax_summary: TaxEntry[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatIsk(value: number): string {
  if (!isFinite(value)) return '0';
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}

function timeUntil(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff < 0) return 'Overdue';
  const h = Math.floor(diff / 3600000);
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  const m = Math.floor((diff % 3600000) / 60000);
  return `${h}h ${m}m`;
}

function hoursUntil(iso: string): number {
  return (new Date(iso).getTime() - Date.now()) / 3600000;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
}

function formatQuantity(value: number): string {
  if (!isFinite(value)) return '0';
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TIME_OPTIONS = [
  { days: 7, label: '7D' },
  { days: 14, label: '14D' },
  { days: 30, label: '30D' },
];

const RARITY_COLORS: Record<string, string> = {
  R64: '#d29922',
  R32: '#a855f7',
  R16: '#00d4ff',
  R8: '#3fb950',
  R4: '#8b949e',
  Unknown: '#555',
};

const STATUS_COLORS: Record<string, string> = {
  active: '#00d4ff',
  ready: '#3fb950',
  expired: '#8b949e',
};

const STATUS_ORDER: Record<string, number> = {
  active: 0,
  ready: 1,
  expired: 2,
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const kpiTileStyle: React.CSSProperties = {
  background: 'rgba(0,0,0,0.3)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '0.75rem 1rem',
  flex: '1 1 0',
  minWidth: '140px',
};

const kpiLabelStyle: React.CSSProperties = {
  fontSize: '0.7rem',
  color: 'rgba(255,255,255,0.4)',
  textTransform: 'uppercase',
  marginBottom: '0.25rem',
};

const kpiValueStyle: React.CSSProperties = {
  fontSize: '1.25rem',
  fontWeight: 700,
  fontFamily: 'monospace',
};

const sectionStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  overflow: 'hidden',
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: '0.9rem',
  fontWeight: 600,
  padding: '0.75rem 1rem',
  borderBottom: '1px solid var(--border-color)',
};

const tableHeaderStyle: React.CSSProperties = {
  fontSize: '0.7rem',
  fontWeight: 700,
  textTransform: 'uppercase',
  color: 'rgba(255,255,255,0.45)',
  padding: '0.6rem 1rem',
  borderBottom: '1px solid var(--border-color)',
};

const tableCellStyle: React.CSSProperties = {
  fontSize: '0.8rem',
  padding: '0.5rem 1rem',
  alignItems: 'center',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MoonMiningTab({ corpId }: { corpId: number }) {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/finance/mining/dashboard/${corpId}?days=${days}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => setDashboard(data))
      .catch(err => setError(err.message ?? 'Failed to load moon mining data'))
      .finally(() => setLoading(false));
  }, [corpId, days]);

  // Derived data
  const nextExtraction = useMemo(() => {
    if (!dashboard?.extractions?.length) return null;
    const active = dashboard.extractions
      .filter(e => e.status === 'active')
      .sort((a, b) => new Date(a.chunk_arrival_time).getTime() - new Date(b.chunk_arrival_time).getTime());
    return active.length > 0 ? active[0] : null;
  }, [dashboard]);

  const activeAndReadyCount = useMemo(() => {
    if (!dashboard?.extractions) return 0;
    return dashboard.extractions.filter(e => e.status === 'active' || e.status === 'ready').length;
  }, [dashboard]);

  const sortedStructures = useMemo(() => {
    if (!dashboard?.performance?.structure_performance) return [];
    return [...dashboard.performance.structure_performance].sort((a, b) => b.total_isk - a.total_isk);
  }, [dashboard]);

  const sortedMiners = useMemo(() => {
    if (!dashboard?.tax_summary) return [];
    return [...dashboard.tax_summary].sort((a, b) => b.total_isk_value - a.total_isk_value);
  }, [dashboard]);

  const sortedExtractions = useMemo(() => {
    if (!dashboard?.extractions) return [];
    return [...dashboard.extractions].sort((a, b) => {
      const orderDiff = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9);
      if (orderDiff !== 0) return orderDiff;
      return new Date(a.chunk_arrival_time).getTime() - new Date(b.chunk_arrival_time).getTime();
    });
  }, [dashboard]);

  // --- Loading state ---
  if (loading) {
    return (
      <div style={{
        padding: '3rem',
        textAlign: 'center',
        color: 'rgba(255,255,255,0.3)',
        fontSize: '0.85rem',
      }}>
        Loading moon mining data...
      </div>
    );
  }

  // --- Error state ---
  if (error) {
    return (
      <div style={{
        padding: '1.5rem',
        border: '1px solid #f85149',
        borderRadius: '8px',
        background: 'rgba(248,81,73,0.08)',
        color: '#f85149',
        fontSize: '0.85rem',
      }}>
        Failed to load moon mining data: {error}
      </div>
    );
  }

  // --- Empty state ---
  if (!dashboard || !dashboard.observers || dashboard.observers.length === 0) {
    return (
      <div style={{
        padding: '2rem',
        textAlign: 'center',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        color: 'var(--text-secondary)',
        fontSize: '0.85rem',
      }}>
        No mining observers found. Mining structures must be anchored and observed to appear here.
      </div>
    );
  }

  // --- Next extraction color ---
  const nextExtColor = (() => {
    if (!nextExtraction) return '#8b949e';
    const h = hoursUntil(nextExtraction.chunk_arrival_time);
    if (h < 0) return '#f85149';
    if (h < 24) return '#d29922';
    return '#00d4ff';
  })();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

      {/* Time Period Selector */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.4rem' }}>
        {TIME_OPTIONS.map(opt => (
          <button
            key={opt.days}
            onClick={() => setDays(opt.days)}
            style={{
              background: days === opt.days ? 'rgba(0,212,255,0.12)' : 'transparent',
              border: days === opt.days ? '1px solid rgba(0,212,255,0.4)' : '1px solid transparent',
              color: days === opt.days ? '#00d4ff' : 'var(--text-secondary)',
              padding: '0.35rem 0.75rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: days === opt.days ? 600 : 400,
              transition: 'all 0.2s',
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* KPI Strip */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={kpiTileStyle}>
          <div style={kpiLabelStyle}>Active Structures</div>
          <div style={{ ...kpiValueStyle, color: '#e6edf3' }}>
            {dashboard.observers.length}
          </div>
        </div>
        <div style={kpiTileStyle}>
          <div style={kpiLabelStyle}>Total ISK Mined</div>
          <div style={{ ...kpiValueStyle, color: '#3fb950' }}>
            {formatIsk(dashboard.performance?.total_isk_mined ?? 0)}
          </div>
        </div>
        <div style={kpiTileStyle}>
          <div style={kpiLabelStyle}>Next Extraction</div>
          <div style={{ ...kpiValueStyle, color: nextExtColor }}>
            {nextExtraction ? timeUntil(nextExtraction.chunk_arrival_time) : 'None'}
          </div>
        </div>
        <div style={kpiTileStyle}>
          <div style={kpiLabelStyle}>Extractions</div>
          <div style={{ ...kpiValueStyle, color: '#e6edf3' }}>
            {activeAndReadyCount}
          </div>
        </div>
      </div>

      {/* Structure Performance Table */}
      {sortedStructures.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>Structure Performance</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 100px 100px 80px 80px',
            gap: '0.5rem',
            ...tableHeaderStyle,
          }}>
            <span>Observer ID</span>
            <span style={{ textAlign: 'right' }}>ISK Total</span>
            <span style={{ textAlign: 'right' }}>ISK/Day</span>
            <span style={{ textAlign: 'right' }}>Miners</span>
            <span style={{ textAlign: 'right' }}>Active Days</span>
          </div>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {sortedStructures.map((sp, idx) => (
              <div
                key={sp.observer_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 100px 100px 80px 80px',
                  gap: '0.5rem',
                  ...tableCellStyle,
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}
              >
                <span style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>
                  {sp.observer_id}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#3fb950' }}>
                  {formatIsk(sp.total_isk)}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#d29922' }}>
                  {formatIsk(sp.isk_per_day)}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>
                  {sp.unique_miners}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>
                  {sp.active_days}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ore Breakdown by Rarity */}
      {dashboard.performance?.ore_breakdown?.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>Ore Breakdown by Rarity</div>
          <div style={{ padding: '0.75rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {dashboard.performance.ore_breakdown.map(ore => {
              const barColor = RARITY_COLORS[ore.rarity] ?? RARITY_COLORS.Unknown;
              const pct = isFinite(ore.percentage) ? ore.percentage : 0;
              return (
                <div key={ore.rarity} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {/* Rarity badge */}
                  <span style={{
                    display: 'inline-block',
                    minWidth: '48px',
                    textAlign: 'center',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    background: `${barColor}22`,
                    color: barColor,
                    border: `1px solid ${barColor}44`,
                  }}>
                    {ore.rarity}
                  </span>

                  {/* Bar */}
                  <div style={{
                    flex: 1,
                    height: '14px',
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: '3px',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${Math.min(pct, 100)}%`,
                      height: '100%',
                      background: barColor,
                      borderRadius: '3px',
                      transition: 'width 0.3s',
                    }} />
                  </div>

                  {/* ISK value */}
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '0.78rem',
                    color: 'rgba(255,255,255,0.7)',
                    minWidth: '70px',
                    textAlign: 'right',
                  }}>
                    {formatIsk(ore.isk_value)}
                  </span>

                  {/* Percentage */}
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '0.72rem',
                    color: 'rgba(255,255,255,0.45)',
                    minWidth: '45px',
                    textAlign: 'right',
                  }}>
                    {pct.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top Miners Table */}
      {sortedMiners.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>Top Miners</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 100px 100px 100px',
            gap: '0.5rem',
            ...tableHeaderStyle,
          }}>
            <span>Character ID</span>
            <span style={{ textAlign: 'right' }}>Total ISK</span>
            <span style={{ textAlign: 'right' }}>Quantity</span>
            <span style={{ textAlign: 'right' }}>Tax</span>
          </div>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {sortedMiners.map((miner, idx) => (
              <div
                key={miner.character_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 100px 100px 100px',
                  gap: '0.5rem',
                  ...tableCellStyle,
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}
              >
                <span style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>
                  {miner.character_id}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#3fb950' }}>
                  {formatIsk(miner.total_isk_value)}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>
                  {formatQuantity(miner.total_mined_quantity)}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#d29922' }}>
                  {formatIsk(miner.total_tax)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Extraction Calendar */}
      {sortedExtractions.length > 0 && (
        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>Extraction Calendar</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '80px 1fr 100px 130px 130px 100px',
            gap: '0.5rem',
            ...tableHeaderStyle,
          }}>
            <span>Status</span>
            <span>Structure / Moon</span>
            <span>Moon ID</span>
            <span>Arrival</span>
            <span>Decay</span>
            <span style={{ textAlign: 'right' }}>Remaining</span>
          </div>
          <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
            {sortedExtractions.map((ext, idx) => {
              const statusColor = STATUS_COLORS[ext.status] ?? '#8b949e';
              const h = hoursUntil(ext.chunk_arrival_time);
              const remainColor = ext.status === 'expired'
                ? '#8b949e'
                : h < 0 ? '#f85149'
                : h < 24 ? '#d29922'
                : '#00d4ff';

              return (
                <div
                  key={`${ext.structure_id}-${ext.moon_id}-${ext.extraction_start_time}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '80px 1fr 100px 130px 130px 100px',
                    gap: '0.5rem',
                    ...tableCellStyle,
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                  }}
                >
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    background: `${statusColor}22`,
                    color: statusColor,
                    textTransform: 'capitalize',
                    textAlign: 'center',
                  }}>
                    {ext.status}
                  </span>
                  <span style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)', fontSize: '0.78rem' }}>
                    {ext.structure_id}
                  </span>
                  <span style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)', fontSize: '0.78rem' }}>
                    {ext.moon_id}
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'rgba(255,255,255,0.5)' }}>
                    {formatDate(ext.chunk_arrival_time)}
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'rgba(255,255,255,0.5)' }}>
                    {formatDate(ext.natural_decay_time)}
                  </span>
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: remainColor,
                  }}>
                    {ext.status === 'expired' ? '--' : timeUntil(ext.chunk_arrival_time)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
