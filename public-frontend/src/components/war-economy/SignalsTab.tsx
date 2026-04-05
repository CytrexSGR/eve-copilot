import { TRADE_HUBS, ISOTOPE_INFO, ANOMALY_THRESHOLDS } from '../../constants/warEconomy';
import { ConfidenceBadge } from './ConfidenceBadge';
import { IsotopeSparkline } from '../Sparkline';
import { formatHoursAgo } from '../../utils/format';
import type {
  FuelTrendsResponse,
  FuelTrend,
  ManipulationAlertsResponse,
  ManipulationAlert,
  SupercapTimersResponse,
  SupercapTimer
} from '../../types/reports';
import type { CapitalAlliancesResponse } from '../../services/api';

interface SignalsTabProps {
  selectedRegion: number;
  onRegionChange: (region: number) => void;
  fuelTrends: FuelTrendsResponse | null;
  manipulationAlerts: ManipulationAlertsResponse | null;
  supercapTimers: SupercapTimersResponse | null;
  capitalAlliances: CapitalAlliancesResponse | null;
  expandedAlliances: Set<number>;
  onToggleAlliance: (id: number) => void;
  loading: boolean;
}

export function SignalsTab({
  selectedRegion,
  onRegionChange,
  fuelTrends,
  manipulationAlerts,
  supercapTimers,
  capitalAlliances,
  expandedAlliances,
  onToggleAlliance,
  loading
}: SignalsTabProps) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
      borderRadius: '12px',
      border: '1px solid rgba(100, 150, 255, 0.1)',
      padding: '1.5rem'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.25rem' }}>📈</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ffcc00' }}>Market Signals</h2>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', margin: 0 }}>
              Fuel anomalies, manipulation detection, supercap tracking
            </p>
          </div>
        </div>
        <select
          id="region-select"
          name="region-select"
          value={selectedRegion}
          onChange={(e) => onRegionChange(Number(e.target.value))}
          style={{
            padding: '0.5rem 1rem',
            background: 'rgba(0,0,0,0.3)',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '6px',
            fontSize: '0.8rem',
            cursor: 'pointer'
          }}
        >
          {TRADE_HUBS.map(hub => (
            <option key={hub.id} value={hub.id}>{hub.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: '300px' }} />
      ) : (
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          <FuelTrendsSection
            fuelTrends={fuelTrends}
            capitalAlliances={capitalAlliances}
            expandedAlliances={expandedAlliances}
            onToggleAlliance={onToggleAlliance}
          />
          <ManipulationAlertsSection alerts={manipulationAlerts} selectedRegion={selectedRegion} />
          <SupercapTimersSection timers={supercapTimers} />
        </div>
      )}
    </div>
  );
}

interface FuelTrendsSectionProps {
  fuelTrends: FuelTrendsResponse | null;
  capitalAlliances: CapitalAlliancesResponse | null;
  expandedAlliances: Set<number>;
  onToggleAlliance: (id: number) => void;
}

function FuelTrendsSection({ fuelTrends, capitalAlliances, expandedAlliances, onToggleAlliance }: FuelTrendsSectionProps) {
  return (
    <div style={{
      padding: '1.5rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '10px',
      border: '1px solid rgba(168,85,247,0.2)',
      borderLeft: '3px solid #a855f7'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <span style={{ fontSize: '1.1rem' }}>⛽</span>
        <h3 style={{ color: '#a855f7', margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Isotope Market Trends</h3>
      </div>
      <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', marginBottom: '1rem' }}>
        Large isotope purchases may indicate capital ship movements
      </p>

      {fuelTrends && fuelTrends.trends.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {fuelTrends.trends.map((trend: FuelTrend) => (
            <IsotopeTrendCard
              key={trend.isotope_id}
              trend={trend}
              capitalAlliances={capitalAlliances}
              expandedAlliances={expandedAlliances}
              onToggleAlliance={onToggleAlliance}
            />
          ))}
        </div>
      ) : (
        <p style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', padding: '2rem' }}>
          No fuel data available. Data collection in progress.
        </p>
      )}
    </div>
  );
}

function IsotopeTrendCard({
  trend,
  capitalAlliances,
  expandedAlliances,
  onToggleAlliance
}: {
  trend: FuelTrendsResponse['trends'][0];
  capitalAlliances: CapitalAlliancesResponse | null;
  expandedAlliances: Set<number>;
  onToggleAlliance: (id: number) => void;
}) {
  const latestSnapshot = trend.snapshots[0];
  const hasAnomaly = latestSnapshot?.anomaly;
  const isoInfo = ISOTOPE_INFO[trend.isotope_id] || { race: 'Unknown', color: '#888', capitals: '' };
  const delta = latestSnapshot?.delta_percent || 0;
  const gaugePercent = Math.min(100, Math.max(0, (delta / ANOMALY_THRESHOLDS.danger) * 100));
  const gaugeColor = delta >= ANOMALY_THRESHOLDS.danger ? '#ff4444' :
                     delta >= ANOMALY_THRESHOLDS.warning ? '#ffcc00' : '#00ff88';

  return (
    <div style={{
      padding: '1.25rem',
      background: hasAnomaly ? 'rgba(255, 68, 68, 0.15)' : 'rgba(0,0,0,0.2)',
      borderRadius: '10px',
      border: hasAnomaly ? '2px solid #ff4444' : '1px solid rgba(255,255,255,0.1)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Race color accent bar */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        height: '3px',
        background: isoInfo.color
      }} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div>
          <p style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.25rem', color: '#fff' }}>{trend.isotope_name}</p>
          <p style={{ fontSize: '0.75rem', color: isoInfo.color, fontWeight: 500, margin: 0 }}>
            {isoInfo.capitals}
          </p>
        </div>
        <span style={{
          padding: '0.25rem 0.5rem',
          background: isoInfo.color,
          color: 'white',
          borderRadius: '4px',
          fontSize: '0.7rem',
          fontWeight: 700,
          textTransform: 'uppercase'
        }}>
          {isoInfo.race}
        </span>
      </div>

      {latestSnapshot && (
        <>
          {/* Stats grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Volume</p>
              <p style={{ fontSize: '1rem', fontWeight: 600, color: '#fff', fontFamily: 'monospace', margin: 0 }}>{(latestSnapshot.volume / 1_000_000).toFixed(1)}M</p>
            </div>
            <div>
              <p style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Price</p>
              <p style={{ fontSize: '1rem', fontWeight: 600, color: '#fff', fontFamily: 'monospace', margin: 0 }}>{latestSnapshot.price.toLocaleString()} ISK</p>
            </div>
          </div>

          {/* Delta gauge */}
          <div style={{ marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>vs 7-day baseline</span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: gaugeColor, fontFamily: 'monospace' }}>
                {delta > 0 ? '+' : ''}{delta.toFixed(1)}%
              </span>
            </div>
            <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', position: 'relative' }}>
              <div style={{
                position: 'absolute',
                left: `${(ANOMALY_THRESHOLDS.warning / ANOMALY_THRESHOLDS.danger) * 100}%`,
                top: 0, bottom: 0,
                width: '2px',
                background: '#ffcc00',
                opacity: 0.5
              }} />
              <div style={{ width: `${gaugePercent}%`, height: '100%', background: gaugeColor, transition: 'width 0.3s ease' }} />
            </div>
          </div>

          {/* Sparkline */}
          {trend.snapshots.length > 1 && (
            <div style={{ marginTop: '0.75rem' }}>
              <p style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                7-Day Trend
              </p>
              <IsotopeSparkline snapshots={trend.snapshots} width={240} height={36} />
            </div>
          )}

          {/* Anomaly badge */}
          {hasAnomaly && (
            <div style={{
              marginTop: '0.75rem',
              padding: '0.5rem',
              background: 'rgba(255, 68, 68, 0.2)',
              borderRadius: '6px',
              textAlign: 'center'
            }}>
              <span style={{ fontSize: '0.8rem', color: '#ff4444', fontWeight: 700 }}>
                ⚠️ {latestSnapshot.severity.toUpperCase()} ANOMALY DETECTED
              </span>
            </div>
          )}

          {/* Capital Intelligence */}
          {(capitalAlliances?.by_isotope[trend.isotope_id]?.alliances?.length ?? 0) > 0 && (
            <CapitalIntelligenceSection
              isotope={trend.isotope_id}
              isoInfo={isoInfo}
              capitalAlliances={capitalAlliances}
              expandedAlliances={expandedAlliances}
              onToggleAlliance={onToggleAlliance}
            />
          )}
        </>
      )}
    </div>
  );
}

function CapitalIntelligenceSection({
  isotope,
  isoInfo,
  capitalAlliances,
  expandedAlliances,
  onToggleAlliance
}: {
  isotope: number;
  isoInfo: { race: string; color: string; capitals: string };
  capitalAlliances: CapitalAlliancesResponse | null;
  expandedAlliances: Set<number>;
  onToggleAlliance: (id: number) => void;
}) {
  const alliances = capitalAlliances?.by_isotope[isotope]?.alliances || [];

  return (
    <div style={{
      marginTop: '0.75rem',
      padding: '0.75rem',
      background: 'rgba(0, 0, 0, 0.2)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.1)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <p style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', margin: 0 }}>
          Capital Intelligence ({isoInfo.race})
        </p>
        {alliances[0]?.confidence_score !== undefined && (
          <ConfidenceBadge score={alliances[0].confidence_score} />
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {alliances.slice(0, 5).map(alliance => (
          <AllianceRow
            key={alliance.alliance_id}
            alliance={alliance}
            isoInfo={isoInfo}
            isExpanded={expandedAlliances.has(alliance.alliance_id)}
            onToggle={() => onToggleAlliance(alliance.alliance_id)}
          />
        ))}
      </div>

      <p style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.5rem', marginBottom: 0 }}>
        Based on {capitalAlliances?.days_analyzed ?? 30}-day capital engagements
      </p>
    </div>
  );
}

function AllianceRow({
  alliance,
  isoInfo,
  isExpanded,
  onToggle
}: {
  alliance: CapitalAlliancesResponse['by_isotope'][number]['alliances'][0];
  isoInfo: { race: string; color: string; capitals: string };
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem',
          background: isExpanded ? 'rgba(255,255,255,0.08)' : 'transparent',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          color: '#fff',
          fontSize: '0.8rem',
          textAlign: 'left'
        }}
      >
        <span style={{ color: 'rgba(255,255,255,0.4)', width: '1rem' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
        <img
          src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=32`}
          alt=""
          style={{ width: 20, height: 20, borderRadius: 4 }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
        <span style={{ fontWeight: 600, color: isoInfo.color }}>
          [{alliance.ticker}]
        </span>
        <span style={{ flex: 1 }}>{alliance.capital_count} ops</span>
        {alliance.active_regions?.[0] && (
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', background: 'rgba(0,0,0,0.3)', padding: '0.15rem 0.4rem', borderRadius: '3px' }}>
            {alliance.active_regions[0].region}
          </span>
        )}
        {alliance.last_activity && (
          <span style={{
            fontSize: '0.65rem',
            color: alliance.active_regions?.[0]?.hours_ago !== undefined && alliance.active_regions[0].hours_ago < 12 ? '#00ff88' : 'rgba(255,255,255,0.4)'
          }}>
            {formatHoursAgo(alliance.active_regions?.[0]?.hours_ago ?? 999)}
          </span>
        )}
      </button>

      {isExpanded && (
        <div style={{
          marginLeft: '1.5rem',
          marginTop: '0.25rem',
          padding: '0.5rem',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '4px',
          borderLeft: `2px solid ${isoInfo.color}`
        }}>
          {alliance.top_corps?.length > 0 && (
            <div style={{ marginBottom: '0.5rem' }}>
              <p style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.25rem' }}>TOP CORPS</p>
              {alliance.top_corps.map(corp => (
                <div key={corp.corporation_id} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.75rem',
                  padding: '0.2rem 0',
                  borderBottom: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.7)'
                }}>
                  <span>{corp.corporation_name}</span>
                  <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                    {corp.engagements} ops, {corp.pilots} pilots
                  </span>
                </div>
              ))}
            </div>
          )}

          {alliance.active_regions?.length > 0 && (
            <div>
              <p style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.25rem' }}>ACTIVE REGIONS (7d)</p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {alliance.active_regions.map(region => (
                  <span
                    key={region.region}
                    style={{
                      padding: '0.2rem 0.4rem',
                      background: 'rgba(255,255,255,0.1)',
                      borderRadius: '3px',
                      fontSize: '0.7rem',
                      color: 'rgba(255,255,255,0.7)'
                    }}
                  >
                    {region.region} ({region.ops} ops)
                  </span>
                ))}
              </div>
            </div>
          )}

          <a
            href={`/alliance/${alliance.alliance_id}`}
            style={{
              display: 'block',
              marginTop: '0.5rem',
              fontSize: '0.7rem',
              color: '#00d4ff',
              textDecoration: 'none'
            }}
          >
            View full alliance intel →
          </a>
        </div>
      )}
    </div>
  );
}

function ManipulationAlertsSection({ alerts, selectedRegion }: { alerts: ManipulationAlertsResponse | null; selectedRegion: number }) {
  return (
    <div style={{
      padding: '1.5rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '10px',
      border: '1px solid rgba(255,136,0,0.2)',
      borderLeft: '3px solid #ff8800'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <span style={{ fontSize: '1.1rem' }}>📈</span>
        <h3 style={{ color: '#ff8800', margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Market Manipulation Alerts</h3>
      </div>
      <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', marginBottom: '1rem' }}>
        Unusual price/volume patterns detected via Z-score analysis
      </p>

      {alerts && alerts.count > 0 ? (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {alerts.alerts.map((alert: ManipulationAlert, idx: number) => {
            const severityColor = alert.severity === 'confirmed' ? '#ff4444' :
                                 alert.severity === 'probable' ? '#ff8800' : '#ffcc00';
            return (
              <div key={idx} style={{
                padding: '1rem',
                background: `${severityColor}10`,
                borderRadius: '8px',
                border: `1px solid ${severityColor}33`,
                borderLeft: `3px solid ${severityColor}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div>
                    <p style={{ fontWeight: 600, fontSize: '1rem', color: '#fff', marginBottom: '0.25rem' }}>{alert.type_name}</p>
                    <p style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', margin: 0 }}>
                      {alert.manipulation_type.replace('_', ' ')} | Z-score: <strong style={{ color: severityColor }}>{alert.z_score.toFixed(2)}</strong>
                    </p>
                  </div>
                  <span style={{
                    padding: '0.25rem 0.75rem',
                    background: `${severityColor}33`,
                    color: severityColor,
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    border: `1px solid ${severityColor}55`
                  }}>
                    {alert.severity.toUpperCase()}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.8rem' }}>
                  <div style={{ padding: '0.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                    <p style={{ color: 'rgba(255,255,255,0.4)', marginBottom: '0.25rem', fontSize: '0.7rem', textTransform: 'uppercase' }}>Price</p>
                    <p style={{ fontWeight: 600, color: '#fff', fontFamily: 'monospace', margin: 0 }}>
                      {alert.current_price.toLocaleString()} ISK
                    </p>
                    <p style={{ color: alert.price_change_percent >= 0 ? '#00ff88' : '#ff4444', fontSize: '0.75rem', margin: 0 }}>
                      {alert.price_change_percent >= 0 ? '+' : ''}{alert.price_change_percent.toFixed(1)}% vs baseline
                    </p>
                  </div>
                  <div style={{ padding: '0.5rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                    <p style={{ color: 'rgba(255,255,255,0.4)', marginBottom: '0.25rem', fontSize: '0.7rem', textTransform: 'uppercase' }}>Volume</p>
                    <p style={{ fontWeight: 600, color: '#fff', fontFamily: 'monospace', margin: 0 }}>
                      {alert.current_volume.toLocaleString()}
                    </p>
                    <p style={{ color: alert.volume_change_percent >= 0 ? '#00ff88' : '#ff4444', fontSize: '0.75rem', margin: 0 }}>
                      {alert.volume_change_percent >= 0 ? '+' : ''}{alert.volume_change_percent.toFixed(1)}% vs baseline
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{
          padding: '2rem',
          background: 'rgba(0, 255, 136, 0.05)',
          borderRadius: '8px',
          border: '1px dashed rgba(0, 255, 136, 0.3)'
        }}>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}>✓</span>
            <p style={{ color: '#00ff88', fontWeight: 600, marginBottom: '0.5rem' }}>Markets Stable</p>
            <p style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}>
              No manipulation patterns detected in {TRADE_HUBS.find(h => h.id === selectedRegion)?.name || 'this hub'}
            </p>
            <p style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)', marginTop: '0.5rem' }}>
              Monitoring top 100 traded items • Z-score threshold: 3.0
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function SupercapTimersSection({ timers }: { timers: SupercapTimersResponse | null }) {
  return (
    <div style={{
      padding: '1.5rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '10px',
      border: '1px solid rgba(255,68,68,0.2)',
      borderLeft: '3px solid #ff4444'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <span style={{ fontSize: '1.1rem' }}>🚀</span>
        <h3 style={{ color: '#ff4444', margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Supercapital Construction Timers</h3>
      </div>
      <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', marginBottom: '1rem' }}>
        Intel on enemy supercap construction - strike windows available
      </p>

      {timers && timers.count > 0 ? (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {timers.timers.map((timer: SupercapTimer) => {
            const alertColor = timer.alert_level === 'critical' ? '#ff4444' :
                              timer.alert_level === 'high' ? '#ff8800' :
                              timer.alert_level === 'medium' ? '#ffcc00' : '#00d4ff';
            return (
              <div key={timer.id} style={{
                padding: '1rem',
                background: `${alertColor}10`,
                borderRadius: '8px',
                border: `1px solid ${alertColor}33`,
                borderLeft: `3px solid ${alertColor}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start'
              }}>
                <div>
                  <p style={{ fontWeight: 700, color: '#fff', marginBottom: '0.25rem' }}>{timer.ship_name}</p>
                  <p style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', margin: 0 }}>
                    {timer.system_name} ({timer.region_name})
                    {timer.alliance_name && <span style={{ color: '#a855f7' }}> - {timer.alliance_name}</span>}
                  </p>
                  <p style={{ fontSize: '0.85rem', color: '#ffcc00', marginTop: '0.25rem', fontFamily: 'monospace', marginBottom: 0 }}>
                    {timer.days_remaining}d {timer.hours_remaining}h remaining
                  </p>
                  <p style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem', marginBottom: 0 }}>
                    {timer.strike_window}
                  </p>
                </div>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  background: `${alertColor}33`,
                  color: alertColor,
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  border: `1px solid ${alertColor}55`
                }}>
                  {timer.alert_level.toUpperCase()}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{
          padding: '2rem',
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '8px',
          border: '1px dashed rgba(255,255,255,0.1)'
        }}>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem', opacity: 0.5 }}>🔭</span>
            <p style={{ color: 'rgba(255,255,255,0.6)', fontWeight: 500, marginBottom: '0.5rem' }}>No Active Intel</p>
            <p style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', maxWidth: '400px', margin: '0 auto' }}>
              Supercap construction intel is gathered from scouts and spies. Report enemy Titan/Super builds to contribute.
            </p>
            <div style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: 'rgba(0,0,0,0.3)',
              borderRadius: '6px',
              display: 'inline-block',
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              <p style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', margin: 0 }}>
                💡 Tip: Watch for enemy Sotiyos with supercap rigs
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
