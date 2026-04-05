// public-frontend/src/components/BattleTimeline.tsx
import { useState, useEffect, useMemo } from 'react';
import { battleApi } from '../services/api';
import type { BattleTimelineResponse, TimelineBucket, TacticalShift } from '../types/reports';
import { formatISKCompact } from '../utils/format';

interface BattleTimelineProps {
  battleId: number;
  onError?: (error: string) => void;
}

export function BattleTimeline({ battleId, onError }: BattleTimelineProps) {
  const [timeline, setTimeline] = useState<BattleTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBucket, setSelectedBucket] = useState<TimelineBucket | null>(null);

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        setLoading(true);
        const data = await battleApi.getBattleTimeline(battleId);
        setTimeline(data);
      } catch (err) {
        console.error('Failed to fetch timeline:', err);
        onError?.('Failed to load battle timeline');
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [battleId, onError]);

  // Calculate max values for scaling
  const maxKills = useMemo(() => {
    if (!timeline?.buckets.length) return 1;
    return Math.max(...timeline.buckets.map(b => b.kills));
  }, [timeline]);

  const formatISK = formatISKCompact;

  const getShiftIcon = (type: TacticalShift['type']) => {
    switch (type) {
      case 'capital_entry': return '⚓';
      case 'kill_spike': return '💥';
      case 'kill_drop': return '📉';
      case 'high_value_kill': return '💎';
      case 'logi_collapse': return '🏥';
      default: return '⚡';
    }
  };

  const getSeverityColor = (severity: TacticalShift['severity']) => {
    switch (severity) {
      case 'high': return '#ff4444';
      case 'medium': return '#ff8800';
      case 'low': return '#58a6ff';
    }
  };

  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <div className="skeleton" style={{ height: '200px' }} />
      </div>
    );
  }

  if (!timeline || timeline.buckets.length === 0) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem',
        textAlign: 'center',
        color: 'rgba(255,255,255,0.5)'
      }}>
        <p>No timeline data available</p>
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      overflow: 'hidden',
      marginBottom: '1rem'
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#a855f7',
          }} />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase' }}>
            Battle Forensics
          </span>
          <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem' }}>
            {timeline.total_minutes}m • {timeline.total_kills} kills
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)' }}>
          <span><span style={{ color: '#58a6ff' }}>●</span> Kills</span>
          <span><span style={{ color: '#ff8800' }}>●</span> Capital</span>
        </div>
      </div>

      {/* Timeline Chart */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        height: '100px',
        gap: '2px',
        padding: '0.4rem 0.5rem',
        marginBottom: '0.3rem',
        position: 'relative'
      }}>
        {timeline.buckets.map((bucket) => {
          const killHeight = (bucket.kills / maxKills) * 100;
          const isSelected = selectedBucket?.bucket_index === bucket.bucket_index;
          const hasShift = timeline.tactical_shifts.some(s => s.minute === bucket.minute);

          return (
            <div
              key={bucket.bucket_index}
              onClick={() => setSelectedBucket(isSelected ? null : bucket)}
              style={{
                flex: 1,
                minWidth: '6px',
                maxWidth: '30px',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                alignItems: 'center',
                cursor: 'pointer',
                position: 'relative',
                transition: 'transform 0.1s',
                transform: isSelected ? 'scale(1.1)' : 'scale(1)',
              }}
            >
              {/* Tactical shift marker */}
              {hasShift && (
                <div style={{
                  position: 'absolute',
                  top: '0',
                  width: '100%',
                  height: '3px',
                  background: '#ff8800',
                  borderRadius: '2px'
                }} />
              )}

              {/* Kill bar */}
              <div style={{
                width: '100%',
                height: `${killHeight}%`,
                background: bucket.has_capital
                  ? 'linear-gradient(to top, #58a6ff, #ff8800)'
                  : '#58a6ff',
                borderRadius: '2px 2px 0 0',
                minHeight: bucket.kills > 0 ? '3px' : '0',
                border: isSelected ? '1px solid white' : 'none',
                position: 'relative',
                opacity: isSelected ? 1 : 0.8
              }}>
                {/* Capital indicator */}
                {bucket.capital_kills > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '-10px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    fontSize: '0.55rem',
                    color: '#ff8800'
                  }}>
                    ⚓{bucket.capital_kills}
                  </div>
                )}
              </div>

              {/* Minute label (every 5 minutes) */}
              {bucket.minute % 5 === 0 && (
                <span style={{
                  fontSize: '0.55rem',
                  color: 'rgba(255,255,255,0.3)',
                  marginTop: '2px',
                  position: 'absolute',
                  bottom: '-12px'
                }}>
                  {bucket.minute}m
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Selected Bucket Details */}
      {selectedBucket && (
        <div style={{
          padding: '0.75rem',
          background: 'rgba(88,166,255,0.1)',
          borderRadius: '6px',
          marginBottom: '0.75rem',
          borderLeft: '3px solid #58a6ff'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '0.5rem'
          }}>
            <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>Minute {selectedBucket.minute}</span>
            <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.8rem' }}>
              {selectedBucket.kills} kills • {formatISK(selectedBucket.isk_destroyed)} ISK
            </span>
          </div>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            {selectedBucket.ship_categories.map(cat => (
              <span key={cat} style={{
                padding: '0.15rem 0.4rem',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: '3px',
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.7)'
              }}>
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tactical Shifts - Compact */}
      {timeline.tactical_shifts.length > 0 && (
        <div>
          <div style={{
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.5)',
            marginBottom: '0.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem'
          }}>
            <span style={{ color: '#ff8800' }}>⚡</span>
            Tactical Shifts ({timeline.tactical_shifts.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', padding: '0 0.4rem 0.4rem' }}>
            {timeline.tactical_shifts.slice(0, 5).map((shift, idx) => (
              <div
                key={idx}
                onClick={() => {
                  const bucket = timeline.buckets.find(b => b.minute === shift.minute);
                  if (bucket) setSelectedBucket(bucket);
                }}
                style={{
                  padding: '0.25rem 0.4rem',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: '4px',
                  borderLeft: `2px solid ${getSeverityColor(shift.severity)}`,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  transition: 'background 0.2s'
                }}
              >
                <span style={{ fontSize: '0.7rem' }}>{getShiftIcon(shift.type)}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{
                    fontWeight: 600,
                    fontSize: '0.65rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: 'block',
                  }}>
                    {shift.description}
                  </span>
                </div>
                <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
                  +{shift.minute}m
                </span>
                <span style={{
                  padding: '1px 4px',
                  borderRadius: '2px',
                  fontSize: '0.5rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  background: `${getSeverityColor(shift.severity)}20`,
                  color: getSeverityColor(shift.severity)
                }}>
                  {shift.severity}
                </span>
              </div>
            ))}
            {timeline.tactical_shifts.length > 5 && (
              <div style={{
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.4)',
                textAlign: 'center',
                padding: '0.25rem'
              }}>
                +{timeline.tactical_shifts.length - 5} more shifts
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
