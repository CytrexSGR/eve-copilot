import { useState, useEffect } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { applicationApi, activityApi } from '../../../services/api/hr';
import { SectionCard } from './SectionCard';
import type { InactiveMember } from '../../../types/hr';

interface PersonnelCardProps {
  corpId: number;
}

/** Module-level ESI cache (same pattern as CorpPageHeader). */
const esiCache: Record<number, number> = {};

function getActiveColor(pct: number): string {
  if (pct >= 75) return '#3fb950';
  if (pct >= 50) return '#d29922';
  return '#f85149';
}

export function PersonnelCard({ corpId }: PersonnelCardProps) {
  const [memberCount, setMemberCount] = useState<number | null>(
    esiCache[corpId] ?? null,
  );
  const [pendingApps, setPendingApps] = useState<number>(0);
  const [inactiveMembers, setInactiveMembers] = useState<InactiveMember[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const fetchEsi = esiCache[corpId]
      ? Promise.resolve(esiCache[corpId])
      : fetch(`https://esi.evetech.net/latest/corporations/${corpId}/`)
          .then(r => r.json())
          .then(data => {
            const count = data.member_count ?? 0;
            esiCache[corpId] = count;
            return count;
          })
          .catch(() => 0);

    Promise.allSettled([
      fetchEsi,
      applicationApi.getApplications({ status: 'pending' }),
      activityApi.getInactive(30),
    ]).then(([esiResult, appsResult, inactiveResult]) => {
      if (cancelled) return;

      if (esiResult.status === 'fulfilled') {
        setMemberCount(esiResult.value as number);
      }
      if (appsResult.status === 'fulfilled') {
        const result = appsResult.value as { applications: unknown[]; count: number };
        setPendingApps(result.count ?? 0);
      }
      if (inactiveResult.status === 'fulfilled') {
        setInactiveMembers(inactiveResult.value as InactiveMember[]);
      }

      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [corpId]);

  const members = memberCount ?? 0;
  const inactiveCount = inactiveMembers.length;
  const activeCount = Math.max(0, members - inactiveCount);
  const activePct = members > 0 ? (activeCount / members) * 100 : 0;
  const activeColor = getActiveColor(activePct);

  return (
    <SectionCard
      title="Personnel"
      borderColor="#00d4ff"
      linkTo="/corp/hr"
      loading={loading}
    >
      {/* Members */}
      <div style={{
        fontSize: fontSize.base,
        fontWeight: 700,
        color: color.textPrimary,
      }}>
        {members > 0 ? `${members.toLocaleString()} Members` : '--'}
      </div>

      {/* Active ratio bar */}
      <div
        style={{
          background: 'rgba(255,255,255,0.1)',
          height: '6px',
          borderRadius: '3px',
          margin: '0.25rem 0',
        }}
      >
        <div
          style={{
            width: `${Math.min(activePct, 100)}%`,
            background: activeColor,
            height: '100%',
            borderRadius: '3px',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      <div style={{
        fontSize: fontSize.tiny,
        color: activeColor,
      }}>
        {activePct.toFixed(0)}% Active (30D)
      </div>

      {/* Stats row */}
      <div style={{
        display: 'flex',
        gap: '0.75rem',
        marginTop: '0.25rem',
        fontSize: fontSize.tiny,
      }}>
        <span style={{
          color: pendingApps > 0 ? '#d29922' : color.killGreen,
        }}>
          {pendingApps} Pending Applications
        </span>
        <span style={{
          color: inactiveCount > 10 ? color.lossRed : color.textSecondary,
        }}>
          {inactiveCount} Inactive (30D)
        </span>
      </div>
    </SectionCard>
  );
}
