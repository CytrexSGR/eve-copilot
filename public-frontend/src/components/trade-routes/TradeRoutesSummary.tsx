import { Link } from 'react-router-dom';
import { RefreshIndicator } from '../RefreshIndicator';
import type { TradeRoutes as TradeRoutesType } from '../../types/reports';
import { TIME_PERIODS, type TimePeriodValue } from './types';

interface TradeRoutesSummaryProps {
  report: TradeRoutesType;
  selectedMinutes: number;
  onTimeChange: (minutes: TimePeriodValue) => void;
  lastUpdated: Date;
}

export function TradeRoutesSummary({ report, selectedMinutes, onTimeChange, lastUpdated }: TradeRoutesSummaryProps) {
  return (
    <div style={{
      position: 'relative',
      background: 'linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 50%, #0d1520 100%)',
      borderRadius: '12px',
      padding: '2rem',
      marginBottom: '1.5rem',
      border: '1px solid rgba(0, 212, 255, 0.2)',
      overflow: 'hidden'
    }}>
      {/* Grid background */}
      <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: `
          linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px',
        pointerEvents: 'none'
      }} />

      {/* Glowing accent */}
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: '300px',
        height: '300px',
        background: 'radial-gradient(circle at top right, rgba(0, 212, 255, 0.1) 0%, transparent 70%)',
        pointerEvents: 'none'
      }} />

      <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <h1 style={{
              margin: 0,
              fontSize: '1.75rem',
              fontWeight: 800,
              background: 'linear-gradient(135deg, #fff 0%, #00d4ff 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '0.05em',
              textTransform: 'uppercase'
            }}>
              Trade Route Intelligence
            </h1>
          </div>
          <p style={{ margin: 0, color: 'rgba(255,255,255,0.5)', fontSize: '0.875rem' }}>
            Real-time danger assessment for major trade corridors
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Time Period Selector */}
          <div style={{
            display: 'flex',
            gap: '0.25rem',
            padding: '0.25rem',
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.1)'
          }}>
            {TIME_PERIODS.map(period => (
              <button
                key={period.value}
                onClick={() => onTimeChange(period.value)}
                style={{
                  padding: '0.4rem 0.75rem',
                  background: selectedMinutes === period.value
                    ? 'linear-gradient(135deg, #00d4ff 0%, #0088cc 100%)'
                    : 'transparent',
                  color: selectedMinutes === period.value ? '#000' : 'rgba(255,255,255,0.6)',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {period.label}
              </button>
            ))}
          </div>
          <Link
            to="/"
            style={{
              padding: '0.4rem 0.75rem',
              background: 'rgba(255,255,255,0.1)',
              color: 'rgba(255,255,255,0.7)',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '0.75rem',
              fontWeight: 600,
              border: '1px solid rgba(255,255,255,0.1)'
            }}
          >
            Back
          </Link>
          <RefreshIndicator lastUpdated={lastUpdated} autoRefreshSeconds={60} />
        </div>
      </div>

      {/* Stats Row */}
      <div style={{
        position: 'relative',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '1rem',
        marginTop: '1.5rem'
      }}>
        <div style={{
          padding: '1rem',
          background: 'rgba(0, 212, 255, 0.1)',
          borderRadius: '8px',
          border: '1px solid rgba(0, 212, 255, 0.2)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Routes Analyzed
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#00d4ff', fontFamily: 'monospace' }}>
            {report.global.total_routes}
          </div>
        </div>
        <div style={{
          padding: '1rem',
          background: 'rgba(255, 68, 68, 0.1)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 68, 68, 0.2)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Dangerous
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
            {report.global.dangerous_routes}
          </div>
        </div>
        <div style={{
          padding: '1rem',
          background: 'rgba(255, 136, 0, 0.1)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 136, 0, 0.2)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Gate Camps
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ff8800', fontFamily: 'monospace' }}>
            {report.global.gate_camps_detected}
          </div>
        </div>
        <div style={{
          padding: '1rem',
          background: 'rgba(255, 204, 0, 0.1)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 204, 0, 0.2)',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Avg Danger
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
            {report.global.avg_danger_score.toFixed(1)}
          </div>
        </div>
      </div>
    </div>
  );
}
