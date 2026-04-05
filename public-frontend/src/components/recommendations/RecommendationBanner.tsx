import type { PersonalizedScore } from '../../hooks/usePersonalizedScore';
import { formatISK } from '../../utils/format';

export function RecommendationBanner({ ps, compact = false }: { ps: PersonalizedScore; compact?: boolean }) {
  if (compact) {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
        fontSize: '0.6rem', color: ps.canAfford && ps.hasSkills ? '#3fb950' : '#ffcc00',
      }}>
        {ps.canAfford ? 'ISK OK' : 'Need ISK'}
        {' | '}
        {ps.iskPerHour > 0 ? `${formatISK(ps.iskPerHour)}/h` : '--'}
      </span>
    );
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem',
      padding: '0.3rem 0.5rem', background: 'rgba(0,212,255,0.04)',
      border: '1px solid rgba(0,212,255,0.1)', borderRadius: '4px',
      fontSize: '0.65rem', marginBottom: '0.25rem',
    }}>
      <span style={{ color: '#00d4ff', fontWeight: 700 }}>YOU:</span>
      <span style={{ color: ps.canAfford ? '#3fb950' : '#f85149' }}>
        {ps.canAfford ? 'Can Afford' : `Need ${ps.affordPercent.toFixed(0)}% ISK`}
      </span>
      <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
      <span style={{ color: ps.hasSkills ? '#3fb950' : '#ffcc00' }}>
        {ps.hasSkills ? 'Skills OK' : `${ps.missingSkillCount} skills missing`}
      </span>
      <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
      <span style={{ color: '#a855f7' }}>
        {ps.iskPerHour > 0 ? `~${formatISK(ps.iskPerHour)}/h` : '--'}
      </span>
      <span style={{ flex: 1 }} />
      <span style={{ color: 'rgba(255,255,255,0.35)', fontStyle: 'italic' }}>
        {ps.recommendation}
      </span>
    </div>
  );
}
