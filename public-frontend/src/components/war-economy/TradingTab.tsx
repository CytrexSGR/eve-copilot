import { formatISK } from '../../utils/format';
import type { ExtendedHotItemsResponse, WarzoneRoutesResponse } from '../../types/reports';

interface TradingTabProps {
  extendedHotItems: ExtendedHotItemsResponse | null;
  warzoneRoutes: WarzoneRoutesResponse | null;
  expandedItem: number | null;
  expandedRoute: number | null;
  onExpandItem: (id: number | null) => void;
  onExpandRoute: (id: number | null) => void;
  loading: boolean;
}

export function TradingTab({
  extendedHotItems,
  warzoneRoutes,
  expandedItem,
  expandedRoute,
  onExpandItem,
  onExpandRoute,
  loading
}: TradingTabProps) {
  return (
    <>
      {/* Hero Stats - Separate Box */}
      <HeroStats extendedHotItems={extendedHotItems} warzoneRoutes={warzoneRoutes} />

      {/* 2-Column Layout */}
      {loading ? (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '8px',
          padding: '2rem',
          textAlign: 'center',
          color: 'rgba(255,255,255,0.4)',
          fontSize: '0.75rem'
        }}>
          Loading trading intelligence...
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.75rem'
        }}>
          <CombatDemandPanel
            items={extendedHotItems?.items || []}
            expandedItem={expandedItem}
            onExpandItem={onExpandItem}
          />
          <TradeRoutesPanel
            routes={warzoneRoutes?.routes || []}
            expandedRoute={expandedRoute}
            onExpandRoute={onExpandRoute}
          />
        </div>
      )}
    </>
  );
}

// ============================================================
// HERO STATS - Separate Compact Box
// ============================================================

function HeroStats({ extendedHotItems, warzoneRoutes }: {
  extendedHotItems: ExtendedHotItemsResponse | null;
  warzoneRoutes: WarzoneRoutesResponse | null;
}) {
  const bestRoute = warzoneRoutes?.routes?.length
    ? warzoneRoutes.routes.reduce((a, b) => a.isk_per_hour > b.isk_per_hour ? a : b)
    : null;

  return (
    <div style={{
      display: 'flex',
      gap: '0.75rem',
      marginBottom: '0.75rem'
    }}>
      {/* Combat Demand */}
      <StatBox
        icon="💰"
        label="Combat Demand"
        sublabel="24h"
        value={extendedHotItems ? formatISK(extendedHotItems.total_opportunity_value) : '—'}
        color="#00ff88"
      />

      {/* Active Warzones */}
      <StatBox
        icon="⚔️"
        label="Active Warzones"
        sublabel="50+ kills"
        value={String(warzoneRoutes?.warzone_count || 0)}
        color="#ff4444"
      />

      {/* Best ISK/Hour */}
      <StatBox
        icon="🚀"
        label="Best ISK/Hour"
        sublabel={bestRoute?.region_name || '—'}
        value={bestRoute ? formatISK(bestRoute.isk_per_hour) : '—'}
        color="#ffcc00"
      />

      {/* Top Item */}
      <StatBox
        icon="🔥"
        label="Top Item"
        sublabel={extendedHotItems?.items?.[0]?.name?.slice(0, 20) || '—'}
        value={extendedHotItems?.items?.[0] ? formatISK(extendedHotItems.items[0].opportunity_value) : '—'}
        color="#ff8800"
      />
    </div>
  );
}

function StatBox({ icon, label, sublabel, value, color }: {
  icon: string;
  label: string;
  sublabel: string;
  value: string;
  color: string;
}) {
  return (
    <div style={{
      flex: 1,
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: `3px solid ${color}`,
      padding: '0.5rem 0.6rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem'
    }}>
      <span style={{ fontSize: '1rem' }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
          {label}
        </div>
        <div style={{ fontSize: '1rem', fontWeight: 700, color, fontFamily: 'monospace' }}>
          {value}
        </div>
        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {sublabel}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// COMBAT DEMAND PANEL (Compact)
// ============================================================

interface CombatDemandPanelProps {
  items: ExtendedHotItemsResponse['items'];
  expandedItem: number | null;
  onExpandItem: (id: number | null) => void;
}

function CombatDemandPanel({ items, expandedItem, onExpandItem }: CombatDemandPanelProps) {
  const totalValue = items.reduce((sum, i) => sum + i.opportunity_value, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '400px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>🔥</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase' }}>
            Combat Demand
          </span>
          <span style={{ fontSize: '0.55rem', background: 'rgba(255,136,0,0.2)', padding: '0.1rem 0.3rem', borderRadius: '3px', color: '#ff8800' }}>
            24h
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem' }}>
          <span style={{ color: '#00ff88' }}>{formatISK(totalValue)}</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>{items.length} items</span>
        </div>
      </div>

      {/* Items List */}
      <div style={{ padding: '0.25rem', flex: 1, overflowY: 'auto' }}>
        {items.length === 0 ? (
          <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
            No hot items
          </div>
        ) : (
          items.map((item, idx) => (
            <ItemRow
              key={item.type_id}
              item={item}
              rank={idx + 1}
              isExpanded={expandedItem === item.type_id}
              onToggle={() => onExpandItem(expandedItem === item.type_id ? null : item.type_id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ItemRow({ item, rank, isExpanded, onToggle }: {
  item: ExtendedHotItemsResponse['items'][0];
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={{
      marginBottom: '0.15rem',
      background: 'rgba(255,136,0,0.05)',
      borderRadius: '4px',
      borderLeft: '2px solid #ff8800',
      overflow: 'hidden'
    }}>
      {/* Row */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.35rem 0.4rem',
          cursor: 'pointer',
        }}
      >
        {/* Rank */}
        <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#ff8800', fontFamily: 'monospace', minWidth: '18px' }}>
          #{rank}
        </span>

        {/* Item Name */}
        <span style={{
          flex: 1,
          fontSize: '0.7rem',
          fontWeight: 600,
          color: '#fff',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap'
        }}>
          {item.name}
        </span>

        {/* Quantity */}
        <span style={{ fontSize: '0.65rem', color: '#ff4444', fontFamily: 'monospace' }}>
          {item.quantity_destroyed}x
        </span>

        {/* Value */}
        <span style={{ fontSize: '0.65rem', color: '#00ff88', fontFamily: 'monospace', minWidth: '50px', textAlign: 'right' }}>
          {formatISK(item.opportunity_value)}
        </span>

        {/* Spread */}
        <span style={{
          fontSize: '0.55rem',
          color: item.spread_percent > 10 ? '#00ff88' : 'rgba(255,255,255,0.4)',
          fontFamily: 'monospace',
          minWidth: '35px',
          textAlign: 'right'
        }}>
          +{item.spread_percent}%
        </span>

        {/* Arrow */}
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div style={{
          padding: '0.4rem 0.5rem',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(0,0,0,0.2)',
          fontSize: '0.65rem'
        }}>
          {/* Arbitrage Info */}
          <div style={{ marginBottom: '0.4rem', color: 'rgba(255,255,255,0.6)' }}>
            Buy: <span style={{ color: '#00ff88' }}>{item.best_buy.hub}</span> {formatISK(item.best_buy.price)}
            <span style={{ color: 'rgba(255,255,255,0.3)' }}> → </span>
            Sell: <span style={{ color: '#ffcc00' }}>{item.best_sell.hub}</span> {formatISK(item.best_sell.price)}
          </div>

          {/* Two columns: Prices & Zones */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            {/* Regional Prices */}
            <div>
              <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)', marginBottom: '0.2rem', textTransform: 'uppercase' }}>
                Hub Prices
              </div>
              {Object.entries(item.regional_prices)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 4)
                .map(([hub, price]) => (
                  <div key={hub} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '0.1rem 0',
                    color: hub === item.best_buy.hub ? '#00ff88' :
                           hub === item.best_sell.hub ? '#ffcc00' : 'rgba(255,255,255,0.5)'
                  }}>
                    <span style={{ textTransform: 'capitalize' }}>
                      {hub === item.best_buy.hub && '▼'}{hub === item.best_sell.hub && '▲'} {hub}
                    </span>
                    <span style={{ fontFamily: 'monospace' }}>{formatISK(price)}</span>
                  </div>
                ))}
            </div>

            {/* Destruction Zones */}
            <div>
              <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)', marginBottom: '0.2rem', textTransform: 'uppercase' }}>
                Destruction Zones
              </div>
              {item.destruction_zones.slice(0, 3).map(zone => (
                <div key={zone.region_id} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.1rem 0',
                  color: 'rgba(255,255,255,0.5)'
                }}>
                  <span>{zone.region_name}</span>
                  <span style={{ color: '#ff4444', fontFamily: 'monospace' }}>{zone.percentage}%</span>
                </div>
              ))}
              <div style={{ color: item.trend_7d > 0 ? '#00ff88' : item.trend_7d < 0 ? '#ff4444' : 'rgba(255,255,255,0.4)', marginTop: '0.2rem' }}>
                7d: {item.trend_7d > 0 ? '↑' : item.trend_7d < 0 ? '↓' : '→'} {item.trend_7d > 0 ? '+' : ''}{item.trend_7d}%
              </div>
            </div>
          </div>

          {/* Suggestion */}
          {item.destruction_zones.length > 0 && item.spread_percent > 0 && (
            <div style={{
              marginTop: '0.4rem',
              padding: '0.3rem 0.4rem',
              background: 'rgba(0, 255, 136, 0.1)',
              borderRadius: '4px',
              borderLeft: '2px solid #00ff88',
              color: 'rgba(255,255,255,0.7)'
            }}>
              💡 {item.best_buy.hub} → {item.destruction_zones[0]?.region_name} <span style={{ color: '#00ff88' }}>+{item.spread_percent}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================
// TRADE ROUTES PANEL (Compact)
// ============================================================

interface TradeRoutesPanelProps {
  routes: WarzoneRoutesResponse['routes'];
  expandedRoute: number | null;
  onExpandRoute: (id: number | null) => void;
}

function TradeRoutesPanel({ routes, expandedRoute, onExpandRoute }: TradeRoutesPanelProps) {
  const totalProfit = routes.reduce((sum, r) => sum + r.estimated_profit, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '400px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>🚚</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00d4ff', textTransform: 'uppercase' }}>
            Warzone Routes
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem' }}>
          <span style={{ color: '#00ff88' }}>{formatISK(totalProfit)}</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>{routes.length} routes</span>
        </div>
      </div>

      {/* Routes List */}
      <div style={{ padding: '0.25rem', flex: 1, overflowY: 'auto' }}>
        {routes.length === 0 ? (
          <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
            No active warzones
          </div>
        ) : (
          routes.map((route) => (
            <RouteRow
              key={route.region_id}
              route={route}
              isExpanded={expandedRoute === route.region_id}
              onToggle={() => onExpandRoute(expandedRoute === route.region_id ? null : route.region_id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function RouteRow({ route, isExpanded, onToggle }: {
  route: WarzoneRoutesResponse['routes'][0];
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const routeColor = route.status_level === 'hellcamp' ? '#00d4ff' :
                     route.status_level === 'battle' ? '#ff8800' : '#ffcc00';
  const statusLabel = route.status_level === 'hellcamp' ? 'HELL' :
                      route.status_level === 'battle' ? 'BTL' : 'WAR';

  return (
    <div style={{
      marginBottom: '0.15rem',
      background: `${routeColor}08`,
      borderRadius: '4px',
      borderLeft: `2px solid ${routeColor}`,
      overflow: 'hidden'
    }}>
      {/* Row */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.35rem 0.4rem',
          cursor: 'pointer',
        }}
      >
        {/* Status Badge */}
        <span style={{ fontSize: '0.55rem', fontWeight: 700, color: routeColor, minWidth: '28px' }}>
          {statusLabel}
        </span>

        {/* Destination */}
        <span style={{
          flex: 1,
          fontSize: '0.7rem',
          fontWeight: 600,
          color: '#fff',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap'
        }}>
          {route.region_name}
        </span>

        {/* Jumps */}
        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
          {route.jumps_from_jita}j
        </span>

        {/* Kills */}
        <span style={{ fontSize: '0.6rem', color: '#ff4444', fontFamily: 'monospace' }}>
          {route.kills_24h}k
        </span>

        {/* Profit */}
        <span style={{ fontSize: '0.65rem', color: '#00ff88', fontFamily: 'monospace', minWidth: '50px', textAlign: 'right' }}>
          {formatISK(route.estimated_profit)}
        </span>

        {/* ISK/hr */}
        <span style={{ fontSize: '0.55rem', color: '#ffcc00', fontFamily: 'monospace', minWidth: '45px', textAlign: 'right' }}>
          {formatISK(route.isk_per_hour)}/h
        </span>

        {/* Arrow */}
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div style={{
          padding: '0.4rem 0.5rem',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(0,0,0,0.2)',
          fontSize: '0.65rem'
        }}>
          {/* Route Stats */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.4rem', color: 'rgba(255,255,255,0.6)' }}>
            <span>Cost: <span style={{ color: '#ffcc00' }}>{formatISK(route.total_buy_cost)}</span></span>
            <span>ROI: <span style={{ color: '#00ff88' }}>{route.roi_percent}%</span></span>
            <span>Items: <span style={{ color: '#00d4ff' }}>{route.cargo_items}</span></span>
          </div>

          {/* Cargo Table */}
          <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.35)', marginBottom: '0.2rem', textTransform: 'uppercase' }}>
            Cargo Manifest
          </div>
          <table style={{ width: '100%', fontSize: '0.6rem' }}>
            <tbody>
              {route.items.slice(0, 5).map(item => (
                <tr key={item.type_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '0.2rem 0', color: 'rgba(255,255,255,0.7)', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.name}
                  </td>
                  <td style={{ padding: '0.2rem 0', textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>
                    {item.suggested_quantity}x
                  </td>
                  <td style={{ padding: '0.2rem 0', textAlign: 'right', fontFamily: 'monospace', color: '#ffcc00' }}>
                    {formatISK(item.jita_price)}
                  </td>
                  <td style={{ padding: '0.2rem 0', textAlign: 'right', color: '#00ff88', fontFamily: 'monospace' }}>
                    +{item.markup_percent}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {route.items.length > 5 && (
            <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', marginTop: '0.2rem' }}>
              +{route.items.length - 5} more items...
            </div>
          )}

          {/* Status Badge */}
          <div style={{
            marginTop: '0.4rem',
            padding: '0.3rem 0.4rem',
            background: `${routeColor}15`,
            borderRadius: '4px',
            borderLeft: `2px solid ${routeColor}`,
            color: 'rgba(255,255,255,0.7)'
          }}>
            💡 <span style={{ color: routeColor, fontWeight: 700 }}>
              {route.status_level === 'hellcamp' ? 'HELLCAMP' : route.status_level === 'battle' ? 'ACTIVE BATTLE' : 'COMBAT ZONE'}
            </span> - {route.kills_24h} kills/24h
          </div>
        </div>
      )}
    </div>
  );
}
