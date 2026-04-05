import { useState, useEffect } from 'react';
import { productionApi } from '../../services/api/production';
import type { ProductionSimulation, CompareResult } from '../../types/production';
import type { ItemSearchResult } from '../../types/market';
import { formatISK } from '../../utils/format';

interface Props {
  selectedItem: ItemSearchResult;
  onNavigateToMaterial?: (typeId: number, typeName: string) => void;
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export function CalculatorTab({ selectedItem, onNavigateToMaterial }: Props) {
  const [me, setMe] = useState(10);
  const [te, setTe] = useState(20);
  const [runs, setRuns] = useState(1);
  const [sim, setSim] = useState<ProductionSimulation | null>(null);
  const [loading, setLoading] = useState(true);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [showCompare, setShowCompare] = useState(false);

  useEffect(() => {
    setLoading(true);
    setSim(null);
    productionApi.simulateGet(selectedItem.typeID, { runs, me, te })
      .then(data => setSim(data))
      .catch(() => setSim(null))
      .finally(() => setLoading(false));
  }, [selectedItem.typeID, me, te, runs]);

  const handleCompare = () => {
    setShowCompare(true);
    setCompareLoading(true);
    setCompareResult(null);
    productionApi.compare({
      type_id: selectedItem.typeID,
      facility_ids: ['npc', 'raitaru', 'azbel', 'sotiyo', 'tatara'],
      me,
      te,
      runs,
    })
      .then(data => setCompareResult(data))
      .catch(() => setCompareResult(null))
      .finally(() => setCompareLoading(false));
  };

  const fa = sim?.financial_analysis;
  const profit = fa?.profit ?? 0;
  const roi = Number.isFinite(fa?.roi) ? fa!.roi : 0;
  const bomTotal = sim?.bom?.reduce((sum, item) => sum + item.total_cost, 0) ?? 0;

  const cheapestFacility = compareResult
    ? compareResult.facilities.reduce<string | null>((best, f) => {
        if (!best) return f.facility_id;
        const bestF = compareResult.facilities.find(x => x.facility_id === best);
        return bestF && bestF.total_cost <= f.total_cost ? best : f.facility_id;
      }, null)
    : null;

  return (
    <div>
      {/* Controls Bar */}
      <div style={{
        display: 'flex',
        gap: '1.2rem',
        alignItems: 'center',
        marginBottom: '1rem',
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>ME</label>
          <input
            type="range"
            min={0}
            max={10}
            value={me}
            onChange={e => setMe(Number(e.target.value))}
            style={{ width: 80, accentColor: '#3fb950' }}
          />
          <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-primary)', minWidth: 20, textAlign: 'right' }}>{me}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>TE</label>
          <input
            type="range"
            min={0}
            max={20}
            value={te}
            onChange={e => setTe(Number(e.target.value))}
            style={{ width: 80, accentColor: '#00d4ff' }}
          />
          <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-primary)', minWidth: 20, textAlign: 'right' }}>{te}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Runs</label>
          <input
            type="number"
            min={1}
            max={100}
            value={runs}
            onChange={e => {
              const v = Math.max(1, Math.min(100, Number(e.target.value) || 1));
              setRuns(v);
            }}
            style={{
              width: 60,
              padding: '2px 6px',
              fontSize: '0.75rem',
              fontFamily: 'monospace',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              color: 'var(--text-primary)',
              textAlign: 'center',
            }}
          />
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && <div className="skeleton" style={{ height: 200 }} />}

      {/* Simulation Results */}
      {!loading && sim && (
        <>
          {/* Financial Summary */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '0.5rem',
            marginBottom: '1rem',
          }}>
            {[
              { label: 'Production Cost', value: formatISK(fa?.production_cost), color: '#f85149' },
              { label: 'Sell Price', value: formatISK(fa?.sell_price), color: '#3fb950' },
              { label: 'Profit', value: formatISK(profit), color: profit >= 0 ? '#3fb950' : '#f85149' },
              { label: 'ROI', value: `${roi.toFixed(1)}%`, color: '#00d4ff' },
            ].map(s => (
              <div key={s.label} style={{
                padding: '0.6rem 0.8rem',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
              }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem', textTransform: 'uppercase' }}>{s.label}</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, fontFamily: 'monospace', color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Production Time */}
          <div style={{
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            marginBottom: '1rem',
          }}>
            Production Time: <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: 600 }}>
              {formatTime(sim.production_time.actual_time)}
            </span>
          </div>

          {/* Warnings */}
          {sim.warnings?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '1rem' }}>
              {sim.warnings.map((w, i) => (
                <span key={i} style={{
                  fontSize: '0.65rem',
                  padding: '2px 8px',
                  background: 'rgba(210,153,34,0.15)',
                  border: '1px solid rgba(210,153,34,0.4)',
                  borderRadius: 3,
                  color: '#d29922',
                  fontWeight: 600,
                }}>
                  {w}
                </span>
              ))}
            </div>
          )}

          {/* Bill of Materials */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.03em',
              marginBottom: '0.5rem',
            }}>
              Bill of Materials
            </div>

            {/* BOM Header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '40px 1fr 120px 120px 140px',
              gap: '0.25rem',
              padding: '0.4rem 0.5rem',
              borderBottom: '1px solid var(--border-color)',
              fontSize: '0.65rem',
              fontWeight: 700,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
            }}>
              <div />
              <div>Material</div>
              <div style={{ textAlign: 'right' }}>Quantity</div>
              <div style={{ textAlign: 'right' }}>Unit Price</div>
              <div style={{ textAlign: 'right' }}>Total Cost</div>
            </div>

            {/* BOM Rows */}
            {sim.bom?.map((item, i) => (
              <div key={item.material_id} style={{
                display: 'grid',
                gridTemplateColumns: '40px 1fr 120px 120px 140px',
                gap: '0.25rem',
                padding: '0.35rem 0.5rem',
                alignItems: 'center',
                background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
              }}>
                <img
                  src={`https://images.evetech.net/types/${item.material_id}/icon?size=32`}
                  alt=""
                  style={{ width: 32, height: 32, borderRadius: 3 }}
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
                <div
                  onClick={onNavigateToMaterial ? () => onNavigateToMaterial(item.material_id, item.material_name) : undefined}
                  style={{
                    fontSize: '0.75rem',
                    color: onNavigateToMaterial ? '#00d4ff' : 'var(--text-primary)',
                    cursor: onNavigateToMaterial ? 'pointer' : 'default',
                  }}
                  onMouseEnter={onNavigateToMaterial ? e => { (e.currentTarget.style.textDecoration = 'underline'); } : undefined}
                  onMouseLeave={onNavigateToMaterial ? e => { (e.currentTarget.style.textDecoration = 'none'); } : undefined}
                >
                  {item.material_name}
                </div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-primary)', textAlign: 'right' }}>
                  {item.quantity.toLocaleString()}
                </div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-secondary)', textAlign: 'right' }}>
                  {formatISK(item.unit_price)}
                </div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-primary)', textAlign: 'right' }}>
                  {formatISK(item.total_cost)}
                </div>
              </div>
            ))}

            {/* BOM Footer / Total */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '40px 1fr 120px 120px 140px',
              gap: '0.25rem',
              padding: '0.5rem 0.5rem',
              borderTop: '1px solid var(--border-color)',
              marginTop: '0.25rem',
            }}>
              <div />
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Total</div>
              <div />
              <div />
              <div style={{ fontSize: '0.8rem', fontWeight: 700, fontFamily: 'monospace', color: 'var(--text-primary)', textAlign: 'right' }}>
                {formatISK(bomTotal)}
              </div>
            </div>
          </div>

          {/* Facility Comparison */}
          {!showCompare && (
            <button
              onClick={handleCompare}
              style={{
                padding: '0.5rem 1.2rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                cursor: 'pointer',
              }}
            >
              Compare Facilities
            </button>
          )}

          {showCompare && (
            <div style={{ marginTop: '1rem' }}>
              <div style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.03em',
                marginBottom: '0.5rem',
              }}>
                Facility Comparison
              </div>

              {compareLoading && <div className="skeleton" style={{ height: 120 }} />}

              {!compareLoading && compareResult && (
                <>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '0.5rem',
                    marginBottom: '0.75rem',
                  }}>
                    {compareResult.facilities?.map(f => {
                      const isCheapest = f.facility_id === cheapestFacility;
                      return (
                        <div key={f.facility_id} style={{
                          padding: '0.7rem',
                          background: isCheapest ? 'rgba(63,185,80,0.05)' : 'var(--bg-secondary)',
                          border: `1px solid ${isCheapest ? 'rgba(63,185,80,0.5)' : 'var(--border-color)'}`,
                          borderRadius: 6,
                        }}>
                          <div style={{
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            color: isCheapest ? '#3fb950' : 'var(--text-primary)',
                            marginBottom: '0.5rem',
                          }}>
                            {f.facility_name}
                            {isCheapest && (
                              <span style={{
                                marginLeft: 6,
                                fontSize: '0.55rem',
                                padding: '1px 5px',
                                background: 'rgba(63,185,80,0.2)',
                                border: '1px solid rgba(63,185,80,0.5)',
                                borderRadius: 3,
                                color: '#3fb950',
                                fontWeight: 700,
                              }}>BEST</span>
                            )}
                          </div>
                          {[
                            { label: 'Material Cost', value: formatISK(f.material_cost) },
                            { label: 'Install Cost', value: formatISK(f.install_cost) },
                            { label: 'Total Cost', value: formatISK(f.total_cost) },
                            { label: 'Time', value: f.production_time_formatted },
                          ].map(row => (
                            <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.15rem' }}>
                              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>{row.label}</span>
                              <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-primary)' }}>{row.value}</span>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>

                  {compareResult.recommendation && (
                    <div style={{
                      fontSize: '0.72rem',
                      color: 'var(--text-secondary)',
                      padding: '0.5rem 0.7rem',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 6,
                    }}>
                      {compareResult.recommendation}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* No data */}
      {!loading && !sim && (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', padding: '2rem 0', textAlign: 'center' }}>
          No production data available for this item.
        </div>
      )}
    </div>
  );
}
