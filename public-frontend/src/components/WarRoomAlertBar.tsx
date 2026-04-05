import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import type { WarRoomAlert, AlertPriority } from '../hooks/useWarRoomAlerts';

interface WarRoomAlertBarProps {
  alerts: WarRoomAlert[];
  maxVisible?: number;
  rotateInterval?: number; // milliseconds
}

const priorityColors: Record<AlertPriority, string> = {
  critical: 'bg-red-900/80 border-red-500 text-red-100',
  high: 'bg-orange-900/80 border-orange-500 text-orange-100',
  medium: 'bg-yellow-900/80 border-yellow-500 text-yellow-100',
  low: 'bg-blue-900/80 border-blue-500 text-blue-100'
};

const priorityDots: Record<AlertPriority, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-blue-500'
};

export function WarRoomAlertBar({
  alerts,
  maxVisible = 3,
  rotateInterval = 8000
}: WarRoomAlertBarProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);

  // Auto-rotate through alerts
  useEffect(() => {
    if (alerts.length <= maxVisible || expanded) return;

    const interval = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % Math.max(1, alerts.length - maxVisible + 1));
    }, rotateInterval);

    return () => clearInterval(interval);
  }, [alerts.length, maxVisible, rotateInterval, expanded]);

  // Reset index when alerts change
  useEffect(() => {
    setCurrentIndex(0);
  }, [alerts.length]);

  if (alerts.length === 0) {
    return (
      <div className="sticky top-0 z-40 border-b bg-emerald-900/60 border-emerald-500 text-emerald-100 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-2">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 shrink-0">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider opacity-80">LIVE</span>
            </div>
            <div className="w-px h-4 bg-current opacity-30" />
            <div className="flex items-center gap-2">
              <span className="text-base">✓</span>
              <span className="opacity-90">All clear — no active alerts</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const visibleAlerts = expanded
    ? alerts
    : alerts.slice(currentIndex, currentIndex + maxVisible);

  const hasMore = alerts.length > maxVisible;
  const hiddenCount = alerts.length - maxVisible;

  // Get highest priority for bar color
  const highestPriority = alerts[0]?.priority || 'low';

  return (
    <div className={`sticky top-0 z-40 border-b ${priorityColors[highestPriority]} backdrop-blur-sm`}>
      <div className="max-w-7xl mx-auto px-4 py-2">
        <div className="flex items-center gap-4">
          {/* Live indicator */}
          <div className="flex items-center gap-2 shrink-0">
            <span className={`w-2 h-2 rounded-full ${priorityDots[highestPriority]} animate-pulse`} />
            <span className="text-xs font-bold uppercase tracking-wider opacity-80">LIVE</span>
          </div>

          {/* Separator */}
          <div className="w-px h-4 bg-current opacity-30" />

          {/* Alerts */}
          <div className="flex-1 flex items-center gap-4 overflow-hidden">
            {visibleAlerts.map((alert, idx) => (
              <AlertItem key={alert.id} alert={alert} isFirst={idx === 0} />
            ))}
          </div>

          {/* More button */}
          {hasMore && (
            <>
              <div className="w-px h-4 bg-current opacity-30" />
              <button
                onClick={() => setExpanded(!expanded)}
                className="shrink-0 text-xs font-medium opacity-80 hover:opacity-100 transition-opacity"
              >
                {expanded ? 'Show less' : `+${hiddenCount} more`}
                <span className="ml-1">{expanded ? '▴' : '▾'}</span>
              </button>
            </>
          )}
        </div>

        {/* Expanded view */}
        {expanded && alerts.length > maxVisible && (
          <div className="mt-2 pt-2 border-t border-current/20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {alerts.slice(maxVisible).map(alert => (
              <AlertItem key={alert.id} alert={alert} compact />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface AlertItemProps {
  alert: WarRoomAlert;
  isFirst?: boolean;
  compact?: boolean;
}

function AlertItem({ alert, isFirst = false, compact = false }: AlertItemProps) {
  const content = (
    <div
      className={`flex items-center gap-2 ${compact ? 'py-1' : ''} ${
        isFirst ? 'font-medium' : 'opacity-90'
      } hover:opacity-100 transition-opacity cursor-pointer`}
    >
      <span className="text-base">{alert.icon}</span>
      <span className="truncate">
        <span className="font-medium">{alert.message}</span>
        {alert.detail && !compact && (
          <span className="opacity-70 ml-1 text-sm">• {alert.detail}</span>
        )}
      </span>
    </div>
  );

  if (alert.link) {
    return (
      <Link to={alert.link} className="min-w-0">
        {content}
      </Link>
    );
  }

  return <div className="min-w-0">{content}</div>;
}
