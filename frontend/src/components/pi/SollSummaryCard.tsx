import { useQuery } from '@tanstack/react-query';
import { Target, TrendingDown, TrendingUp, HelpCircle } from 'lucide-react';
import { getProjectSollSummary, type PIProjectSollSummary } from '../../api/pi';

interface SollSummaryCardProps {
  projectId: number;
}

export function SollSummaryCard({ projectId }: SollSummaryCardProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['pi-soll-summary', projectId],
    queryFn: () => getProjectSollSummary(projectId),
    enabled: projectId > 0,
  });

  if (isLoading || !data) {
    return null;
  }

  const varianceClass =
    Math.abs(data.overall_variance_percent) <= 5 ? 'neutral' :
    data.overall_variance_percent > 0 ? 'positive' : 'negative';

  const totalMaterials =
    data.materials_on_target +
    data.materials_under_target +
    data.materials_over_target +
    data.materials_no_soll;

  // Don't show if no SOLL values are set
  if (data.materials_no_soll === totalMaterials) {
    return null;
  }

  return (
    <div className="soll-summary-card">
      <div className="soll-summary-header">
        <span className="soll-summary-title">
          <Target size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          SOLL vs IST
        </span>
        <span className={`soll-summary-variance ${varianceClass}`}>
          {data.overall_variance_percent > 0 ? '+' : ''}
          {data.overall_variance_percent.toFixed(1)}%
        </span>
      </div>
      <div className="soll-summary-stats">
        <div className="soll-stat on-target">
          <div className="soll-stat-value">{data.materials_on_target}</div>
          <div className="soll-stat-label">On Target</div>
        </div>
        <div className="soll-stat under-target">
          <div className="soll-stat-value">{data.materials_under_target}</div>
          <div className="soll-stat-label">Under</div>
        </div>
        <div className="soll-stat over-target">
          <div className="soll-stat-value">{data.materials_over_target}</div>
          <div className="soll-stat-label">Over</div>
        </div>
        <div className="soll-stat">
          <div className="soll-stat-value">{data.materials_no_soll}</div>
          <div className="soll-stat-label">No SOLL</div>
        </div>
      </div>
    </div>
  );
}
