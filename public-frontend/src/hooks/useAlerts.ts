import { useState, useEffect, useCallback } from 'react';
import { usePilotIntel } from './usePilotIntel';
import { useAuth } from './useAuth';
import type { Alert } from '../types/alerts';

const DISMISSED_KEY = 'eve_dismissed_alerts';

function getDismissed(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]'));
  } catch { return new Set(); }
}

function saveDismissed(ids: Set<string>) {
  const arr = [...ids].slice(-200);
  localStorage.setItem(DISMISSED_KEY, JSON.stringify(arr));
}

export function useAlerts() {
  const { derived } = usePilotIntel();
  const { isLoggedIn } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [dismissed, setDismissedState] = useState<Set<string>>(getDismissed);

  useEffect(() => {
    if (!isLoggedIn) { setAlerts([]); return; }

    const newAlerts: Alert[] = [];
    const now = new Date();

    // Outbid alerts
    if (derived.outbidCount > 0) {
      newAlerts.push({
        id: `outbid-${now.toDateString()}`,
        type: 'market', severity: 'warning',
        title: `${derived.outbidCount} orders outbid`,
        message: 'Check your market orders for undercuts',
        timestamp: now, actionUrl: '/market?tab=portfolio',
        dismissed: false,
      });
    }

    // Jobs completing soon
    for (const job of derived.completingSoonJobs) {
      newAlerts.push({
        id: `job-${job.jobName}-${job.endsAt.toISOString().slice(0, 13)}`,
        type: 'industry', severity: 'info',
        title: `${job.jobName} completing soon`,
        message: `${job.characterName} — ready in ${Math.round((job.endsAt.getTime() - now.getTime()) / 60000)}min`,
        timestamp: now, actionUrl: '/characters?tab=industry',
        dismissed: false,
      });
    }

    const filtered = newAlerts.map(a => ({ ...a, dismissed: dismissed.has(a.id) }));
    setAlerts(filtered);
  }, [derived, isLoggedIn, dismissed]);

  const dismiss = useCallback((id: string) => {
    setDismissedState(prev => {
      const next = new Set(prev);
      next.add(id);
      saveDismissed(next);
      return next;
    });
  }, []);

  const dismissAll = useCallback(() => {
    setDismissedState(prev => {
      const next = new Set(prev);
      for (const a of alerts) next.add(a.id);
      saveDismissed(next);
      return next;
    });
  }, [alerts]);

  const unreadCount = alerts.filter(a => !a.dismissed).length;

  return { alerts, unreadCount, dismiss, dismissAll };
}
