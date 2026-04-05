import { useState, useEffect } from 'react';
import { getEctmapBaseUrl } from '../utils/format';

/**
 * Ectmap Page - Full-screen EVE Universe Map with status level filters
 */
export function Ectmap() {
  const [activityMinutes, setActivityMinutes] = useState(60);
  const [totalIsk, setTotalIsk] = useState(0);
  const [filters, setFilters] = useState({
    gank: true,
    brawl: true,
    battle: true,
    hellcamp: true,
  });

  // Fetch ISK destroyed for display
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`/api/war/battles/active?minutes=${activityMinutes}`);
        const data = await res.json();
        const isk = data.battles?.reduce((sum: number, b: any) => sum + (b.total_isk_destroyed || 0), 0) || 0;
        setTotalIsk(isk);
      } catch (e) {
        console.error('Failed to fetch battle stats', e);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, [activityMinutes]);

  // Build iframe URL with filter params
  const filterParams = Object.entries(filters)
    .filter(([_, enabled]) => enabled)
    .map(([level]) => level)
    .join(',');

  const iframeSrc = `${getEctmapBaseUrl()}?minutes=${activityMinutes}&levels=${filterParams}`;

  const toggleFilter = (level: keyof typeof filters) => {
    setFilters(prev => ({ ...prev, [level]: !prev[level] }));
  };

  const filterButtons = [
    { key: 'gank', label: 'Gank', bgActive: 'bg-red-600' },
    { key: 'brawl', label: 'Brawl', bgActive: 'bg-orange-500' },
    { key: 'battle', label: 'Battle', bgActive: 'bg-yellow-500' },
    { key: 'hellcamp', label: 'Hellcamp', bgActive: 'bg-cyan-500' },
  ] as const;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: '#0a0a0f',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 1.5rem',
        borderBottom: '1px solid #333',
        backgroundColor: '#111118',
        flexShrink: 0
      }}>
        {/* Left: Title + ISK */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <h1 style={{ margin: 0, fontSize: '1.25rem', color: 'white' }}>🗺️ Live Battle Map</h1>
          <span style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: '#ef4444',
            fontFamily: 'monospace'
          }}>
            💰 {(totalIsk / 1_000_000_000).toFixed(1)}B ISK
            <span style={{ fontSize: '0.875rem', color: '#888', marginLeft: '0.5rem' }}>
              ({activityMinutes < 60 ? `${activityMinutes}m` : `${activityMinutes / 60}h`})
            </span>
          </span>
        </div>

        {/* Right: Filters + Time selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {filterButtons.map(({ key, label, bgActive }) => (
            <button
              key={key}
              onClick={() => toggleFilter(key)}
              style={{
                padding: '0.375rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
                backgroundColor: filters[key] ? undefined : '#374151',
                color: filters[key] ? (key === 'battle' || key === 'hellcamp' ? '#000' : '#fff') : '#9ca3af',
              }}
              className={filters[key] ? bgActive : ''}
            >
              {label}
            </button>
          ))}

          <div style={{ width: '1px', height: '24px', backgroundColor: '#444', margin: '0 0.5rem' }} />

          <select
            value={activityMinutes}
            onChange={(e) => setActivityMinutes(parseInt(e.target.value))}
            style={{
              padding: '0.375rem 0.75rem',
              fontSize: '0.75rem',
              borderRadius: '4px',
              backgroundColor: '#374151',
              color: '#d1d5db',
              border: '1px solid #4b5563',
              cursor: 'pointer'
            }}
          >
            <option value={10}>10m</option>
            <option value={60}>1h</option>
          </select>
        </div>
      </div>

      {/* Map iframe */}
      <iframe
        src={iframeSrc}
        style={{
          flex: 1,
          width: '100%',
          border: 'none'
        }}
        title="EC Trade Interactive Map"
        allow="fullscreen"
      />
    </div>
  );
}

export default Ectmap;
