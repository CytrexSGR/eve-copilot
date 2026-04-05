import { ChevronDown, ChevronUp } from 'lucide-react';
import type { DoctrineTemplate, ItemsMaterialsResponse } from '../../types/reports';

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

// ============== Component ==============

interface DetectedDoctrineCardProps {
  doctrine: DoctrineTemplate;
  isExpanded: boolean;
  onToggle: () => void;
  itemsData?: ItemsMaterialsResponse;
  itemsLoading: boolean;
}

export function DetectedDoctrineCard({ doctrine, isExpanded, onToggle, itemsData, itemsLoading }: DetectedDoctrineCardProps) {
  const items = itemsData?.items;
  const totalMaterials = itemsData?.total_materials;
  const regionName = doctrine.region_name || REGIONS[doctrine.region_id] || `Region ${doctrine.region_id}`;
  const confidencePercent = (doctrine.confidence_score * 100).toFixed(1);

  // Use composition_with_names if available, fallback to legacy composition
  const sortedComposition = doctrine.composition_with_names
    ? doctrine.composition_with_names.slice(0, 5)
    : Object.entries(doctrine.composition)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
        .map(([typeId, ratio]) => ({ type_id: parseInt(typeId), type_name: `Ship ${typeId}`, ratio }));

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
          <h3 style={{ marginBottom: '0.75rem', fontSize: '1.25rem' }}>
            {doctrine.doctrine_name || `Doctrine #${doctrine.id}`}
          </h3>
          <div style={{
            display: 'flex',
            gap: '1.5rem',
            flexWrap: 'wrap',
            fontSize: '0.95rem',
            color: 'var(--text-secondary)'
          }}>
            {doctrine.alliance_name && (
              <span>
                <strong style={{ color: 'var(--text-primary)' }}>Alliance:</strong>{' '}
                <span style={{ color: 'var(--accent-blue)' }}>{doctrine.alliance_name}</span>
              </span>
            )}
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Region:</strong> {regionName}
            </span>
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Fleet Size:</strong> ~{doctrine.total_pilots_avg} pilots
            </span>
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Confidence:</strong>{' '}
              <span
                style={{
                  color:
                    doctrine.confidence_score >= 0.8
                      ? 'var(--success)'
                      : doctrine.confidence_score >= 0.6
                      ? 'var(--warning)'
                      : 'var(--text-secondary)',
                  fontWeight: 600
                }}
              >
                {confidencePercent}%
              </span>
            </span>
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Observations:</strong> {doctrine.observation_count}
            </span>
          </div>

          {/* Top Ships Preview */}
          <div style={{
            marginTop: '1rem',
            fontSize: '0.9rem',
            color: 'var(--text-secondary)'
          }}>
            <strong style={{ color: 'var(--text-primary)' }}>Top Ships:</strong>{' '}
            {sortedComposition.map((ship, idx) => (
              <span key={ship.type_id}>
                {idx > 0 && ', '}
                <span style={{ color: 'var(--text-primary)' }}>{ship.type_name}</span>
                {' '}({(ship.ratio * 100).toFixed(0)}%)
              </span>
            ))}
          </div>
        </div>

        <div style={{ color: 'var(--text-secondary)' }}>
          {isExpanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div style={{
          borderTop: '1px solid var(--border)',
          paddingTop: '1.5rem'
        }}>
          <h4 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>
            Consumed Items (from Battle Data)
          </h4>

          {itemsLoading ? (
            <p style={{ color: 'var(--text-secondary)' }}>Loading items...</p>
          ) : items && items.length > 0 ? (
            <div>
              {/* Group items by category */}
              {['ammunition', 'fuel', 'module', 'drone'].map((category) => {
                const categoryItems = items.filter((i) => i.item_category === category);
                if (categoryItems.length === 0) return null;

                const categoryLabels: Record<string, string> = {
                  ammunition: 'Ammunition',
                  fuel: 'Fuel & Isotopes',
                  module: 'Modules & Consumables',
                  drone: 'Drones',
                };

                return (
                  <div key={category} style={{ marginBottom: '1.5rem' }}>
                    <h5 style={{
                      fontSize: '0.95rem',
                      color: 'var(--text-secondary)',
                      marginBottom: '0.75rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      {categoryLabels[category] || category}
                    </h5>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                      gap: '0.5rem'
                    }}>
                      {categoryItems.slice(0, 10).map((item) => (
                        <div
                          key={item.id}
                          style={{
                            padding: '0.75rem 1rem',
                            backgroundColor: 'var(--surface-elevated)',
                            borderRadius: '6px',
                            fontSize: '0.9rem'
                          }}
                        >
                          <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: item.materials.length > 0 ? '0.5rem' : 0
                          }}>
                            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                              {item.item_name}
                            </span>
                            <span style={{
                              color: item.consumption_rate && item.consumption_rate > 100000
                                ? 'var(--warning)'
                                : item.consumption_rate
                                ? 'var(--text-secondary)'
                                : 'var(--accent-purple)',
                              fontWeight: item.consumption_rate && item.consumption_rate > 100000 ? 600 : 400,
                              fontSize: item.consumption_rate ? '0.9rem' : '0.75rem'
                            }}>
                              {item.consumption_rate
                                ? item.consumption_rate >= 1000000
                                  ? `${(item.consumption_rate / 1000000).toFixed(1)}M`
                                  : item.consumption_rate >= 1000
                                  ? `${(item.consumption_rate / 1000).toFixed(0)}k`
                                  : item.consumption_rate.toLocaleString()
                                : 'Essential'}
                            </span>
                          </div>
                          {/* Materials for manufacturable items */}
                          {item.materials.length > 0 && (
                            <div style={{
                              paddingTop: '0.5rem',
                              borderTop: '1px solid var(--border)',
                              fontSize: '0.8rem',
                              color: 'var(--text-tertiary)'
                            }}>
                              <span style={{ color: 'var(--accent-blue)', fontSize: '0.75rem' }}>
                                {item.blueprint_name} (x{item.produced_quantity})
                              </span>
                              <div style={{ marginTop: '0.25rem' }}>
                                {item.materials.slice(0, 4).map((mat, idx) => (
                                  <span key={mat.type_id}>
                                    {idx > 0 && ' | '}
                                    {mat.type_name}: {mat.quantity >= 1000
                                      ? `${(mat.quantity / 1000).toFixed(1)}k`
                                      : mat.quantity}
                                  </span>
                                ))}
                                {item.materials.length > 4 && (
                                  <span> +{item.materials.length - 4}</span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    {categoryItems.length > 10 && (
                      <p style={{
                        color: 'var(--text-tertiary)',
                        fontSize: '0.85rem',
                        marginTop: '0.5rem'
                      }}>
                        +{categoryItems.length - 10} more items
                      </p>
                    )}
                  </div>
                );
              })}

              {/* Total Materials Summary */}
              {totalMaterials && Object.keys(totalMaterials).length > 0 && (
                <div style={{
                  marginTop: '1.5rem',
                  padding: '1rem',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--accent-blue)',
                  borderRadius: '8px'
                }}>
                  <h5 style={{
                    fontSize: '0.95rem',
                    color: 'var(--accent-blue)',
                    marginBottom: '0.75rem'
                  }}>
                    Total Materials Required (for manufacturables)
                  </h5>
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.5rem'
                  }}>
                    {Object.values(totalMaterials)
                      .sort((a, b) => b.quantity - a.quantity)
                      .slice(0, 12)
                      .map((mat) => (
                        <span
                          key={mat.type_id}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: 'var(--surface-elevated)',
                            borderRadius: '4px',
                            fontSize: '0.85rem',
                            color: 'var(--text-primary)'
                          }}
                        >
                          {mat.type_name}: {mat.quantity >= 1000000
                            ? `${(mat.quantity / 1000000).toFixed(1)}M`
                            : mat.quantity >= 1000
                            ? `${(mat.quantity / 1000).toFixed(1)}k`
                            : mat.quantity}
                        </span>
                      ))}
                    {Object.keys(totalMaterials).length > 12 && (
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        fontSize: '0.85rem',
                        color: 'var(--text-tertiary)'
                      }}>
                        +{Object.keys(totalMaterials).length - 12} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: 'var(--text-secondary)' }}>No items derived yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
