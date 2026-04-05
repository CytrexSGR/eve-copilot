import { useState, useCallback } from 'react';
import {
  DEFAULT_ACTIVITY_MINUTES,
  type StatusLevel,
  type ColorMode,
} from '../constants';
import type { StatusFilters, StatusCounts } from '../components/home/StatusFilterBar';
import { getEctmapBaseUrl } from '../utils/format';

const DEFAULT_STATUS_FILTERS: StatusFilters = {
  gank: true,
  brawl: true,
  battle: true,
  hellcamp: true,
};

const DEFAULT_STATUS_COUNTS: StatusCounts = {
  gank: 0,
  brawl: 0,
  battle: 0,
  hellcamp: 0,
};

export function useMapState() {
  const [activityMinutes, setActivityMinutes] = useState(DEFAULT_ACTIVITY_MINUTES);
  const [statusFilters, setStatusFilters] = useState<StatusFilters>(DEFAULT_STATUS_FILTERS);
  const [statusCounts, setStatusCounts] = useState<StatusCounts>(DEFAULT_STATUS_COUNTS);
  const [colorMode, setColorMode] = useState<ColorMode>('alliance');

  const toggleStatusFilter = useCallback((key: StatusLevel) => {
    setStatusFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const getEnabledLevels = useCallback(() => {
    return Object.entries(statusFilters)
      .filter(([, v]) => v)
      .map(([k]) => k)
      .join(',');
  }, [statusFilters]);

  const getMapUrl = useCallback(() => {
    const levels = getEnabledLevels();
    return `${getEctmapBaseUrl()}?minutes=${activityMinutes}&levels=${levels}&colorMode=${colorMode}&showCampaigns=true`;
  }, [activityMinutes, colorMode, getEnabledLevels]);

  return {
    // State
    activityMinutes,
    statusFilters,
    statusCounts,
    colorMode,
    // Setters
    setActivityMinutes,
    setStatusCounts,
    setColorMode,
    toggleStatusFilter,
    // Computed
    getEnabledLevels,
    getMapUrl,
  };
}
