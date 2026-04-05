import { useState, useEffect } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { srpApi } from '../../../services/api/srp';
import { formatIsk } from '../../../types/finance';
import { SectionCard } from './SectionCard';
import type { SrpRequest } from '../../../types/srp';

interface DefenseCardProps {
  corpId: number;
}

export function DefenseCard({ corpId }: DefenseCardProps) {
  const [pendingRequests, setPendingRequests] = useState<SrpRequest[]>([]);
  const [approvedRequests, setApprovedRequests] = useState<SrpRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      srpApi.getRequests(corpId, { status: 'pending' }),
      srpApi.getRequests(corpId, { status: 'approved', limit: 100 }),
    ]).then(([pendingResult, approvedResult]) => {
      if (cancelled) return;

      if (pendingResult.status === 'fulfilled') {
        setPendingRequests(pendingResult.value);
      }
      if (approvedResult.status === 'fulfilled') {
        setApprovedRequests(approvedResult.value);
      }

      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [corpId]);

  const pendingCount = pendingRequests.length;
  const approvedCount = approvedRequests.length;

  const totalPayout = approvedRequests.reduce((sum, req) => {
    const amount = req.payout_amount || 0;
    return sum + amount;
  }, 0);

  return (
    <SectionCard
      title="Ship Replacement"
      borderColor="#ff8800"
      linkTo="/corp/srp"
      loading={loading}
    >
      {/* Pending requests */}
      <div
        style={{
          fontSize: fontSize.base,
          fontWeight: 700,
          color: pendingCount > 0 ? color.lossRed : color.killGreen,
        }}
      >
        {pendingCount} Pending Request{pendingCount !== 1 ? 's' : ''}
      </div>

      {/* Approved count */}
      <div
        style={{
          fontSize: fontSize.tiny,
          color: color.textSecondary,
          marginTop: '0.15rem',
        }}
      >
        {approvedCount} Approved
      </div>

      {/* Payout estimate */}
      <div
        style={{
          fontSize: fontSize.tiny,
          fontFamily: 'monospace',
          color: color.textSecondary,
          marginTop: '0.15rem',
        }}
      >
        {totalPayout > 0 ? `~${formatIsk(totalPayout)} in payouts` : '\u2014'}
      </div>
    </SectionCard>
  );
}
