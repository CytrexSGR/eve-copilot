import { createContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { authApi, tierApi, moduleApi } from '../services/api/auth';
import type { AccountInfo, TierInfo, OrgPlan } from '../types/auth';

export interface AuthState {
  isLoading: boolean;
  isLoggedIn: boolean;
  account: AccountInfo | null;
  tierInfo: TierInfo | null;
  activeModules: string[];
  orgPlan: OrgPlan | null;
  activeCharacterId: number | null;
  setActiveCharacter: (charId: number) => void;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthState>({
  isLoading: true,
  isLoggedIn: false,
  account: null,
  tierInfo: null,
  activeModules: [],
  orgPlan: null,
  activeCharacterId: null,
  setActiveCharacter: () => {},
  login: async () => {},
  logout: async () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [tierInfo, setTierInfo] = useState<TierInfo | null>(null);
  const [activeModules, setActiveModules] = useState<string[]>([]);
  const [orgPlan, setOrgPlan] = useState<OrgPlan | null>(null);
  const [activeCharacterId, setActiveCharacterId] = useState<number | null>(() => {
    const saved = localStorage.getItem('eve_active_char');
    return saved ? Number(saved) : null;
  });

  const refresh = useCallback(async () => {
    // Skip API calls when no session exists (avoids 401 console noise)
    if (!localStorage.getItem('eve_auth')) {
      setAccount(null);
      setTierInfo(null);
      setActiveModules([]);
      setOrgPlan(null);
      return;
    }
    try {
      const [accountRes, tierRes, moduleRes] = await Promise.allSettled([
        authApi.getAccount(),
        tierApi.getMyTier(),
        moduleApi.getActiveModules(),
      ]);
      if (accountRes.status === 'fulfilled' && accountRes.value) {
        setAccount(accountRes.value);
        setActiveCharacterId(prev => prev || accountRes.value.primary_character_id);
      } else {
        setAccount(null);
      }
      setTierInfo(tierRes.status === 'fulfilled' ? tierRes.value : null);
      if (moduleRes.status === 'fulfilled') {
        setActiveModules(moduleRes.value.modules ?? []);
        setOrgPlan(moduleRes.value.org_plan ?? null);
      } else {
        setActiveModules([]);
        setOrgPlan(null);
      }
      // Session expired — clear the flag
      if (accountRes.status !== 'fulfilled') {
        localStorage.removeItem('eve_auth');
      }
    } catch {
      setAccount(null);
      setTierInfo(null);
      setActiveModules([]);
      setOrgPlan(null);
      localStorage.removeItem('eve_auth');
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setIsLoading(false));
  }, [refresh]);

  const login = useCallback(async () => {
    const { auth_url } = await authApi.getLoginUrl(window.location.origin + '/auth/callback');
    window.location.href = auth_url;
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    localStorage.removeItem('eve_auth');
    setAccount(null);
    setTierInfo(null);
    setActiveModules([]);
    setOrgPlan(null);
    setActiveCharacterId(null);
    localStorage.removeItem('eve_active_char');
  }, []);

  const setActiveCharacter = useCallback((charId: number) => {
    setActiveCharacterId(charId);
    localStorage.setItem('eve_active_char', String(charId));
  }, []);

  // Sync active character across browser tabs via storage event
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'eve_active_char' && e.newValue) {
        setActiveCharacterId(Number(e.newValue));
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isLoading,
        isLoggedIn: !!account,
        account,
        tierInfo,
        activeModules,
        orgPlan,
        activeCharacterId,
        setActiveCharacter,
        login,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
