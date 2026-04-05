import { useAuth } from './useAuth';
import { ENTITY_MODULE_GROUPS } from '../types/auth';

export function useModules() {
  const { activeModules, orgPlan, isLoggedIn } = useAuth();

  const hasModule = (moduleName: string): boolean => {
    // Public access: non-logged-in users can view all content freely.
    // Module gating only applies to authenticated users based on subscription.
    if (!isLoggedIn) return true;
    if (!activeModules || activeModules.length === 0) return false;
    // Direct match
    if (activeModules.includes(moduleName)) return true;
    // Entity group match: if checking corp_intel, accept corp_intel_1/5/unlimited
    const variants = ENTITY_MODULE_GROUPS[moduleName];
    if (variants) {
      return variants.some(v => activeModules.includes(v));
    }
    return false;
  };

  const hasOrgPlan = (orgType?: 'corporation' | 'alliance'): boolean => {
    if (!orgPlan) return false;
    if (!orgType) return true;
    if (orgType === 'corporation') return true; // any org plan includes corp
    return orgPlan.type === 'alliance';
  };

  // Public access: non-logged-in users bypass seat check.
  const hasSeat = (): boolean => !isLoggedIn ? true : (orgPlan?.has_seat ?? false);

  return { hasModule, hasOrgPlan, hasSeat, activeModules, orgPlan, isLoggedIn };
}
