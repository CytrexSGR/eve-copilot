// Corporation Wormhole View - J-Space Activity Intelligence
import { useState, useEffect } from 'react';
import { corpApi } from '../../services/corporationApi';
import { formatISKCompact } from '../../utils/format';

interface CorporationWormholeIntel {
  corporation_id: number;
  period_days: number;
  summary: {
    kills: number;
    deaths: number;
    isk_destroyed: number;
    isk_lost: number;
    efficiency: number;
    systems_active: number;
    kd_ratio: number;
  };
  hunting_grounds: Array<{
    system_id: number;
    system_name: string;
    wh_class: number | null;
    kills: number;
    isk_destroyed: number;
  }>;
  danger_zones: Array<{
    system_id: number;
    system_name: string;
    wh_class: number | null;
    deaths: number;
    isk_lost: number;
  }>;
  class_distribution: Array<{
    wh_class: number | null;
    kills: number;
  }>;
  top_enemies: Array<{
    corporation_id: number;
    corporation_name: string;
    kills: number;
  }>;
  top_victims: Array<{
    corporation_id: number;
    corporation_name: string;
    kills: number;
  }>;
  recent_kills: Array<{
    killmail_id: number;
    system_name: string;
    wh_class: number | null;
    ship_name: string;
    value: number;
    time: string | null;
    type: string;
  }>;
  recent_losses: Array<{
    killmail_id: number;
    system_name: string;
    wh_class: number | null;
    ship_name: string;
    value: number;
    time: string | null;
    type: string;
  }>;
  ships_used: Array<{
    ship_type_id: number;
    ship_name: string;
    ship_class: string;
    uses: number;
  }>;
}

interface Props {
  corpId: number;
  days: number;
}

const WH_CLASS_COLORS: Record<number, string> = {
  1: '#58a6ff',
  2: '#3fb950',
  3: '#ffcc00',
  4: '#ff6600',
  5: '#f85149',
  6: '#a855f7',
  13: '#ec4899',  // Shattered
  14: '#00ffff',  // Thera
  15: '#ff00ff',  // Drifter
  16: '#ff00ff',
  17: '#ff00ff',
  18: '#ff00ff',
};

const getClassColor = (whClass: number | null): string => {
  return whClass ? (WH_CLASS_COLORS[whClass] || '#58a6ff') : '#666';
};

const getClassLabel = (whClass: number | null): string => {
  if (!whClass) return '?';
  if (whClass === 13) return 'Shattered';
  if (whClass === 14) return 'Thera';
  if (whClass >= 15 && whClass <= 18) return 'Drifter';
  return `C${whClass}`;
};

const formatTimeAgo = (isoDate: string | null): string => {
  if (!isoDate) return 'Unknown';
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  return 'Just now';
};

export function CorporationWormholeView({ corpId, days }: Props) {
  const [intel, setIntel] = useState<CorporationWormholeIntel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    corpApi.getWormholeIntel(corpId, days)
      .then(setIntel)
      .catch((err) => console.error('Wormhole intel error:', err))
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div className="skeleton" style={{ height: '80px', borderRadius: '6px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
          <div className="skeleton" style={{ height: '300px', borderRadius: '6px' }} />
          <div className="skeleton" style={{ height: '300px', borderRadius: '6px' }} />
        </div>
      </div>
    );
  }

  if (!intel || intel.summary.kills === 0) {
    return (
      <div style={{
        padding: '2rem',
        textAlign: 'center',
        color: 'rgba(255,255,255,0.5)',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🌀</div>
        <div style={{ fontSize: '0.8rem', marginBottom: '0.25rem' }}>No Wormhole Activity</div>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)' }}>
          This corporation has no detected activity in J-Space
        </div>
      </div>
    );
  }

  const { summary, hunting_grounds, danger_zones, class_distribution, top_enemies, top_victims, recent_kills, recent_losses, ships_used } = intel;
  const maxClassCount = Math.max(...class_distribution.map(c => c.kills), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* HERO STATS - Wormhole Activity Summary */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '0.5rem',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: '0.75rem',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#a855f7', fontFamily: 'monospace' }}>
            {summary.systems_active}
          </div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Systems</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {summary.kills}
          </div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Kills</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f85149', fontFamily: 'monospace' }}>
            {summary.deaths}
          </div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Deaths</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
            {formatISKCompact(summary.isk_destroyed)}
          </div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>ISK Destroyed</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: summary.efficiency >= 50 ? '#3fb950' : '#f85149', fontFamily: 'monospace' }}>
            {(isFinite(summary.efficiency) ? summary.efficiency : 0).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Efficiency</div>
        </div>
      </div>

      {/* ROW 1: Hunting Grounds + Danger Zones + WH Class Distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        {/* HUNTING GROUNDS */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: '2px solid #3fb950',
          padding: '0.5rem',
          maxHeight: '320px',
          overflowY: 'auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#3fb950', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            • Hunting Grounds ({hunting_grounds.length})
          </div>
          {hunting_grounds.map((sys) => (
            <div key={sys.system_id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.3rem 0.4rem',
              marginBottom: '0.2rem',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: '3px',
              borderLeft: `2px solid ${getClassColor(sys.wh_class)}`,
            }}>
              <span style={{
                fontSize: '0.6rem',
                fontWeight: 600,
                color: getClassColor(sys.wh_class),
                minWidth: '25px',
              }}>
                {getClassLabel(sys.wh_class)}
              </span>
              <a
                href={`/system/${sys.system_id}`}
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  color: '#fff',
                  textDecoration: 'none',
                  flex: 1,
                }}
              >
                {sys.system_name}
              </a>
              <span style={{ fontSize: '0.55rem', color: '#3fb950', fontFamily: 'monospace' }}>
                {sys.kills} kills
              </span>
            </div>
          ))}
        </div>

        {/* DANGER ZONES */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: '2px solid #f85149',
          padding: '0.5rem',
          maxHeight: '320px',
          overflowY: 'auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#f85149', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            • Danger Zones ({danger_zones.length})
          </div>
          {danger_zones.map((sys) => (
            <div key={sys.system_id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.3rem 0.4rem',
              marginBottom: '0.2rem',
              background: 'rgba(248,81,73,0.08)',
              borderRadius: '3px',
              borderLeft: `2px solid ${getClassColor(sys.wh_class)}`,
            }}>
              <span style={{
                fontSize: '0.6rem',
                fontWeight: 600,
                color: getClassColor(sys.wh_class),
                minWidth: '25px',
              }}>
                {getClassLabel(sys.wh_class)}
              </span>
              <a
                href={`/system/${sys.system_id}`}
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  color: '#fff',
                  textDecoration: 'none',
                  flex: 1,
                }}
              >
                {sys.system_name}
              </a>
              <span style={{ fontSize: '0.55rem', color: '#f85149', fontFamily: 'monospace' }}>
                {sys.deaths} deaths
              </span>
            </div>
          ))}
        </div>

        {/* WH CLASS DISTRIBUTION */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: '2px solid #58a6ff',
          padding: '0.5rem',
          maxHeight: '320px',
          overflowY: 'auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#58a6ff', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            • WH Class Breakdown
          </div>
          {class_distribution.map((cls) => (
            <div key={cls.wh_class || 0} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              marginBottom: '0.4rem',
            }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                color: getClassColor(cls.wh_class),
                minWidth: '35px',
              }}>
                {getClassLabel(cls.wh_class)}
              </span>
              <div style={{
                flex: 1,
                height: '12px',
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '2px',
                overflow: 'hidden',
              }}>
                <div style={{
                  width: `${(cls.kills / maxClassCount) * 100}%`,
                  height: '100%',
                  background: getClassColor(cls.wh_class),
                  opacity: 0.7,
                }} />
              </div>
              <span style={{
                fontSize: '0.6rem',
                color: 'rgba(255,255,255,0.6)',
                fontFamily: 'monospace',
                minWidth: '20px',
                textAlign: 'right',
              }}>
                {cls.kills}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ROW 2: Top Enemies + Top Victims + Ships Used */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        {/* TOP ENEMIES */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: '2px solid #ff6600',
          padding: '0.5rem',
          maxHeight: '280px',
          overflowY: 'auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff6600', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            • Top Enemies ({top_enemies.length})
          </div>
          {top_enemies.map((enemy) => (
            <div key={enemy.corporation_id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.3rem 0.4rem',
              marginBottom: '0.2rem',
              background: 'rgba(255,102,0,0.11)',
              borderRadius: '3px',
            }}>
              <img
                src={`https://images.evetech.net/corporations/${enemy.corporation_id}/logo?size=32`}
                alt=""
                style={{ width: 18, height: 18, borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.65rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {enemy.corporation_name}
                </div>
              </div>
              <span style={{ fontSize: '0.55rem', color: '#ff6600', fontWeight: 600 }}>
                {enemy.kills} kills
              </span>
            </div>
          ))}
        </div>

        {/* TOP VICTIMS */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: '2px solid #3fb950',
          padding: '0.5rem',
          maxHeight: '280px',
          overflowY: 'auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#3fb950', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            • Top Victims ({top_victims.length})
          </div>
          {top_victims.map((victim) => (
            <div key={victim.corporation_id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.3rem 0.4rem',
              marginBottom: '0.2rem',
              background: 'rgba(63,185,80,0.08)',
              borderRadius: '3px',
            }}>
              <img
                src={`https://images.evetech.net/corporations/${victim.corporation_id}/logo?size=32`}
                alt=""
                style={{ width: 18, height: 18, borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.65rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {victim.corporation_name}
                </div>
              </div>
              <span style={{ fontSize: '0.55rem', color: '#3fb950', fontWeight: 600 }}>
                {victim.kills} kills
              </span>
            </div>
          ))}
        </div>

        {/* SHIPS USED */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: '2px solid #a855f7',
          padding: '0.5rem',
          maxHeight: '280px',
          overflowY: 'auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            • Ships Used ({ships_used.length})
          </div>
          {ships_used.map((ship) => (
            <div key={ship.ship_type_id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.3rem 0.4rem',
              marginBottom: '0.2rem',
              background: 'rgba(168,85,247,0.08)',
              borderRadius: '3px',
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.65rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {ship.ship_name}
                </div>
                <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
                  {ship.ship_class}
                </div>
              </div>
              <span style={{ fontSize: '0.55rem', color: '#a855f7', fontWeight: 600 }}>
                {ship.uses} uses
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ROW 3: Recent Activity */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.08)',
        borderLeft: '2px solid #ffcc00',
        padding: '0.5rem',
        maxHeight: '250px',
        overflowY: 'auto',
      }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ffcc00', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
          • Recent High-Value Activity
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.25rem' }}>
          {[...recent_kills, ...recent_losses].sort((a, b) =>
            new Date(b.time || 0).getTime() - new Date(a.time || 0).getTime()
          ).slice(0, 10).map((km, idx) => (
            <a
              key={`${km.killmail_id}-${idx}`}
              href={`https://zkillboard.com/kill/${km.killmail_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.3rem 0.4rem',
                background: km.type === 'kill' ? 'rgba(63,185,80,0.08)' : 'rgba(248,81,73,0.08)',
                borderRadius: '3px',
                borderLeft: `2px solid ${km.type === 'kill' ? '#3fb950' : '#f85149'}`,
                textDecoration: 'none',
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.65rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {km.ship_name}
                </div>
                <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
                  {km.system_name} {km.wh_class ? `(${getClassLabel(km.wh_class)})` : ''}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.6rem', fontWeight: 600, color: '#ffcc00', fontFamily: 'monospace' }}>
                  {formatISKCompact(km.value)}
                </div>
                <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
                  {formatTimeAgo(km.time)}
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
