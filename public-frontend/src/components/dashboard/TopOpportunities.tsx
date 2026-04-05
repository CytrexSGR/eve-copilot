import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { marketApi } from '../../services/api/market';
import { usePersonalizedScore, type PersonalizedScore, type OpportunityInput } from '../../hooks/usePersonalizedScore';
import { usePilotIntel } from '../../hooks/usePilotIntel';
import { formatISK } from '../../utils/format';

interface ScoredOpp {
  label: string;
  type: 'manufacturing' | 'arbitrage' | 'trading';
  profit: number;
  details: string;
  link: string;
  ps: PersonalizedScore;
}

export function TopOpportunities() {
  const { score } = usePersonalizedScore();
  const { derived } = usePilotIntel();
  const [opps, setOpps] = useState<ScoredOpp[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (derived.totalWallet === 0 && derived.primaryCharacter === null) return;

    Promise.allSettled([
      marketApi.scanOpportunities({ min_roi: 10, top: 10 }),
      marketApi.getArbitrageRoutes({ min_profit_per_trip: 5_000_000, max_jumps: 15 }),
      marketApi.getTradingOpportunities({ min_margin: 5 }),
    ]).then(([mfgRes, arbRes, tradRes]) => {
      const scored: ScoredOpp[] = [];

      // Manufacturing
      if (mfgRes.status === 'fulfilled') {
        for (const m of (mfgRes.value?.results ?? []).slice(0, 5)) {
          const netProfit = m.net_profit ?? m.profit;
          const netRoi = m.net_roi ?? m.roi;
          const avgVol = m.avg_daily_volume ?? 0;
          const input: OpportunityInput = {
            type: 'manufacturing',
            capitalRequired: m.material_cost,
            estimatedProfit: netProfit,
            riskScore: avgVol === 0 ? 90 : (m.risk_score ?? 50),
          };
          scored.push({
            label: m.product_name,
            type: 'manufacturing',
            profit: netProfit,
            details: `${netRoi.toFixed(0)}% ROI | ${formatISK(m.material_cost)} capital${avgVol === 0 ? ' | No Volume' : ''}`,
            link: '/market?tab=opportunities',
            ps: score(input),
          });
        }
      }

      // Arbitrage
      if (arbRes.status === 'fulfilled') {
        for (const r of (arbRes.value?.routes ?? []).slice(0, 3)) {
          const input: OpportunityInput = {
            type: 'arbitrage',
            capitalRequired: r.summary.total_buy_cost,
            estimatedProfit: r.summary.total_profit,
            estimatedTimeHours: parseFloat(r.logistics.round_trip_time) || 1,
            recommendedShip: r.logistics.recommended_ship,
            cargoVolume: r.summary.total_volume,
            riskScore: r.safety === 'SAFE' ? 10 : r.safety === 'RISKY' ? 60 : 90,
          };
          scored.push({
            label: `Haul to ${r.destination_hub}`,
            type: 'arbitrage',
            profit: r.summary.total_profit,
            details: `${r.jumps}J ${r.safety} | ${r.logistics.recommended_ship}`,
            link: '/market?tab=arbitrage',
            ps: score(input),
          });
        }
      }

      // Trading
      if (tradRes.status === 'fulfilled') {
        for (const t of (tradRes.value?.results ?? []).slice(0, 5)) {
          const input: OpportunityInput = {
            type: 'trading',
            capitalRequired: t.buy_price * Math.min(t.volume, 10),
            estimatedProfit: t.profit_per_unit * Math.min(t.volume, 10),
            riskScore: t.risk_score,
          };
          scored.push({
            label: t.item_name,
            type: 'trading',
            profit: t.profit_per_unit,
            details: `${t.roi.toFixed(1)}% margin | ${t.volume} vol/day`,
            link: '/market?tab=opportunities',
            ps: score(input),
          });
        }
      }

      // Sort by personal score descending, take top 5
      scored.sort((a, b) => b.ps.score - a.ps.score);
      setOpps(scored.slice(0, 5));
      setLoading(false);
    });
  }, [derived, score]);

  const TYPE_COLORS: Record<string, string> = { manufacturing: '#3fb950', arbitrage: '#00d4ff', trading: '#ffcc00' };
  const TYPE_LABELS: Record<string, string> = { manufacturing: 'MFG', arbitrage: 'HAUL', trading: 'TRADE' };

  if (loading) return <div className="skeleton" style={{ height: 200, marginBottom: '0.75rem' }} />;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '8px', padding: '0.75rem', marginBottom: '0.75rem',
    }}>
      <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
        Top Opportunities For You
      </div>
      {opps.length === 0 ? (
        <div style={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>
          No opportunities found — check Market tab for more options
        </div>
      ) : opps.map((opp, i) => (
        <Link to={opp.link} key={i} style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.45rem 0.5rem', textDecoration: 'none', color: 'inherit',
          borderBottom: i < opps.length - 1 ? '1px solid rgba(255,255,255,0.04)' : undefined,
        }}>
          {/* Score badge */}
          <div style={{
            width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: '0.7rem', fontFamily: 'monospace',
            background: opp.ps.score >= 70 ? 'rgba(63,185,80,0.15)' : opp.ps.score >= 40 ? 'rgba(255,204,0,0.15)' : 'rgba(248,81,73,0.15)',
            border: `1px solid ${opp.ps.score >= 70 ? '#3fb950' : opp.ps.score >= 40 ? '#ffcc00' : '#f85149'}44`,
            color: opp.ps.score >= 70 ? '#3fb950' : opp.ps.score >= 40 ? '#ffcc00' : '#f85149',
          }}>
            {opp.ps.score}
          </div>
          {/* Type badge */}
          <span style={{
            padding: '2px 5px', borderRadius: '3px', fontSize: '0.55rem', fontWeight: 700,
            background: `${TYPE_COLORS[opp.type]}15`, border: `1px solid ${TYPE_COLORS[opp.type]}33`,
            color: TYPE_COLORS[opp.type], textTransform: 'uppercase', flexShrink: 0,
          }}>
            {TYPE_LABELS[opp.type]}
          </span>
          {/* Info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {opp.label}
            </div>
            <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)' }}>{opp.details}</div>
          </div>
          {/* Profit */}
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: '#3fb950', fontWeight: 700 }}>
              +{formatISK(opp.profit)}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)' }}>
              {opp.ps.canAfford ? 'Ready' : 'Need ISK'}
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
