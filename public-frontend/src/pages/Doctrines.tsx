import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  HeroSection,
  TabNavigation,
  DoctrinesTicker,
  LiveOpsTab,
  IntelTab,
  TrendsTab,
  type DoctrineTab
} from '../components/doctrines';
import { getLiveOpsData } from '../services/api/fingerprints';
import { ModuleGate } from '../components/ModuleGate';

export function Doctrines() {
  const [activeTab, setActiveTab] = useState<DoctrineTab>('live-ops');
  const [timeFilter, setTimeFilter] = useState(60); // 1 hour default

  // Single API call for all live ops data
  const { data, isLoading } = useQuery({
    queryKey: ['liveOpsData', timeFilter],
    queryFn: () => getLiveOpsData(timeFilter),
    staleTime: 60000,
    refetchInterval: 120000,
  });

  const heroStats = useMemo(() => {
    if (!data) return {
      activeDoctrines: 0,
      fleetsDetected: 0,
      alliancesTracked: 0,
      hotRegions: 0,
      dominantDoctrine: 'Loading...'
    };
    return {
      activeDoctrines: data.summary.active_doctrines,
      fleetsDetected: data.summary.total_fleets,
      alliancesTracked: data.summary.alliances_active,
      hotRegions: data.summary.hot_regions,
      dominantDoctrine: data.summary.dominant_doctrine,
    };
  }, [data]);

  const quickIntel = useMemo(() => {
    if (!data) return undefined;
    return {
      hottestRegion: data.summary.hottest_region,
      peakHour: data.summary.peak_hour,
      avgFleetSize: data.summary.avg_fleet_size,
    };
  }, [data]);

  const tickerAlerts = useMemo(() => {
    if (!data?.alerts?.length) return [];
    return data.alerts.map((alert, idx) => ({
      id: String(idx),
      type: alert.type,
      message: alert.message,
      timestamp: alert.timestamp ? new Date(alert.timestamp) : new Date(),
    }));
  }, [data]);

  return (
    <div style={{ padding: '1rem' }}>
      <HeroSection
        stats={heroStats}
        timeFilter={timeFilter}
        onTimeFilterChange={setTimeFilter}
        quickIntel={quickIntel}
      />

      <DoctrinesTicker alerts={tickerAlerts} />

      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'live-ops' && (
        <LiveOpsTab
          timeFilter={timeFilter}
          activeDoctrines={data?.active_doctrines}
          hotspots={data?.hotspots}
          counterMatrix={data?.counter_matrix}
          isLoading={isLoading}
        />
      )}
      {activeTab === 'intel' && (
        <ModuleGate module="doctrine_intel">
          <IntelTab timeFilter={timeFilter} />
        </ModuleGate>
      )}
      {activeTab === 'trends' && (
        <ModuleGate module="doctrine_intel">
          <TrendsTab
            timeFilter={timeFilter}
            trends={data?.trends}
            shipDistribution={data?.ship_distribution}
            efficiencyRanking={data?.efficiency_ranking}
            isLoading={isLoading}
          />
        </ModuleGate>
      )}
    </div>
  );
}
