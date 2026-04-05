import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Crosshair } from 'lucide-react';
import { counterDoctrineApi } from '../../services/api';
import type { FleetCounterRecommendation } from '../../types/reports';

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

// ============== Types ==============

interface KnownDoctrine {
  name: string;
  tank: 'shield' | 'armor';
  range: 'short' | 'medium' | 'long';
  avg_dps: number;
  weapon: string;
  counters: string[];
}

// ============== Counter-Doctrine Tab ==============

export function CounterDoctrineTab() {
  const [selectedDoctrine, setSelectedDoctrine] = useState<KnownDoctrine | null>(null);
  const [enemyCount, setEnemyCount] = useState<number>(30);

  // Fetch known doctrines
  const doctrinesQuery = useQuery<{ doctrines: KnownDoctrine[] }>({
    queryKey: ['knownDoctrines'],
    queryFn: () => counterDoctrineApi.listKnownDoctrines(),
    staleTime: 10 * 60 * 1000,
  });

  // Counter recommendation mutation
  const counterMutation = useMutation<FleetCounterRecommendation, Error, void>({
    mutationFn: async () => {
      if (!selectedDoctrine) throw new Error('Select a doctrine first');
      // Extract ship name from doctrine name (e.g., "Ferox Fleet" -> "Ferox")
      const shipName = selectedDoctrine.name.replace(' Fleet', '');
      return counterDoctrineApi.getCounter({
        doctrine_name: selectedDoctrine.name,
        ship_name: shipName,
        estimated_count: enemyCount,
        tank_type: selectedDoctrine.tank,
        engagement_range: selectedDoctrine.range,
        avg_dps: selectedDoctrine.avg_dps,
      });
    },
  });

  const knownDoctrines = doctrinesQuery.data?.doctrines || [];
  const recommendation = counterMutation.data;

  return (
    <div>
      {/* Input Section */}
      <div style={{
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: 'var(--surface)',
        borderRadius: '8px',
        border: '1px solid var(--border)'
      }}>
        <h3 style={{ marginBottom: '1.5rem', fontSize: '1.1rem', color: 'var(--text-primary)' }}>
          Enemy Fleet Configuration
        </h3>

        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {/* Doctrine Dropdown */}
          <div style={{ flex: '1', minWidth: '250px' }}>
            <label style={{
              display: 'block',
              fontWeight: 600,
              marginBottom: '0.5rem',
              color: 'var(--text-primary)'
            }}>
              Enemy Doctrine
            </label>
            <select
              value={selectedDoctrine?.name || ''}
              onChange={(e) => {
                const doctrine = knownDoctrines.find(d => d.name === e.target.value);
                setSelectedDoctrine(doctrine || null);
              }}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-elevated)',
                color: 'var(--text-primary)',
                fontSize: '1rem'
              }}
            >
              <option value="">Select doctrine...</option>
              {knownDoctrines.map((d) => (
                <option key={d.name} value={d.name}>
                  {d.name} ({d.weapon})
                </option>
              ))}
            </select>
          </div>

          {/* Enemy Count */}
          <div style={{ minWidth: '150px' }}>
            <label style={{
              display: 'block',
              fontWeight: 600,
              marginBottom: '0.5rem',
              color: 'var(--text-primary)'
            }}>
              Enemy Count
            </label>
            <input
              type="number"
              min={1}
              max={500}
              value={enemyCount}
              onChange={(e) => setEnemyCount(Math.max(1, Math.min(500, parseInt(e.target.value) || 1)))}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface-elevated)',
                color: 'var(--text-primary)',
                fontSize: '1rem'
              }}
            />
          </div>

          {/* Get Counter Button */}
          <button
            onClick={() => counterMutation.mutate()}
            disabled={!selectedDoctrine || counterMutation.isPending}
            style={{
              padding: '0.75rem 2rem',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: selectedDoctrine ? 'var(--accent-blue)' : 'var(--surface-elevated)',
              color: selectedDoctrine ? '#fff' : 'var(--text-secondary)',
              fontWeight: 600,
              cursor: selectedDoctrine ? 'pointer' : 'not-allowed',
              fontSize: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <Crosshair size={18} />
            {counterMutation.isPending ? 'Analyzing...' : 'Get Counter'}
          </button>
        </div>

        {/* Selected Doctrine Info */}
        {selectedDoctrine && (
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: 'var(--surface-elevated)',
            borderRadius: '8px',
            fontSize: '0.9rem'
          }}>
            <span style={{ color: 'var(--text-secondary)' }}>Tank:</span>{' '}
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{selectedDoctrine.tank}</span>
            <span style={{ margin: '0 1rem', color: 'var(--border)' }}>|</span>
            <span style={{ color: 'var(--text-secondary)' }}>Range:</span>{' '}
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{selectedDoctrine.range}</span>
            <span style={{ margin: '0 1rem', color: 'var(--border)' }}>|</span>
            <span style={{ color: 'var(--text-secondary)' }}>DPS:</span>{' '}
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{selectedDoctrine.avg_dps}</span>
          </div>
        )}
      </div>

      {/* Error State */}
      {counterMutation.isError && (
        <div style={{
          marginBottom: '2rem',
          padding: '1.5rem',
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--danger)',
          borderRadius: '8px',
          color: 'var(--danger)'
        }}>
          Error: {counterMutation.error?.message}
        </div>
      )}

      {/* Counter Recommendation Display */}
      {recommendation && (
        <div style={{
          padding: '1.5rem',
          backgroundColor: 'var(--surface)',
          borderRadius: '8px',
          border: '1px solid var(--accent-blue)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                Counter: {recommendation.counter_doctrine}
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                vs {recommendation.their_count}x {recommendation.their_doctrine}
              </p>
            </div>
            <div style={{
              padding: '0.5rem 1rem',
              backgroundColor: recommendation.confidence >= 0.8 ? 'var(--success)' : recommendation.confidence >= 0.5 ? 'var(--warning)' : 'var(--danger)',
              color: '#fff',
              borderRadius: '8px',
              fontWeight: 600
            }}>
              {(recommendation.confidence * 100).toFixed(0)}% Confidence
            </div>
          </div>

          {/* Fleet Composition */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Fleet Composition
            </h4>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: '0.75rem'
            }}>
              {recommendation.composition.map((ship, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem 1rem',
                    backgroundColor: 'var(--surface-elevated)',
                    borderRadius: '8px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{ship.ship}</span>
                    <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{ship.count}x</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {ship.role} - {formatNumber(ship.dps_per_ship)} DPS
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* DPS Comparison */}
          <div style={{
            padding: '1rem',
            backgroundColor: 'var(--surface-elevated)',
            borderRadius: '8px',
            marginBottom: '1.5rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Their DPS</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--danger)' }}>
                  {formatNumber(recommendation.their_dps)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Your DPS</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--success)' }}>
                  {formatNumber(recommendation.total_dps)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Advantage</div>
                <div style={{
                  fontSize: '1.25rem',
                  fontWeight: 600,
                  color: recommendation.dps_advantage > 0 ? 'var(--success)' : 'var(--danger)'
                }}>
                  {recommendation.dps_advantage > 0 ? '+' : ''}{(recommendation.dps_advantage * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>

          {/* Engagement Advice */}
          <div style={{ marginBottom: '1rem' }}>
            <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              Engagement Advice
            </h4>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {recommendation.engagement_advice}
            </p>
          </div>

          {/* Positioning */}
          <div style={{ marginBottom: '1rem' }}>
            <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              Positioning
            </h4>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {recommendation.positioning}
            </p>
          </div>

          {/* Notes */}
          {recommendation.notes && (
            <div style={{
              padding: '1rem',
              backgroundColor: 'var(--surface-elevated)',
              borderRadius: '8px',
              borderLeft: '3px solid var(--warning)'
            }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                {recommendation.notes}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!recommendation && !counterMutation.isPending && (
        <div style={{
          padding: '3rem',
          textAlign: 'center',
          backgroundColor: 'var(--surface)',
          borderRadius: '8px',
          border: '1px solid var(--border)'
        }}>
          <Crosshair size={48} style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }} />
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
            Select an enemy doctrine and click "Get Counter" for recommendations
          </p>
        </div>
      )}
    </div>
  );
}
