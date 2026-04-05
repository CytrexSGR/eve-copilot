import type { DefenseStats, ResistProfile as ResistProfileType } from '../../types/fittings';
import { DAMAGE_COLORS } from '../../types/fittings';

interface ResistProfileProps {
  defense: DefenseStats;
}

function ResistBar({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(value, 100));

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <div style={{
        flex: 1,
        height: '18px',
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '4px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: color,
          transition: 'width 0.3s',
        }} />
      </div>
      <span style={{
        fontSize: '0.7rem',
        fontFamily: 'monospace',
        color: 'var(--text-primary)',
        minWidth: '45px',
        textAlign: 'right',
      }}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function ResistRow({
  label,
  resists,
  ehp,
  color,
}: {
  label: string;
  resists: ResistProfileType;
  ehp: number;
  color: string;
}) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '0.75rem',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '0.5rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: color,
          }} />
          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{label}</span>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {(ehp ?? 0).toLocaleString()} EHP
        </span>
      </div>

      <div style={{ display: 'grid', gap: '0.35rem' }}>
        {Object.entries(resists).map(([type, value]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              minWidth: '65px',
            }}>
              {type.toUpperCase()}
            </span>
            <ResistBar value={value} color={DAMAGE_COLORS[type] || '#888'} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResistProfile({ defense }: ResistProfileProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '0.75rem',
    }}>
      <h3 style={{
        fontSize: '0.9rem',
        fontWeight: 600,
        margin: '0 0 0.25rem 0',
        color: 'var(--text-primary)',
      }}>
        Resist Profile
      </h3>

      <ResistRow
        label="Shield"
        resists={defense.shield_resists}
        ehp={defense.shield_ehp}
        color="#00d4ff"
      />

      <ResistRow
        label="Armor"
        resists={defense.armor_resists}
        ehp={defense.armor_ehp}
        color="#ff8800"
      />

      <ResistRow
        label="Hull"
        resists={defense.hull_resists}
        ehp={defense.hull_ehp}
        color="#8b949e"
      />

      {/* Total EHP Summary */}
      <div style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '0.75rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Total EHP</span>
        <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#00d4ff' }}>
          {(defense.total_ehp ?? 0).toLocaleString()}
        </span>
      </div>
    </div>
  );
}
