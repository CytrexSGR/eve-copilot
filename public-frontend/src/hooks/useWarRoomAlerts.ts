import { useState, useEffect, useCallback, useRef } from 'react';
import { warApi, battleApi } from '../services/api';
import type { ActiveBattle, FuelTrendsResponse, ManipulationAlertsResponse } from '../types/reports';

export type AlertPriority = 'critical' | 'high' | 'medium' | 'low';
export type AlertType = 'battle' | 'doctrine' | 'manipulation' | 'fuel';

export interface WarRoomAlert {
  id: string;
  type: AlertType;
  priority: AlertPriority;
  icon: string;
  message: string;
  detail?: string;
  timestamp: Date;
  link?: string;
}

interface DoctrineInfo {
  region: string;
  doctrine: string;
  shipCount: number;
}

interface UseWarRoomAlertsOptions {
  pollInterval?: number; // milliseconds
  enabled?: boolean;
}

export function useWarRoomAlerts(options: UseWarRoomAlertsOptions = {}) {
  const { pollInterval = 60000, enabled = true } = options;

  const [alerts, setAlerts] = useState<WarRoomAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastBattleStates, setLastBattleStates] = useState<Map<number, string>>(new Map());
  const mountedRef = useRef(true);

  const generateAlerts = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    const newAlerts: WarRoomAlert[] = [];
    const now = new Date();

    try {
      // 1. Fetch active battles for escalation detection
      const battlesResponse = await battleApi.getActiveBattles(20, 60);
      const battles: ActiveBattle[] = battlesResponse?.battles || [];

      // Check for battle escalations (status_level changes)
      battles.forEach(battle => {
        const prevState = lastBattleStates.get(battle.battle_id);
        const currentState = battle.status_level || 'gank';

        // Alert on significant battles or escalations
        if (currentState === 'hellcamp') {
          newAlerts.push({
            id: `battle-${battle.battle_id}`,
            type: 'battle',
            priority: 'critical',
            icon: '⚔️',
            message: `${battle.region_name} → HELLCAMP`,
            detail: `${battle.total_kills} kills in ${battle.system_name}`,
            timestamp: now,
            link: `/battle/${battle.battle_id}`
          });
        } else if (currentState === 'battle' && prevState !== 'battle' && prevState !== 'hellcamp') {
          newAlerts.push({
            id: `battle-${battle.battle_id}`,
            type: 'battle',
            priority: 'high',
            icon: '⚔️',
            message: `${battle.region_name} escalated to BATTLE`,
            detail: `${battle.total_kills} kills in ${battle.system_name}`,
            timestamp: now,
            link: `/battle/${battle.battle_id}`
          });
        }
      });

      // Update battle states for next comparison
      const newStates = new Map<number, string>();
      battles.forEach(b => newStates.set(b.battle_id, b.status_level || 'gank'));
      setLastBattleStates(newStates);

      // 2. Fetch manipulation alerts (all trade hubs)
      const tradeHubs = [10000002, 10000043, 10000030, 10000032, 10000042];
      const hubNames: Record<number, string> = {
        10000002: 'Jita',
        10000043: 'Amarr',
        10000030: 'Rens',
        10000032: 'Dodixie',
        10000042: 'Hek'
      };

      for (const hubId of tradeHubs) {
        try {
          const manipulation: ManipulationAlertsResponse = await warApi.getManipulationAlerts(hubId, 24);

          manipulation.alerts?.forEach(alert => {
            if (alert.severity === 'confirmed' || alert.z_score >= 3.5) {
              newAlerts.push({
                id: `manipulation-${alert.type_id}-${hubId}`,
                type: 'manipulation',
                priority: alert.severity === 'confirmed' ? 'high' : 'medium',
                icon: '📈',
                message: `${alert.type_name} Z-Score ${alert.z_score.toFixed(1)}`,
                detail: `${hubNames[hubId]} - ${alert.manipulation_type}`,
                timestamp: new Date(alert.detected_at),
                link: '/war-economy'
              });
            }
          });
        } catch (e) {
          // Skip failed hub
        }
      }

      // 3. Fetch fuel anomalies
      for (const hubId of tradeHubs) {
        try {
          const fuel: FuelTrendsResponse = await warApi.getFuelTrends(hubId, 24);

          fuel.trends?.forEach(trend => {
            trend.snapshots?.forEach(snapshot => {
              if (snapshot.anomaly && (snapshot.severity === 'high' || snapshot.severity === 'critical')) {
                const deltaStr = snapshot.delta_percent > 0 ? `+${snapshot.delta_percent.toFixed(0)}%` : `${snapshot.delta_percent.toFixed(0)}%`;
                newAlerts.push({
                  id: `fuel-${trend.isotope_id}-${hubId}`,
                  type: 'fuel',
                  priority: snapshot.severity === 'critical' ? 'high' : 'medium',
                  icon: '⛽',
                  message: `${trend.isotope_name} ${deltaStr}`,
                  detail: `${hubNames[hubId]} - possible capital movement`,
                  timestamp: new Date(snapshot.timestamp),
                  link: '/war-economy'
                });
              }
            });
          });
        } catch (e) {
          // Skip failed hub
        }
      }

    } catch (err) {
      console.error('Failed to fetch war room alerts:', err);
    }

    // Sort by priority and timestamp
    const priorityOrder: Record<AlertPriority, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3
    };

    newAlerts.sort((a, b) => {
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return b.timestamp.getTime() - a.timestamp.getTime();
    });

    // Deduplicate by id
    const uniqueAlerts = newAlerts.filter((alert, index, self) =>
      index === self.findIndex(a => a.id === alert.id)
    );

    if (mountedRef.current) {
      setAlerts(uniqueAlerts);
      setLoading(false);
    }
  }, [enabled, lastBattleStates]);

  // Add doctrine alerts from war economy report
  const addDoctrineAlerts = useCallback((doctrines: DoctrineInfo[]) => {
    const now = new Date();
    const doctrineAlerts: WarRoomAlert[] = doctrines.map((d, i) => ({
      id: `doctrine-${d.region}-${i}`,
      type: 'doctrine' as AlertType,
      priority: d.shipCount >= 30 ? 'high' as AlertPriority : 'medium' as AlertPriority,
      icon: '🛡️',
      message: `${d.doctrine} detected`,
      detail: `${d.region} - ${d.shipCount} ships`,
      timestamp: now,
      link: '/war-economy'
    }));

    setAlerts(prev => {
      const filtered = prev.filter(a => a.type !== 'doctrine');
      return [...doctrineAlerts, ...filtered].sort((a, b) => {
        const priorityOrder: Record<AlertPriority, number> = { critical: 0, high: 1, medium: 2, low: 3 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      });
    });
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    if (enabled) {
      generateAlerts();
      const interval = setInterval(generateAlerts, pollInterval);
      return () => {
        mountedRef.current = false;
        clearInterval(interval);
      };
    }

    return () => {
      mountedRef.current = false;
    };
  }, [enabled, pollInterval, generateAlerts]);

  return {
    alerts,
    loading,
    refresh: generateAlerts,
    addDoctrineAlerts
  };
}
