import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { warApi } from '../../services/api';

interface CapitalAlliance {
  alliance_id: number;
  alliance_name: string;
  ticker: string;
  total_caps: number;
  titans: number;
  supers: number;
  dreads: number;
}

interface CapitalSummary {
  total_engagements: number;
  unique_alliances: number;
  systems_active: number;
}

interface CapitalIntelSectionProps {
  timeframeMinutes?: number;
}

function getTimeframeLabel(minutes: number): string {
  if (minutes <= 10) return '10m';
  if (minutes <= 60) return '1h';
  if (minutes <= 720) return '12h';
  if (minutes <= 1440) return '24h';
  return '7d';
}

export function CapitalIntelSection({ timeframeMinutes = 1440 }: CapitalIntelSectionProps) {
  const [summary, setSummary] = useState<CapitalSummary | null>(null);
  const [topAlliances, setTopAlliances] = useState<CapitalAlliance[]>([]);
  const [loading, setLoading] = useState(true);

  const timeframeLabel = getTimeframeLabel(timeframeMinutes);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const days = Math.max(1, Math.ceil(timeframeMinutes / 1440));
        const data = await warApi.getCapitalIntel(days);
        setSummary(data.summary);
        setTopAlliances(data.top_alliances || []);
      } catch (err) {
        console.error('Failed to load capital intel:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [timeframeMinutes]);

  const totalCaps = topAlliances.reduce((sum, a) => sum + a.total_caps, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.65rem' }}>🚀</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00ff88', textTransform: 'uppercase' }}>
            Capital Intel
          </span>
          {summary && (
            <div style={{ display: 'flex', gap: '0.75rem', marginLeft: '1rem', fontSize: '0.65rem' }}>
              <span><span style={{ color: '#ff8800', fontWeight: 700, fontFamily: 'monospace' }}>{summary.total_engagements}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>ops</span></span>
              <span><span style={{ color: '#a855f7', fontWeight: 700, fontFamily: 'monospace' }}>{summary.unique_alliances}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>alliances</span></span>
              <span><span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>{summary.systems_active}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>systems</span></span>
              <span><span style={{ color: '#00ff88', fontWeight: 700, fontFamily: 'monospace' }}>{totalCaps}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>caps</span></span>
            </div>
          )}
        </div>
        <span style={{ fontSize: '0.55rem', color: '#00ff88' }}>({timeframeLabel})</span>
      </div>

      {/* Alliance Grid - Horizontal */}
      <div style={{
        padding: '0.4rem',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '0.4rem',
      }}>
        {loading ? (
          [1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="skeleton" style={{ height: '60px', borderRadius: '4px' }} />
          ))
        ) : topAlliances.length === 0 ? (
          <div style={{
            padding: '1.5rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.7rem',
            gridColumn: '1 / -1',
          }}>
            No capital activity
          </div>
        ) : (
          topAlliances.slice(0, 12).map((alliance) => (
            <CapitalAllianceCard key={alliance.alliance_id} alliance={alliance} />
          ))
        )}
      </div>
    </div>
  );
}

function CapitalAllianceCard({ alliance }: { alliance: CapitalAlliance }) {
  const totalCaps = alliance.titans + alliance.supers + alliance.dreads;
  const titanPct = totalCaps > 0 ? (alliance.titans / totalCaps) * 100 : 0;
  const superPct = totalCaps > 0 ? (alliance.supers / totalCaps) * 100 : 0;
  const dreadPct = totalCaps > 0 ? (alliance.dreads / totalCaps) * 100 : 0;

  // Color based on titan count
  const borderColor = alliance.titans > 0 ? '#ff4444' : alliance.supers > 0 ? '#ff8800' : '#00d4ff';

  return (
    <Link
      to={`/alliance/${alliance.alliance_id}`}
      style={{
        display: 'block',
        padding: '0.4rem 0.5rem',
        marginBottom: '0.2rem',
        background: `${borderColor}10`,
        borderRadius: '4px',
        borderLeft: `2px solid ${borderColor}`,
        textDecoration: 'none',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = `${borderColor}10`; }}
    >
      {/* Header Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <img
          src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=64`}
          alt=""
          style={{ width: 24, height: 24, borderRadius: '3px', background: 'rgba(0,0,0,0.3)' }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ fontSize: '0.7rem', color: '#00d4ff', fontWeight: 700 }}>[{alliance.ticker}]</span>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {alliance.alliance_name}
            </span>
          </div>
        </div>
        <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#00ff88', fontFamily: 'monospace' }}>
          {alliance.total_caps}
        </span>
      </div>

      {/* Stats Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.25rem' }}>
        {/* Cap Type Breakdown */}
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.65rem' }}>
          {alliance.titans > 0 && (
            <span><span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>{alliance.titans}</span><span style={{ color: 'rgba(255,255,255,0.3)' }}>T</span></span>
          )}
          {alliance.supers > 0 && (
            <span><span style={{ color: '#ff8800', fontWeight: 700, fontFamily: 'monospace' }}>{alliance.supers}</span><span style={{ color: 'rgba(255,255,255,0.3)' }}>S</span></span>
          )}
          {alliance.dreads > 0 && (
            <span><span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>{alliance.dreads}</span><span style={{ color: 'rgba(255,255,255,0.3)' }}>D</span></span>
          )}
        </div>

        {/* Composition Bar */}
        <div style={{ marginLeft: 'auto', width: '60px' }}>
          <div style={{ display: 'flex', height: '4px', borderRadius: '2px', overflow: 'hidden', background: 'rgba(255,255,255,0.1)' }}>
            {titanPct > 0 && <div style={{ width: `${titanPct}%`, background: '#ff4444' }} />}
            {superPct > 0 && <div style={{ width: `${superPct}%`, background: '#ff8800' }} />}
            {dreadPct > 0 && <div style={{ width: `${dreadPct}%`, background: '#00d4ff' }} />}
          </div>
        </div>
      </div>
    </Link>
  );
}
