import type { CommanderIntelResponse } from '../../services/api';

interface BattleDoctrinesProps {
  doctrines: CommanderIntelResponse['doctrines'];
}

// Ship classification for counter doctrine analysis
const SHIP_CLASSES: Record<string, string[]> = {
  hac: ['Muninn', 'Eagle', 'Cerberus', 'Sacrilege', 'Vagabond', 'Ishtar', 'Deimos', 'Zealot'],
  battleship: ['Maelstrom', 'Tempest', 'Typhoon', 'Raven', 'Rokh', 'Scorpion', 'Megathron', 'Hyperion', 'Dominix', 'Abaddon', 'Apocalypse', 'Armageddon', 'Nightmare', 'Machariel', 'Rattlesnake', 'Barghest', 'Praxis'],
  battlecruiser: ['Hurricane', 'Brutix', 'Ferox', 'Harbinger', 'Drake', 'Myrmidon', 'Prophecy', 'Cyclone', 'Gnosis'],
  t3c: ['Loki', 'Tengu', 'Proteus', 'Legion'],
  bomber: ['Hound', 'Nemesis', 'Purifier', 'Manticore'],
  frigate: ['Atron', 'Merlin', 'Rifter', 'Punisher', 'Tristan', 'Kestrel', 'Breacher', 'Tormentor', 'Incursus', 'Slasher', 'Condor', 'Executioner'],
  destroyer: ['Catalyst', 'Thrasher', 'Coercer', 'Cormorant', 'Algos', 'Talwar', 'Dragoon', 'Corax'],
  interdictor: ['Sabre', 'Heretic', 'Flycatcher', 'Eris'],
  logistics: ['Scimitar', 'Basilisk', 'Guardian', 'Oneiros', 'Logi'],
  ewar: ['Blackbird', 'Celestis', 'Bellicose', 'Arbitrator', 'Kitsune', 'Sentinel', 'Keres', 'Hyena'],
  capital: ['Naglfar', 'Phoenix', 'Moros', 'Revelation', 'Carrier', 'Thanatos', 'Archon', 'Chimera', 'Nidhoggur', 'Apostle', 'Lif', 'Ninazu', 'Minokawa'],
  super: ['Titan', 'Supercarrier', 'Avatar', 'Erebus', 'Ragnarok', 'Leviathan', 'Aeon', 'Hel', 'Nyx', 'Wyvern', 'Vendetta', 'Revenant', 'Molok', 'Vanquisher', 'Komodo'],
  commandDestroyer: ['Bifrost', 'Pontifex', 'Magus', 'Stork'],
};

// Counter doctrine mappings
const COUNTER_DOCTRINES: Record<string, { name: string; ships: string[]; reason: string }[]> = {
  hac: [
    { name: 'Bomber Wing', ships: ['Hound', 'Purifier', 'Nemesis', 'Manticore'], reason: 'Void bombs + torpedo alpha' },
    { name: 'Command Destroyers', ships: ['Bifrost', 'Stork', 'Pontifex', 'Magus'], reason: 'Boosh to separate' },
    { name: 'Battleship Fleet', ships: ['Maelstrom', 'Rokh', 'Nightmare'], reason: 'Alpha strike through ADC' },
  ],
  battleship: [
    { name: 'Bomber Wing', ships: ['Hound', 'Purifier', 'Nemesis', 'Manticore'], reason: 'Torpedo alpha volley' },
    { name: 'Dreadnought Drop', ships: ['Naglfar', 'Phoenix', 'Revelation'], reason: 'Capital DPS' },
    { name: 'HAC Fleet', ships: ['Muninn', 'Eagle', 'Cerberus'], reason: 'Speed + range control' },
  ],
  battlecruiser: [
    { name: 'HAC Fleet', ships: ['Muninn', 'Eagle', 'Ishtar'], reason: 'Superior mobility' },
    { name: 'Bomber Wing', ships: ['Hound', 'Purifier', 'Nemesis'], reason: 'Torpedo alpha' },
    { name: 'Battleship Fleet', ships: ['Nightmare', 'Machariel'], reason: 'Higher DPS/tank' },
  ],
  t3c: [
    { name: 'Bomber Wing', ships: ['Hound', 'Purifier', 'Nemesis', 'Manticore'], reason: 'Void bombs + alpha' },
    { name: 'Command Destroyers', ships: ['Bifrost', 'Stork'], reason: 'Boosh disruption' },
    { name: 'HAC Fleet', ships: ['Muninn', 'Eagle'], reason: 'Similar engagement profile' },
  ],
  bomber: [
    { name: 'Fast Tackle', ships: ['Interceptor', 'Stiletto', 'Ares', 'Malediction'], reason: 'Catch and decloak' },
    { name: 'Destroyer Wing', ships: ['Thrasher', 'Catalyst', 'Cormorant'], reason: 'Smartbombs + insta-lock' },
    { name: 'Anti-Bomber BS', ships: ['Typhoon', 'Armageddon'], reason: 'Smartbombs' },
  ],
  frigate: [
    { name: 'Destroyer Wing', ships: ['Thrasher', 'Catalyst', 'Coercer'], reason: 'Superior alpha' },
    { name: 'Smartbomb BS', ships: ['Rokh', 'Maelstrom'], reason: 'AoE clear' },
    { name: 'Command Destroyers', ships: ['Bifrost', 'Stork'], reason: 'Boosh + clear' },
  ],
  destroyer: [
    { name: 'Cruiser Fleet', ships: ['Caracal', 'Omen', 'Thorax'], reason: 'Tank + DPS advantage' },
    { name: 'Battlecruiser', ships: ['Ferox', 'Hurricane'], reason: 'Alpha strike' },
  ],
  logistics: [
    { name: 'Alpha Fleet', ships: ['Tornado', 'Oracle', 'Naga'], reason: 'One-shot before reps' },
    { name: 'ECM Wing', ships: ['Blackbird', 'Kitsune', 'Falcon'], reason: 'Break logi locks' },
    { name: 'Neut Pressure', ships: ['Armageddon', 'Bhaalgorn', 'Curse'], reason: 'Cap warfare' },
  ],
  capital: [
    { name: 'Super Capital', ships: ['Titan', 'Supercarrier'], reason: 'Escalation dominance' },
    { name: 'Bomber Swarm', ships: ['Hound', 'Purifier', 'Nemesis'], reason: 'Void bomb + torpedo' },
    { name: 'Dread Bomb', ships: ['Naglfar', 'Phoenix', 'Revelation', 'Moros'], reason: 'Counter-drop' },
  ],
  super: [
    { name: 'Super Fleet', ships: ['Titan', 'Supercarrier'], reason: 'Escalation match' },
    { name: 'Dread Bomb', ships: ['Naglfar', 'Phoenix', 'Revelation'], reason: 'Sacrificial DPS' },
  ],
};

function detectDoctrineTypes(doctrines: CommanderIntelResponse['doctrines']): Map<string, number> {
  const detected = new Map<string, number>();

  for (const doctrine of Object.values(doctrines)) {
    for (const ship of doctrine.fielding) {
      const shipName = ship.ship_name;
      for (const [docType, ships] of Object.entries(SHIP_CLASSES)) {
        if (ships.some(s => shipName.includes(s))) {
          detected.set(docType, (detected.get(docType) || 0) + ship.engagements);
        }
      }
    }
  }

  return detected;
}

function getCounterSuggestions(detectedTypes: Map<string, number>): { name: string; ships: string[]; reason: string; priority: number }[] {
  const suggestions: { name: string; ships: string[]; reason: string; priority: number }[] = [];
  const seen = new Set<string>();

  // Sort by engagement count
  const sorted = [...detectedTypes.entries()].sort((a, b) => b[1] - a[1]);

  for (const [docType, count] of sorted) {
    const counters = COUNTER_DOCTRINES[docType];
    if (counters) {
      for (const counter of counters) {
        if (!seen.has(counter.name)) {
          seen.add(counter.name);
          suggestions.push({ ...counter, priority: count });
        }
      }
    }
  }

  return suggestions.sort((a, b) => b.priority - a.priority).slice(0, 4);
}

export function BattleDoctrines({ doctrines }: BattleDoctrinesProps) {
  const allianceCount = Object.keys(doctrines).length;
  const totalShipTypes = Object.values(doctrines).reduce((sum, d) => sum + d.fielding.length, 0);
  const totalLosses = Object.values(doctrines).reduce((sum, d) => sum + d.losses.reduce((s, l) => s + l.count, 0), 0);

  // Detect doctrine types and get counter suggestions
  const detectedTypes = detectDoctrineTypes(doctrines);
  const counterSuggestions = getCounterSuggestions(detectedTypes);
  const primaryDoctrine = [...detectedTypes.entries()].sort((a, b) => b[1] - a[1])[0];

  if (allianceCount === 0) return null;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
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
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: '#a855f7',
            textTransform: 'uppercase'
          }}>
            Fleet Doctrines
          </span>
          {primaryDoctrine && (
            <span style={{
              padding: '2px 6px',
              borderRadius: '3px',
              background: 'rgba(0, 212, 255, 0.2)',
              color: '#00d4ff',
              fontSize: '0.55rem',
              fontWeight: 700,
              textTransform: 'uppercase',
            }}>
              {primaryDoctrine[0]} Meta
            </span>
          )}
        </div>

        {/* Summary Stats */}
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.65rem' }}>
          <span>
            <span style={{ color: '#a855f7', fontWeight: 700, fontFamily: 'monospace' }}>
              {allianceCount}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>alliances</span>
          </span>
          <span>
            <span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>
              {totalShipTypes}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>ship types</span>
          </span>
          {totalLosses > 0 && (
            <span>
              <span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>
                {totalLosses}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>losses</span>
            </span>
          )}
        </div>
      </div>

      {/* Two Column Layout: Doctrines + Counters */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: counterSuggestions.length > 0 ? '1fr 280px' : '1fr',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {/* Left: Alliance Doctrines Grid - Limited to top 6 by engagements */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '0.3rem',
        }}>
          {Object.entries(doctrines)
            .map(([alliance, doctrine]) => ({
              alliance,
              doctrine,
              totalEngagements: doctrine.fielding.reduce((sum, s) => sum + s.engagements, 0)
            }))
            .sort((a, b) => b.totalEngagements - a.totalEngagements)
            .slice(0, 6)
            .map(({ alliance, doctrine }) => (
              <AllianceDoctrineCard key={alliance} alliance={alliance} doctrine={doctrine} />
            ))}
        </div>

        {/* Right: Counter Doctrines */}
        {counterSuggestions.length > 0 && (
          <CounterDoctrinesPanel suggestions={counterSuggestions} detectedTypes={detectedTypes} />
        )}
      </div>
    </div>
  );
}

interface Doctrine {
  fielding: { ship_name: string; engagements: number }[];
  losses: { ship_name: string; count: number }[];
}

function AllianceDoctrineCard({ alliance, doctrine }: { alliance: string; doctrine: Doctrine }) {
  const totalFielding = doctrine.fielding.reduce((sum, s) => sum + s.engagements, 0);
  const totalLosses = doctrine.losses.reduce((sum, s) => sum + s.count, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      {/* Alliance Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(168, 85, 247, 0.1)',
        borderLeft: '3px solid #a855f7',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff' }}>
          {alliance}
        </span>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem' }}>
          <span style={{ color: '#00d4ff' }}>{totalFielding} engagements</span>
          {totalLosses > 0 && <span style={{ color: '#ff4444' }}>{totalLosses} lost</span>}
        </div>
      </div>

      {/* Ships */}
      <div style={{ padding: '0.4rem' }}>
        {/* Fielding Ships */}
        {doctrine.fielding.length > 0 && (
          <div style={{ marginBottom: doctrine.losses.length > 0 ? '0.4rem' : 0 }}>
            <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              Fielding
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
              {doctrine.fielding.slice(0, 8).map((ship, idx) => {
                // Color intensity based on engagement count
                const isHighEngagement = ship.engagements >= 10;
                const isMedEngagement = ship.engagements >= 5;
                const bgOpacity = isHighEngagement ? 0.3 : isMedEngagement ? 0.2 : 0.15;

                return (
                  <span key={idx} style={{
                    padding: '2px 6px',
                    background: `rgba(168, 85, 247, ${bgOpacity})`,
                    borderRadius: '3px',
                    fontSize: '0.6rem',
                    color: '#a855f7',
                    fontWeight: isHighEngagement ? 700 : 500,
                  }}>
                    {ship.ship_name}
                    <span style={{
                      marginLeft: '0.2rem',
                      color: isHighEngagement ? '#fff' : 'rgba(168, 85, 247, 0.6)',
                      fontWeight: 700,
                    }}>
                      {ship.engagements}
                    </span>
                  </span>
                );
              })}
              {doctrine.fielding.length > 8 && (
                <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', padding: '2px 4px' }}>
                  +{doctrine.fielding.length - 8}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Lost Ships */}
        {doctrine.losses.length > 0 && (
          <div>
            <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              Losses
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
              {doctrine.losses.slice(0, 6).map((ship, idx) => (
                <span key={idx} style={{
                  padding: '2px 6px',
                  background: 'rgba(255, 68, 68, 0.15)',
                  borderRadius: '3px',
                  fontSize: '0.6rem',
                  color: '#ff4444',
                }}>
                  -{ship.count}x {ship.ship_name}
                </span>
              ))}
              {doctrine.losses.length > 6 && (
                <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', padding: '2px 4px' }}>
                  +{doctrine.losses.length - 6}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// COUNTER DOCTRINES PANEL
// ============================================

interface CounterSuggestion {
  name: string;
  ships: string[];
  reason: string;
  priority: number;
}

function CounterDoctrinesPanel({ suggestions, detectedTypes }: { suggestions: CounterSuggestion[]; detectedTypes: Map<string, number> }) {
  // Get primary detected types for display
  const primaryTypes = [...detectedTypes.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([type]) => type);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      overflow: 'hidden',
      borderLeft: '3px solid #22d3ee',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(34, 211, 238, 0.1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#22d3ee' }} />
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#22d3ee', textTransform: 'uppercase' }}>
            Counter Intel
          </span>
        </div>
        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
          {suggestions.length} options
        </span>
      </div>

      {/* Detected Composition */}
      <div style={{ padding: '0.4rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
          Detected Composition
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
          {primaryTypes.map((type) => (
            <span key={type} style={{
              padding: '2px 6px',
              background: 'rgba(255, 136, 0, 0.2)',
              borderRadius: '3px',
              fontSize: '0.6rem',
              color: '#ff8800',
              fontWeight: 600,
              textTransform: 'uppercase',
            }}>
              {type}
            </span>
          ))}
        </div>
      </div>

      {/* Counter Suggestions */}
      <div style={{ padding: '0.4rem' }}>
        <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
          Recommended Counters
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {suggestions.map((counter, idx) => (
            <div
              key={counter.name}
              style={{
                padding: '0.4rem 0.5rem',
                background: idx === 0 ? 'rgba(34, 211, 238, 0.15)' : 'rgba(0,0,0,0.2)',
                borderRadius: '4px',
                borderLeft: `3px solid ${idx === 0 ? '#22d3ee' : 'rgba(34, 211, 238, 0.4)'}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  color: idx === 0 ? '#22d3ee' : '#fff',
                }}>
                  {counter.name}
                </span>
                {idx === 0 && (
                  <span style={{
                    padding: '1px 4px',
                    borderRadius: '2px',
                    background: 'rgba(0, 255, 136, 0.2)',
                    color: '#00ff88',
                    fontSize: '0.5rem',
                    fontWeight: 700,
                  }}>
                    BEST
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.25rem' }}>
                {counter.reason}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.15rem' }}>
                {counter.ships.slice(0, 4).map((ship, shipIdx) => (
                  <span key={shipIdx} style={{
                    padding: '1px 4px',
                    background: 'rgba(255,255,255,0.08)',
                    borderRadius: '2px',
                    fontSize: '0.55rem',
                    color: 'rgba(255,255,255,0.6)',
                  }}>
                    {ship}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
