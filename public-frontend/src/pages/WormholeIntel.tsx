import { useState, useEffect, useCallback } from 'react';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { wormholeApi } from '../services/api/wormhole';
import {
  WormholeHero,
  WormholeTicker,
  WormholeTabNav,
  ResidentsTab,
  HuntersTab,
  MarketTab,
  TheraRouterTab,
} from '../components/wormhole';
import { ModuleGate } from '../components/ModuleGate';
import type {
  WormholeSummary,
  WormholeThreat,
  WormholeOpportunity,
  WormholeEviction,
  WormholeTabId,
} from '../types/wormhole';

export function WormholeIntel() {
  // State
  const [summary, setSummary] = useState<WormholeSummary | null>(null);
  const [threats, setThreats] = useState<WormholeThreat[]>([]);
  const [opportunities, setOpportunities] = useState<WormholeOpportunity[]>([]);
  const [evictions, setEvictions] = useState<WormholeEviction[]>([]);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<WormholeTabId>('hunters');
  const [selectedClass, setSelectedClass] = useState<number | null>(null);

  // Fetch functions
  const fetchSummary = useCallback(async () => {
    try {
      const data = await wormholeApi.getSummary();
      setSummary(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch summary:', err);
    }
  }, []);

  const fetchThreats = useCallback(async () => {
    try {
      const { threats } = await wormholeApi.getThreats(selectedClass ?? undefined);
      setThreats(threats);
    } catch (err) {
      console.error('Failed to fetch threats:', err);
    }
  }, [selectedClass]);

  const fetchOpportunities = useCallback(async () => {
    try {
      const { opportunities } = await wormholeApi.getOpportunities(selectedClass ?? undefined);
      setOpportunities(opportunities);
    } catch (err) {
      console.error('Failed to fetch opportunities:', err);
    }
  }, [selectedClass]);

  const fetchEvictions = useCallback(async () => {
    try {
      const { evictions } = await wormholeApi.getEvictions(7);
      setEvictions(evictions);
    } catch (err) {
      console.error('Failed to fetch evictions:', err);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchSummary(),
      fetchThreats(),
      fetchEvictions(),
    ]);
    setLoading(false);
  }, [fetchSummary, fetchThreats, fetchEvictions]);

  // Initial load
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Tab-specific data
  useEffect(() => {
    if (activeTab === 'hunters') {
      fetchOpportunities();
    }
    // MarketTab handles its own data fetching
  }, [activeTab, fetchOpportunities]);

  // Refetch when class filter changes
  useEffect(() => {
    fetchThreats();
    if (activeTab === 'hunters') {
      fetchOpportunities();
    }
  }, [selectedClass, fetchThreats, fetchOpportunities, activeTab]);

  // Auto-refresh
  useAutoRefresh(fetchAll, 60);

  // Handlers
  const handleSystemSearch = (query: string) => {
    console.log('Search for system:', query);
    // TODO: Implement system search navigation
  };

  return (
    <div style={{ padding: '1rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Hero Section */}
      <WormholeHero summary={summary} lastUpdated={lastUpdated} loading={loading} />

      {/* Ticker */}
      <WormholeTicker threats={threats} evictions={evictions} />

      {/* Tab Navigation */}
      <WormholeTabNav activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab Content */}
      {activeTab === 'residents' && (
        <ModuleGate module="wormhole_intel">
          <ResidentsTab
            threats={threats}
            evictions={evictions}
            selectedClass={selectedClass}
            onClassChange={setSelectedClass}
            onSystemSearch={handleSystemSearch}
          />
        </ModuleGate>
      )}
      {activeTab === 'hunters' && (
        <HuntersTab
          opportunities={opportunities}
          selectedClass={selectedClass}
          onClassChange={setSelectedClass}
          loading={loading}
        />
      )}
      {activeTab === 'market' && (
        <ModuleGate module="wormhole_intel">
          <MarketTab />
        </ModuleGate>
      )}
      {activeTab === 'thera-router' && (
        <ModuleGate module="wormhole_intel">
          <TheraRouterTab />
        </ModuleGate>
      )}
    </div>
  );
}
