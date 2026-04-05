import { useState, useEffect } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { useAllReports } from '../hooks/useReports';
import { useMapState } from '../hooks/useMapState';
import { useCombatIntel } from '../hooks/useCombatIntel';
import { AUTO_REFRESH_SECONDS } from '../constants';
import {
  HeroSection,
  NewsFeedSection,
  SovCampaignsSection,
  BattleMapSection,
  PowerBlocsSection,
  PowerDynamicsSection,
  ActiveConflictsSection,
  TradeRouteSection,
} from '../components/home';

export function Home() {
  return <IntelDashboard />;
}

function IntelDashboard() {
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Map state management
  const {
    activityMinutes,
    statusFilters,
    statusCounts,
    colorMode,
    setActivityMinutes,
    setStatusCounts,
    setColorMode,
    toggleStatusFilter,
    getMapUrl,
  } = useMapState();

  // Combat intel data fetching
  const { mapIskDestroyed, powerAssessment, refetch: refetchCombatIntel } = useCombatIntel({
    activityMinutes,
    onStatusCountsChange: setStatusCounts,
  });

  // Other reports (alliance wars, trade routes)
  const { allianceWars, tradeRoutes, isLoading, isError, error, refetch } = useAllReports();

  // Listen for messages from ectmap iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'ectmap-activity-change' && typeof event.data.minutes === 'number') {
        setActivityMinutes(event.data.minutes);
      }
      if (event.data?.type === 'ectmap-navigate' && typeof event.data.url === 'string') {
        window.location.href = event.data.url;
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [setActivityMinutes]);

  // Auto-refresh
  useAutoRefresh(() => {
    refetch();
    refetchCombatIntel();
    setLastUpdated(new Date());
  }, AUTO_REFRESH_SECONDS);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (isError) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : 'Failed to load reports. Please try again.'}
        onRetry={() => {
          refetch();
          setLastUpdated(new Date());
        }}
      />
    );
  }

  return (
    <div>
      <HeroSection
        lastUpdated={lastUpdated}
        autoRefreshSeconds={AUTO_REFRESH_SECONDS}
        mapIskDestroyed={mapIskDestroyed}
        allianceWars={allianceWars}
        statusCounts={statusCounts}
      />

      <NewsFeedSection />

      <SovCampaignsSection />

      <BattleMapSection
        activityMinutes={activityMinutes}
        mapIskDestroyed={mapIskDestroyed}
        statusFilters={statusFilters}
        statusCounts={statusCounts}
        colorMode={colorMode}
        mapUrl={getMapUrl()}
        onStatusFilterChange={toggleStatusFilter}
        onColorModeChange={setColorMode}
        onActivityMinutesChange={setActivityMinutes}
      />

      <PowerBlocsSection coalitions={allianceWars?.coalitions} />

      <PowerDynamicsSection
        powerAssessment={powerAssessment}
        activityMinutes={activityMinutes}
      />

      <ActiveConflictsSection allianceWars={allianceWars ?? null} />

      <TradeRouteSection tradeRoutes={tradeRoutes ?? null} />
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div>
      <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
      <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
      <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      className="card"
      style={{
        background: 'var(--danger)',
        color: 'white',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <h2>{message}</h2>
      <button
        onClick={onRetry}
        style={{
          marginTop: '1rem',
          padding: '0.5rem 1rem',
          background: 'white',
          color: 'var(--danger)',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontWeight: 600,
        }}
      >
        Retry
      </button>
    </div>
  );
}
