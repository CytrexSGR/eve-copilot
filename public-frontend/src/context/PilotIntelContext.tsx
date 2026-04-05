import { createContext, useState, useEffect, useCallback, useMemo, type ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import { characterApi } from '../services/api/character';
import { portfolioApi, ordersApi } from '../services/api/market';
import type { PilotProfile, PilotDerived, PilotIntelState } from '../types/pilot-intel';

const EMPTY_DERIVED: PilotDerived = {
  totalWallet: 0, totalAssetValue: 0, totalSellOrderValue: 0, totalBuyEscrow: 0,
  totalNetWorth: 0, activeIndustryJobs: 0, completingSoonJobs: [], outbidCount: 0,
  skillMap: new Map(), primaryCharacter: null,
};

const EMPTY_PROFILE: PilotProfile = {
  characters: [], portfolioSummary: null, orders: null, lastUpdated: null,
};

export const PilotIntelContext = createContext<PilotIntelState>({
  profile: EMPTY_PROFILE, derived: EMPTY_DERIVED, isLoading: true, refresh: async () => {},
});

function deriveData(profile: PilotProfile): PilotDerived {
  const { characters, portfolioSummary, orders } = profile;
  const totalWallet = characters.reduce((s, c) => s + (c.wallet?.balance ?? 0), 0);

  // Merge skills from all characters (highest level wins)
  const skillMap = new Map<number, number>();
  for (const char of characters) {
    for (const skill of char.skills?.skills ?? []) {
      const cur = skillMap.get(skill.skill_id) ?? 0;
      if (skill.trained_level > cur) skillMap.set(skill.skill_id, skill.trained_level);
    }
  }

  // Jobs completing within 4 hours
  const soonMs = 4 * 3600 * 1000;
  const now = Date.now();
  const completingSoonJobs: PilotDerived['completingSoonJobs'] = [];
  let activeIndustryJobs = 0;
  for (const char of characters) {
    for (const job of char.industry?.jobs ?? []) {
      if (job.status === 'active') {
        activeIndustryJobs++;
        if (job.end_date) {
          const endsAt = new Date(job.end_date);
          if (endsAt.getTime() - now < soonMs && endsAt.getTime() > now) {
            completingSoonJobs.push({
              characterName: char.character_name,
              jobName: job.product_type_name || job.blueprint_type_name,
              endsAt,
            });
          }
        }
      }
    }
  }

  const totalSellOrderValue = orders?.summary?.total_isk_in_sell_orders ?? 0;
  const totalBuyEscrow = orders?.summary?.total_isk_in_buy_orders ?? 0;
  const totalAssetValue = portfolioSummary?.combined_liquid ?? 0;
  const outbidCount = orders?.summary?.outbid_count ?? 0;

  return {
    totalWallet, totalAssetValue, totalSellOrderValue, totalBuyEscrow,
    totalNetWorth: totalWallet + totalSellOrderValue + totalBuyEscrow,
    activeIndustryJobs, completingSoonJobs, outbidCount, skillMap,
    primaryCharacter: characters[0] ?? null,
  };
}

export function PilotIntelProvider({ children }: { children: ReactNode }) {
  const { isLoggedIn, account, activeCharacterId } = useAuth();
  const [profile, setProfile] = useState<PilotProfile>(EMPTY_PROFILE);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!isLoggedIn || !account) {
      setProfile(EMPTY_PROFILE);
      setIsLoading(false);
      return;
    }
    try {
      const [charRes, portRes, ordRes] = await Promise.allSettled([
        characterApi.getSummaryAll(),
        portfolioApi.getSummaryAll(),
        ordersApi.getAggregated(),
      ]);
      setProfile({
        characters: charRes.status === 'fulfilled' ? charRes.value.characters : [],
        portfolioSummary: portRes.status === 'fulfilled' ? portRes.value : null,
        orders: ordRes.status === 'fulfilled' ? ordRes.value : null,
        lastUpdated: new Date(),
      });
    } catch {
      setProfile(EMPTY_PROFILE);
    } finally {
      setIsLoading(false);
    }
  }, [isLoggedIn, account, activeCharacterId]);

  // Initial load + 5 min refresh interval
  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 300_000);
    return () => clearInterval(interval);
  }, [refresh]);

  const derived = useMemo(() => deriveData(profile), [profile]);

  return (
    <PilotIntelContext.Provider value={{ profile, derived, isLoading, refresh }}>
      {children}
    </PilotIntelContext.Provider>
  );
}
