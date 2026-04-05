export type AlertType = 'market' | 'industry' | 'intel' | 'corp';
export type AlertSeverity = 'info' | 'warning' | 'urgent';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: Date;
  actionUrl?: string;
  dismissed: boolean;
}

export const ALERT_COLORS: Record<AlertType, string> = {
  market: '#3fb950',
  industry: '#00d4ff',
  intel: '#f85149',
  corp: '#ffcc00',
};
