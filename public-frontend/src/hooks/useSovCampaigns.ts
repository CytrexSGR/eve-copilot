/**
 * React Query hook for fetching active sovereignty campaigns
 */

import { useQuery } from '@tanstack/react-query';
import type { SovCampaign } from '../types/dotlan';

export function useSovCampaigns() {
  return useQuery<SovCampaign[]>({
    queryKey: ['sov-campaigns'],
    queryFn: async () => {
      const res = await fetch('/api/dotlan/sovereignty/campaigns?status=active');
      if (!res.ok) throw new Error('Failed to fetch sov campaigns');
      return res.json();
    },
    staleTime: 60_000,       // Consider fresh for 1 minute
    refetchInterval: 60_000, // Auto-refetch every minute
  });
}
