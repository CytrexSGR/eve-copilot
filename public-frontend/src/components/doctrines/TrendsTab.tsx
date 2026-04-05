import { memo } from 'react';
import { TrendIndicator } from './shared';
import type { LiveOpsData } from '../../services/api/fingerprints';

interface TrendsTabProps {
  timeFilter: number;
  trends?: LiveOpsData['trends'];
  shipDistribution?: LiveOpsData['ship_distribution'];
  efficiencyRanking?: LiveOpsData['efficiency_ranking'];
  isLoading: boolean;
}

const SHIP_CLASS_COLORS: Record<string, string> = {
  'Cruiser': '#ff4444',
  'Battleship': '#ff8800',
  'Frigate': '#ffcc00',
  'Destroyer': '#00d4ff',
  'Battlecruiser': '#a855f7',
  'Logistics': '#58a6ff',
  'Stealth Bomber': '#00ff88',
  'Dreadnought': '#ff2222',
  'Carrier': '#d29922',
  'Force Auxiliary': '#3fb950',
  'Supercarrier': '#ff6699',
  'Titan': '#ffffff',
  'Capital': '#ff4444',
};

function getShipColor(shipClass: string): string {
  return SHIP_CLASS_COLORS[shipClass] || '#888888';
}

export const TrendsTab = memo(function TrendsTab({
  timeFilter,
  trends = [],
  shipDistribution = [],
  efficiencyRanking,
  isLoading
}: TrendsTabProps) {

  const timeLabel = timeFilter >= 1440
    ? `${Math.round(timeFilter / 1440)}D`
    : timeFilter >= 60
    ? `${Math.round(timeFilter / 60)}H`
    : `${timeFilter}M`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem'
      }}>
        {/* Column 1: Doctrine Trends */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(63, 185, 80, 0.2)',
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>📈</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#3fb950' }}>
              Doctrine Trends
            </h3>
            <span style={{
              marginLeft: 'auto',
              fontSize: '0.6rem',
              color: 'rgba(255,255,255,0.4)',
              padding: '0.2rem 0.4rem',
              background: 'rgba(63, 185, 80, 0.1)',
              borderRadius: '4px'
            }}>
              VS PREV {timeLabel}
            </span>
          </div>

          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading trends...
            </div>
          ) : trends.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No trend data available
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {trends.map((trend) => {
                const color = trend.change_percent > 5 ? '#00ff88' : trend.change_percent < -5 ? '#ff4444' : '#ffcc00';
                return (
                  <div
                    key={trend.ship_class}
                    style={{
                      padding: '0.5rem 0.75rem',
                      background: `${color}08`,
                      borderRadius: '6px',
                      borderLeft: `3px solid ${color}`
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 600 }}>
                        {trend.ship_class}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                        {trend.current_activity} / {trend.previous_activity}
                      </span>
                    </div>
                    <TrendIndicator change={trend.change_percent} label={timeLabel} />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Column 2: Ship-Typ Verteilung */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(0, 212, 255, 0.2)',
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>🚀</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00d4ff' }}>
              Ship-Typ Verteilung
            </h3>
          </div>

          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading distribution...
            </div>
          ) : shipDistribution.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No distribution data available
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {shipDistribution.map((ship) => {
                const color = getShipColor(ship.ship_class);
                return (
                  <div key={ship.ship_class}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span style={{ fontSize: '0.8rem', color: '#fff', fontWeight: 600 }}>
                        {ship.ship_class}
                      </span>
                      <span style={{ fontSize: '0.75rem', color, fontFamily: 'monospace' }}>
                        {ship.percent}%
                      </span>
                    </div>
                    <div style={{
                      height: '8px',
                      background: 'rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${ship.percent}%`,
                        height: '100%',
                        background: color,
                        borderRadius: '4px'
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Column 3: Efficiency Ranking */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(210, 175, 34, 0.2)',
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>📊</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#d4af22' }}>
              Efficiency Ranking
            </h3>
          </div>

          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading rankings...
            </div>
          ) : !efficiencyRanking ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No efficiency data available
            </div>
          ) : (
            <>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#00ff88', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                  Top Performers
                </div>
                {efficiencyRanking.top.map((doc, idx) => (
                  <div
                    key={doc.ship_class}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0.35rem 0.5rem',
                      marginBottom: '0.25rem',
                      background: 'rgba(0, 255, 136, 0.05)',
                      borderRadius: '4px'
                    }}
                  >
                    <span style={{ fontSize: '0.7rem', color: '#00ff88', fontFamily: 'monospace', minWidth: '1.5rem' }}>
                      #{idx + 1}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#fff', flex: 1 }}>
                      {doc.ship_class}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace', marginRight: '0.5rem' }}>
                      {doc.kills}K/{doc.losses}L
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#00ff88', fontFamily: 'monospace', fontWeight: 700 }}>
                      {doc.efficiency}%
                    </span>
                  </div>
                ))}
              </div>

              {efficiencyRanking.bottom.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#ff4444', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                    Worst Performers
                  </div>
                  {efficiencyRanking.bottom.map((doc, idx) => (
                    <div
                      key={doc.ship_class}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0.35rem 0.5rem',
                        marginBottom: '0.25rem',
                        background: 'rgba(255, 68, 68, 0.05)',
                        borderRadius: '4px'
                      }}
                    >
                      <span style={{ fontSize: '0.7rem', color: '#ff4444', fontFamily: 'monospace', minWidth: '1.5rem' }}>
                        #{idx + 1}
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#fff', flex: 1 }}>
                        {doc.ship_class}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace', marginRight: '0.5rem' }}>
                        {doc.kills}K/{doc.losses}L
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 700 }}>
                        {doc.efficiency}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
});
