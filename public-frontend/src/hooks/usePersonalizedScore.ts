import { useCallback } from 'react';
import { usePilotIntel } from './usePilotIntel';

export interface OpportunityInput {
  type: 'manufacturing' | 'arbitrage' | 'trading';
  capitalRequired: number;
  estimatedProfit: number;
  estimatedTimeHours?: number;
  requiredSkillIds?: number[];
  blueprintTypeId?: number;
  riskScore?: number;           // 0-100, higher = riskier
  recommendedShip?: string;
  cargoVolume?: number;
}

export interface PersonalizedScore {
  score: number;               // 0-100
  canAfford: boolean;
  affordPercent: number;
  hasSkills: boolean;
  missingSkillCount: number;
  iskPerHour: number;
  riskLevel: 'low' | 'medium' | 'high';
  recommendation: string;
}

export function usePersonalizedScore() {
  const { derived } = usePilotIntel();

  const score = useCallback((opp: OpportunityInput): PersonalizedScore => {
    const { totalWallet, skillMap } = derived;

    // Affordability (0-30 points)
    const affordPercent = opp.capitalRequired > 0
      ? Math.min(100, (totalWallet / opp.capitalRequired) * 100)
      : 100;
    const canAfford = affordPercent >= 100;
    const affordScore = Math.min(30, (affordPercent / 100) * 30);

    // Skills (0-30 points)
    const reqSkills = opp.requiredSkillIds ?? [];
    const missingSkillCount = reqSkills.filter(id => !skillMap.has(id)).length;
    const hasSkills = missingSkillCount === 0;
    const skillScore = reqSkills.length > 0
      ? ((reqSkills.length - missingSkillCount) / reqSkills.length) * 30
      : 30;

    // ISK/hour (0-25 points)
    const iskPerHour = opp.estimatedTimeHours && opp.estimatedTimeHours > 0
      ? opp.estimatedProfit / opp.estimatedTimeHours
      : opp.estimatedProfit;
    const iskScore = Math.min(25, (iskPerHour / 100_000_000) * 25); // 100M/h = max

    // Risk (0-15 points, lower risk = more points)
    const risk = opp.riskScore ?? 30;
    const riskLevel: 'low' | 'medium' | 'high' = risk < 33 ? 'low' : risk < 66 ? 'medium' : 'high';
    const riskScore = Math.max(0, 15 - (risk / 100) * 15);

    const totalScore = Math.round(affordScore + skillScore + iskScore + riskScore);

    // Generate recommendation
    let recommendation = '';
    if (totalScore >= 80) recommendation = 'Excellent opportunity — you have everything needed';
    else if (!canAfford && hasSkills) recommendation = `Need ${((opp.capitalRequired - totalWallet) / 1e6).toFixed(0)}M more ISK`;
    else if (canAfford && !hasSkills) recommendation = `Missing ${missingSkillCount} required skill(s)`;
    else if (totalScore >= 50) recommendation = 'Good opportunity with some preparation';
    else recommendation = 'Not ready — check requirements';

    return {
      score: totalScore, canAfford, affordPercent, hasSkills, missingSkillCount,
      iskPerHour, riskLevel, recommendation,
    };
  }, [derived]);

  return { score };
}
