import { useState, useEffect } from 'react';
import { wormholeApi } from '../../services/api/wormhole';
import type {
  CommodityPrices,
  CommodityPrice,
  EvictionIntel,
  SupplyDisruption,
  MarketIndex,
  PriceHistory,
  PriceHistoryItem,
  PriceContext,
  PriceContextItem,
} from '../../types/wormhole';

// Simple SVG Sparkline component
function Sparkline({ data, width = 60, height = 20 }: { data: PriceHistoryItem | null; width?: number; height?: number }) {
  if (!data || data.data_points < 2) {
    return (
      <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>
        —
      </span>
    );
  }

  const prices = data.prices;
  const min = data.min_price;
  const max = data.max_price;
  const range = max - min || 1;

  // Normalize prices to 0-height range
  const points = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * width;
    const y = height - ((p - min) / range) * height;
    return `${x},${y}`;
  });

  // Determine color based on trend
  const first = prices[0];
  const last = prices[prices.length - 1];
  const color = last > first * 1.02 ? '#00ff88' : last < first * 0.98 ? '#ff4444' : '#888';

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Dot at end */}
      <circle
        cx={width}
        cy={height - ((last - min) / range) * height}
        r="2"
        fill={color}
      />
    </svg>
  );
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toLocaleString();
}

function formatVolume(value: number): string {
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
  return value.toLocaleString();
}

function TrendIndicator({ trend, size = 'normal' }: { trend: number; size?: 'normal' | 'large' }) {
  const isUp = trend > 2;
  const isDown = trend < -2;
  const color = isUp ? '#00ff88' : isDown ? '#ff4444' : '#888';
  const arrow = isUp ? '▲' : isDown ? '▼' : '―';
  const fontSize = size === 'large' ? '1.2rem' : '0.75rem';

  return (
    <span style={{ color, fontSize, fontWeight: 600 }}>
      {arrow} {Math.abs(trend).toFixed(1)}%
    </span>
  );
}

function CommodityRow({ item, context }: { item: CommodityPrice; context?: PriceContextItem | null }) {
  const tierColors = {
    high: '#ff4444',
    mid: '#ffcc00',
    low: '#888',
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 100px 40px 80px 80px 80px',
        alignItems: 'center',
        padding: '0.5rem 0',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        fontSize: '0.8rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: tierColors[item.tier],
          }}
        />
        <span style={{ color: '#fff' }}>{item.name}</span>
        {item.class && (
          <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
            ({item.class})
          </span>
        )}
      </div>
      <div style={{ color: '#00d4ff', textAlign: 'right' }}>
        {formatISK(item.sell_price)}
      </div>
      <div style={{ textAlign: 'center' }}>
        <PriceVsAvgBadge pctVsAvg={context?.pct_vs_30d} />
      </div>
      <div style={{ textAlign: 'right' }}>
        <TrendIndicator trend={item.trend_7d} />
      </div>
      <div style={{ color: 'rgba(255,255,255,0.5)', textAlign: 'right' }}>
        {item.spread.toFixed(1)}%
      </div>
      <div style={{ color: 'rgba(255,255,255,0.5)', textAlign: 'right' }}>
        {formatVolume(item.daily_volume)}
      </div>
    </div>
  );
}

function PriceVsAvgBadge({ pctVsAvg }: { pctVsAvg: number | undefined }) {
  if (pctVsAvg === undefined) {
    return <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.2)' }}>—</span>;
  }

  const isHigh = pctVsAvg > 5;
  const isLow = pctVsAvg < -5;
  const color = isHigh ? '#ff4444' : isLow ? '#00ff88' : 'rgba(255,255,255,0.4)';
  const label = isHigh ? 'HIGH' : isLow ? 'LOW' : 'AVG';

  return (
    <span
      style={{
        fontSize: '0.6rem',
        fontWeight: 600,
        padding: '0.1rem 0.3rem',
        background: `${color}22`,
        color: color,
        borderRadius: '2px',
      }}
      title={`${pctVsAvg >= 0 ? '+' : ''}${pctVsAvg.toFixed(1)}% vs 30d avg`}
    >
      {label}
    </span>
  );
}

function GasRow({ item, rank, history, context }: { item: CommodityPrice; rank: number; history?: PriceHistoryItem | null; context?: PriceContextItem | null }) {
  const tierColors = {
    high: '#ff4444',
    mid: '#ffcc00',
    low: '#888',
  };

  const rankColors = ['#ffd700', '#c0c0c0', '#cd7f32']; // Gold, Silver, Bronze

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '30px 1fr 70px 40px 80px 80px 65px 50px',
        alignItems: 'center',
        padding: '0.5rem 0',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        fontSize: '0.8rem',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <span
          style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            color: rank <= 3 ? rankColors[rank - 1] : 'rgba(255,255,255,0.3)',
          }}
        >
          #{rank}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: tierColors[item.tier],
          }}
        />
        <span style={{ color: '#fff' }}>{item.name}</span>
        {item.class && (
          <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
            ({item.class})
          </span>
        )}
      </div>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <Sparkline data={history || null} width={50} height={16} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <PriceVsAvgBadge pctVsAvg={context?.pct_vs_30d} />
      </div>
      <div style={{ color: '#00ff88', textAlign: 'right', fontWeight: 600 }}>
        {formatISK(item.isk_per_m3 || 0)}
      </div>
      <div style={{ color: '#00d4ff', textAlign: 'right' }}>
        {formatISK(item.sell_price)}
      </div>
      <div style={{ textAlign: 'right' }}>
        <TrendIndicator trend={item.trend_7d} />
      </div>
      <div style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'right', fontSize: '0.7rem' }}>
        {item.unit_volume}m³
      </div>
    </div>
  );
}

function GasTable({ items, priceHistory, priceContext }: { items: CommodityPrice[]; priceHistory: PriceHistory; priceContext: PriceContext }) {
  // Sort by ISK/m³ descending for harvest priority
  const sortedItems = [...items].sort((a, b) => (b.isk_per_m3 || 0) - (a.isk_per_m3 || 0));

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fff', margin: 0 }}>
          ⛽ FULLERITE GAS
        </h4>
        <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
          Sorted by ISK/m³ (harvest priority)
        </span>
      </div>

      {/* Header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '30px 1fr 70px 40px 80px 80px 65px 50px',
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.4)',
          textTransform: 'uppercase',
          padding: '0 0 0.5rem 0',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <span style={{ textAlign: 'center' }}>#</span>
        <span>Gas</span>
        <span style={{ textAlign: 'center' }}>7d</span>
        <span style={{ textAlign: 'center' }}>30d</span>
        <span style={{ textAlign: 'right' }}>ISK/m³</span>
        <span style={{ textAlign: 'right' }}>Price</span>
        <span style={{ textAlign: 'right' }}>Trend</span>
        <span style={{ textAlign: 'right' }}>Vol</span>
      </div>

      {/* Rows */}
      {sortedItems.map((item, idx) => (
        <GasRow
          key={item.type_id}
          item={item}
          rank={idx + 1}
          history={priceHistory[item.type_id]}
          context={priceContext[item.type_id]}
        />
      ))}

      {/* Summary */}
      <div
        style={{
          marginTop: '0.75rem',
          padding: '0.5rem',
          background: 'rgba(0,255,136,0.05)',
          borderRadius: '4px',
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.5)',
        }}
      >
        <span style={{ color: '#00ff88', fontWeight: 600 }}>ISK/m³</span> = Price ÷ Volume per unit •
        <span style={{ color: '#00ff88', marginLeft: '0.5rem' }}>LOW</span>/<span style={{ color: '#ff4444' }}>HIGH</span> = vs 30d average
      </div>
    </div>
  );
}

function BlueLootRow({ item, context }: { item: CommodityPrice; context?: PriceContextItem | null }) {
  const tierColors = {
    high: '#ff4444',
    mid: '#ffcc00',
    low: '#888',
  };

  const npcBuy = item.npc_buy || 0;
  const marketSell = item.sell_price;
  // ~5% fees (broker + tax) on market sales
  const marketNet = marketSell * 0.95;
  const sellToNpc = npcBuy > marketNet;
  const premium = npcBuy > 0 && marketSell > 0
    ? ((marketNet - npcBuy) / npcBuy * 100)
    : 0;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 90px 40px 90px 80px 100px',
        alignItems: 'center',
        padding: '0.5rem 0',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        fontSize: '0.8rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: tierColors[item.tier],
          }}
        />
        <span style={{ color: '#fff' }}>{item.name}</span>
      </div>
      <div style={{ color: '#00d4ff', textAlign: 'right' }}>
        {formatISK(marketSell)}
      </div>
      <div style={{ textAlign: 'center' }}>
        <PriceVsAvgBadge pctVsAvg={context?.pct_vs_30d} />
      </div>
      <div style={{ color: '#ffcc00', textAlign: 'right' }}>
        {formatISK(npcBuy)}
      </div>
      <div style={{ textAlign: 'right' }}>
        <TrendIndicator trend={item.trend_7d} />
      </div>
      <div style={{ textAlign: 'right' }}>
        {npcBuy > 0 && marketSell > 0 ? (
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              padding: '0.15rem 0.4rem',
              background: sellToNpc ? 'rgba(255,204,0,0.2)' : 'rgba(0,212,255,0.2)',
              color: sellToNpc ? '#ffcc00' : '#00d4ff',
              borderRadius: '3px',
            }}
          >
            {sellToNpc ? 'NPC' : `+${premium.toFixed(0)}%`}
          </span>
        ) : (
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>
        )}
      </div>
    </div>
  );
}

function BlueLootTable({ items, priceContext }: { items: CommodityPrice[]; priceContext: PriceContext }) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
      }}
    >
      <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fff', margin: '0 0 0.75rem 0' }}>
        💎 SLEEPER BLUE LOOT
      </h4>

      {/* Header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 90px 40px 90px 80px 100px',
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.4)',
          textTransform: 'uppercase',
          padding: '0 0 0.5rem 0',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <span>Item</span>
        <span style={{ textAlign: 'right' }}>Market</span>
        <span style={{ textAlign: 'center' }}>30d</span>
        <span style={{ textAlign: 'right' }}>NPC Buy</span>
        <span style={{ textAlign: 'right' }}>7d Trend</span>
        <span style={{ textAlign: 'right' }}>Sell To</span>
      </div>

      {/* Rows */}
      {items.map((item) => (
        <BlueLootRow key={item.type_id} item={item} context={priceContext[item.type_id]} />
      ))}

      {/* Legend */}
      <div
        style={{
          marginTop: '0.75rem',
          padding: '0.5rem',
          background: 'rgba(255,255,255,0.03)',
          borderRadius: '4px',
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.4)',
        }}
      >
        <span style={{ color: '#ffcc00' }}>NPC</span> = Sell to NPC (instant, no fees) •
        <span style={{ color: '#00d4ff', marginLeft: '0.5rem' }}>+X%</span> = Market premium after ~5% fees
      </div>
    </div>
  );
}

function CommodityTable({ title, icon, items, priceContext }: { title: string; icon: string; items: CommodityPrice[]; priceContext: PriceContext }) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
      }}
    >
      <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fff', margin: '0 0 0.75rem 0' }}>
        {icon} {title}
      </h4>

      {/* Header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 100px 40px 80px 80px 80px',
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.4)',
          textTransform: 'uppercase',
          padding: '0 0 0.5rem 0',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <span>Item</span>
        <span style={{ textAlign: 'right' }}>Price</span>
        <span style={{ textAlign: 'center' }}>30d</span>
        <span style={{ textAlign: 'right' }}>7d Trend</span>
        <span style={{ textAlign: 'right' }}>Spread</span>
        <span style={{ textAlign: 'right' }}>Volume</span>
      </div>

      {/* Rows */}
      {items.map((item) => (
        <CommodityRow key={item.type_id} item={item} context={priceContext[item.type_id]} />
      ))}
    </div>
  );
}

function EvictionCard({ eviction }: { eviction: EvictionIntel }) {
  const [expanded, setExpanded] = useState(false);

  const statusColors = {
    imminent: '#ff4444',
    expected: '#ffcc00',
    dumped: '#888',
  };

  const zkillSystemUrl = `https://zkillboard.com/system/${eviction.system_id}/`;
  const zkillCorpUrl = (corpId: number) => `https://zkillboard.com/corporation/${corpId}/`;
  const zkillAllianceUrl = (allianceId: number) => `https://zkillboard.com/alliance/${allianceId}/`;

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '6px',
        padding: '0.75rem',
        borderLeft: `3px solid ${statusColors[eviction.loot_status]}`,
        cursor: 'pointer',
        transition: 'background 0.2s',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header - Always visible */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: 600, color: '#fff' }}>{eviction.system_name}</span>
            <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)' }}>
              C{eviction.wh_class || '?'}
            </span>
            <a
              href={zkillSystemUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{ fontSize: '0.65rem', color: '#00d4ff', textDecoration: 'none' }}
            >
              [zkill]
            </a>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginTop: '0.25rem' }}>
            {eviction.total_kills} kills • {formatISK(eviction.isk_destroyed)} destroyed
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              padding: '0.15rem 0.4rem',
              background: `${statusColors[eviction.loot_status]}22`,
              color: statusColors[eviction.loot_status],
              borderRadius: '3px',
            }}
          >
            {eviction.loot_status.toUpperCase()}
          </span>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem' }}>
            ETA: {eviction.loot_eta}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div style={{ marginTop: '0.5rem', fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
        ⏱ {eviction.hours_ago.toFixed(0)}h ago
        <span style={{ marginLeft: '0.5rem', color: expanded ? '#00d4ff' : 'rgba(255,255,255,0.3)' }}>
          {expanded ? '▼ collapse' : '▶ expand'}
        </span>
      </div>

      {/* Victims - Collapsed view */}
      {!expanded && eviction.victims.length > 0 && (
        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem' }}>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Evicted: </span>
          <span style={{ color: '#ff8800' }}>
            {eviction.victims.slice(0, 3).map(v => v.name).join(', ')}
          </span>
        </div>
      )}

      {/* Expanded Detail View */}
      {expanded && (
        <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          {/* Victims with details */}
          {eviction.victims.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                Evicted Parties
              </div>
              {eviction.victims.map((victim, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.35rem 0',
                    borderBottom: idx < eviction.victims.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: '#ff8800', fontSize: '0.8rem' }}>{victim.name}</span>
                    {victim.alliance_id && (
                      <a
                        href={zkillAllianceUrl(victim.alliance_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        style={{ fontSize: '0.6rem', color: '#00d4ff', textDecoration: 'none' }}
                      >
                        [A]
                      </a>
                    )}
                    {victim.corporation_id && (
                      <a
                        href={zkillCorpUrl(victim.corporation_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        style={{ fontSize: '0.6rem', color: '#00d4ff', textDecoration: 'none' }}
                      >
                        [C]
                      </a>
                    )}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>
                    {victim.losses} losses • {formatISK(victim.isk_lost)}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Structures Lost */}
          {eviction.structures_lost && eviction.structures_lost.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                Structures Destroyed
              </div>
              {eviction.structures_lost.map((structure, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '0.75rem',
                    padding: '0.25rem 0',
                  }}
                >
                  <span style={{ color: '#ff4444' }}>
                    {structure.count}x {structure.type}
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                    {formatISK(structure.value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Estimated Loot */}
      <div
        style={{
          marginTop: '0.5rem',
          padding: '0.35rem 0.5rem',
          background: 'rgba(0,255,136,0.1)',
          borderRadius: '4px',
          fontSize: '0.75rem',
        }}
      >
        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Est. Loot: </span>
        <span style={{ color: '#00ff88', fontWeight: 600 }}>{formatISK(eviction.estimated_loot)}</span>
      </div>
    </div>
  );
}

function MarketIndexWidget({ index }: { index: MarketIndex | null }) {
  if (!index) return null;

  const statusColors = {
    bullish: '#00ff88',
    bearish: '#ff4444',
    stable: '#ffcc00',
  };

  return (
    <div
      style={{
        background: `linear-gradient(135deg, ${statusColors[index.market_status]}11, transparent)`,
        border: `1px solid ${statusColors[index.market_status]}33`,
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '1rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>
            J-Space Market Index
          </div>
          <div
            style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              color: statusColors[index.market_status],
              textTransform: 'uppercase',
            }}
          >
            {index.market_status}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>GAS</div>
              <TrendIndicator trend={index.gas_trend} size="large" />
            </div>
            <div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>LOOT</div>
              <TrendIndicator trend={index.loot_trend} size="large" />
            </div>
          </div>
        </div>
      </div>
      <div
        style={{
          marginTop: '0.75rem',
          padding: '0.5rem',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '4px',
          fontSize: '0.8rem',
          color: statusColors[index.market_status],
          fontWeight: 500,
        }}
      >
        {index.recommendation}
      </div>
    </div>
  );
}

function DisruptionAlert({ disruption }: { disruption: SupplyDisruption }) {
  const impactColors = {
    high: '#ff4444',
    medium: '#ffcc00',
    low: '#888',
  };

  return (
    <div
      style={{
        background: 'rgba(255,0,0,0.05)',
        border: '1px solid rgba(255,0,0,0.2)',
        borderRadius: '6px',
        padding: '0.75rem',
        marginBottom: '0.5rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontWeight: 600, color: '#fff' }}>{disruption.corporation_name}</span>
          {disruption.alliance_name !== 'No Alliance' && (
            <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginLeft: '0.5rem' }}>
              [{disruption.alliance_name}]
            </span>
          )}
        </div>
        <span
          style={{
            fontSize: '0.65rem',
            fontWeight: 600,
            padding: '0.15rem 0.4rem',
            background: `${impactColors[disruption.impact_level]}22`,
            color: impactColors[disruption.impact_level],
            borderRadius: '3px',
            textTransform: 'uppercase',
          }}
        >
          {disruption.impact_level} impact
        </span>
      </div>
      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginTop: '0.25rem' }}>
        {disruption.systems_affected} systems affected
      </div>
      <div style={{ marginTop: '0.5rem' }}>
        {disruption.predicted_effects.map((effect, i) => (
          <div key={i} style={{ fontSize: '0.7rem', color: '#ffcc00', marginTop: '0.15rem' }}>
            • {effect}
          </div>
        ))}
      </div>
    </div>
  );
}

export function MarketTab() {
  const [commodities, setCommodities] = useState<CommodityPrices | null>(null);
  const [evictions, setEvictions] = useState<EvictionIntel[]>([]);
  const [disruptions, setDisruptions] = useState<SupplyDisruption[]>([]);
  const [marketIndex, setMarketIndex] = useState<MarketIndex | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistory>({});
  const [priceContext, setPriceContext] = useState<PriceContext>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [commodityData, evictionData, disruptionData, indexData, historyData, contextData] = await Promise.all([
          wormholeApi.getCommodityPrices(),
          wormholeApi.getEvictionIntel(7),
          wormholeApi.getSupplyDisruptions(7),
          wormholeApi.getMarketIndex(),
          wormholeApi.getPriceHistory(7),
          wormholeApi.getPriceContext(),
        ]);
        setCommodities(commodityData);
        setEvictions(evictionData);
        setDisruptions(disruptionData);
        setMarketIndex(indexData);
        setPriceHistory(historyData);
        setPriceContext(contextData);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch market data:', err);
        setError('Failed to load market intelligence');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', padding: '3rem' }}>
        Loading market intelligence...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ color: '#ff4444', textAlign: 'center', padding: '3rem' }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ marginTop: '1rem' }}>
      {/* Market Index */}
      <MarketIndexWidget index={marketIndex} />

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
        {/* Left: Commodity Prices */}
        <div>
          {commodities && (
            <>
              <GasTable
                items={commodities.gas.filter(g => g.sell_price > 0)}
                priceHistory={priceHistory}
                priceContext={priceContext}
              />
              <BlueLootTable
                items={commodities.blue_loot.filter(l => l.sell_price > 0 || l.npc_buy)}
                priceContext={priceContext}
              />
              <CommodityTable
                title="HYBRID POLYMERS"
                icon="🧪"
                items={commodities.polymers.filter(p => p.sell_price > 0)}
                priceContext={priceContext}
              />
            </>
          )}
        </div>

        {/* Right: Intel */}
        <div>
          {/* Eviction Intel */}
          <div
            style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '8px',
              padding: '1rem',
              marginBottom: '1rem',
            }}
          >
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ff8800', margin: '0 0 0.75rem 0' }}>
              📦 LOOT DUMP TRACKER
            </h4>
            {evictions.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', padding: '1rem 0' }}>
                No major evictions in the last 7 days
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {evictions.slice(0, 5).map((e) => (
                  <EvictionCard key={e.battle_id} eviction={e} />
                ))}
              </div>
            )}
          </div>

          {/* Supply Disruptions */}
          {disruptions.length > 0 && (
            <div
              style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '8px',
                padding: '1rem',
              }}
            >
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ff4444', margin: '0 0 0.75rem 0' }}>
                ⚠️ SUPPLY DISRUPTIONS
              </h4>
              {disruptions.slice(0, 3).map((d) => (
                <DisruptionAlert key={d.corporation_id} disruption={d} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
