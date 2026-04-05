import { useState, useEffect } from 'react';
import { battleApi } from '../services/api';
import './TelegramMirror.css';

interface AllianceInfo {
  alliance_id: number;
  alliance_name: string;
  kills?: number;
  losses?: number;
}

interface TelegramAlert {
  battle_id: number;
  system_name: string;
  region_name: string;
  security: number;
  alert_type: 'milestone' | 'new_battle' | 'ended' | 'unknown';
  milestone: number;
  total_kills: number;
  total_isk_destroyed: number;
  telegram_message_id: number;
  sent_at: string;
  status: 'active' | 'ended';
  attackers?: AllianceInfo[];
  victims?: AllianceInfo[];
}

/**
 * TelegramMirror Component
 *
 * Displays recent Telegram alerts sent for battles
 *
 * Features:
 * - Shows last 5 Telegram notifications
 * - Different icons for alert types (🎯 milestone, ⚠️ new battle, ✅ ended)
 * - Displays system, kills, ISK, and time sent
 * - Links to Telegram channel
 * - Auto-refreshes every 60 seconds
 */
export default function TelegramMirror() {
  const [alerts, setAlerts] = useState<TelegramAlert[]>([]);
  const [milestonesLastHour, setMilestonesLastHour] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      setError(null);
      // Single fetch for both display and milestone count (was 2 calls, now 1)
      const data = await battleApi.getRecentTelegramAlerts(20);
      const allAlerts = data.alerts || [];

      // Display first 5
      setAlerts(allAlerts.slice(0, 5));

      // Count milestones from the same data
      const oneHourAgo = Date.now() - 60 * 60 * 1000;
      const milestonesCount = allAlerts.filter((a: TelegramAlert) => {
        const alertTime = new Date(a.sent_at).getTime();
        return a.alert_type === 'milestone' && alertTime >= oneHourAgo;
      }).length;
      setMilestonesLastHour(milestonesCount);

      setLoading(false);
    } catch (err) {
      console.error('Error fetching telegram alerts:', err);
      setError('Error loading alerts');
      setLoading(false);
    }
  };

  /**
   * Get icon for alert type
   */
  const getAlertIcon = (alertType: string): string => {
    switch (alertType) {
      case 'milestone': return '🎯';
      case 'new_battle': return '⚠️';
      case 'ended': return '✅';
      default: return '📢';
    }
  };

  /**
   * Get alert title based on type
   */
  const getAlertTitle = (alert: TelegramAlert): string => {
    switch (alert.alert_type) {
      case 'milestone':
        return `MILESTONE: ${alert.milestone} kills`;
      case 'new_battle':
        return 'NEW BATTLE';
      case 'ended':
        return 'BATTLE ENDED';
      default:
        return 'BATTLE UPDATE';
    }
  };

  /**
   * Format ISK value to B (billions) or M (millions)
   */
  const formatISK = (isk: number): string => {
    if (isk >= 1_000_000_000) {
      return `${(isk / 1_000_000_000).toFixed(1)}B`;
    } else if (isk >= 1_000_000) {
      return `${(isk / 1_000_000).toFixed(0)}M`;
    }
    return `${isk.toLocaleString()}`;
  };

  /**
   * Format relative time (e.g., "2h ago")
   */
  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      return `${diffDays}d ago`;
    }
  };

  if (loading) {
    return (
      <div className="telegram-mirror" data-testid="telegram-loading">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <div className="telegram-loading">Loading alerts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="telegram-mirror" data-testid="telegram-error">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <div className="telegram-error">{error}</div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="telegram-mirror">
        <h3 className="telegram-header">📱 Telegram Alerts</h3>
        <div className="telegram-empty" data-testid="telegram-empty">
          <div className="empty-icon">📭</div>
          <div className="empty-text">No recent alerts</div>
        </div>
      </div>
    );
  }

  return (
    <div className="telegram-mirror">
      <div className="telegram-header-row">
        <h3 className="telegram-header">
          📱 Telegram Alerts
          {milestonesLastHour > 0 && (
            <span className="milestones-badge">{milestonesLastHour} Milestones in 1h</span>
          )}
        </h3>
        <a
          href="https://t.me/infinimind_eve"
          target="_blank"
          rel="noopener noreferrer"
          className="telegram-link"
          title="Open Telegram Channel"
        >
          📢
        </a>
      </div>
      <div className="telegram-container" data-testid="telegram-container">
        {alerts.map((alert) => (
          <div
            key={`${alert.battle_id}-${alert.telegram_message_id}`}
            className="telegram-alert"
            data-testid={`alert-${alert.telegram_message_id}`}
          >
            <div className="alert-header">
              <div className="alert-icon">{getAlertIcon(alert.alert_type)}</div>
              <div className="alert-title">{getAlertTitle(alert)}</div>
            </div>
            <div className="alert-body">
              <div className="alert-location">
                {alert.system_name} ({alert.security?.toFixed(1)}) - {alert.region_name}
              </div>
              <div className="alert-stats">
                {alert.total_kills.toLocaleString()} kills • {formatISK(alert.total_isk_destroyed)} ISK
              </div>
            </div>
            {(alert.attackers?.length || alert.victims?.length) ? (
              <div className="alert-alliances">
                {alert.attackers?.slice(0, 2).map((a) => (
                  <span key={a.alliance_id} className="alliance-tag attacker" title={`${a.alliance_name} - ${a.kills} kills`}>
                    <img src={`https://images.evetech.net/alliances/${a.alliance_id}/logo?size=32`} alt="" className="alliance-logo" />
                    {a.alliance_name}
                  </span>
                ))}
                {alert.victims?.slice(0, 2).map((v) => (
                  <span key={v.alliance_id} className="alliance-tag victim" title={`${v.alliance_name} - ${v.losses} losses`}>
                    <img src={`https://images.evetech.net/alliances/${v.alliance_id}/logo?size=32`} alt="" className="alliance-logo" />
                    {v.alliance_name}
                  </span>
                ))}
              </div>
            ) : null}
            <div className="alert-footer">
              <span className="alert-sent">{formatRelativeTime(alert.sent_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
