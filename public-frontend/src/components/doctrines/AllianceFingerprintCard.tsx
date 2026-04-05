import { Link } from 'react-router-dom';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { AllianceFingerprint } from '../../types/reports';

// ============== Helper ==============

function formatNumber(value: number): string {
  if (value >= 1000000000) {
    return (value / 1000000000).toFixed(1) + 'B';
  }
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + 'M';
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(1) + 'K';
  }
  return value.toLocaleString();
}

// ============== Component ==============

interface AllianceFingerprintCardProps {
  fingerprint: AllianceFingerprint;
  isExpanded: boolean;
  onToggle: () => void;
}

export function AllianceFingerprintCard({ fingerprint, isExpanded, onToggle }: AllianceFingerprintCardProps) {
  const topShips = fingerprint.ship_fingerprint.slice(0, 5);

  return (
    <div style={{
      padding: '1.5rem',
      backgroundColor: 'var(--surface)',
      borderRadius: '8px',
      border: '1px solid var(--border)',
      cursor: 'pointer',
      transition: 'border-color 0.2s'
    }}>
      {/* Header */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: isExpanded ? '1.5rem' : 0,
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <Link
              to={`/alliance/${fingerprint.alliance_id}`}
              onClick={(e) => e.stopPropagation()}
              style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: 'var(--accent-blue)',
                textDecoration: 'none'
              }}
            >
              {fingerprint.alliance_name}
            </Link>
            <span style={{
              padding: '0.25rem 0.5rem',
              backgroundColor: 'var(--surface-elevated)',
              borderRadius: '4px',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)'
            }}>
              {fingerprint.primary_doctrine}
            </span>
          </div>

          <div style={{
            display: 'flex',
            gap: '1.5rem',
            flexWrap: 'wrap',
            fontSize: '0.9rem',
            color: 'var(--text-secondary)'
          }}>
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Ships Used:</strong>{' '}
              {formatNumber(fingerprint.total_uses)}
            </span>
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Unique:</strong>{' '}
              {fingerprint.unique_ships}
            </span>
            {fingerprint.coalition_leader_name && (
              <span>
                <strong style={{ color: 'var(--text-primary)' }}>Coalition:</strong>{' '}
                <span style={{ color: 'var(--accent-purple)' }}>{fingerprint.coalition_leader_name}</span>
              </span>
            )}
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Period:</strong>{' '}
              {fingerprint.data_period_days} days
            </span>
          </div>

          {/* Top Ships Preview */}
          <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>Top Ships:</strong>{' '}
            {topShips.map((ship, idx) => (
              <span key={ship.type_id}>
                {idx > 0 && ', '}
                <span style={{ color: 'var(--text-primary)' }}>{ship.type_name}</span>
                {' '}({ship.percentage.toFixed(1)}%)
              </span>
            ))}
          </div>
        </div>

        <div style={{ color: 'var(--text-secondary)' }}>
          {isExpanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
        </div>
      </div>

      {/* Expanded Content - Full Ship Breakdown */}
      {isExpanded && (
        <div style={{
          borderTop: '1px solid var(--border)',
          paddingTop: '1.5rem'
        }}>
          <h4 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Ship Breakdown</h4>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
            gap: '0.5rem'
          }}>
            {fingerprint.ship_fingerprint.slice(0, 20).map((ship) => (
              <div
                key={ship.type_id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.5rem 0.75rem',
                  backgroundColor: 'var(--surface-elevated)',
                  borderRadius: '4px'
                }}
              >
                <div>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{ship.type_name}</span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginLeft: '0.5rem' }}>
                    ({ship.ship_class})
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    {ship.uses} uses
                  </span>
                  <span style={{
                    padding: '0.2rem 0.5rem',
                    backgroundColor: 'var(--accent-blue)',
                    color: '#fff',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 600
                  }}>
                    {ship.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
          {fingerprint.ship_fingerprint.length > 20 && (
            <p style={{ marginTop: '0.75rem', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
              +{fingerprint.ship_fingerprint.length - 20} more ships
            </p>
          )}
        </div>
      )}
    </div>
  );
}
