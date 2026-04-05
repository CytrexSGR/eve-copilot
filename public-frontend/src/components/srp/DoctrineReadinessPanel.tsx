import { useState, useEffect, useCallback } from 'react';
import { doctrineStatsApi } from '../../services/api/srp';

interface MissingSkill {
  skill_id: number;
  skill_name: string;
  required_level: number;
  trained_level: number;
}

interface ReadinessData {
  doctrine_id: number;
  character_id: number;
  all_v_stats: Record<string, unknown>;
  character_stats: Record<string, unknown>;
  dps_ratio: number;
  ehp_ratio: number;
  missing_skills: MissingSkill[];
  can_fly: boolean;
}

const ROMAN = ['0', 'I', 'II', 'III', 'IV', 'V'];

function toRoman(level: number): string {
  return ROMAN[level] ?? String(level);
}

export function DoctrineReadinessPanel({ doctrineId, characterId }: { doctrineId: number; characterId: number }) {
  const [data, setData] = useState<ReadinessData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [skillsExpanded, setSkillsExpanded] = useState(false);
  const [exportMsg, setExportMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [exporting, setExporting] = useState<'text' | 'evemon' | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    setData(null);

    doctrineStatsApi.getReadiness(doctrineId, characterId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [doctrineId, characterId]);

  // Auto-dismiss export message after 3s
  useEffect(() => {
    if (!exportMsg) return;
    const timer = setTimeout(() => setExportMsg(null), 3000);
    return () => clearTimeout(timer);
  }, [exportMsg]);

  const handleExport = useCallback(async (format: 'text' | 'evemon') => {
    setExporting(format);
    setExportMsg(null);
    try {
      const result = await doctrineStatsApi.getSkillPlan(doctrineId, characterId, format);
      await navigator.clipboard.writeText(result.content);
      setExportMsg({
        type: 'success',
        text: format === 'text'
          ? `Copied ${result.skill_count} skills to clipboard`
          : `Copied EVEMon XML (${result.skill_count} skills) to clipboard`,
      });
    } catch (err) {
      console.error('Skill plan export failed:', err);
      setExportMsg({ type: 'error', text: 'Failed to export skill plan' });
    } finally {
      setExporting(null);
    }
  }, [doctrineId, characterId]);

  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.15)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1rem',
      }}>
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.85rem' }}>Loading...</span>
      </div>
    );
  }

  if (error || !data) return null;

  const dpsPercent = data.dps_ratio * 100;
  const ehpPercent = data.ehp_ratio * 100;
  const hasMissing = data.missing_skills.length > 0;

  const actionBtnStyle = (disabled: boolean): React.CSSProperties => ({
    background: 'rgba(0,212,255,0.1)',
    border: '1px solid rgba(0,212,255,0.3)',
    borderRadius: '4px',
    color: '#00d4ff',
    padding: '0.25rem 0.6rem',
    fontSize: '0.7rem',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    whiteSpace: 'nowrap',
  });

  return (
    <div style={{
      background: 'rgba(0,0,0,0.15)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.75rem',
    }}>
      {/* Hero badge */}
      <div style={{
        display: 'inline-flex',
        alignSelf: 'flex-start',
        padding: '0.35rem 0.85rem',
        borderRadius: '4px',
        background: data.can_fly ? 'rgba(63,185,80,0.25)' : 'rgba(248,81,73,0.25)',
        border: `1px solid ${data.can_fly ? 'rgba(63,185,80,0.5)' : 'rgba(248,81,73,0.5)'}`,
      }}>
        <span style={{
          fontWeight: 700,
          fontSize: '0.85rem',
          letterSpacing: '0.05em',
          color: data.can_fly ? '#3fb950' : '#f85149',
        }}>
          {data.can_fly ? 'CAN FLY' : 'CANNOT FLY'}
        </span>
      </div>

      {/* DPS ratio bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          color: 'rgba(255,255,255,0.6)',
          width: '32px',
          flexShrink: 0,
        }}>DPS</span>
        <div style={{
          flex: 1,
          background: 'rgba(255,255,255,0.05)',
          height: '6px',
          borderRadius: '3px',
          overflow: 'hidden',
        }}>
          <div style={{
            width: `${Math.min(dpsPercent, 100)}%`,
            height: '100%',
            background: '#d29922',
            borderRadius: '3px',
            transition: 'width 0.3s ease',
          }} />
        </div>
        <span style={{
          fontSize: '0.75rem',
          fontFamily: 'monospace',
          color: 'rgba(255,255,255,0.6)',
          width: '100px',
          textAlign: 'right',
          flexShrink: 0,
        }}>
          {dpsPercent.toFixed(1)}% of All V
        </span>
      </div>

      {/* EHP ratio bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          color: 'rgba(255,255,255,0.6)',
          width: '32px',
          flexShrink: 0,
        }}>EHP</span>
        <div style={{
          flex: 1,
          background: 'rgba(255,255,255,0.05)',
          height: '6px',
          borderRadius: '3px',
          overflow: 'hidden',
        }}>
          <div style={{
            width: `${Math.min(ehpPercent, 100)}%`,
            height: '100%',
            background: '#00d4ff',
            borderRadius: '3px',
            transition: 'width 0.3s ease',
          }} />
        </div>
        <span style={{
          fontSize: '0.75rem',
          fontFamily: 'monospace',
          color: 'rgba(255,255,255,0.6)',
          width: '100px',
          textAlign: 'right',
          flexShrink: 0,
        }}>
          {ehpPercent.toFixed(1)}% of All V
        </span>
      </div>

      {/* Missing skills (collapsible) */}
      {hasMissing && (
        <div style={{
          borderTop: '1px solid var(--border-color)',
          paddingTop: '0.5rem',
          marginTop: '0.25rem',
        }}>
          <button
            onClick={() => setSkillsExpanded(!skillsExpanded)}
            style={{
              background: 'none',
              border: 'none',
              color: 'rgba(255,255,255,0.7)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <span style={{
              display: 'inline-block',
              transition: 'transform 0.2s',
              transform: skillsExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              fontSize: '0.7rem',
            }}>
              &#9654;
            </span>
            Missing Skills ({data.missing_skills.length})
          </button>

          {skillsExpanded && (
            <div style={{
              marginTop: '0.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.2rem',
            }}>
              {data.missing_skills.map((skill) => (
                <div key={skill.skill_id} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: '3px',
                }}>
                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                    {skill.skill_name}
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', display: 'flex', gap: '0.5rem' }}>
                    <span style={{ color: 'rgba(255,255,255,0.4)' }}>
                      Required: {toRoman(skill.required_level)}
                    </span>
                    <span style={{
                      color: skill.trained_level < skill.required_level ? '#f85149' : 'rgba(255,255,255,0.4)',
                    }}>
                      Trained: {toRoman(skill.trained_level)}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Skill plan export buttons */}
          <div style={{
            display: 'flex', gap: '0.5rem', marginTop: '0.5rem', alignItems: 'center', flexWrap: 'wrap',
          }}>
            <button
              onClick={() => handleExport('text')}
              disabled={exporting !== null}
              style={actionBtnStyle(exporting !== null)}
            >
              {exporting === 'text' ? 'Copying...' : 'Copy Skill Plan'}
            </button>
            <button
              onClick={() => handleExport('evemon')}
              disabled={exporting !== null}
              style={actionBtnStyle(exporting !== null)}
            >
              {exporting === 'evemon' ? 'Copying...' : 'Export EVEMon XML'}
            </button>
          </div>

          {/* Export feedback message */}
          {exportMsg && (
            <div style={{
              marginTop: '0.4rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              color: exportMsg.type === 'success' ? '#3fb950' : '#f85149',
              padding: '0.25rem 0.5rem',
              borderRadius: '3px',
              background: exportMsg.type === 'success' ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
              display: 'inline-block',
            }}>
              {exportMsg.text}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
