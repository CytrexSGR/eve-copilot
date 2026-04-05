import { useState, useEffect, useMemo } from 'react';
import { inventionApi } from '../../services/api/production';
import type { DecryptorComparisonResult, DecryptorComparison, InventionDetail } from '../../types/production';
import type { ItemSearchResult } from '../../types/market';
import { formatISK } from '../../utils/format';

interface Props {
  selectedItem: ItemSearchResult;
}

export function InventionTab({ selectedItem }: Props) {
  const [comparison, setComparison] = useState<DecryptorComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDecryptorId, setSelectedDecryptorId] = useState<number | null | undefined>(undefined);
  const [detail, setDetail] = useState<InventionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Auto-fetch decryptor comparison on item change
  useEffect(() => {
    setLoading(true);
    setError(null);
    setComparison(null);
    setDetail(null);
    setSelectedDecryptorId(undefined);

    inventionApi.getDecryptors(selectedItem.typeID)
      .then(data => setComparison(data))
      .catch(err => {
        const status = err?.response?.status;
        if (status === 404) {
          setError('This item has no invention data. Invention is only available for T2 items.');
        } else {
          setError(err.message || 'Failed to load invention data');
        }
      })
      .finally(() => setLoading(false));
  }, [selectedItem.typeID]);

  // Fetch detail when a decryptor card is clicked
  useEffect(() => {
    if (selectedDecryptorId === undefined) return;
    setDetailLoading(true);
    const params = selectedDecryptorId != null ? { decryptor_type_id: selectedDecryptorId } : {};
    inventionApi.getDetail(selectedItem.typeID, params)
      .then(data => setDetail(data))
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedItem.typeID, selectedDecryptorId]);

  // Sort comparisons by total_cost_per_run ascending (cheapest first)
  const sortedComparisons = useMemo(() => {
    if (!comparison) return [];
    return [...comparison.comparisons].sort((a, b) => a.total_cost_per_run - b.total_cost_per_run);
  }, [comparison]);

  const cheapestCost = sortedComparisons.length > 0 ? sortedComparisons[0].total_cost_per_run : null;
  const mostExpensiveCost = sortedComparisons.length > 0 ? sortedComparisons[sortedComparisons.length - 1].total_cost_per_run : null;

  const probColor = (prob: number) => {
    if (prob > 0.30) return '#3fb950';
    if (prob >= 0.20) return '#d29922';
    return '#f85149';
  };

  const costColor = (cost: number) => {
    if (cheapestCost != null && cost === cheapestCost) return '#3fb950';
    if (mostExpensiveCost != null && cost === mostExpensiveCost) return 'rgba(248,81,73,0.7)';
    return 'var(--text-primary)';
  };

  const isBestRow = (row: DecryptorComparison) =>
    comparison?.best_option != null && row.decryptor === comparison.best_option.decryptor;

  if (loading) return <div className="skeleton" style={{ height: 300 }} />;

  if (error) {
    const isNotFound = error.includes('no invention data');
    return (
      <div style={{
        padding: '1rem',
        background: isNotFound ? 'rgba(210,153,34,0.08)' : 'rgba(248,81,73,0.1)',
        border: `1px solid ${isNotFound ? 'rgba(210,153,34,0.3)' : '#f85149'}`,
        borderRadius: 8,
        color: isNotFound ? '#d29922' : '#f85149',
        fontSize: '0.85rem',
      }}>
        {error}
      </div>
    );
  }

  if (!comparison || sortedComparisons.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        No invention data available for this item
      </div>
    );
  }

  const headerCellStyle: React.CSSProperties = {
    textTransform: 'uppercase',
    fontSize: '0.65rem',
    fontWeight: 700,
    color: 'var(--text-secondary)',
    padding: '0.5rem 0.5rem',
  };

  return (
    <div>
      {/* Best Option Banner */}
      {comparison.best_option && (
        <div style={{
          background: 'rgba(63,185,80,0.05)',
          border: '1px solid rgba(63,185,80,0.3)',
          borderRadius: 6,
          padding: '0.6rem 0.8rem',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#3fb950',
            padding: '1px 6px', background: 'rgba(63,185,80,0.12)', borderRadius: 3,
          }}>
            LOWEST COST/RUN
          </span>
          <span style={{ fontSize: '0.8rem', color: '#3fb950', fontWeight: 600 }}>
            {comparison.best_option.decryptor_name}
          </span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
            {formatISK(comparison.best_option.total_cost_per_run)}/run
          </span>
        </div>
      )}

      {/* Section: Decryptor Comparison */}
      <div style={{
        fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)',
        textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: '0.75rem',
      }}>
        Decryptor Comparison
      </div>

      {/* Comparison Table */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        overflow: 'hidden',
        marginBottom: '1.5rem',
      }}>
        {/* Header row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 60px 60px 70px 80px 120px 130px',
          borderBottom: '1px solid var(--border-color)',
        }}>
          <div style={headerCellStyle}>Decryptor</div>
          <div style={{ ...headerCellStyle, textAlign: 'right' }}>ME</div>
          <div style={{ ...headerCellStyle, textAlign: 'right' }}>TE</div>
          <div style={{ ...headerCellStyle, textAlign: 'right' }}>Runs</div>
          <div style={{ ...headerCellStyle, textAlign: 'right' }}>Prob</div>
          <div style={{ ...headerCellStyle, textAlign: 'right' }}>Inv. Cost</div>
          <div style={{ ...headerCellStyle, textAlign: 'right' }}>Cost/Run</div>
        </div>

        {/* Data rows */}
        {sortedComparisons.map((row, idx) => {
          const best = isBestRow(row);
          return (
            <div
              key={row.decryptor ?? 'none'}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 60px 60px 70px 80px 120px 130px',
                alignItems: 'center',
                padding: '0.4rem 0',
                fontSize: '0.78rem',
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                borderLeft: best ? '3px solid #3fb950' : '3px solid transparent',
                background: best
                  ? 'rgba(63,185,80,0.06)'
                  : idx % 2 === 1
                    ? 'rgba(255,255,255,0.02)'
                    : 'transparent',
              }}
            >
              <div style={{
                padding: '0 0.5rem',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontWeight: best ? 600 : 400,
                color: best ? '#3fb950' : 'var(--text-primary)',
              }}>
                {row.decryptor == null ? 'No Decryptor' : row.decryptor_name}
              </div>
              <div style={{ textAlign: 'right', fontFamily: 'monospace', padding: '0 0.5rem' }}>
                {row.result_me}
              </div>
              <div style={{ textAlign: 'right', fontFamily: 'monospace', padding: '0 0.5rem' }}>
                {row.result_te}
              </div>
              <div style={{ textAlign: 'right', fontFamily: 'monospace', padding: '0 0.5rem' }}>
                {row.output_runs}
              </div>
              <div style={{
                textAlign: 'right', fontFamily: 'monospace', padding: '0 0.5rem',
                color: probColor(row.probability),
              }}>
                {(row.probability * 100).toFixed(1)}%
              </div>
              <div style={{
                textAlign: 'right', fontFamily: 'monospace', padding: '0 0.5rem',
                color: '#d29922',
              }}>
                {formatISK(row.invention_cost)}
              </div>
              <div style={{
                textAlign: 'right', fontFamily: 'monospace', padding: '0 0.5rem',
                fontWeight: 600,
                color: costColor(row.total_cost_per_run),
              }}>
                {formatISK(row.total_cost_per_run)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Section: Decryptor Selector Cards */}
      <div style={{
        fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)',
        textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: '0.75rem',
      }}>
        Decryptor Detail
      </div>

      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        marginBottom: '1rem',
      }}>
        {/* No Decryptor card */}
        <button
          onClick={() => setSelectedDecryptorId(null)}
          style={{
            background: 'var(--bg-secondary)',
            border: selectedDecryptorId === null
              ? '1px solid #00d4ff'
              : '1px solid var(--border-color)',
            borderRadius: 6,
            padding: '0.5rem 0.75rem',
            cursor: 'pointer',
            textAlign: 'left',
            minWidth: 120,
          }}
        >
          <div style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: selectedDecryptorId === null ? '#00d4ff' : 'var(--text-primary)',
            marginBottom: '0.15rem',
          }}>
            No Decryptor
          </div>
          <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
            Base stats
          </div>
        </button>

        {sortedComparisons
          .filter(c => c.decryptor != null)
          .map(c => (
            <button
              key={c.decryptor}
              onClick={() => setSelectedDecryptorId(c.decryptor)}
              style={{
                background: 'var(--bg-secondary)',
                border: selectedDecryptorId === c.decryptor
                  ? '1px solid #00d4ff'
                  : '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '0.5rem 0.75rem',
                cursor: 'pointer',
                textAlign: 'left',
                minWidth: 120,
              }}
            >
              <div style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: selectedDecryptorId === c.decryptor ? '#00d4ff' : 'var(--text-primary)',
                marginBottom: '0.15rem',
              }}>
                {c.decryptor_name}
              </div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
                ME{c.result_me} TE{c.result_te} R{c.output_runs}
              </div>
            </button>
          ))}
      </div>

      {/* Invention Cost Breakdown */}
      {detailLoading && <div className="skeleton" style={{ height: 200 }} />}

      {!detailLoading && detail && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 8,
          padding: '1rem',
        }}>
          {/* Probability */}
          <div style={{ marginBottom: '1rem' }}>
            <div style={{
              fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)',
              textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: '0.5rem',
            }}>
              Invention Probability
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              fontSize: '0.9rem', fontFamily: 'monospace',
            }}>
              <span style={{ color: probColor(detail.invention.base_probability) }}>
                {(detail.invention.base_probability * 100).toFixed(1)}%
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                &rarr;
              </span>
              <span style={{ color: probColor(detail.invention.adjusted_probability), fontWeight: 700 }}>
                {(detail.invention.adjusted_probability * 100).toFixed(1)}%
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                ME {detail.invention.result_me} / TE {detail.invention.result_te} / {detail.invention.adjusted_output_runs} runs
              </span>
            </div>
          </div>

          {/* Invention Inputs */}
          {detail.invention.inputs?.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{
                fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)',
                textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: '0.5rem',
              }}>
                Invention Inputs
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {detail.invention.inputs.map(input => (
                  <div key={input.type_id} style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    padding: '0.3rem 0',
                  }}>
                    <img
                      src={`https://images.evetech.net/types/${input.type_id}/icon?size=32`}
                      alt=""
                      width={32}
                      height={32}
                      style={{ borderRadius: 4, flexShrink: 0 }}
                      loading="lazy"
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                    <span style={{
                      fontSize: '0.78rem', color: 'var(--text-primary)',
                      flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {input.type_name}
                    </span>
                    <span style={{
                      fontSize: '0.75rem', fontFamily: 'monospace',
                      color: 'var(--text-secondary)', minWidth: 30, textAlign: 'right',
                    }}>
                      x{input.quantity}
                    </span>
                    <span style={{
                      fontSize: '0.75rem', fontFamily: 'monospace',
                      color: '#d29922', minWidth: 90, textAlign: 'right',
                    }}>
                      {formatISK(input.unit_price)}
                    </span>
                  </div>
                ))}
              </div>
              <div style={{
                display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
                marginTop: '0.5rem', paddingTop: '0.5rem',
                borderTop: '1px solid rgba(255,255,255,0.05)',
                gap: '0.5rem',
              }}>
                <span style={{
                  fontSize: '0.7rem', color: 'var(--text-secondary)',
                  textTransform: 'uppercase', fontWeight: 700,
                }}>
                  Invention Cost
                </span>
                <span style={{
                  fontSize: '0.9rem', fontWeight: 700,
                  fontFamily: 'monospace', color: '#d29922',
                }}>
                  {formatISK(detail.invention.cost_per_bpc)}
                </span>
              </div>
            </div>
          )}

          {/* Summary Stats */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: '0.5rem',
            marginBottom: '1rem',
          }}>
            {[
              { label: 'Output Runs', value: String(detail.invention.adjusted_output_runs) },
              { label: 'Material Cost/Run', value: formatISK(detail.manufacturing.material_cost_per_run) },
              { label: 'Total Cost/Run', value: formatISK(detail.manufacturing.total_cost_per_run) },
            ].map(s => (
              <div key={s.label} style={{
                padding: '0.5rem 0.6rem',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
              }}>
                <div style={{
                  fontSize: '0.6rem', color: 'var(--text-secondary)',
                  marginBottom: '0.15rem', textTransform: 'uppercase',
                }}>
                  {s.label}
                </div>
                <div style={{
                  fontSize: '0.85rem', fontWeight: 600,
                  fontFamily: 'monospace', color: 'var(--text-primary)',
                }}>
                  {s.value}
                </div>
              </div>
            ))}
          </div>

          {/* T2 BOM */}
          {detail.manufacturing.materials?.length > 0 && (
            <div>
              <div style={{
                fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)',
                textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: '0.5rem',
              }}>
                T2 Materials
              </div>
              <div style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                overflow: 'hidden',
              }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '36px 1fr 70px 100px 110px',
                  borderBottom: '1px solid var(--border-color)',
                }}>
                  <div style={{ ...headerCellStyle, cursor: 'default' }} />
                  <div style={headerCellStyle}>Material</div>
                  <div style={{ ...headerCellStyle, textAlign: 'right' }}>Qty</div>
                  <div style={{ ...headerCellStyle, textAlign: 'right' }}>Unit Price</div>
                  <div style={{ ...headerCellStyle, textAlign: 'right' }}>Total</div>
                </div>
                {detail.manufacturing.materials.map((mat, idx) => (
                  <div
                    key={mat.type_id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '36px 1fr 70px 100px 110px',
                      alignItems: 'center',
                      padding: '0.3rem 0',
                      fontSize: '0.75rem',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                      background: idx % 2 === 1 ? 'rgba(255,255,255,0.02)' : 'transparent',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <img
                        src={`https://images.evetech.net/types/${mat.type_id}/icon?size=32`}
                        alt=""
                        width={28}
                        height={28}
                        style={{ borderRadius: 3 }}
                        loading="lazy"
                        onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                    </div>
                    <div style={{
                      padding: '0 0.4rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {mat.type_name}
                    </div>
                    <div style={{
                      textAlign: 'right', fontFamily: 'monospace',
                      padding: '0 0.5rem',
                    }}>
                      {mat.quantity_per_run.toLocaleString()}
                    </div>
                    <div style={{
                      textAlign: 'right', fontFamily: 'monospace',
                      color: '#d29922', padding: '0 0.5rem',
                    }}>
                      {formatISK(mat.unit_price)}
                    </div>
                    <div style={{
                      textAlign: 'right', fontFamily: 'monospace',
                      color: '#d29922', fontWeight: 600, padding: '0 0.5rem',
                    }}>
                      {formatISK(mat.total_cost)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
