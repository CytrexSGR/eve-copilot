import { useState, useEffect } from 'react';
import { fontSize, color, spacing } from '../../../styles/theme';
import { formatIsk } from '../../../types/finance';
import { Sparkline } from './Sparkline';
import { formatTimeUntil } from '../../../types/timers';
import { corpApi } from '../../../services/corporationApi';
import { timerApi } from '../../../services/api/timers';
import type { OffensiveStats } from '../../../types/corporation';
import type { DefensiveStats } from '../../../types/corporation';
import type { TimerUpcomingResponse } from '../../../types/timers';

interface MilitarySectionProps {
  corpId: number;
  days: number;
}

// ---------------------------------------------------------------------------
// State types
// ---------------------------------------------------------------------------

interface DataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function initialState<T>(): DataState<T> {
  return { data: null, loading: true, error: null };
}

// ---------------------------------------------------------------------------
// Panel wrapper
// ---------------------------------------------------------------------------

function Panel({ title, borderColor, gridColumn, children }: {
  title: string;
  borderColor: string;
  gridColumn?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: `2px solid ${borderColor}`,
      gridColumn,
    }}>
      <div style={{
        fontSize: fontSize.xxs,
        textTransform: 'uppercase' as const,
        color: color.textSecondary,
        marginBottom: spacing.sm,
      }}>
        &middot; {title}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Horizontal bar helper
// ---------------------------------------------------------------------------

function HorizontalBar({ label, count, maxCount, barColor, percentage }: {
  label: string;
  count: number;
  maxCount: number;
  barColor: string;
  percentage: number;
}) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs }}>
        <span style={{ color: color.textPrimary }}>{label}</span>
        <span style={{ fontFamily: 'monospace', color: barColor }}>
          {count} ({percentage > 0 ? percentage.toFixed(1) : '0.0'}%)
        </span>
      </div>
      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '6px', overflow: 'hidden', marginTop: '2px' }}>
        <div style={{ background: barColor, height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mini loading / error helpers
// ---------------------------------------------------------------------------

function MiniLoader() {
  return (
    <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>Loading...</div>
  );
}

function MiniError({ message }: { message: string }) {
  return (
    <div style={{ color: color.lossRed, fontSize: fontSize.xxs }}>{message}</div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function MilitarySection({ corpId, days }: MilitarySectionProps) {
  const [offensive, setOffensive] = useState<DataState<OffensiveStats>>(initialState());
  const [defensive, setDefensive] = useState<DataState<DefensiveStats>>(initialState());
  const [timers, setTimers] = useState<DataState<TimerUpcomingResponse>>(initialState());

  useEffect(() => {
    let cancelled = false;

    // Reset all to loading
    setOffensive(initialState());
    setDefensive(initialState());
    setTimers(initialState());

    Promise.allSettled([
      corpApi.getOffensiveStats(corpId, days),   // 0: offensive
      corpApi.getDefensiveStats(corpId, days),    // 1: defensive
      timerApi.getUpcoming({ hours: 72 }),         // 2: timers
    ]).then(([offRes, defRes, timerRes]) => {
      if (cancelled) return;

      // Offensive
      if (offRes.status === 'fulfilled') {
        setOffensive({ data: offRes.value, loading: false, error: null });
      } else {
        setOffensive({ data: null, loading: false, error: 'Failed to load offensive stats' });
      }

      // Defensive
      if (defRes.status === 'fulfilled') {
        setDefensive({ data: defRes.value, loading: false, error: null });
      } else {
        setDefensive({ data: null, loading: false, error: 'Failed to load defensive stats' });
      }

      // Timers
      if (timerRes.status === 'fulfilled') {
        setTimers({ data: timerRes.value, loading: false, error: null });
      } else {
        setTimers({ data: null, loading: false, error: 'Failed to load timers' });
      }
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  return (
    <div>
      {/* Section header */}
      <div style={{
        fontSize: fontSize.xs,
        textTransform: 'uppercase' as const,
        color: color.textSecondary,
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        paddingBottom: spacing.sm,
        marginBottom: spacing.sm,
      }}>
        &middot; MILITARY &amp; WAR
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: spacing.base,
      }}>
        {/* 1. Combat Performance - full width */}
        <Panel title="Combat Performance" borderColor="#3fb950" gridColumn="1 / -1">
          <CombatPerformanceContent offState={offensive} defState={defensive} />
        </Panel>

        {/* 2. Kill Timeline - span 2 */}
        <Panel title="Kill Timeline" borderColor="#00d4ff" gridColumn="span 2">
          <KillTimelineContent state={offensive} />
        </Panel>

        {/* 3. Structure Timers */}
        <Panel title="Structure Timers" borderColor="#f85149">
          <StructureTimersContent state={timers} />
        </Panel>

        {/* 4. Hot Systems */}
        <Panel title="Hot Systems" borderColor="#14b8a6">
          <HotSystemsContent state={offensive} />
        </Panel>

        {/* 5. Losses */}
        <Panel title="Losses" borderColor="#ff8800">
          <LossesContent state={defensive} />
        </Panel>

        {/* 6. Fleet Activity */}
        <Panel title="Fleet Activity" borderColor="#58a6ff">
          <FleetActivityContent state={offensive} />
        </Panel>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. Combat Performance Content
// ---------------------------------------------------------------------------

function CombatPerformanceContent({ offState, defState }: {
  offState: DataState<OffensiveStats>;
  defState: DataState<DefensiveStats>;
}) {
  if (offState.loading || defState.loading) return <MiniLoader />;
  if (offState.error && defState.error) return <MiniError message={offState.error} />;

  const summary = offState.data?.summary;
  const defSummary = defState.data?.summary;
  const engagement = offState.data?.engagement_profile;

  const iskDestroyed = summary?.isk_destroyed ?? '--';
  const efficiency = summary?.efficiency ?? 0;
  const totalKills = summary?.total_kills ?? 0;
  const totalDeaths = defSummary?.total_deaths ?? 0;
  const soloKills = engagement?.solo?.kills ?? 0;

  // Efficiency color thresholds
  const effColor = efficiency >= 70 ? '#3fb950' : efficiency >= 50 ? '#d29922' : '#f85149';

  // Parse ISK destroyed - it's a formatted string like "123.4B ISK"
  // We display it as-is since formatIsk already formatted it
  const iskDisplay = typeof iskDestroyed === 'string' ? iskDestroyed : formatIsk(iskDestroyed);

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing.base }}>
      <StatCard label="ISK Destroyed" value={iskDisplay} valueColor="#00d4ff" />
      <StatCard label="Efficiency" value={`${isFinite(efficiency) ? efficiency.toFixed(1) : '0.0'}%`} valueColor={effColor} />
      <StatCard label="Kills" value={totalKills.toLocaleString()} valueColor="#3fb950" />
      <StatCard label="Deaths" value={totalDeaths.toLocaleString()} valueColor="#f85149" />
      <StatCard label="K/D Ratio" value={totalDeaths > 0 ? (totalKills / totalDeaths).toFixed(2) : totalKills > 0 ? totalKills.toFixed(0) : '0'} valueColor="#58a6ff" />
      <StatCard label="Solo Kills" value={soloKills.toLocaleString()} valueColor="#a855f7" />
    </div>
  );
}

function StatCard({ label, value, valueColor }: {
  label: string;
  value: string;
  valueColor: string;
}) {
  return (
    <div style={{ flex: 1, minWidth: '80px' }}>
      <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, textTransform: 'uppercase' as const }}>{label}</div>
      <div style={{ fontSize: fontSize.lg, fontFamily: 'monospace', color: valueColor, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. Kill Timeline Content
// ---------------------------------------------------------------------------

function KillTimelineContent({ state }: { state: DataState<OffensiveStats> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const timeline = state.data.kill_timeline;
  if (!timeline || timeline.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No kill data</div>;
  }

  const killData = timeline.map(d => d.kills ?? 0);
  const totalDays = timeline.length;
  const totalKills = timeline.reduce((sum, d) => sum + (d.kills ?? 0), 0);
  const avgKillsPerDay = totalDays > 0 ? totalKills / totalDays : 0;

  // Find peak day
  let peakKills = 0;
  let peakDate = '';
  for (const day of timeline) {
    const k = day.kills ?? 0;
    if (k > peakKills) {
      peakKills = k;
      peakDate = day.day;
    }
  }

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ marginBottom: spacing.sm }}>
        <Sparkline
          data={killData}
          width={400}
          height={48}
          color="#00d4ff"
        />
      </div>
      <div style={{ display: 'flex', gap: spacing.lg, flexWrap: 'wrap', marginBottom: spacing.sm }}>
        <div>
          <span style={{ color: color.textSecondary }}>Period: </span>
          <span style={{ fontFamily: 'monospace', color: color.textPrimary }}>{totalDays} days</span>
        </div>
        <div>
          <span style={{ color: color.textSecondary }}>Total: </span>
          <span style={{ fontFamily: 'monospace', color: '#00d4ff' }}>{totalKills.toLocaleString()} kills</span>
        </div>
      </div>
      <div>
        <span style={{ color: color.textSecondary }}>Avg: </span>
        <span style={{ fontFamily: 'monospace', color: color.textPrimary }}>
          {isFinite(avgKillsPerDay) ? avgKillsPerDay.toFixed(1) : '0.0'} kills/day
        </span>
        <span style={{ color: color.textSecondary }}> | Peak: </span>
        <span style={{ fontFamily: 'monospace', color: '#3fb950' }}>
          {peakKills} kills
        </span>
        {peakDate && (
          <span style={{ color: color.textSecondary }}> on {peakDate}</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. Structure Timers Content
// ---------------------------------------------------------------------------

function StructureTimersContent({ state }: { state: DataState<TimerUpcomingResponse> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>
        Timer data unavailable
      </div>
    );
  }

  const allTimers = state.data.timers;
  if (!allTimers || allTimers.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No active structure timers</div>;
  }

  // Sort by hoursUntil ascending, take top 5
  const sorted = [...allTimers]
    .sort((a, b) => a.hoursUntil - b.hoursUntil)
    .slice(0, 5);

  return (
    <div>
      {sorted.map((timer) => {
        const h = timer.hoursUntil;
        let badgeLabel: string;
        let badgeBg: string;

        if (h < 24) {
          badgeLabel = 'CRITICAL';
          badgeBg = '#f85149';
        } else if (h < 72) {
          badgeLabel = 'UPCOMING';
          badgeBg = '#d29922';
        } else {
          badgeLabel = 'SCHEDULED';
          badgeBg = '#8b949e';
        }

        return (
          <div key={timer.id} style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: fontSize.xxs,
            marginBottom: spacing.xs,
            gap: spacing.xs,
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: color.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {timer.structureName}
              </div>
              <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>
                {timer.systemName}
              </div>
            </div>
            <div style={{ fontFamily: 'monospace', color: color.textSecondary, whiteSpace: 'nowrap', fontSize: fontSize.tiny }}>
              {formatTimeUntil(h)}
            </div>
            <span style={{
              fontSize: fontSize.pico,
              fontWeight: 700,
              padding: '2px 5px',
              borderRadius: '2px',
              background: badgeBg,
              color: '#000',
              whiteSpace: 'nowrap',
            }}>
              {badgeLabel}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Hot Systems Content
// ---------------------------------------------------------------------------

function HotSystemsContent({ state }: { state: DataState<OffensiveStats> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const hotSystems = state.data.hot_systems;
  if (!hotSystems || hotSystems.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No hot system data</div>;
  }

  const top3 = [...hotSystems]
    .sort((a, b) => b.kills - a.kills)
    .slice(0, 3);

  const maxKills = Math.max(...top3.map(s => s.kills), 0);

  return (
    <div>
      {top3.map((sys, idx) => {
        const pct = maxKills > 0 ? (sys.kills / maxKills) * 100 : 0;
        return (
          <div key={idx} style={{ marginBottom: spacing.sm }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs }}>
              <span style={{ color: color.textPrimary }}>
                {sys.system_name}{' '}
                <span style={{ color: color.textSecondary }}>({sys.region_name})</span>
              </span>
              <span style={{ fontFamily: 'monospace', color: '#14b8a6' }}>{sys.kills} kills</span>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '6px', overflow: 'hidden', marginTop: '2px' }}>
              <div style={{ background: '#14b8a6', height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 5. Losses Content
// ---------------------------------------------------------------------------

function LossesContent({ state }: { state: DataState<DefensiveStats> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>
        No losses recorded
      </div>
    );
  }

  const summary = state.data.summary;
  const highValueLosses = state.data.high_value_losses;
  const shipLosses = state.data.ship_losses;

  const totalDeaths = summary?.total_deaths ?? 0;
  const iskLost = summary?.isk_lost ?? '0 ISK';

  if (totalDeaths === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No losses recorded</div>;
  }

  // Biggest loss
  const biggestLoss = highValueLosses && highValueLosses.length > 0
    ? [...highValueLosses].sort((a, b) => b.isk_value - a.isk_value)[0]
    : null;

  // Most-lost ship class
  let mostLostClass = '';
  let mostLostCount = 0;
  if (shipLosses && shipLosses.length > 0) {
    for (const sc of shipLosses) {
      if (sc.count > mostLostCount) {
        mostLostCount = sc.count;
        mostLostClass = sc.ship_class;
      }
    }
  }

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ marginBottom: spacing.xs }}>
        <span style={{ color: color.textSecondary }}>Total: </span>
        <span style={{ fontFamily: 'monospace', color: '#ff8800' }}>{totalDeaths.toLocaleString()}</span>
        <span style={{ color: color.textSecondary }}> losses | </span>
        <span style={{ fontFamily: 'monospace', color: '#ff8800' }}>{iskLost}</span>
      </div>

      {biggestLoss && (
        <div style={{ marginBottom: spacing.xs }}>
          <span style={{ color: color.textSecondary }}>Biggest: </span>
          <span style={{ color: color.textPrimary }}>{biggestLoss.ship_name ?? 'Unknown'}</span>
          <span style={{ color: color.textSecondary }}> — </span>
          <span style={{ fontFamily: 'monospace', color: '#f85149' }}>{formatIsk(biggestLoss.isk_value)}</span>
          {biggestLoss.system_name && (
            <span style={{ color: color.textSecondary }}> in {biggestLoss.system_name}</span>
          )}
        </div>
      )}

      {mostLostClass && (
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: spacing.xs }}>
          <span style={{ color: color.textSecondary }}>Most Lost: </span>
          <span style={{ color: color.textPrimary }}>{mostLostClass}</span>
          <span style={{ color: color.textSecondary }}> ({mostLostCount})</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 6. Fleet Activity Content
// ---------------------------------------------------------------------------

function FleetActivityContent({ state }: { state: DataState<OffensiveStats> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const profile = state.data.engagement_profile;
  if (!profile) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No engagement data</div>;
  }

  const entries = [
    { label: 'Solo', kills: profile.solo?.kills ?? 0, percentage: profile.solo?.percentage ?? 0 },
    { label: 'Small Gang', kills: profile.small?.kills ?? 0, percentage: profile.small?.percentage ?? 0 },
    { label: 'Medium Fleet', kills: profile.medium?.kills ?? 0, percentage: profile.medium?.percentage ?? 0 },
    { label: 'Large Fleet', kills: profile.large?.kills ?? 0, percentage: profile.large?.percentage ?? 0 },
  ];

  const totalKills = entries.reduce((s, e) => s + e.kills, 0);
  if (totalKills === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No engagement data</div>;
  }

  const maxKills = Math.max(...entries.map(e => e.kills), 0);

  return (
    <div>
      {entries.map((entry, idx) => (
        <HorizontalBar
          key={idx}
          label={entry.label}
          count={entry.kills}
          maxCount={maxKills}
          barColor="#58a6ff"
          percentage={entry.percentage}
        />
      ))}
    </div>
  );
}
