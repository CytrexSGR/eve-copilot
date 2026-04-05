import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { warApi, reportsApi } from '../../services/api';
import type { Conflict } from '../../types/reports';
import { ConflictDashboard } from '../warfare/ConflictDashboard';
import { ActiveCombatZones } from '../battlefield/ActiveCombatZones';
import { TradeRouteThreats } from '../battlefield/TradeRouteThreats';
import { CapitalIntelSection } from '../battlefield/CapitalIntelSection';
import { DoctrinesSection } from '../battlefield/DoctrinesSection';

interface BattlefieldTabProps {
  timeframeMinutes: number;
}


interface HotSystem {
  solar_system_id: number;
  system_name: string;
  region_name: string;
  security_status: number;
  kill_count: number;
  total_value: number;
  capital_kills: number;
  last_kill_minutes_ago: number | null;
  threat_level: 'critical' | 'hot' | 'active' | 'low';
  sov_alliance_id: number | null;
  sov_alliance_name: string | null;
  sov_alliance_ticker: string | null;
}

interface TradeRoute {
  origin_system: string;
  destination_system: string;
  jumps: number;
  danger_score: number;
  total_kills: number;
  total_isk_destroyed: number;
  systems: Array<{
    system_id: number;
    system_name: string;
    security_status: number;
    danger_score: number;
    kills_24h: number;
    isk_destroyed_24h: number;
    is_gate_camp: boolean;
    battle_id?: number;
  }>;
}

export function BattlefieldTab({ timeframeMinutes }: BattlefieldTabProps) {
  const navigate = useNavigate();
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [conflictsLoading, setConflictsLoading] = useState(true);
  const [conflictsError, setConflictsError] = useState<string | null>(null);

  const [hotSystems, setHotSystems] = useState<HotSystem[]>([]);
  const [tradeRoutes, setTradeRoutes] = useState<TradeRoute[]>([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  const fetchConflicts = async (minutes: number) => {
    try {
      setConflictsError(null);
      setConflictsLoading(true);
      const data = await warApi.getConflicts(minutes);
      setConflicts(data.conflicts);
    } catch (err) {
      console.error('Failed to fetch conflicts:', err);
      setConflictsError('Failed to load conflicts');
    } finally {
      setConflictsLoading(false);
    }
  };

  const fetchAnalytics = async (minutes: number) => {
    setAnalyticsLoading(true);
    try {
      const [hotSystemsData, tradeRoutesData] = await Promise.all([
        warApi.getHotSystems(minutes, 15),
        reportsApi.getTradeRoutes(minutes).catch(() => ({ routes: [] })),
      ]);

      setHotSystems(hotSystemsData.systems || []);
      setTradeRoutes(tradeRoutesData.routes || []);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    fetchConflicts(timeframeMinutes);
    fetchAnalytics(timeframeMinutes);
  }, [timeframeMinutes]);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConflicts(timeframeMinutes);
      fetchAnalytics(timeframeMinutes);
    }, 60000);
    return () => clearInterval(interval);
  }, [timeframeMinutes]);

  return (
    <>
      {/* TOP ROW: 3-Column Grid - Active Engagements | Coalition Wars | Trade Routes */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: '1rem',
        marginBottom: '1rem'
      }}>
        {/* ACTIVE COMBAT ZONES */}
        <ActiveCombatZones
          systems={hotSystems}
          onSystemClick={(systemId) => navigate(`/system/${systemId}?minutes=${timeframeMinutes}`)}
        />

        {/* COALITION WARS - Center position for prominence */}
        <ConflictDashboard
          conflicts={conflicts}
          loading={conflictsLoading}
          error={conflictsError}
        />

        {/* FLEET DOCTRINES */}
        <DoctrinesSection timeframeMinutes={timeframeMinutes} />
      </div>

      {/* TRADE ROUTE THREATS - Full Width */}
      <div style={{ marginBottom: '1rem' }}>
        <TradeRouteThreats
          routes={tradeRoutes}
          onRouteClick={(origin, destination) => {
            navigate(`/route/${encodeURIComponent(origin)}/${encodeURIComponent(destination)}?minutes=${timeframeMinutes}`);
          }}
          onSystemClick={(systemId, battleId) => {
            if (battleId) navigate(`/battle/${battleId}`);
            else navigate(`/system/${systemId}?minutes=${timeframeMinutes}`);
          }}
        />
      </div>

      {/* CAPITAL INTELLIGENCE - Full Width */}
      <div style={{ marginBottom: '1rem' }}>
        <CapitalIntelSection timeframeMinutes={timeframeMinutes} />
      </div>

      {/* Loading placeholder */}
      {analyticsLoading && hotSystems.length === 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
          <div className="skeleton" style={{ height: '280px', borderRadius: '8px' }} />
          <div className="skeleton" style={{ height: '280px', borderRadius: '8px' }} />
          <div className="skeleton" style={{ height: '280px', borderRadius: '8px' }} />
        </div>
      )}
    </>
  );
}
