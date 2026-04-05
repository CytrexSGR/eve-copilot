import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { reportsApi, warApi, getExtendedHotItems, getWarzoneRoutes } from '../services/api';
import type { CapitalAlliancesResponse } from '../services/api';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type {
  WarEconomy as WarEconomyType,
  WarEconomyAnalysis,
  FuelTrendsResponse,
  SupercapTimersResponse,
  ManipulationAlertsResponse,
  ExtendedHotItemsResponse,
  WarzoneRoutesResponse
} from '../types/reports';
import type { TabId } from '../constants/warEconomy';
import {
  HeroSection,
  TabNavigation,
  EconomySummaryBar,
  CombatTab,
  TradingTab,
  RoutesTab,
  SignalsTab,
  IntelTab,
  WarEconomyTicker
} from '../components/war-economy';
import { TimeFilter } from '../components/warfare/TimeFilter';
import type { TimePeriodValue } from '../components/trade-routes';
import { ModuleGate } from '../components/ModuleGate';

export function WarEconomy() {
  const location = useLocation();
  const [report, setReport] = useState<WarEconomyType | null>(null);
  const [analysis, setAnalysis] = useState<WarEconomyAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Initialize activeTab and timeframe from URL hash
  const getInitialState = (): { tab: TabId; minutes: TimePeriodValue } => {
    const hash = location.hash.replace('#', '');
    const [tabPart, queryPart] = hash.split('?');
    let tab: TabId = 'combat';
    let minutes: TimePeriodValue = 60;

    if (['combat', 'trading', 'routes', 'signals', 'intel'].includes(tabPart)) {
      tab = tabPart as TabId;
    }
    if (queryPart) {
      const match = queryPart.match(/t=(\d+)/);
      if (match) {
        const m = parseInt(match[1], 10);
        if ([10, 60, 360, 720, 1440].includes(m)) {
          minutes = m as TimePeriodValue;
        }
      }
    }
    return { tab, minutes };
  };
  const initial = getInitialState();
  const [activeTab, setActiveTab] = useState<TabId>(initial.tab);
  const [selectedMinutes, setSelectedMinutes] = useState<TimePeriodValue>(initial.minutes);

  // Trading Tab State
  const [extendedHotItems, setExtendedHotItems] = useState<ExtendedHotItemsResponse | null>(null);
  const [warzoneRoutes, setWarzoneRoutes] = useState<WarzoneRoutesResponse | null>(null);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [expandedRoute, setExpandedRoute] = useState<number | null>(null);
  const [tradingLoading, setTradingLoading] = useState(false);

  // Note: selectedMinutes is shared between Combat and Routes tabs (initialized above)

  // Combat Summary State (timeframe-aware)
  const [combatSummary, setCombatSummary] = useState<{
    total_kills: number;
    total_isk_destroyed: number;
    active_systems: number;
    capital_kills: number;
  } | null>(null);

  // Signals Tab State
  const [selectedRegion, setSelectedRegion] = useState(10000002);
  const [fuelTrends, setFuelTrends] = useState<FuelTrendsResponse | null>(null);
  const [manipulationAlerts, setManipulationAlerts] = useState<ManipulationAlertsResponse | null>(null);
  const [supercapTimers, setSupercapTimers] = useState<SupercapTimersResponse | null>(null);
  const [capitalAlliances, setCapitalAlliances] = useState<CapitalAlliancesResponse | null>(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [expandedAlliances, setExpandedAlliances] = useState<Set<number>>(new Set());

  const toggleAlliance = (allianceId: number) => {
    setExpandedAlliances(prev => {
      const next = new Set(prev);
      if (next.has(allianceId)) next.delete(allianceId);
      else next.add(allianceId);
      return next;
    });
  };

  // War Room Alert Bar - DISABLED to reduce API load (was causing rate limiting)
  const alerts: never[] = [];

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getWarEconomy();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load war economy report');
      setLoading(false);
    }
  };

  const fetchAnalysis = async () => {
    try {
      setAnalysisLoading(true);
      const data = await reportsApi.getWarEconomyAnalysis();
      setAnalysis(data);
      setAnalysisLoading(false);
    } catch (err) {
      console.error('Failed to load war economy analysis:', err);
      setAnalysisLoading(false);
    }
  };

  const fetchIntelligence = async (regionId: number) => {
    setIntelLoading(true);
    try {
      const [fuel, manipulation, timers, alliances] = await Promise.all([
        warApi.getFuelTrends(regionId, 168),
        warApi.getManipulationAlerts(regionId, 24),
        warApi.getSupercapTimers(regionId),
        warApi.getCapitalAlliances(30)
      ]);
      setFuelTrends(fuel);
      setManipulationAlerts(manipulation);
      setSupercapTimers(timers);
      setCapitalAlliances(alliances);
    } catch (err) {
      console.error('Failed to load intelligence data:', err);
    }
    setIntelLoading(false);
  };

  const fetchCombatSummary = async (minutes: number) => {
    try {
      const hours = Math.max(1, Math.ceil(minutes / 60));
      const data = await warApi.getWarSummary(hours);
      setCombatSummary(data);
    } catch (err) {
      console.error('Failed to fetch combat summary:', err);
    }
  };

  useEffect(() => {
    fetchReport();
    // fetchAnalysis loaded lazily when Intel tab is active
  }, []);

  // Fetch combat summary only when combat or routes tab is active
  useEffect(() => {
    if (activeTab === 'combat' || activeTab === 'routes') {
      fetchCombatSummary(selectedMinutes);
    }
  }, [selectedMinutes, activeTab]);

  // Lazy load analysis only when Intel tab is active
  useEffect(() => {
    if (activeTab === 'intel' && !analysis && !analysisLoading) {
      fetchAnalysis();
    }
  }, [activeTab, analysis, analysisLoading]);

  // Update activeTab and timeframe when hash changes (from external navigation)
  useEffect(() => {
    const hash = location.hash.replace('#', '');
    const [tabPart, queryPart] = hash.split('?');
    if (['combat', 'trading', 'routes', 'signals', 'intel'].includes(tabPart)) {
      setActiveTab(tabPart as TabId);
    }
    if (queryPart) {
      const match = queryPart.match(/t=(\d+)/);
      if (match) {
        const m = parseInt(match[1], 10);
        if ([10, 60, 360, 720, 1440].includes(m)) {
          setSelectedMinutes(m as TimePeriodValue);
        }
      }
    }
  }, [location.hash]);

  // Update URL hash when tab or timeframe changes (for bookmarking/sharing)
  useEffect(() => {
    window.location.hash = `${activeTab}?t=${selectedMinutes}`;
  }, [activeTab, selectedMinutes]);

  useEffect(() => {
    if (activeTab === 'signals') {
      fetchIntelligence(selectedRegion);
    }
  }, [activeTab, selectedRegion]);

  useEffect(() => {
    if (activeTab === 'trading') {
      setTradingLoading(true);
      Promise.all([
        getExtendedHotItems(10),
        getWarzoneRoutes(5)
      ]).then(([items, routes]) => {
        setExtendedHotItems(items);
        setWarzoneRoutes(routes);
      }).catch(err => {
        console.error('Failed to load trading data:', err);
      }).finally(() => {
        setTradingLoading(false);
      });
    }
  }, [activeTab]);

  useAutoRefresh(fetchReport, 300); // 5 min refresh to reduce API load

  // Doctrine alerts disabled to reduce API load
  // useEffect(() => { ... }, [report, addDoctrineAlerts]);

  if (loading) return <div className="skeleton" style={{ height: '500px' }} />;
  if (error) return <div className="card" style={{ background: 'var(--danger)', color: 'white' }}>{error}</div>;
  if (!report) return null;

  return (
    <div>
      <HeroSection report={report} lastUpdated={lastUpdated} />

      <WarEconomyTicker report={report} alerts={alerts} />

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
        <EconomySummaryBar summary={combatSummary} />
        {(activeTab === 'combat' || activeTab === 'routes') && (
          <TimeFilter
            value={selectedMinutes}
            onChange={(m) => setSelectedMinutes(m as TimePeriodValue)}
            options={[
              { label: '10m', minutes: 10 },
              { label: '1h', minutes: 60 },
              { label: '6h', minutes: 360 },
              { label: '12h', minutes: 720 },
              { label: '24h', minutes: 1440 },
            ]}
          />
        )}
      </div>

      {activeTab === 'combat' && <CombatTab report={report} timeframeMinutes={selectedMinutes} />}

      {activeTab === 'trading' && (
        <ModuleGate module="war_economy">
          <TradingTab
            extendedHotItems={extendedHotItems}
            warzoneRoutes={warzoneRoutes}
            expandedItem={expandedItem}
            expandedRoute={expandedRoute}
            onExpandItem={setExpandedItem}
            onExpandRoute={setExpandedRoute}
            loading={tradingLoading}
          />
        </ModuleGate>
      )}

      {activeTab === 'routes' && (
        <ModuleGate module="war_economy">
          <RoutesTab
            selectedMinutes={selectedMinutes}
            onTimeChange={setSelectedMinutes}
          />
        </ModuleGate>
      )}

      {activeTab === 'signals' && (
        <ModuleGate module="war_economy">
          <SignalsTab
            selectedRegion={selectedRegion}
            onRegionChange={setSelectedRegion}
            fuelTrends={fuelTrends}
            manipulationAlerts={manipulationAlerts}
            supercapTimers={supercapTimers}
            capitalAlliances={capitalAlliances}
            expandedAlliances={expandedAlliances}
            onToggleAlliance={toggleAlliance}
            loading={intelLoading}
          />
        </ModuleGate>
      )}

      {activeTab === 'intel' && (
        <ModuleGate module="war_economy">
          <IntelTab analysis={analysis} loading={analysisLoading} />
        </ModuleGate>
      )}
    </div>
  );
}
