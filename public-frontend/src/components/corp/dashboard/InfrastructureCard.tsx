import { useState, useEffect } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { timerApi } from '../../../services/api/timers';
import { SectionCard } from './SectionCard';
import type { StructureTimer } from '../../../types/timers';

function formatCountdown(ms: number): string {
  if (ms <= 0) return 'Expired';
  const hours = ms / (1000 * 60 * 60);
  if (hours >= 24) {
    const d = Math.floor(hours / 24);
    const h = Math.round(hours % 24);
    return `${d}d ${h}h`;
  }
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return `${h}h ${m}m`;
}

export function InfrastructureCard() {
  const [timers, setTimers] = useState<StructureTimer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    timerApi.getUpcoming({ hours: 168 }).then((response) => {
      if (cancelled) return;
      setTimers(response.timers || []);
      setLoading(false);
    }).catch(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const activeCount = timers.length;

  const now = Date.now();
  const criticalCount = timers.filter((t) => {
    const end = new Date(t.timerEnd).getTime();
    return end - now > 0 && end - now < 24 * 60 * 60 * 1000;
  }).length;

  // Sort by timerEnd to find the next one
  const sorted = [...timers]
    .filter((t) => new Date(t.timerEnd).getTime() > now)
    .sort((a, b) => new Date(a.timerEnd).getTime() - new Date(b.timerEnd).getTime());
  const nextTimer = sorted[0] || null;

  return (
    <SectionCard
      title="Infrastructure"
      borderColor="#d29922"
      linkTo="/corp/timers"
      loading={loading}
    >
      {activeCount > 0 ? (
        <>
          {/* Active timer count */}
          <div
            style={{
              fontSize: fontSize.base,
              fontWeight: 700,
              color: color.textPrimary,
            }}
          >
            {activeCount} Active Timer{activeCount !== 1 ? 's' : ''}
          </div>

          {/* Critical count */}
          {criticalCount > 0 && (
            <div
              style={{
                fontSize: fontSize.tiny,
                fontWeight: 600,
                color: color.lossRed,
                marginTop: '0.15rem',
              }}
            >
              {criticalCount} Critical (&lt;24h)
            </div>
          )}

          {/* Next timer */}
          {nextTimer && (
            <div
              style={{
                fontSize: fontSize.tiny,
                color: color.textSecondary,
                marginTop: '0.25rem',
              }}
            >
              <span style={{ color: color.warningOrange }}>Next: </span>
              {nextTimer.structureName}
              {nextTimer.systemName ? ` (${nextTimer.systemName})` : ''}
              {' \u2014 '}
              <span style={{ fontFamily: 'monospace', fontWeight: 600, color: color.textPrimary }}>
                {formatCountdown(new Date(nextTimer.timerEnd).getTime() - now)}
              </span>
            </div>
          )}
        </>
      ) : (
        <div
          style={{
            fontSize: fontSize.base,
            color: color.textSecondary,
          }}
        >
          No active timers
        </div>
      )}
    </SectionCard>
  );
}
