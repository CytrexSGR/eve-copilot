import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import axios from 'axios';

const api = axios.create({ baseURL: '/api', timeout: 10_000, withCredentials: true });

export function CorpSummary() {
  const { tierInfo, account } = useAuth();
  const [data, setData] = useState<{ srp_pending: number; timers_24h: number; applications: number } | null>(null);

  const isCorp = tierInfo?.tier === 'corporation' || tierInfo?.tier === 'alliance' || tierInfo?.tier === 'coalition';
  const corpId = account?.corporation_id;

  useEffect(() => {
    if (!isCorp) return;
    const requests: Promise<any>[] = [
      corpId ? api.get(`/finance/srp/requests/${corpId}`, { params: { status: 'pending' } }) : Promise.reject('no corp'),
      api.get('/timers/upcoming', { params: { hours: 24 } }),
      api.get('/hr/applications/', { params: { status: 'pending' } }),
    ];
    Promise.allSettled(requests).then(([srpRes, timerRes, appRes]) => {
      const count = (res: PromiseSettledResult<any>) => {
        if (res.status !== 'fulfilled') return 0;
        const d = res.value?.data;
        if (Array.isArray(d)) return d.length;
        return d?.total ?? d?.length ?? 0;
      };
      setData({
        srp_pending: count(srpRes),
        timers_24h: count(timerRes),
        applications: count(appRes),
      });
    });
  }, [isCorp, corpId]);

  if (!isCorp) return null;

  return (
    <div style={{
      background: 'rgba(255,204,0,0.04)', border: '1px solid rgba(255,204,0,0.15)',
      borderRadius: '8px', padding: '0.65rem', marginBottom: '0.75rem',
    }}>
      <div style={{ fontSize: '0.65rem', color: '#ffcc00', textTransform: 'uppercase', fontWeight: 700, marginBottom: '0.4rem' }}>
        Corporation Status
      </div>
      {data ? (
        <div style={{ display: 'flex', gap: '1rem' }}>
          <Link to="/corp/srp" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 700, color: data.srp_pending > 0 ? '#f85149' : '#3fb950' }}>
              {data.srp_pending}
            </span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.3rem' }}>SRP pending</span>
          </Link>
          <Link to="/corp/timers" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 700, color: data.timers_24h > 0 ? '#ff8800' : '#3fb950' }}>
              {data.timers_24h}
            </span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.3rem' }}>timers &lt;24h</span>
          </Link>
          <Link to="/corp/hr" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 700, color: data.applications > 0 ? '#00d4ff' : '#3fb950' }}>
              {data.applications}
            </span>
            <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: '0.3rem' }}>applications</span>
          </Link>
        </div>
      ) : (
        <div className="skeleton" style={{ height: 30 }} />
      )}
    </div>
  );
}
