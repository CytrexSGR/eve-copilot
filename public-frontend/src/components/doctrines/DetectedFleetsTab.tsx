import { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { doctrineApi } from '../../services/api';
import { DetectedDoctrineCard } from './DetectedDoctrineCard';
import type {
  DoctrineListResponse,
  ItemsMaterialsResponse,
} from '../../types/reports';

// ============== Constants ==============

const REGIONS: Record<number, string> = {
  10000002: 'The Forge (Jita)',
  10000043: 'Domain (Amarr)',
  10000030: 'Heimatar (Rens)',
  10000032: 'Sinq Laison (Dodixie)',
  10000042: 'Metropolis (Hek)',
  10000016: 'Lonetrek',
  10000020: 'Tash-Murkon',
  10000033: 'The Citadel',
  10000037: 'Everyshore',
  10000044: 'Solitude',
};

// ============== Detected Fleets Tab (Legacy DBSCAN) ==============

export function DetectedFleetsTab() {
  const [searchParams, setSearchParams] = useSearchParams();
  const regionId = searchParams.get('region') ? Number(searchParams.get('region')) : undefined;
  const minConfidence = Number(searchParams.get('confidence') || 0.5);

  const [expandedDoctrine, setExpandedDoctrine] = useState<number | null>(null);

  // Fetch doctrines
  const doctrinesQuery = useQuery<DoctrineListResponse>({
    queryKey: ['doctrines', regionId, minConfidence],
    queryFn: () => doctrineApi.getDoctrineTemplates(100, 0, regionId),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch items with materials for expanded doctrine
  const itemsQuery = useQuery<ItemsMaterialsResponse>({
    queryKey: ['doctrineitemsmaterials', expandedDoctrine],
    queryFn: () => doctrineApi.getDoctrineItemsWithMaterials(expandedDoctrine!),
    enabled: expandedDoctrine !== null,
    staleTime: 5 * 60 * 1000,
  });

  const doctrines = useMemo(() => {
    if (!doctrinesQuery.data?.doctrines) return [];
    return doctrinesQuery.data.doctrines.filter(
      (d) => d.confidence_score >= minConfidence
    );
  }, [doctrinesQuery.data, minConfidence]);

  const handleRegionChange = (region: string) => {
    const params = new URLSearchParams(searchParams);
    if (region) {
      params.set('region', region);
    } else {
      params.delete('region');
    }
    setSearchParams(params);
  };

  const handleConfidenceChange = (confidence: string) => {
    const params = new URLSearchParams(searchParams);
    params.set('confidence', confidence);
    setSearchParams(params);
  };

  const toggleDoctrine = (id: number) => {
    setExpandedDoctrine(expandedDoctrine === id ? null : id);
  };

  return (
    <div>
      {/* Note about DBSCAN */}
      <div style={{
        marginBottom: '1.5rem',
        padding: '1rem 1.25rem',
        backgroundColor: 'var(--surface)',
        borderRadius: '8px',
        border: '1px solid var(--warning)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
      }}>
        <AlertTriangle size={20} style={{ color: 'var(--warning)', flexShrink: 0 }} />
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Raw Statistical Patterns:</strong>{' '}
          These doctrines are detected using DBSCAN clustering on zkillboard data.
          They represent observed fleet compositions but may not reflect intentional doctrines.
        </span>
      </div>

      {/* Filters */}
      <div style={{
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: 'var(--surface)',
        borderRadius: '8px',
        border: '1px solid var(--border)'
      }}>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label style={{
              fontWeight: 600,
              marginRight: '0.75rem',
              color: 'var(--text-primary)'
            }}>
              Region:
            </label>
            <select
              value={regionId || ''}
              onChange={(e) => handleRegionChange(e.target.value)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-elevated)',
                color: 'var(--text-primary)',
                minWidth: '200px'
              }}
            >
              <option value="">All Regions</option>
              {Object.entries(REGIONS).map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{
              fontWeight: 600,
              marginRight: '0.75rem',
              color: 'var(--text-primary)'
            }}>
              Min Confidence:
            </label>
            <select
              value={minConfidence}
              onChange={(e) => handleConfidenceChange(e.target.value)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-elevated)',
                color: 'var(--text-primary)'
              }}
            >
              <option value={0.0}>0% (Show All)</option>
              <option value={0.5}>50%</option>
              <option value={0.7}>70%</option>
              <option value={0.8}>80%</option>
              <option value={0.9}>90%</option>
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {doctrinesQuery.isLoading && (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          color: 'var(--text-secondary)'
        }}>
          <p>Loading doctrines...</p>
        </div>
      )}

      {/* Error State */}
      {doctrinesQuery.isError && (
        <div style={{
          padding: '1.5rem',
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--danger)',
          borderRadius: '8px',
          color: 'var(--danger)'
        }}>
          <p>
            Error loading doctrines: {(doctrinesQuery.error as Error).message}
          </p>
        </div>
      )}

      {/* Doctrines Grid */}
      {doctrinesQuery.isSuccess && (
        <div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.5rem'
          }}>
            <h3 style={{ fontSize: '1.25rem' }}>
              {doctrines.length} Doctrine{doctrines.length !== 1 ? 's' : ''} Found
            </h3>
          </div>

          {doctrines.length === 0 ? (
            <div style={{
              padding: '3rem',
              textAlign: 'center',
              backgroundColor: 'var(--surface)',
              borderRadius: '8px',
              border: '1px solid var(--border)'
            }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
                No doctrines found. Try adjusting filters or trigger reclustering.
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '1.5rem' }}>
              {doctrines.map((doctrine) => (
                <DetectedDoctrineCard
                  key={doctrine.id}
                  doctrine={doctrine}
                  isExpanded={expandedDoctrine === doctrine.id}
                  onToggle={() => toggleDoctrine(doctrine.id)}
                  itemsData={expandedDoctrine === doctrine.id ? itemsQuery.data : undefined}
                  itemsLoading={itemsQuery.isLoading}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
