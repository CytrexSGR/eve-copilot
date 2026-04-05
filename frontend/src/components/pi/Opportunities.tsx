import { Fragment, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { getOpportunities, getProductionChain } from '../../api/pi';
import type { PIProfitability, PIChainNode } from '../../api/pi';

type SortField = 'profit_per_hour' | 'roi_percent' | 'score';

function calculateScore(item: PIProfitability, maxRoi: number, maxVolume: number): number {
  const roiNorm = maxRoi > 0 ? item.roi_percent / maxRoi : 0;
  const volumeNorm = maxVolume > 0 ? item.profit_per_hour / maxVolume : 0;
  return roiNorm * 0.6 + volumeNorm * 0.4;
}

export function Opportunities() {
  const [tier, setTier] = useState<number | undefined>(undefined);
  const [minRoi, setMinRoi] = useState(10);
  const [sortBy, setSortBy] = useState<SortField>('profit_per_hour');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: opportunities, isLoading } = useQuery({
    queryKey: ['pi-opportunities', tier, minRoi],
    queryFn: () => getOpportunities({ tier, limit: 100, min_roi: minRoi }),
  });

  const { data: chainData } = useQuery({
    queryKey: ['pi-chain', expandedId],
    queryFn: () => expandedId ? getProductionChain(expandedId) : null,
    enabled: expandedId !== null,
  });

  const maxRoi = opportunities ? Math.max(...opportunities.map(o => o.roi_percent)) : 0;
  const maxVolume = opportunities ? Math.max(...opportunities.map(o => o.profit_per_hour)) : 0;

  const sortedData = opportunities
    ? [...opportunities].sort((a, b) => {
        if (sortBy === 'score') {
          return calculateScore(b, maxRoi, maxVolume) - calculateScore(a, maxRoi, maxVolume);
        }
        return (b[sortBy] || 0) - (a[sortBy] || 0);
      })
    : [];

  const formatIsk = (value: number) => {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toFixed(0);
  };

  const getRoiClass = (roi: number) => {
    if (roi >= 50) return 'roi-high';
    if (roi >= 20) return 'roi-medium';
    return '';
  };

  return (
    <div className="opportunities">
      <div className="filter-bar">
        <div className="filter-group">
          <label>Tier</label>
          <select value={tier || ''} onChange={(e) => setTier(e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">All Tiers</option>
            <option value="1">P1</option>
            <option value="2">P2</option>
            <option value="3">P3</option>
            <option value="4">P4</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Min ROI %</label>
          <input
            type="number"
            value={minRoi}
            onChange={(e) => setMinRoi(Number(e.target.value))}
            min={0}
            max={1000}
          />
        </div>

        <div className="filter-group">
          <label>Sort By</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortField)}>
            <option value="profit_per_hour">Profit/Hour</option>
            <option value="roi_percent">ROI %</option>
            <option value="score">Score (ROI + Volume)</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="loading">Loading opportunities...</div>
      ) : (
        <table className="opportunities-table">
          <thead>
            <tr>
              <th></th>
              <th>Product</th>
              <th>Tier</th>
              <th>Input Cost</th>
              <th>Sell Price</th>
              <th>Profit/Run</th>
              <th>ROI %</th>
              <th>Profit/Hour</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((item) => (
              <Fragment key={item.type_id}>
                <tr
                  className={`opportunity-row ${expandedId === item.type_id ? 'expanded' : ''}`}
                  onClick={() => setExpandedId(expandedId === item.type_id ? null : item.type_id)}
                >
                  <td>
                    {expandedId === item.type_id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </td>
                  <td className="product-name">{item.type_name}</td>
                  <td>P{item.tier}</td>
                  <td>{formatIsk(item.input_cost)}</td>
                  <td>{formatIsk(item.output_value)}</td>
                  <td className="profit">{formatIsk(item.profit_per_run)}</td>
                  <td className={getRoiClass(item.roi_percent)}>{item.roi_percent.toFixed(1)}%</td>
                  <td>{formatIsk(item.profit_per_hour)}/h</td>
                  <td>{(calculateScore(item, maxRoi, maxVolume) * 100).toFixed(0)}</td>
                </tr>
                {expandedId === item.type_id && chainData && (
                  <tr className="chain-row">
                    <td colSpan={9}>
                      <div className="production-chain">
                        <h4>Production Chain</h4>
                        <ChainTree node={chainData} />
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ChainTree({ node, depth = 0 }: { node: PIChainNode; depth?: number }) {
  const tierColors = ['#6b7280', '#22c55e', '#3b82f6', '#a855f7', '#f97316'];

  return (
    <div className="chain-node" style={{ marginLeft: depth * 24 }}>
      <div className="chain-item">
        <span
          className="tier-badge"
          style={{ backgroundColor: tierColors[node.tier] || tierColors[0] }}
        >
          P{node.tier}
        </span>
        <span className="chain-name">{node.type_name}</span>
        <span className="chain-qty">x{node.quantity_needed.toFixed(1)}</span>
      </div>
      {node.children?.map((child, i) => (
        <ChainTree key={`${child.type_id}-${i}`} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}
