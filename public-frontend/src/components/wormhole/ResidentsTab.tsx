import { useState } from 'react';
import { THREAT_SEVERITY_COLORS, WORMHOLE_CLASS_COLORS } from '../../constants/wormhole';
import type { WormholeThreat, WormholeEviction } from '../../types/wormhole';

interface ResidentsTabProps {
  threats: WormholeThreat[];
  evictions: WormholeEviction[];
  selectedClass: number | null;
  onClassChange: (cls: number | null) => void;
  onSystemSearch: (query: string) => void;
}

function formatTimeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  return value.toLocaleString();
}

export function ResidentsTab({
  threats,
  evictions,
  selectedClass,
  onClassChange,
  onSystemSearch,
}: ResidentsTabProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = () => {
    if (searchQuery.trim()) {
      onSystemSearch(searchQuery.trim());
    }
  };

  return (
    <div style={{ marginTop: '1rem' }}>
      {/* Search Bar */}
      <div
        style={{
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          padding: '1rem',
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '8px',
          marginBottom: '1rem',
        }}
      >
        <span style={{ fontSize: '1rem' }}>🔍</span>
        <input
          type="text"
          placeholder="Enter your J-signature (e.g., J123456)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          style={{
            flex: 1,
            padding: '0.5rem 0.75rem',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '4px',
            color: '#fff',
            fontSize: '0.9rem',
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: '0.5rem 1rem',
            background: '#00d4ff22',
            border: '1px solid #00d4ff44',
            borderRadius: '4px',
            color: '#00d4ff',
            cursor: 'pointer',
          }}
        >
          Search
        </button>
        <select
          value={selectedClass ?? ''}
          onChange={(e) => onClassChange(e.target.value ? parseInt(e.target.value) : null)}
          style={{
            padding: '0.5rem 0.75rem',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '4px',
            color: '#fff',
          }}
        >
          <option value="">All Classes</option>
          {[1, 2, 3, 4, 5, 6].map((c) => (
            <option key={c} value={c}>C{c}</option>
          ))}
        </select>
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        {/* Threat Feed */}
        <div
          style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '8px',
            padding: '1rem',
          }}
        >
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ff4444', margin: '0 0 1rem 0' }}>
            ⚠️ THREAT FEED
            {selectedClass && (
              <span style={{ marginLeft: '0.5rem', color: 'rgba(255,255,255,0.5)' }}>
                (C{selectedClass})
              </span>
            )}
          </h3>

          {!threats || threats.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', padding: '2rem' }}>
              No active threats detected
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {(threats || []).map((threat, i) => (
                <div
                  key={i}
                  style={{
                    padding: '0.75rem',
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '6px',
                    borderLeft: `3px solid ${THREAT_SEVERITY_COLORS[threat.severity]}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        padding: '0.15rem 0.4rem',
                        background: `${THREAT_SEVERITY_COLORS[threat.severity]}22`,
                        color: THREAT_SEVERITY_COLORS[threat.severity],
                        borderRadius: '3px',
                        fontWeight: 600,
                      }}
                    >
                      {threat.type}
                    </span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        color: WORMHOLE_CLASS_COLORS[threat.wormhole_class] || '#888',
                      }}
                    >
                      C{threat.wormhole_class}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#fff', marginTop: '0.35rem' }}>
                    {threat.description}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem' }}>
                    {formatTimeAgo(threat.timestamp)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Evictions */}
        <div
          style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '8px',
            padding: '1rem',
          }}
        >
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ff8800', margin: '0 0 1rem 0' }}>
            💀 EVICTIONS (7 Days)
          </h3>

          {!evictions || evictions.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', padding: '2rem' }}>
              No recent evictions
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {(evictions || []).map((eviction, i) => (
                <div
                  key={i}
                  style={{
                    padding: '0.75rem',
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '6px',
                    borderLeft: `3px solid #ff8800`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fff' }}>
                      {eviction.system_name}
                    </span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        color: WORMHOLE_CLASS_COLORS[eviction.wormhole_class] || '#888',
                      }}
                    >
                      C{eviction.wormhole_class}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', marginTop: '0.35rem' }}>
                    {eviction.total_kills} kills • {formatISK(eviction.total_isk_destroyed)} ISK destroyed
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem' }}>
                    {formatTimeAgo(eviction.started_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
