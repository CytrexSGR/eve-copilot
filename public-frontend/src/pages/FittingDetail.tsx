import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, useSearchParams, Link } from 'react-router-dom';
import { ModuleGate } from '../components/ModuleGate';
import { useAuth } from '../hooks/useAuth';
import { fittingApi, resolveTypeNames } from '../services/api/fittings';
import { projectApi } from '../services/api/production';
import { generateEft } from '../lib/eft-parser';
import { StatsPanel } from '../components/fittings/StatsPanel';
import { EnrichedModuleList } from '../components/fittings/EnrichedModuleList';
import type { ESIFitting, CustomFitting, FittingStats, SkillRequirement } from '../types/fittings';
import { SLOT_RANGES, getShipRenderUrl } from '../types/fittings';

// ────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────

type Tab = 'modules' | 'export' | 'skills';

// ────────────────────────────────────────────────────
// Export Tab
// ────────────────────────────────────────────────────

function ExportTab({ fitting, stats, typeNames }: {
  fitting: ESIFitting | CustomFitting; stats: FittingStats; typeNames: Map<number, string>;
}) {
  const [copied, setCopied] = useState(false);

  const buildEft = () => {
    const modulesBySlot: Record<string, { name: string; quantity: number }[]> = { high: [], mid: [], low: [], rig: [] };
    for (const [slotType, range] of Object.entries(SLOT_RANGES)) {
      const slotItems = fitting.items.filter(i => i.flag >= range.start && i.flag <= range.end);
      modulesBySlot[slotType] = slotItems.map(item => ({
        name: typeNames.get(item.type_id) || `Type #${item.type_id}`,
        quantity: 1,
      }));
    }

    // Drones (flag 87)
    const droneItemsList = fitting.items.filter(i => i.flag === 87);
    const droneMap = new Map<number, number>();
    for (const d of droneItemsList) {
      droneMap.set(d.type_id, (droneMap.get(d.type_id) || 0) + d.quantity);
    }
    const drones = Array.from(droneMap.entries()).map(([typeId, qty]) => ({
      name: typeNames.get(typeId) || `Type #${typeId}`,
      quantity: qty,
    }));

    return generateEft(
      stats.ship.type_name || stats.ship.name || '',
      fitting.name,
      modulesBySlot,
      drones.length > 0 ? drones : undefined,
    );
  };

  const eftText = buildEft();

  const handleCopy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(eftText);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = eftText;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* silent */ }
  };

  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
      borderRadius: '8px', padding: '1rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>EFT Format</span>
        <button onClick={handleCopy} style={{
          padding: '6px 14px', fontSize: '0.75rem', fontWeight: 600,
          background: copied ? '#3fb95022' : '#00d4ff', color: copied ? '#3fb950' : '#000',
          border: copied ? '1px solid #3fb95055' : 'none', borderRadius: '5px', cursor: 'pointer',
        }}>
          {copied ? 'Copied!' : 'Copy to Clipboard'}
        </button>
      </div>
      <pre style={{
        background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
        borderRadius: '6px', padding: '0.75rem', fontSize: '0.72rem',
        fontFamily: 'monospace', color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
        lineHeight: 1.6, maxHeight: '400px', overflowY: 'auto',
      }}>
        {eftText}
      </pre>
    </div>
  );
}

// ────────────────────────────────────────────────────
// Required Skills Tab
// ────────────────────────────────────────────────────

const ROMAN = ['', 'I', 'II', 'III', 'IV', 'V'];

function LevelPips({ required, trained }: { required: number; trained: number | null }) {
  return (
    <span style={{ display: 'inline-flex', gap: '2px', marginLeft: '6px' }}>
      {[1, 2, 3, 4, 5].map(lvl => {
        const isTrained = trained !== null && trained >= lvl;
        const isRequired = lvl <= required;
        let bg = 'rgba(255,255,255,0.06)';
        if (isTrained && isRequired) bg = '#3fb950';
        else if (isTrained) bg = '#3fb95066';
        else if (isRequired) bg = '#f8514988';
        return (
          <span
            key={lvl}
            style={{
              width: 8, height: 8, borderRadius: 1,
              background: bg,
              border: isRequired && !isTrained ? '1px solid #f8514966' : '1px solid transparent',
            }}
          />
        );
      })}
    </span>
  );
}

function SkillsTab({ skills, skillSource }: { skills: SkillRequirement[]; skillSource?: string }) {
  if (!skills || skills.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', padding: '2rem', textAlign: 'center',
      }}>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>No skill requirements found</div>
      </div>
    );
  }

  const hasCharacter = skillSource && skillSource !== 'all_v';
  const totalSkills = skills.length;
  const trainedSkills = hasCharacter ? skills.filter(s => s.trained_level !== null && s.trained_level >= s.required_level).length : 0;
  const missingSkills = hasCharacter ? skills.filter(s => s.trained_level !== null && s.trained_level < s.required_level) : [];
  const totalSp = skills.reduce((sum, s) => sum + s.sp_required, 0);
  const missingSp = hasCharacter ? missingSkills.reduce((sum, s) => sum + s.sp_required, 0) : 0;

  const fmtSp = (sp: number) => {
    if (sp >= 1_000_000) return `${(sp / 1_000_000).toFixed(1)}M SP`;
    if (sp >= 1_000) return `${(sp / 1_000).toFixed(0)}K SP`;
    return `${sp} SP`;
  };

  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
      borderRadius: '8px', overflow: 'hidden',
    }}>
      {/* Summary header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '10px 12px',
        borderBottom: '1px solid var(--border-color)',
        background: 'rgba(255,255,255,0.02)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>
            REQUIRED SKILLS
          </span>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>
            {totalSkills} skills · {fmtSp(totalSp)}
          </span>
        </div>
        {hasCharacter && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '0.65rem', fontWeight: 600, fontFamily: 'monospace',
              color: trainedSkills === totalSkills ? '#3fb950' : '#d29922',
            }}>
              {trainedSkills}/{totalSkills} trained
            </span>
            {missingSp > 0 && (
              <span style={{
                fontSize: '0.6rem', padding: '2px 6px', borderRadius: '3px',
                background: '#f8514922', color: '#f85149', fontFamily: 'monospace',
              }}>
                {fmtSp(missingSp)} missing
              </span>
            )}
          </div>
        )}
      </div>

      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 50px 50px 70px',
        alignItems: 'center',
        gap: '4px',
        padding: '4px 12px',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontWeight: 600 }}>SKILL</span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontWeight: 600, textAlign: 'center' }}>REQ</span>
        {hasCharacter && (
          <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontWeight: 600, textAlign: 'center' }}>CUR</span>
        )}
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontWeight: 600, textAlign: 'right' }}>LEVEL</span>
      </div>

      {/* Skill rows */}
      {skills.map(skill => {
        const met = hasCharacter && skill.trained_level !== null && skill.trained_level >= skill.required_level;
        const missing = hasCharacter && skill.trained_level !== null && skill.trained_level < skill.required_level;

        return (
          <div
            key={skill.skill_id}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 50px 50px 70px',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 12px',
              borderBottom: '1px solid rgba(255,255,255,0.02)',
              transition: 'background 0.1s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            title={skill.required_by.length > 0 ? `Required by: ${skill.required_by.join(', ')}` : undefined}
          >
            {/* Skill name */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
              <span style={{
                width: 4, height: 4, borderRadius: '50%', flexShrink: 0,
                background: met ? '#3fb950' : missing ? '#f85149' : 'var(--text-tertiary)',
              }} />
              <span style={{
                fontSize: '0.72rem',
                color: met ? '#3fb950' : missing ? '#f85149' : '#58a6ff',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {skill.skill_name}
              </span>
              {skill.rank > 1 && (
                <span style={{
                  fontSize: '0.55rem', color: 'var(--text-tertiary)', fontFamily: 'monospace', flexShrink: 0,
                }}>
                  x{skill.rank}
                </span>
              )}
            </div>

            {/* Required level */}
            <span style={{
              fontSize: '0.7rem', fontWeight: 600, fontFamily: 'monospace',
              textAlign: 'center', color: 'var(--text-primary)',
            }}>
              {ROMAN[skill.required_level] || skill.required_level}
            </span>

            {/* Trained level */}
            {hasCharacter && (
              <span style={{
                fontSize: '0.7rem', fontFamily: 'monospace', textAlign: 'center',
                color: met ? '#3fb950' : missing ? '#f85149' : 'var(--text-tertiary)',
                fontWeight: met ? 400 : 600,
              }}>
                {skill.trained_level !== null ? (ROMAN[skill.trained_level] || skill.trained_level) : '—'}
              </span>
            )}

            {/* Level pips */}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <LevelPips required={skill.required_level} trained={hasCharacter ? skill.trained_level : null} />
            </div>
          </div>
        );
      })}

      {/* Footer with SP total */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '6px 12px',
        borderTop: '1px solid var(--border-color)',
        background: 'rgba(255,255,255,0.02)',
      }}>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
          {!hasCharacter && 'Select a character to compare trained levels'}
        </span>
        <span style={{ fontSize: '0.68rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
          Total: {fmtSp(totalSp)}
        </span>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────────────

export function FittingDetail() {
  const { fittingId } = useParams<{ fittingId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { account } = useAuth();

  const [fitting, setFitting] = useState<ESIFitting | CustomFitting | null>(null);
  const [stats, setStats] = useState<FittingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeNames, setTypeNames] = useState<Map<number, string>>(new Map());
  const [activeTab, setActiveTab] = useState<Tab>('modules');
  const [selectedCharacterId, setSelectedCharacterId] = useState<number | undefined>(undefined);
  const [selectedTarget, setSelectedTarget] = useState<string>('cruiser');
  const [simulationMode, setSimulationMode] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);

  const isESI = location.pathname.includes('/esi/');
  const isCustom = location.pathname.includes('/custom/');

  useEffect(() => {
    if (!fittingId) { setError('Missing fitting ID'); setLoading(false); return; }
    if (!account?.primary_character_id && isESI && !searchParams.get('ship')) {
      setError('Sign in to view ESI fittings'); setLoading(false); return;
    }

    const loadFitting = async () => {
      try {
        setLoading(true);
        setError(null);
        let loadedFitting: ESIFitting | CustomFitting | null = null;

        if (isESI && account?.primary_character_id) {
          const esiFittings = await fittingApi.getCharacterFittings(account.primary_character_id);
          loadedFitting = esiFittings.find(f => f.fitting_id === parseInt(fittingId)) || null;
        } else if (isCustom) {
          loadedFitting = await fittingApi.getCustomFittingById(parseInt(fittingId));
        }

        if (!loadedFitting) { setError('Fitting not found'); return; }
        setFitting(loadedFitting);

        const typeIds = [...new Set(loadedFitting.items.map(i => i.type_id))];
        const fittingCharges = 'charges' in loadedFitting ? (loadedFitting as CustomFitting).charges : undefined;
        const [fittingStats, names] = await Promise.all([
          fittingApi.getFittingStats(loadedFitting.ship_type_id, loadedFitting.items, fittingCharges, undefined, selectedTarget, simulationMode),
          typeIds.length > 0 ? resolveTypeNames(typeIds) : Promise.resolve(new Map<number, string>()),
        ]);

        setStats(fittingStats);
        setTypeNames(names);
      } catch {
        setError('Failed to load fitting');
      } finally {
        setLoading(false);
      }
    };
    loadFitting();
  }, [fittingId, account, isESI, isCustom, searchParams]);

  // Re-fetch stats when character, target profile, or simulation mode changes
  useEffect(() => {
    if (!fitting) return;
    const charges = 'charges' in fitting ? (fitting as CustomFitting).charges : undefined;
    fittingApi.getFittingStats(fitting.ship_type_id, fitting.items, charges, selectedCharacterId, selectedTarget, simulationMode)
      .then(setStats)
      .catch(() => {});
  }, [selectedCharacterId, selectedTarget, simulationMode, fitting]);

  const handleEdit = () => {
    if (!fitting) return;
    const customFittingId = isCustom && 'id' in fitting ? (fitting as CustomFitting).id : undefined;
    navigate('/fittings/new', { state: { shipTypeId: fitting.ship_type_id, items: fitting.items, charges: 'charges' in fitting ? fitting.charges : {}, name: fitting.name, sourceUrl: location.pathname, fittingId: customFittingId } });
  };

  const handleCreateProject = async () => {
    if (!fitting || !account?.characters?.[0]?.character_id) return;
    setCreatingProject(true);
    try {
      const characterId = account.characters[0].character_id;
      const project = await projectApi.create({
        creator_character_id: characterId,
        name: `${fitting.name} Project`,
      });
      // Add ship hull
      await projectApi.addItem(project.id, { type_id: fitting.ship_type_id, quantity: 1, me_level: 0 });
      // Add unique modules/drones (aggregate quantities by type_id)
      const moduleCounts = new Map<number, number>();
      for (const item of fitting.items) {
        moduleCounts.set(item.type_id, (moduleCounts.get(item.type_id) || 0) + item.quantity);
      }
      for (const [typeId, qty] of moduleCounts) {
        await projectApi.addItem(project.id, { type_id: typeId, quantity: qty, me_level: 0 });
      }
      navigate(`/production/projects/${project.id}`);
    } catch {
      // stay on page
    } finally {
      setCreatingProject(false);
    }
  };

  // Loading
  if (loading) {
    return (
      <div style={{ maxWidth: 1400, margin: '0 auto', padding: '2rem 1rem' }}>
        <ModuleGate module="character_suite" preview={true}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '6rem 0' }}>
            <div style={{ width: 48, height: 48, border: '3px solid var(--border-color)', borderTopColor: '#00d4ff', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Loading fitting...</span>
            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
          </div>
        </ModuleGate>
      </div>
    );
  }

  // Error
  if (error || !fitting || !stats) {
    return (
      <div style={{ maxWidth: 1400, margin: '0 auto', padding: '2rem 1rem' }}>
        <ModuleGate module="character_suite" preview={true}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '6rem 0' }}>
            <div style={{ fontSize: '2rem', opacity: 0.3 }}>⚠</div>
            <span style={{ color: '#f85149', fontSize: '0.9rem' }}>{error || 'Fitting not found'}</span>
            <Link to="/fittings" style={{ color: '#00d4ff', fontSize: '0.8rem' }}>← Back to Fittings</Link>
          </div>
        </ModuleGate>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'modules', label: 'MODULES' },
    { key: 'export', label: 'EXPORT' },
    { key: 'skills', label: 'REQUIRED SKILLS' },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '1rem' }}>
      <ModuleGate module="character_suite" preview={true}>

        {/* Tab Bar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0',
          borderBottom: '1px solid var(--border-color)', marginBottom: '1rem',
        }}>
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                padding: '0.6rem 1.25rem', fontSize: '0.75rem', fontWeight: 700,
                letterSpacing: '0.05em', color: activeTab === tab.key ? '#00d4ff' : 'var(--text-secondary)',
                background: 'none', border: 'none', cursor: 'pointer',
                borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
                transition: 'all 0.15s', marginBottom: '-1px',
              }}
            >
              {tab.label}
            </button>
          ))}
          {/* Spacer + Character Selector + Back + Edit */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', alignItems: 'center', paddingBottom: '0.4rem' }}>
            {account?.characters && account.characters.length > 0 && (
              <select
                value={selectedCharacterId ?? ''}
                onChange={e => setSelectedCharacterId(e.target.value ? Number(e.target.value) : undefined)}
                style={{
                  padding: '0.3rem 0.5rem',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  color: 'var(--text-primary)',
                  fontSize: '0.72rem',
                  cursor: 'pointer',
                }}
              >
                <option value="">All Skills V</option>
                {account.characters.map(c => (
                  <option key={c.character_id} value={c.character_id}>
                    {c.character_name}
                  </option>
                ))}
              </select>
            )}
            <select
              value={selectedTarget}
              onChange={e => setSelectedTarget(e.target.value)}
              style={{
                padding: '0.3rem 0.5rem',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                color: 'var(--text-primary)',
                fontSize: '0.72rem',
                cursor: 'pointer',
              }}
            >
              <option value="frigate">vs Frigate</option>
              <option value="destroyer">vs Destroyer</option>
              <option value="cruiser">vs Cruiser</option>
              <option value="battlecruiser">vs Battlecruiser</option>
              <option value="battleship">vs Battleship</option>
              <option value="capital">vs Capital</option>
              <option value="structure">vs Structure</option>
            </select>
            <button
              onClick={() => setSimulationMode(m => !m)}
              title={simulationMode ? 'Simulation: All modules active' : 'Fitting: Passive modules only'}
              style={{
                padding: '0.3rem 0.5rem',
                background: simulationMode ? 'rgba(0,212,255,0.15)' : 'var(--bg-secondary)',
                border: `1px solid ${simulationMode ? 'rgba(0,212,255,0.4)' : 'var(--border-color)'}`,
                borderRadius: '4px',
                color: simulationMode ? '#00d4ff' : 'var(--text-secondary)',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: simulationMode ? 600 : 400,
              }}
            >
              {simulationMode ? 'SIM' : 'FIT'}
            </button>
            <Link to="/fittings" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textDecoration: 'none' }}>← Fittings</Link>
            <button onClick={handleEdit} style={{
              padding: '5px 12px', fontSize: '0.72rem', fontWeight: 600,
              background: '#00d4ff', color: '#000', border: 'none', borderRadius: '4px', cursor: 'pointer',
            }}>
              Edit
            </button>
            <button
              onClick={handleCreateProject}
              disabled={creatingProject}
              style={{
                padding: '5px 12px', fontSize: '0.72rem', fontWeight: 600,
                background: creatingProject ? 'rgba(210,153,34,0.15)' : 'rgba(210,153,34,0.1)',
                color: '#d29922', border: '1px solid rgba(210,153,34,0.3)',
                borderRadius: '4px', cursor: creatingProject ? 'wait' : 'pointer',
                opacity: creatingProject ? 0.6 : 1,
              }}
            >
              {creatingProject ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </div>

        {/* 2-Column Layout: Content + Stats Sidebar */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '1rem', alignItems: 'start' }}>

          {/* Left: Ship + Tab Content */}
          <div>
            {/* Ship Header Card */}
            <div style={{
              background: 'linear-gradient(180deg, rgba(13,17,23,0) 0%, var(--bg-secondary) 100%), radial-gradient(ellipse at center, rgba(0,40,60,0.3) 0%, transparent 70%)',
              border: '1px solid var(--border-color)', borderRadius: '8px',
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              padding: '2rem 1.5rem 1.5rem', marginBottom: '1rem', position: 'relative',
            }}>
              {/* Ship Image */}
              <img
                src={getShipRenderUrl(stats.ship.type_id, 512)}
                alt={stats.ship.name}
                style={{
                  width: '100%', maxWidth: 420, height: 'auto', objectFit: 'contain',
                  filter: 'drop-shadow(0 8px 24px rgba(0,0,0,0.6))',
                  marginBottom: '1rem',
                }}
              />
              {/* Ship name + Fitting name */}
              <h1 style={{ fontSize: '1.3rem', fontWeight: 700, margin: '0 0 0.25rem 0', textAlign: 'center' }}>
                {fitting.name}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.85rem', color: '#00d4ff', fontWeight: 500 }}>{stats.ship.name}</span>
                <span style={{ color: 'var(--text-tertiary)' }}>·</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{stats.ship.group_name}</span>
              </div>
              {fitting.description && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textAlign: 'center', maxWidth: '500px', margin: '0.25rem 0 0 0' }}>
                  {fitting.description}
                </p>
              )}
            </div>

            {/* Tab Content */}
            {activeTab === 'modules' && (
              <EnrichedModuleList stats={stats} />
            )}

            {activeTab === 'export' && <ExportTab fitting={fitting} stats={stats} typeNames={typeNames} />}
            {activeTab === 'skills' && <SkillsTab skills={stats.required_skills || []} skillSource={stats.skill_source} />}
          </div>

          {/* Right: Stats Sidebar */}
          <StatsPanel stats={stats} />
        </div>

      </ModuleGate>
    </div>
  );
}
