import { useState, useEffect, useCallback } from 'react';
import { reportsApi, battleApi } from '../services/api';
import type { ActiveBattle, PowerAssessment } from '../types/reports';
import type { StatusCounts } from '../components/home/StatusFilterBar';

interface UseCombatIntelOptions {
  activityMinutes: number;
  onStatusCountsChange: (counts: StatusCounts) => void;
}

interface CombatIntelState {
  mapIskDestroyed: number;
  powerAssessment: PowerAssessment | null;
  isLoading: boolean;
  error: Error | null;
}

export function useCombatIntel({ activityMinutes, onStatusCountsChange }: UseCombatIntelOptions) {
  const [state, setState] = useState<CombatIntelState>({
    mapIskDestroyed: 0,
    powerAssessment: null,
    isLoading: false,
    error: null,
  });

  const fetchData = useCallback(async (minutes: number) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Fetch battles and power assessment in parallel
      const [battlesData, powerData] = await Promise.all([
        battleApi.getActiveBattles(1000, minutes),
        reportsApi.getPowerAssessment(minutes),
      ]);

      // Calculate ISK destroyed and status counts
      let totalIsk = 0;
      const counts: StatusCounts = { gank: 0, brawl: 0, battle: 0, hellcamp: 0 };

      battlesData.battles.forEach((battle: ActiveBattle) => {
        totalIsk += battle.total_isk_destroyed;
        const level = (battle.status_level || 'gank') as keyof StatusCounts;
        if (counts[level] !== undefined) counts[level]++;
      });

      setState({
        mapIskDestroyed: totalIsk,
        powerAssessment: powerData,
        isLoading: false,
        error: null,
      });

      onStatusCountsChange(counts);
    } catch (err) {
      console.error('Failed to fetch combat intel:', err);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err : new Error('Failed to fetch data'),
      }));
    }
  }, [onStatusCountsChange]);

  // Fetch on mount and when activityMinutes changes
  useEffect(() => {
    fetchData(activityMinutes);
  }, [activityMinutes, fetchData]);

  const refetch = useCallback(() => {
    fetchData(activityMinutes);
  }, [activityMinutes, fetchData]);

  return {
    ...state,
    refetch,
  };
}
