import { Link } from 'react-router-dom';
import { PowerList } from './PowerList';
import { COLORS } from '../../constants';
import type { PowerAssessment } from '../../types/reports';

interface PowerDynamicsSectionProps {
  powerAssessment: PowerAssessment | null;
  activityMinutes: number;
}

export function PowerDynamicsSection({
  powerAssessment,
  activityMinutes,
}: PowerDynamicsSectionProps) {
  const timeLabel = activityMinutes < 60 ? `${activityMinutes}m` : `${activityMinutes / 60}h`;
  const risingCount = powerAssessment?.gaining_power?.filter(e => typeof e !== 'string').length || 0;
  const fallingCount = powerAssessment?.losing_power?.filter(e => typeof e !== 'string').length || 0;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ff8800' }} />
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase' }}>
            Alliance Dynamics
          </span>
          <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
            {timeLabel}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.6rem' }}>
            {risingCount > 0 && (
              <span style={{ color: COLORS.positive }}>{risingCount} rising</span>
            )}
            {fallingCount > 0 && (
              <span style={{ color: COLORS.negative }}>{fallingCount} falling</span>
            )}
          </div>
          <Link
            to="/battle-report#alliances"
            style={{
              padding: '3px 8px',
              background: 'rgba(0, 212, 255, 0.1)',
              color: '#00d4ff',
              borderRadius: '3px',
              textDecoration: 'none',
              fontSize: '0.6rem',
              fontWeight: 600,
              border: '1px solid rgba(0, 212, 255, 0.2)',
              textTransform: 'uppercase',
            }}
          >
            Full Intel
          </Link>
        </div>
      </div>

      {/* Content - 2 Column Grid: Rising | Falling */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {powerAssessment ? (
          <PowerList entries={powerAssessment.gaining_power} type="rising" />
        ) : (
          <EmptyState message="No power data" />
        )}
        {powerAssessment ? (
          <PowerList entries={powerAssessment.losing_power} type="falling" />
        ) : (
          <EmptyState message="No power data" />
        )}
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{
      padding: '0.75rem',
      textAlign: 'center',
      color: 'rgba(255,255,255,0.3)',
      fontSize: '0.65rem',
    }}>
      {message}
    </div>
  );
}
