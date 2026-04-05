import { useState } from 'react';
import { dscanApi } from '../../services/api/military';
import type { DScanResult, DScanComparison } from '../../types/military';
import { THREAT_COLORS, SHIP_CLASS_COLORS } from '../../types/military';

export function DScanParser() {
  const [rawText, setRawText] = useState('');
  const [compareText, setCompareText] = useState('');
  const [compareMode, setCompareMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DScanResult | null>(null);
  const [comparison, setComparison] = useState<DScanComparison | null>(null);
  const [expandedClasses, setExpandedClasses] = useState<Set<string>>(new Set());

  const handleParse = async () => {
    if (!rawText.trim()) return;
    setLoading(true);
    setError(null);
    setComparison(null);
    try {
      const data = await dscanApi.parse(rawText);
      setResult(data);
      const allClasses = new Set(data.shipClasses.map((sc) => sc.shipClass));
      setExpandedClasses(allClasses);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to parse D-Scan';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!rawText.trim() || !compareText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await dscanApi.compare(rawText, compareText);
      setComparison(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to compare scans';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setRawText('');
    setCompareText('');
    setResult(null);
    setComparison(null);
    setError(null);
    setCompareMode(false);
    setExpandedClasses(new Set());
  };

  const toggleClass = (className: string) => {
    setExpandedClasses((prev) => {
      const next = new Set(prev);
      if (next.has(className)) next.delete(className);
      else next.add(className);
      return next;
    });
  };

  const sortedClasses = result
    ? [...result.shipClasses].sort((a, b) => b.count - a.count)
    : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Input Section */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)' }}>D-Scan Parser</h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={compareMode}
                onChange={(e) => setCompareMode(e.target.checked)}
              />
              Compare with previous scan
            </label>
          </div>
        </div>

        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Paste D-Scan results here..."
          style={textareaStyle}
        />

        {compareMode && (
          <textarea
            value={compareText}
            onChange={(e) => setCompareText(e.target.value)}
            placeholder="Paste older D-Scan for comparison..."
            style={{ ...textareaStyle, marginTop: '8px' }}
          />
        )}

        {error && (
          <div style={{ color: '#f85149', fontSize: '0.85rem', marginTop: '8px' }}>{error}</div>
        )}

        <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
          {!compareMode ? (
            <button onClick={handleParse} disabled={loading || !rawText.trim()} style={buttonStyle}>
              {loading ? 'Parsing...' : 'Parse D-Scan'}
            </button>
          ) : (
            <button onClick={handleCompare} disabled={loading || !rawText.trim() || !compareText.trim()} style={buttonStyle}>
              {loading ? 'Comparing...' : 'Compare'}
            </button>
          )}
          <button onClick={handleClear} style={clearButtonStyle}>Clear</button>
        </div>
      </div>

      {/* Parse Results */}
      {result && !comparison && (
        <>
          {/* Threat Assessment Banner */}
          <div style={{
            ...cardStyle,
            background: `${THREAT_COLORS[result.threatLevel]}18`,
            borderColor: THREAT_COLORS[result.threatLevel],
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px 16px',
          }}>
            <span style={{
              background: THREAT_COLORS[result.threatLevel],
              color: '#fff',
              padding: '2px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}>
              {result.threatLevel}
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', flex: 1 }}>
              {result.threatSummary}
            </span>
            <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {result.totalShips} ships
            </span>
          </div>

          {/* Summary Cards */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <SummaryCard label="Total Items" value={result.totalItems} />
            <SummaryCard label="Total Ships" value={result.totalShips} />
            <SummaryCard label="Capsules" value={result.capsules} />
            <SummaryCard label="Unknown Lines" value={result.unknownLines} />
          </div>

          {/* Ship Classes Breakdown */}
          {sortedClasses.length > 0 && (
            <div style={cardStyle}>
              <h4 style={sectionTitle}>Ship Classes</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {sortedClasses.map((sc) => {
                  const color = SHIP_CLASS_COLORS[sc.shipClass] || SHIP_CLASS_COLORS.Other;
                  const isExpanded = expandedClasses.has(sc.shipClass);
                  const sortedTypes = [...sc.types].sort((a, b) => b.count - a.count);

                  return (
                    <div key={sc.shipClass}>
                      <div
                        onClick={() => toggleClass(sc.shipClass)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '8px 12px',
                          cursor: 'pointer',
                          borderRadius: '4px',
                          background: isExpanded ? 'rgba(255,255,255,0.03)' : 'transparent',
                        }}
                      >
                        <span style={{
                          width: '8px', height: '8px', borderRadius: '50%',
                          background: color, flexShrink: 0,
                        }} />
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', flex: 1 }}>
                          {sc.shipClass}
                        </span>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          {sc.count}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>
                          &#9654;
                        </span>
                      </div>

                      {isExpanded && (
                        <div style={{ paddingLeft: '28px', paddingBottom: '4px' }}>
                          {sortedTypes.map((t) => (
                            <div key={t.typeId} style={{
                              display: 'flex', alignItems: 'center', gap: '8px',
                              padding: '4px 8px', fontSize: '0.85rem',
                            }}>
                              <img
                                src={`https://images.evetech.net/types/${t.typeId}/icon?size=32`}
                                alt={t.typeName}
                                width={32} height={32}
                                style={{ borderRadius: '4px' }}
                              />
                              <span style={{ flex: 1, color: 'var(--text-primary)' }}>{t.typeName}</span>
                              <span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{t.count}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Structures */}
          {result.structures.length > 0 && (
            <div style={cardStyle}>
              <h4 style={sectionTitle}>Structures</h4>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Type Name</th>
                    <th style={thStyle}>Name</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Distance (km)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.structures.map((s, i) => (
                    <tr key={i}>
                      <td style={tdStyle}>{s.typeName}</td>
                      <td style={tdStyle}>{s.name}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontFamily: 'monospace' }}>
                        {s.distanceKm.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Deployables */}
          {result.deployables.length > 0 && (
            <div style={cardStyle}>
              <h4 style={sectionTitle}>Deployables</h4>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Type Name</th>
                    <th style={thStyle}>Name</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Distance (km)</th>
                  </tr>
                </thead>
                <tbody>
                  {result.deployables.map((d, i) => (
                    <tr key={i}>
                      <td style={tdStyle}>{d.typeName}</td>
                      <td style={tdStyle}>{d.name}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontFamily: 'monospace' }}>
                        {d.distanceKm.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Comparison Results */}
      {comparison && (
        <>
          {/* Delta Summary */}
          <div style={{
            ...cardStyle,
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            padding: '12px 16px',
          }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
              <strong style={{ color: '#3fb950', fontFamily: 'monospace' }}>+{comparison.newCount}</strong> new ships arrived,{' '}
              <strong style={{ color: '#f85149', fontFamily: 'monospace' }}>-{comparison.goneCount}</strong> ships left
            </span>
          </div>

          {/* Delta by Class */}
          {Object.keys(comparison.deltaByClass).length > 0 && (
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {Object.entries(comparison.deltaByClass)
                .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                .map(([cls, delta]) => (
                  <div key={cls} style={{
                    ...cardStyle,
                    padding: '6px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    borderColor: delta > 0 ? '#3fb950' : delta < 0 ? '#f85149' : 'var(--border-color)',
                  }}>
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: SHIP_CLASS_COLORS[cls] || SHIP_CLASS_COLORS.Other,
                    }} />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{cls}</span>
                    <span style={{
                      fontFamily: 'monospace', fontSize: '0.85rem', fontWeight: 700,
                      color: delta > 0 ? '#3fb950' : delta < 0 ? '#f85149' : 'var(--text-secondary)',
                    }}>
                      {delta > 0 ? `+${delta}` : delta}
                    </span>
                  </div>
                ))}
            </div>
          )}

          {/* New Ships */}
          {comparison.newShips.length > 0 && (
            <div style={cardStyle}>
              <h4 style={sectionTitle}>New Ships</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {comparison.newShips.map((s) => (
                  <div key={s.typeId} style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '6px 12px', borderRadius: '4px',
                    background: 'rgba(63, 185, 80, 0.08)',
                  }}>
                    <img
                      src={`https://images.evetech.net/types/${s.typeId}/icon?size=32`}
                      alt={s.typeName}
                      width={32} height={32}
                      style={{ borderRadius: '4px' }}
                    />
                    <span style={{ flex: 1, fontSize: '0.85rem', color: 'var(--text-primary)' }}>{s.typeName}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{s.shipClass}</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#3fb950', fontWeight: 700 }}>
                      +{s.delta}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gone Ships */}
          {comparison.goneShips.length > 0 && (
            <div style={cardStyle}>
              <h4 style={sectionTitle}>Gone Ships</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {comparison.goneShips.map((s) => (
                  <div key={s.typeId} style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '6px 12px', borderRadius: '4px',
                    background: 'rgba(248, 81, 73, 0.08)',
                  }}>
                    <img
                      src={`https://images.evetech.net/types/${s.typeId}/icon?size=32`}
                      alt={s.typeName}
                      width={32} height={32}
                      style={{ borderRadius: '4px' }}
                    />
                    <span style={{ flex: 1, fontSize: '0.85rem', color: 'var(--text-primary)' }}>{s.typeName}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{s.shipClass}</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#f85149', fontWeight: 700 }}>
                      {s.delta}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={{
      ...cardStyle,
      flex: '1 1 120px',
      padding: '12px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
    }}>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </span>
      <span style={{ fontFamily: 'monospace', fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
        {value.toLocaleString()}
      </span>
    </div>
  );
}

/* ── Shared styles ── */

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '16px',
};

const textareaStyle: React.CSSProperties = {
  width: '100%',
  minHeight: '200px',
  background: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  padding: '12px',
  fontFamily: 'monospace',
  fontSize: '0.85rem',
  resize: 'vertical',
  outline: 'none',
  boxSizing: 'border-box',
};

const buttonStyle: React.CSSProperties = {
  background: 'var(--accent-color, #58a6ff)',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  padding: '8px 20px',
  fontSize: '0.85rem',
  fontWeight: 600,
  cursor: 'pointer',
};

const clearButtonStyle: React.CSSProperties = {
  background: 'transparent',
  color: 'var(--text-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  padding: '8px 20px',
  fontSize: '0.85rem',
  cursor: 'pointer',
};

const sectionTitle: React.CSSProperties = {
  margin: '0 0 12px 0',
  fontSize: '0.85rem',
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '6px 12px',
  fontSize: '0.7rem',
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  borderBottom: '1px solid var(--border-color)',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 12px',
  fontSize: '0.85rem',
  color: 'var(--text-primary)',
  borderBottom: '1px solid rgba(255,255,255,0.04)',
};
