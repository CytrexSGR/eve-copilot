import { useState, useEffect } from 'react';
import { fontSize, color, spacing } from '../../../styles/theme';
import { activityApi, applicationApi, redListApi } from '../../../services/api/hr';
import type { InactiveMember, HrApplication, RedListEntity } from '../../../types/hr';

interface PersonnelSectionProps {
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

export function PersonnelSection({ corpId, days }: PersonnelSectionProps) {
  const [inactive, setInactive] = useState<DataState<InactiveMember[]>>(initialState());
  const [applications, setApplications] = useState<DataState<{ applications: HrApplication[]; count: number }>>(initialState());
  const [redList, setRedList] = useState<DataState<RedListEntity[]>>(initialState());

  useEffect(() => {
    let cancelled = false;

    setInactive(initialState());
    setApplications(initialState());
    setRedList(initialState());

    Promise.allSettled([
      activityApi.getInactive(30),
      applicationApi.getApplications({ limit: 50 }),
      redListApi.getEntries({ active_only: true }),
    ]).then(([inactiveRes, appRes, redRes]) => {
      if (cancelled) return;

      if (inactiveRes.status === 'fulfilled') {
        setInactive({ data: inactiveRes.value, loading: false, error: null });
      } else {
        setInactive({ data: null, loading: false, error: 'Failed to load inactive members' });
      }

      if (appRes.status === 'fulfilled') {
        setApplications({ data: appRes.value, loading: false, error: null });
      } else {
        setApplications({ data: null, loading: false, error: 'Failed to load applications' });
      }

      if (redRes.status === 'fulfilled') {
        setRedList({ data: redRes.value, loading: false, error: null });
      } else {
        setRedList({ data: null, loading: false, error: 'Failed to load red list' });
      }
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  return (
    <div>
      {/* Section header */}
      <div style={{
        fontSize: fontSize.xxs,
        textTransform: 'uppercase' as const,
        color: color.textSecondary,
        marginBottom: spacing.sm,
        letterSpacing: '0.05em',
      }}>
        &middot; PERSONNEL &amp; SECURITY
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: spacing.base,
      }}>
        {/* 1. Member Overview - span 2 */}
        <Panel title="Member Overview" borderColor="#58a6ff" gridColumn="span 2">
          <MemberOverviewContent state={inactive} />
        </Panel>

        {/* 2. Activity Health */}
        <Panel title="Activity Health" borderColor="#3fb950">
          <ActivityHealthContent state={inactive} />
        </Panel>

        {/* 3. Applications */}
        <Panel title="Applications" borderColor="#d29922">
          <ApplicationsContent state={applications} />
        </Panel>

        {/* 4. Red List */}
        <Panel title="Red List" borderColor="#f85149">
          <RedListContent state={redList} />
        </Panel>

        {/* 5. Recent Vetting */}
        <Panel title="Recent Vetting" borderColor="#a855f7">
          <RecentVettingContent state={applications} />
        </Panel>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. Member Overview Content
// ---------------------------------------------------------------------------

function MemberOverviewContent({ state }: { state: DataState<InactiveMember[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const members = state.data;
  const totalInactive = members.length;
  const inactive7d = members.filter(m => m.days_inactive <= 7).length;
  const inactive90d = members.filter(m => m.days_inactive >= 90).length;
  const noKills30d = members.filter(m => m.kill_count_30d === 0).length;

  const stats = [
    { label: 'Inactive (30D)', value: totalInactive, valueColor: '#ff8800' },
    { label: 'Inactive (7D)', value: inactive7d, valueColor: '#ff8800' },
    { label: 'Inactive (90D)', value: inactive90d, valueColor: '#f85149' },
    { label: '0 Kills (30D)', value: noKills30d, valueColor: color.textPrimary },
  ];

  return (
    <div style={{ display: 'flex', gap: spacing.lg, flexWrap: 'wrap' }}>
      {stats.map((stat, idx) => (
        <div key={idx} style={{ minWidth: '80px' }}>
          <div style={{
            fontSize: fontSize.tiny,
            textTransform: 'uppercase' as const,
            color: color.textSecondary,
            marginBottom: '2px',
          }}>
            {stat.label}
          </div>
          <div style={{
            fontSize: fontSize.lg,
            fontFamily: 'monospace',
            fontWeight: 700,
            color: stat.valueColor,
          }}>
            {stat.value}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. Activity Health Content
// ---------------------------------------------------------------------------

function ActivityHealthContent({ state }: { state: DataState<InactiveMember[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const members = state.data;
  const inactiveCount = members.length;
  const hasAlert = members.some(m => m.days_inactive > 90);

  // Top 3 longest-inactive
  const topInactive = [...members]
    .sort((a, b) => b.days_inactive - a.days_inactive)
    .slice(0, 3);

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.sm }}>
        <span style={{ color: '#ff8800' }}>{inactiveCount} members inactive (30D)</span>
        {hasAlert && (
          <span style={{
            fontSize: fontSize.pico,
            fontWeight: 700,
            background: '#f85149',
            color: '#000',
            padding: '2px 5px',
            borderRadius: '2px',
          }}>
            ALERT
          </span>
        )}
      </div>

      {topInactive.length > 0 && (
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.06)',
          paddingTop: spacing.xs,
        }}>
          {topInactive.map((m, idx) => (
            <div key={idx} style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '2px',
            }}>
              <span style={{ color: color.textPrimary }}>{m.character_name}</span>
              <span style={{
                fontFamily: 'monospace',
                color: m.days_inactive >= 90 ? '#f85149' : '#ff8800',
              }}>
                {m.days_inactive}d
              </span>
            </div>
          ))}
        </div>
      )}

      {topInactive.length === 0 && (
        <div style={{ color: color.textSecondary }}>No inactive members</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. Applications Content
// ---------------------------------------------------------------------------

function ApplicationsContent({ state }: { state: DataState<{ applications: HrApplication[]; count: number }> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const { applications, count } = state.data;

  if (applications.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No applications</div>;
  }

  const statusCounts: Record<string, number> = {
    pending: 0,
    reviewing: 0,
    approved: 0,
    rejected: 0,
  };

  for (const app of applications) {
    if (app.status in statusCounts) {
      statusCounts[app.status]++;
    }
  }

  const statusConfig: { key: string; label: string; badgeColor: string }[] = [
    { key: 'pending', label: 'Pending', badgeColor: '#d29922' },
    { key: 'reviewing', label: 'Reviewing', badgeColor: '#58a6ff' },
    { key: 'approved', label: 'Approved', badgeColor: '#3fb950' },
    { key: 'rejected', label: 'Rejected', badgeColor: '#f85149' },
  ];

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing.sm, marginBottom: spacing.sm }}>
        {statusConfig.map(s => (
          <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span style={{
              fontSize: fontSize.pico,
              fontWeight: 700,
              background: s.badgeColor,
              color: '#000',
              padding: '2px 5px',
              borderRadius: '2px',
              display: 'inline-block',
            }}>
              {s.label}
            </span>
            <span style={{ color: color.textPrimary, fontFamily: 'monospace' }}>
              {statusCounts[s.key]}
            </span>
          </div>
        ))}
      </div>
      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        paddingTop: spacing.xs,
        color: color.textSecondary,
      }}>
        Total: <span style={{ fontFamily: 'monospace', color: color.textPrimary }}>{count}</span> applications
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Red List Content
// ---------------------------------------------------------------------------

function RedListContent({ state }: { state: DataState<RedListEntity[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const entries = state.data;
  const activeEntries = entries.filter(e => e.active);

  if (activeEntries.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>Red list is clean</div>;
  }

  // Group by category
  const byCategory: Record<string, number> = {};
  for (const e of activeEntries) {
    byCategory[e.category] = (byCategory[e.category] || 0) + 1;
  }

  // Last 3 additions
  const recent = [...activeEntries]
    .sort((a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime())
    .slice(0, 3);

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ marginBottom: spacing.sm }}>
        <span style={{ color: '#f85149', fontWeight: 600 }}>{activeEntries.length}</span>
        <span style={{ color: color.textSecondary }}> active entities</span>
        {Object.keys(byCategory).length > 0 && (
          <span style={{ color: color.textTertiary }}>
            {' '}({Object.entries(byCategory).map(([cat, cnt]) => `${cnt} ${cat}`).join(', ')})
          </span>
        )}
      </div>

      {recent.length > 0 && (
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.06)',
          paddingTop: spacing.xs,
        }}>
          {recent.map((e, idx) => (
            <div key={idx} style={{ marginBottom: '3px' }}>
              <div style={{ display: 'flex', gap: spacing.xs, alignItems: 'center' }}>
                <span style={{ color: color.textPrimary }}>{e.entity_name}</span>
                <span style={{
                  fontSize: fontSize.pico,
                  color: color.textTertiary,
                  textTransform: 'uppercase' as const,
                }}>
                  {e.category}
                </span>
              </div>
              <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>
                {e.reason.length > 50 ? e.reason.slice(0, 50) + '...' : e.reason}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 5. Recent Vetting Content
// ---------------------------------------------------------------------------

function RecentVettingContent({ state }: { state: DataState<{ applications: HrApplication[]; count: number }> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const { applications } = state.data;

  // Applications that are approved or reviewing (have some vetting activity)
  const vettedApps = applications
    .filter(a => a.status === 'approved' || a.status === 'reviewing')
    .sort((a, b) => new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime())
    .slice(0, 3);

  if (vettedApps.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No recent vetting reports</div>;
  }

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ color: color.textSecondary, marginBottom: spacing.sm }}>
        Recent applications with vetting
      </div>

      {vettedApps.map((app, idx) => (
        <div key={idx} style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '3px',
        }}>
          <span style={{ color: color.textPrimary }}>{app.character_name}</span>
          <span style={{
            fontSize: fontSize.pico,
            fontWeight: 700,
            background: app.status === 'approved' ? '#3fb950' : '#58a6ff',
            color: '#000',
            padding: '2px 5px',
            borderRadius: '2px',
          }}>
            {app.status.toUpperCase()}
          </span>
        </div>
      ))}

      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        paddingTop: spacing.xs,
        marginTop: spacing.xs,
        color: color.textTertiary,
        fontSize: fontSize.tiny,
      }}>
        See HR for full reports
      </div>
    </div>
  );
}
