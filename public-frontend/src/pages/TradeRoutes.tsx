import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { reportsApi } from '../services/api';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type { TradeRoutes as TradeRoutesType } from '../types/reports';
import {
  SystemTooltip,
  TradeRoutesSummary,
  TradeRouteCard,
  type SystemTooltipData,
  type RouteSystem,
  type TimePeriodValue,
} from '../components/trade-routes';

export function TradeRoutes() {
  const [report, setReport] = useState<TradeRoutesType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [expandedRoute, setExpandedRoute] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<SystemTooltipData | null>(null);
  const [selectedMinutes, setSelectedMinutes] = useState<TimePeriodValue>(1440);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchReport = async (minutes: number = selectedMinutes) => {
    try {
      setError(null);
      setLoading(true);
      const data = await reportsApi.getTradeRoutes(minutes);
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load trade routes report');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(selectedMinutes);
  }, [selectedMinutes]);

  const handleTimeChange = (minutes: TimePeriodValue) => {
    setSelectedMinutes(minutes);
  };

  useAutoRefresh(() => fetchReport(selectedMinutes), 60);

  const handleSystemHover = (
    e: React.MouseEvent,
    system: RouteSystem
  ) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      system,
      x: rect.left + rect.width / 2,
      y: rect.top - 10
    });
  };

  const handleSystemLeave = () => {
    setTooltip(null);
  };

  const handleBattleClick = (battleId: number) => {
    navigate(`/battle/${battleId}`);
  };

  const handleRouteToggle = (routeKey: string) => {
    setExpandedRoute(expandedRoute === routeKey ? null : routeKey);
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem' }}>
        <div className="skeleton" style={{ height: '200px', marginBottom: '1rem', borderRadius: '12px' }} />
        <div className="skeleton" style={{ height: '400px', borderRadius: '12px' }} />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '2rem',
        background: 'rgba(255, 68, 68, 0.1)',
        border: '1px solid rgba(255, 68, 68, 0.3)',
        borderRadius: '12px',
        color: '#ff4444',
        textAlign: 'center'
      }}>
        <h2>Error Loading Data</h2>
        <p>{error}</p>
        <button
          onClick={() => fetchReport()}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            background: '#ff4444',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div>
      {/* System Tooltip */}
      {tooltip && (
        <SystemTooltip
          ref={tooltipRef}
          tooltip={tooltip}
          selectedMinutes={selectedMinutes}
        />
      )}

      {/* Hero Header */}
      <TradeRoutesSummary
        report={report}
        selectedMinutes={selectedMinutes}
        onTimeChange={handleTimeChange}
        lastUpdated={lastUpdated}
      />

      {/* Route Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {report.routes.map((route) => {
          const routeKey = `${route.origin_system}-${route.destination_system}`;
          return (
            <TradeRouteCard
              key={routeKey}
              route={route}
              isExpanded={expandedRoute === routeKey}
              onToggle={() => handleRouteToggle(routeKey)}
              onSystemHover={handleSystemHover}
              onSystemLeave={handleSystemLeave}
              onBattleClick={handleBattleClick}
              selectedMinutes={selectedMinutes}
            />
          );
        })}
      </div>
    </div>
  );
}
