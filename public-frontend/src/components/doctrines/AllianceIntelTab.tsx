import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { fingerprintApi } from '../../services/api';
import { AllianceFingerprintCard } from './AllianceFingerprintCard';
import type {
  FingerprintListResponse,
  CoalitionSummary,
  DoctrineDistribution,
} from '../../types/reports';

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

// ============== Alliance Intel Tab ==============

export function AllianceIntelTab() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDoctrine, setSelectedDoctrine] = useState<string | null>(null);
  const [expandedAlliance, setExpandedAlliance] = useState<number | null>(null);

  // Fetch doctrine distribution (for filter pills)
  const distributionQuery = useQuery<DoctrineDistribution>({
    queryKey: ['doctrineDistribution'],
    queryFn: () => fingerprintApi.getDoctrineDistribution(),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch coalitions
  const coalitionsQuery = useQuery<{ coalitions: CoalitionSummary[] }>({
    queryKey: ['coalitions'],
    queryFn: () => fingerprintApi.getCoalitions(2),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch fingerprints with filters
  const fingerprintsQuery = useQuery<FingerprintListResponse>({
    queryKey: ['fingerprints', searchTerm, selectedDoctrine],
    queryFn: () => fingerprintApi.list({
      limit: 100,
      search: searchTerm || undefined,
      doctrine: selectedDoctrine || undefined,
    }),
    staleTime: 5 * 60 * 1000,
  });

  const distribution = distributionQuery.data?.distribution || [];
  const coalitions = coalitionsQuery.data?.coalitions || [];
  const fingerprints = fingerprintsQuery.data?.fingerprints || [];

  return (
    <div>
      {/* Meta Overview - Doctrine Distribution Pills */}
      <div style={{
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: 'var(--surface)',
        borderRadius: '8px',
        border: '1px solid var(--border)'
      }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--text-primary)' }}>
          Doctrine Distribution
        </h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          <button
            onClick={() => setSelectedDoctrine(null)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '20px',
              border: '1px solid var(--border)',
              backgroundColor: selectedDoctrine === null ? 'var(--accent-blue)' : 'var(--surface-elevated)',
              color: selectedDoctrine === null ? '#fff' : 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
          >
            All ({fingerprints.length})
          </button>
          {distribution.map((d) => (
            <button
              key={d.doctrine}
              onClick={() => setSelectedDoctrine(selectedDoctrine === d.doctrine ? null : d.doctrine)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '20px',
                border: '1px solid var(--border)',
                backgroundColor: selectedDoctrine === d.doctrine ? 'var(--accent-blue)' : 'var(--surface-elevated)',
                color: selectedDoctrine === d.doctrine ? '#fff' : 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 500,
                transition: 'all 0.2s'
              }}
            >
              {d.doctrine} ({d.alliances})
            </button>
          ))}
        </div>
      </div>

      {/* Search */}
      <div style={{
        marginBottom: '2rem',
        position: 'relative',
        maxWidth: '400px'
      }}>
        <Search size={18} style={{
          position: 'absolute',
          left: '1rem',
          top: '50%',
          transform: 'translateY(-50%)',
          color: 'var(--text-secondary)'
        }} />
        <input
          type="text"
          placeholder="Search alliance name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '0.75rem 1rem 0.75rem 2.75rem',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            backgroundColor: 'var(--surface)',
            color: 'var(--text-primary)',
            fontSize: '1rem'
          }}
        />
      </div>

      {/* Coalitions Summary */}
      {coalitions.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', color: 'var(--text-primary)' }}>
            Major Coalitions
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '1rem'
          }}>
            {coalitions.slice(0, 6).map((coalition) => (
              <div
                key={coalition.coalition_id}
                style={{
                  padding: '1rem 1.25rem',
                  backgroundColor: 'var(--surface)',
                  borderRadius: '8px',
                  border: '1px solid var(--border)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {coalition.leader_name}
                  </h4>
                  <span style={{
                    fontSize: '0.8rem',
                    padding: '0.25rem 0.5rem',
                    backgroundColor: 'var(--accent-blue)',
                    color: '#fff',
                    borderRadius: '4px'
                  }}>
                    {coalition.member_count} alliances
                  </span>
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  {formatNumber(coalition.total_ship_uses)} ships used
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                  {coalition.primary_doctrines.slice(0, 3).map((doctrine) => (
                    <span
                      key={doctrine}
                      style={{
                        fontSize: '0.75rem',
                        padding: '0.2rem 0.5rem',
                        backgroundColor: 'var(--surface-elevated)',
                        borderRadius: '4px',
                        color: 'var(--text-secondary)'
                      }}
                    >
                      {doctrine}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alliance Fingerprint Cards */}
      <div style={{ marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>
          Alliance Fingerprints ({fingerprintsQuery.data?.total || 0})
        </h3>
      </div>

      {fingerprintsQuery.isLoading && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Loading alliance fingerprints...
        </div>
      )}

      {fingerprintsQuery.isError && (
        <div style={{
          padding: '1.5rem',
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--danger)',
          borderRadius: '8px',
          color: 'var(--danger)'
        }}>
          Error loading fingerprints: {(fingerprintsQuery.error as Error).message}
        </div>
      )}

      {fingerprintsQuery.isSuccess && (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {fingerprints.length === 0 ? (
            <div style={{
              padding: '3rem',
              textAlign: 'center',
              backgroundColor: 'var(--surface)',
              borderRadius: '8px',
              border: '1px solid var(--border)'
            }}>
              <p style={{ color: 'var(--text-secondary)' }}>
                No alliances found matching your criteria.
              </p>
            </div>
          ) : (
            fingerprints.map((fp) => (
              <AllianceFingerprintCard
                key={fp.alliance_id}
                fingerprint={fp}
                isExpanded={expandedAlliance === fp.alliance_id}
                onToggle={() => setExpandedAlliance(expandedAlliance === fp.alliance_id ? null : fp.alliance_id)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
