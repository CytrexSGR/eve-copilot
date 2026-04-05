import { usePilotIntel } from '../hooks/usePilotIntel';
import { useAuth } from '../hooks/useAuth';
import { ModuleGate } from '../components/ModuleGate';
import { WealthSummaryBar, QuickStatus, TopOpportunities, ActiveJobs, CorpSummary } from '../components/dashboard';

export function Dashboard() {
  const { isLoading, profile, refresh } = usePilotIntel();
  const { isLoggedIn } = useAuth();

  if (!isLoggedIn) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'rgba(255,255,255,0.4)' }}>
        <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Login with EVE Online to access your Command Center</p>
      </div>
    );
  }

  return (
    <ModuleGate module="character_suite" preview={false}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.75rem' }}>
          <div>
            <h1 style={{ fontSize: '1.4rem', margin: 0, fontWeight: 800 }}>
              <span style={{ color: '#00d4ff' }}>COMMAND</span> CENTER
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem', margin: 0 }}>
              Personalized intelligence for maximum ISK/hour
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {profile.lastUpdated && (
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.25)' }}>
                Updated {Math.round((Date.now() - profile.lastUpdated.getTime()) / 60000)}m ago
              </span>
            )}
            <button
              onClick={refresh}
              disabled={isLoading}
              style={{
                background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
                color: '#00d4ff', padding: '4px 10px', borderRadius: '4px',
                fontSize: '0.7rem', fontWeight: 600, cursor: isLoading ? 'wait' : 'pointer',
              }}
            >
              {isLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Wealth Summary */}
        <WealthSummaryBar />

        {/* Character Quick Status */}
        <QuickStatus />

        {/* Top Opportunities — personalized scoring */}
        <TopOpportunities />

        {/* Active Industry + Market Orders */}
        <ActiveJobs />

        {/* Corp Status (only for corp+ tier) */}
        <CorpSummary />
      </div>
    </ModuleGate>
  );
}
