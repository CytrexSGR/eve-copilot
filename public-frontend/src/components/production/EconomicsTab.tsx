import { useState, useEffect, useMemo } from 'react';
import { economicsApi } from '../../services/api/production';
import type { ManufacturingOpportunity } from '../../types/production';
import { formatISK } from '../../utils/format';

type SortField = 'type_name' | 'production_cost' | 'sell_price' | 'profit_per_unit' | 'roi_percent' | 'daily_volume';
type SortDir = 'asc' | 'desc';

const LIMIT_OPTIONS = [25, 50, 100];

interface Props {
  onNavigateToItem?: (typeId: number, typeName: string) => void;
}

export function EconomicsTab({ onNavigateToItem }: Props) {
  const [opportunities, setOpportunities] = useState<ManufacturingOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [minRoi, setMinRoi] = useState(5);
  const [maxRoi, setMaxRoi] = useState(300);
  const [minProfit, setMinProfit] = useState(1000000);
  const [minVolume, setMinVolume] = useState(10);
  const [limit, setLimit] = useState(50);

  // Sort state
  const [sortField, setSortField] = useState<SortField>('roi_percent');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Row hover state
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);

  const fetchOpportunities = () => {
    setLoading(true);
    setError(null);
    economicsApi.getOpportunities({ min_roi: minRoi, min_profit: minProfit, min_volume: minVolume, limit })
      .then(data => setOpportunities(data.opportunities))
      .catch(err => setError(err.message || 'Failed to load opportunities'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchOpportunities(); }, []);

  const sorted = useMemo(() => {
    const copy = opportunities.filter(o => maxRoi <= 0 || o.roi_percent <= maxRoi);
    copy.sort((a, b) => {
      const av = a[sortField];
      const bv = b[sortField];
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const an = av as number;
      const bn = bv as number;
      return sortDir === 'asc' ? an - bn : bn - an;
    });
    return copy;
  }, [opportunities, sortField, sortDir, maxRoi]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sortArrow = (field: SortField) =>
    sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : '';

  const roiColor = (roi: number) =>
    roi > 30 ? '#3fb950' : roi >= 10 ? '#d29922' : '#8b949e';

  const inputStyle: React.CSSProperties = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: 4,
    color: 'var(--text-primary)',
    padding: '6px 10px',
    fontSize: '0.8rem',
  };

  const headerCellStyle: React.CSSProperties = {
    cursor: 'pointer',
    userSelect: 'none',
    textTransform: 'uppercase',
    fontSize: '0.65rem',
    fontWeight: 700,
    color: 'var(--text-secondary)',
    padding: '0.5rem 0.75rem',
  };

  return (
    <div>
      {/* Section header */}
      <div style={{
        fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)',
        textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: '0.75rem',
      }}>
        Manufacturing Opportunities
      </div>

      {/* Filter Bar */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem',
        padding: '0.75rem', background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)', borderRadius: 8,
        alignItems: 'flex-end',
      }}>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Min ROI %</div>
          <input
            type="number"
            value={minRoi}
            onChange={e => setMinRoi(Number(e.target.value))}
            min={0}
            style={{ ...inputStyle, width: 70 }}
          />
        </div>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Max ROI %</div>
          <input
            type="number"
            value={maxRoi}
            onChange={e => setMaxRoi(Number(e.target.value))}
            min={0}
            style={{ ...inputStyle, width: 70 }}
          />
        </div>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Min Profit ISK</div>
          <input
            type="number"
            value={minProfit}
            onChange={e => setMinProfit(Number(e.target.value))}
            min={0}
            style={{ ...inputStyle, width: 120 }}
          />
        </div>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Min Daily Vol</div>
          <input
            type="number"
            value={minVolume}
            onChange={e => setMinVolume(Number(e.target.value))}
            min={0}
            style={{ ...inputStyle, width: 80 }}
          />
        </div>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Limit</div>
          <select
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            style={inputStyle}
          >
            {LIMIT_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <button
          onClick={fetchOpportunities}
          disabled={loading}
          style={{
            padding: '6px 16px',
            background: loading ? 'var(--bg-elevated)' : 'transparent',
            border: '1px solid #00d4ff',
            borderRadius: 4,
            color: '#00d4ff',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '0.8rem',
            fontWeight: 600,
          }}
        >
          {loading ? 'Loading...' : 'Search'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: '1rem', background: 'rgba(248,81,73,0.1)',
          border: '1px solid #f85149', borderRadius: 8,
          color: '#f85149', marginBottom: '1rem', fontSize: '0.85rem',
        }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && <div className="skeleton" style={{ height: 400 }} />}

      {/* Table */}
      {!loading && !error && (
        opportunities.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
            No profitable opportunities found
          </div>
        ) : (
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            overflow: 'hidden',
          }}>
            {/* Header row */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '40px 1fr 130px 130px 130px 90px 100px',
              borderBottom: '1px solid var(--border-color)',
            }}>
              <div style={{ ...headerCellStyle, cursor: 'default' }} />
              <div style={headerCellStyle} onClick={() => handleSort('type_name')}>
                Item{sortArrow('type_name')}
              </div>
              <div style={{ ...headerCellStyle, textAlign: 'right' }} onClick={() => handleSort('production_cost')}>
                Prod. Cost{sortArrow('production_cost')}
              </div>
              <div style={{ ...headerCellStyle, textAlign: 'right' }} onClick={() => handleSort('sell_price')}>
                Sell Price{sortArrow('sell_price')}
              </div>
              <div style={{ ...headerCellStyle, textAlign: 'right' }} onClick={() => handleSort('profit_per_unit')}>
                Profit/Unit{sortArrow('profit_per_unit')}
              </div>
              <div style={{ ...headerCellStyle, textAlign: 'right' }} onClick={() => handleSort('roi_percent')}>
                ROI %{sortArrow('roi_percent')}
              </div>
              <div style={{ ...headerCellStyle, textAlign: 'right' }} onClick={() => handleSort('daily_volume')}>
                Daily Vol{sortArrow('daily_volume')}
              </div>
            </div>

            {/* Data rows */}
            {sorted.map((opp, idx) => (
              <div
                key={opp.type_id}
                onMouseEnter={() => setHoveredRow(idx)}
                onMouseLeave={() => setHoveredRow(null)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '40px 1fr 130px 130px 130px 90px 100px',
                  alignItems: 'center',
                  padding: '0.35rem 0',
                  fontSize: '0.78rem',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                  background: hoveredRow === idx
                    ? 'var(--bg-elevated)'
                    : idx % 2 === 1 ? 'rgba(255,255,255,0.02)' : 'transparent',
                }}
              >
                {/* Icon */}
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <img
                    src={`https://images.evetech.net/types/${opp.type_id}/icon?size=32`}
                    alt=""
                    width={32}
                    height={32}
                    style={{ borderRadius: 4 }}
                    loading="lazy"
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                </div>
                {/* Name */}
                <div
                  onClick={onNavigateToItem ? () => onNavigateToItem(opp.type_id, opp.type_name) : undefined}
                  style={{
                    padding: '0 0.5rem',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    cursor: onNavigateToItem ? 'pointer' : 'default',
                    color: onNavigateToItem ? '#00d4ff' : 'var(--text-primary)',
                    transition: 'color 0.1s',
                  }}
                  onMouseEnter={onNavigateToItem ? e => { e.currentTarget.style.textDecoration = 'underline'; } : undefined}
                  onMouseLeave={onNavigateToItem ? e => { e.currentTarget.style.textDecoration = 'none'; } : undefined}
                >
                  {opp.type_name}
                </div>
                {/* Production cost */}
                <div style={{
                  textAlign: 'right', fontFamily: 'monospace',
                  color: '#f85149', padding: '0 0.75rem',
                }}>
                  {formatISK(opp.production_cost)}
                </div>
                {/* Sell price */}
                <div style={{
                  textAlign: 'right', fontFamily: 'monospace',
                  color: '#3fb950', padding: '0 0.75rem',
                }}>
                  {formatISK(opp.sell_price)}
                </div>
                {/* Profit/Unit */}
                <div style={{
                  textAlign: 'right', fontFamily: 'monospace',
                  color: '#3fb950', padding: '0 0.75rem',
                }}>
                  {formatISK(opp.profit_per_unit)}
                </div>
                {/* ROI % */}
                <div style={{
                  textAlign: 'right', fontFamily: 'monospace',
                  color: roiColor(opp.roi_percent), padding: '0 0.75rem',
                }}>
                  {opp.roi_percent.toFixed(1)}%
                </div>
                {/* Daily Volume */}
                <div style={{
                  textAlign: 'right', fontFamily: 'monospace',
                  padding: '0 0.75rem',
                }}>
                  {opp.daily_volume.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
