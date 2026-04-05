import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import type {
  BattleReport as BattleReportType,
  StrategicBriefing,
  AllianceWars as AllianceWarsType,
  AllianceWarsAnalysis
} from '../types/reports';
import { TABS } from '../constants/battleReport';
import type { TabId } from '../constants/battleReport';
import {
  HeroSection,
  BattleReportTicker,
  TabNavigation,
  CombatSummaryBar,
  BattlefieldTab,
  AlliancesTab,
  IntelligenceTab
} from '../components/battle-report';
import { warApi } from '../services/api';
import { TimeFilter } from '../components/warfare/TimeFilter';
import { ModuleGate } from '../components/ModuleGate';

export function BattleReport() {
  const [activeTab, setActiveTab] = useState<TabId>('battlefield');
  const [timeframeMinutes, setTimeframeMinutes] = useState(60);
  const [report, setReport] = useState<BattleReportType | null>(null);
  const [briefing, setBriefing] = useState<StrategicBriefing | null>(null);
  const [allianceWars, setAllianceWars] = useState<AllianceWarsType | null>(null);
  const [allianceAnalysis, setAllianceAnalysis] = useState<AllianceWarsAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [briefingLoading, setBriefingLoading] = useState(true);
  const [allianceLoading, setAllianceLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [livePowerBlocs, setLivePowerBlocs] = useState<AllianceWarsType['coalitions'] | null>(null);
  const [powerBlocsTimeframe, setPowerBlocsTimeframe] = useState<string>('7d');
  const [combatSummary, setCombatSummary] = useState<{
    total_kills: number;
    total_isk_destroyed: number;
    active_systems: number;
    capital_kills: number;
  } | null>(null);

  // Read tab and timeframe from URL hash on mount
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const [tabPart, queryPart] = hash.split('?');
    const tabId = tabPart as TabId;
    if (TABS.some(t => t.id === tabId)) {
      setActiveTab(tabId);
    }
    // Parse timeframe from query
    if (queryPart) {
      const match = queryPart.match(/t=(\d+)/);
      if (match) {
        const minutes = parseInt(match[1], 10);
        if ([10, 60, 720, 1440, 10080].includes(minutes)) {
          setTimeframeMinutes(minutes);
        }
      }
    }
  }, []);

  // Update URL hash when tab or timeframe changes
  useEffect(() => {
    window.location.hash = `${activeTab}?t=${timeframeMinutes}`;
  }, [activeTab, timeframeMinutes]);

  const fetchReport = async () => {
    try {
      setError(null);
      const data = await reportsApi.getBattleReport();
      setReport(data);
      setLastUpdated(new Date());
      setLoading(false);
    } catch (err) {
      setError('Failed to load battle report');
      setLoading(false);
    }
  };

  const fetchBriefing = async () => {
    try {
      setBriefingLoading(true);
      const data = await reportsApi.getStrategicBriefing();
      setBriefing(data);
    } catch (err) {
      console.error('Failed to load strategic briefing:', err);
    } finally {
      setBriefingLoading(false);
    }
  };

  const fetchAllianceWars = async () => {
    try {
      setAllianceLoading(true);
      const [warsData, analysisData] = await Promise.all([
        reportsApi.getAllianceWars(),
        reportsApi.getAllianceWarsAnalysis()
      ]);
      setAllianceWars(warsData);
      setAllianceAnalysis(analysisData);
    } catch (err) {
      console.error('Failed to load alliance wars:', err);
    } finally {
      setAllianceLoading(false);
    }
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
    fetchBriefing();
    fetchAllianceWars();
  }, []);

  useEffect(() => {
    fetchCombatSummary(timeframeMinutes);
  }, [timeframeMinutes]);

  // Fetch live power blocs when on alliances tab with dynamic timeframe
  useEffect(() => {
    if (activeTab === 'alliances') {
      const fetchLivePowerBlocs = async () => {
        try {
          const data = await reportsApi.getPowerBlocsLive(timeframeMinutes);
          setLivePowerBlocs(data.coalitions);
          setPowerBlocsTimeframe(data.timeframe);
        } catch (err) {
          console.error('Failed to load live power blocs:', err);
          // Fall back to pre-generated coalitions
          setLivePowerBlocs(null);
        }
      };
      fetchLivePowerBlocs();
    }
  }, [activeTab, timeframeMinutes]);

  useAutoRefresh(fetchReport, 60);

  if (loading) return <div className="skeleton" style={{ height: '500px' }} />;
  if (error) return <div className="card" style={{ background: 'var(--danger)', color: 'white' }}>{error}</div>;
  if (!report) return null;

  return (
    <div>
      <HeroSection
        report={report}
        allianceWars={allianceWars}
        lastUpdated={lastUpdated}
      />

      <BattleReportTicker />

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
        {(activeTab === 'battlefield' || activeTab === 'alliances') && (
          <>
            <CombatSummaryBar summary={combatSummary} />
            <TimeFilter value={timeframeMinutes} onChange={setTimeframeMinutes} />
          </>
        )}
      </div>

      {activeTab === 'battlefield' && <BattlefieldTab timeframeMinutes={timeframeMinutes} />}

      {activeTab === 'alliances' && (
        <ModuleGate module="warfare_intel">
          <AlliancesTab
            allianceWars={allianceWars}
            livePowerBlocs={livePowerBlocs}
            powerBlocsTimeframe={powerBlocsTimeframe}
            loading={allianceLoading}
          />
        </ModuleGate>
      )}

      {activeTab === 'intelligence' && (
        <ModuleGate module="warfare_intel">
          <IntelligenceTab
            briefing={briefing}
            briefingLoading={briefingLoading}
            allianceAnalysis={allianceAnalysis}
            allianceLoading={allianceLoading}
          />
        </ModuleGate>
      )}
    </div>
  );
}
