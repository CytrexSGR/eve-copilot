import { useState, useEffect } from 'react';

interface EsiStatus {
  players: number;
  server_version: string;
  start_time: string;
}

export function EsiStatusBadge() {
  const [status, setStatus] = useState<'loading' | 'online' | 'offline'>('loading');
  const [players, setPlayers] = useState(0);

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await window.fetch('https://esi.evetech.net/latest/status/?datasource=tranquility');
        if (resp.ok) {
          const data: EsiStatus = await resp.json();
          setStatus('online');
          setPlayers(data.players || 0);
        } else {
          setStatus('offline');
        }
      } catch {
        setStatus('offline');
      }
    };
    fetch();
    const interval = setInterval(fetch, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (status === 'loading') return null;

  const online = status === 'online';
  const dotColor = online ? '#3fb950' : '#f85149';
  const label = online
    ? `TQ: ${players.toLocaleString()}`
    : 'TQ: Offline';

  return (
    <div
      title={online ? `Tranquility — ${players.toLocaleString()} pilots online` : 'Tranquility offline'}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: '0.7rem',
        color: 'var(--text-secondary)',
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid var(--border-color)',
        cursor: 'default',
        userSelect: 'none',
      }}
    >
      <span style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: dotColor,
        boxShadow: `0 0 4px ${dotColor}`,
        flexShrink: 0,
      }} />
      {label}
    </div>
  );
}
