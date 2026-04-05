import { useState, useEffect } from 'react';
import { fleetApi } from '../../services/api/fleet';
import type { FleetOperationSummary, FleetParticipation } from '../../types/fleet';
import { formatDuration } from '../../types/fleet';

export function PapStatsTab({ corpId: _corpId }: { corpId: number }) {
  const [history, setHistory] = useState<FleetOperationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [papMap, setPapMap] = useState<Map<number, FleetParticipation>>(new Map());
  const [loadingPaps, setLoadingPaps] = useState(false);

  useEffect(() => {
    setLoading(true);
    fleetApi.getHistory({ limit: 100 })
      .then(setHistory)
      .catch(err => console.error('Failed to load fleet history:', err))
      .finally(() => setLoading(false));
  }, []);

  // Load all PAP data for aggregate
  useEffect(() => {
    if (history.length === 0) return;
    setLoadingPaps(true);
    const load = async () => {
      const map = new Map<number, FleetParticipation>();
      for (const op of history) {
        try {
          const pap = await fleetApi.getParticipation(op.id);
          map.set(op.id, pap);
        } catch {
          // skip failed
        }
      }
      setPapMap(map);
      setLoadingPaps(false);
    };
    load();
  }, [history]);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>;
  }

  // Aggregate pilot stats from all fleets
  const pilotStats: Record<number, {
    name: string;
    totalOps: number;
    totalSnapshots: number;
    avgParticipation: number;
    totalDurationMinutes: number;
    ships: Set<string>;
  }> = {};

  papMap.forEach((pap, opId) => {
    const op = history.find(h => h.id === opId);
    const opDuration = op?.durationMinutes ?? 0;

    for (const p of pap.participants) {
      if (!pilotStats[p.characterId]) {
        pilotStats[p.characterId] = {
          name: p.characterName || `ID ${p.characterId}`,
          totalOps: 0,
          totalSnapshots: 0,
          avgParticipation: 0,
          totalDurationMinutes: 0,
          ships: new Set(),
        };
      }
      const stat = pilotStats[p.characterId];
      stat.totalOps++;
      stat.totalSnapshots += p.snapshotCount;
      stat.avgParticipation += (p.participationPct ?? 0);
      stat.totalDurationMinutes += opDuration * ((p.participationPct ?? 100) / 100);
      if (p.shipTypeName) stat.ships.add(p.shipTypeName);
      else if (p.shipName) stat.ships.add(p.shipName);
    }
  });

  // Calculate averages
  const leaderboard = Object.entries(pilotStats)
    .map(([id, stat]) => ({
      characterId: Number(id),
      name: stat.name,
      totalOps: stat.totalOps,
      totalSnapshots: stat.totalSnapshots,
      avgParticipation: stat.totalOps > 0 ? stat.avgParticipation / stat.totalOps : 0,
      totalDurationMinutes: stat.totalDurationMinutes,
      shipCount: stat.ships.size,
    }))
    .sort((a, b) => b.totalOps - a.totalOps);

  const totalFleets = history.length;
  const totalPilots = leaderboard.length;
  const avgPilotsPerFleet = totalFleets > 0
    ? history.reduce((sum, op) => sum + (op.totalParticipants ?? op.memberCount ?? 0), 0) / totalFleets
    : 0;
  const avgDuration = totalFleets > 0
    ? history.reduce((sum, op) => sum + (op.durationMinutes ?? 0), 0) / totalFleets
    : 0;

  const statCardStyle = {
    background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
    borderRadius: '8px', padding: '1rem',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '0.75rem' }}>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Total Fleets</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace' }}>{totalFleets}</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Unique Pilots</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: '#00d4ff' }}>{totalPilots}</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Avg Fleet Size</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: '#3fb950' }}>{avgPilotsPerFleet.toFixed(1)}</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Avg Duration</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace', color: '#d29922' }}>{formatDuration(avgDuration)}</div>
        </div>
      </div>

      {loadingPaps && (
        <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center' }}>Loading participation data...</div>
      )}

      {/* PAP Leaderboard */}
      <div style={statCardStyle}>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>PAP Leaderboard ({leaderboard.length} pilots)</div>

        <div style={{
          display: 'grid', gridTemplateColumns: '30px 1.5fr 70px 70px 70px 70px 70px',
          gap: '0.5rem', padding: '0.4rem 0', borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
        }}>
          <span>#</span><span>Pilot</span>
          <span style={{ textAlign: 'right' }}>Fleets</span>
          <span style={{ textAlign: 'right' }}>Snaps</span>
          <span style={{ textAlign: 'right' }}>Avg PAP</span>
          <span style={{ textAlign: 'right' }}>Time</span>
          <span style={{ textAlign: 'right' }}>Ships</span>
        </div>

        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {leaderboard.length === 0 ? (
            <div style={{ padding: '1rem', color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>No participation data</div>
          ) : (
            leaderboard.slice(0, 50).map((pilot, i) => (
              <div key={pilot.characterId} style={{
                display: 'grid', gridTemplateColumns: '30px 1.5fr 70px 70px 70px 70px 70px',
                gap: '0.5rem', padding: '0.35rem 0', fontSize: '0.8rem',
                borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
              }}>
                <span style={{
                  fontFamily: 'monospace', fontSize: '0.7rem',
                  color: i < 3 ? '#ffcc00' : 'rgba(255,255,255,0.3)',
                  fontWeight: i < 3 ? 700 : 400,
                }}>#{i + 1}</span>
                <span style={{ fontWeight: i < 3 ? 600 : 400 }}>{pilot.name}</span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#3fb950' }}>{pilot.totalOps}</span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{pilot.totalSnapshots}</span>
                <span style={{
                  textAlign: 'right', fontFamily: 'monospace', fontWeight: 700,
                  color: pilot.avgParticipation >= 80 ? '#3fb950' : pilot.avgParticipation >= 50 ? '#d29922' : '#f85149',
                }}>
                  {pilot.avgParticipation.toFixed(0)}%
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>
                  {formatDuration(pilot.totalDurationMinutes)}
                </span>
                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.4)' }}>{pilot.shipCount}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
