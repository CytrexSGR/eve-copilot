import { Link } from 'react-router-dom';
import { RouteCard } from './RouteCard';
import { MAX_ROUTES_DISPLAY, DANGER_COLORS } from '../../constants';
import type { TradeRoutes } from '../../types/reports';

interface TradeRouteSectionProps {
  tradeRoutes: TradeRoutes | null;
}

const ROUTE_COLOR = '#00d4ff';

export function TradeRouteSection({ tradeRoutes }: TradeRouteSectionProps) {
  if (!tradeRoutes || tradeRoutes.routes.length === 0) return null;

  const g = tradeRoutes.global;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: ROUTE_COLOR }} />
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: ROUTE_COLOR, textTransform: 'uppercase' }}>
          Trade Route Intel
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          24h
        </span>
        <div style={{ display: 'flex', gap: '0.6rem', marginLeft: 'auto', alignItems: 'center' }}>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
            <span style={{ color: ROUTE_COLOR, fontWeight: 600 }}>{g.total_routes}</span> routes
          </span>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
            <span style={{ color: DANGER_COLORS.CRITICAL, fontWeight: 600 }}>{g.dangerous_routes}</span> dangerous
          </span>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
            <span style={{ color: '#ff8800', fontWeight: 600 }}>{g.gate_camps_detected}</span> camps
          </span>
          <Link to="/trade-routes" style={{
            padding: '3px 8px',
            background: 'rgba(0,212,255,0.1)', color: ROUTE_COLOR,
            borderRadius: '3px', textDecoration: 'none',
            fontSize: '0.6rem', fontWeight: 600,
            border: '1px solid rgba(0,212,255,0.2)',
            textTransform: 'uppercase',
          }}>
            All Routes
          </Link>
        </div>
      </div>

      {/* Route grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {tradeRoutes.routes.slice(0, MAX_ROUTES_DISPLAY).map((route) => (
          <RouteCard
            key={`${route.origin_system}-${route.destination_system}`}
            route={route}
          />
        ))}
      </div>
    </div>
  );
}
