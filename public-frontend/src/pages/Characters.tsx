import { MailTab } from '../components/characters/MailTab';
import { SkillfarmTab } from '../components/characters/SkillfarmTab';
import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import { ModuleGate } from '../components/ModuleGate';
import { characterApi } from '../services/api/character';
import { characterSummaryApi } from '../services/api/auth';
import { pilotApi } from '../services/api/fleet';
import { formatDuration as formatFleetDuration } from '../types/fleet';
import { formatISK, formatNumber } from '../utils/format';
import { ACTIVITY_NAMES, ACTIVITY_COLORS } from '../types/character';
import { WealthDashboard } from '../components/characters/WealthDashboard';
import { fontSize, color, spacing } from '../styles/theme';

import type {
  CharacterSummary,
  SkillData,
  ValuedAssetData,
  IndustryData,
  SkillQueueItem,
  AssetEntry,
} from '../types/character';
import type { AccountSummary } from '../types/auth';

type TabId = 'overview' | 'skills' | 'assets' | 'industry' | 'wealth' | 'implants' | 'skillfarm' | 'mail' | 'fleet';

export function Characters() {
  const { account, activeCharacterId } = useAuth();
  const [characters, setCharacters] = useState<CharacterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // Drill-down data
  const [skillData, setSkillData] = useState<SkillData | null>(null);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [assetData, setAssetData] = useState<ValuedAssetData | null>(null);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [industryData, setIndustryData] = useState<IndustryData | null>(null);
  const [industryLoading, setIndustryLoading] = useState(false);
  const [implantData, setImplantData] = useState<any>(null);
  const [implantsLoading, setImplantsLoading] = useState(false);
  const [fleetData, setFleetData] = useState<any>(null);
  const [fleetLoading, setFleetLoading] = useState(false);
  const [accountSummary, setAccountSummary] = useState<AccountSummary | null>(null);
  const [openSkillGroups, setOpenSkillGroups] = useState<Set<string>>(new Set());
  const [openAssetLocations, setOpenAssetLocations] = useState<Set<number>>(new Set());

  // Load account summary for aggregated stats
  useEffect(() => {
    if (!account) return;
    characterSummaryApi.getAccountSummary()
      .then(setAccountSummary)
      .catch(() => {});
  }, [account, activeCharacterId]);

  // Load only the account's characters (fast: fetches 1 char instead of all)
  useEffect(() => {
    if (!account) return;
    setLoading(true);
    const myCharIds = account.characters.map(c => c.character_id);
    characterApi.getSummaryAll(myCharIds)
      .then(data => {
        setCharacters(data.characters);
        if (data.characters.length > 0) {
          setSelectedId(data.characters[0].character_id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [account, activeCharacterId]);

  const selected = useMemo(
    () => characters.find(c => c.character_id === selectedId) ?? null,
    [characters, selectedId]
  );

  // Drill-down: load skills when Skills tab selected
  useEffect(() => {
    if (activeTab !== 'skills' || !selectedId) return;
    setSkillsLoading(true);
    characterApi.getSkills(selectedId)
      .then(setSkillData)
      .catch(() => setSkillData(null))
      .finally(() => setSkillsLoading(false));
  }, [activeTab, selectedId]);

  // Drill-down: load assets when Assets tab selected
  useEffect(() => {
    if (activeTab !== 'assets' || !selectedId) return;
    setAssetsLoading(true);
    characterApi.getAssets(selectedId)
      .then(setAssetData)
      .catch(() => setAssetData(null))
      .finally(() => setAssetsLoading(false));
  }, [activeTab, selectedId]);

  // Drill-down: load industry when Industry tab selected
  useEffect(() => {
    if (activeTab !== 'industry' || !selectedId) return;
    setIndustryLoading(true);
    characterApi.getIndustry(selectedId)
      .then(setIndustryData)
      .catch(() => setIndustryData(null))
      .finally(() => setIndustryLoading(false));
  }, [activeTab, selectedId]);

  // Drill-down: load implants when Implants tab selected
  useEffect(() => {
    if (activeTab !== 'implants' || !selectedId) return;
    setImplantsLoading(true);
    characterApi.getImplants(selectedId)
      .then(setImplantData)
      .catch(() => setImplantData(null))
      .finally(() => setImplantsLoading(false));
  }, [activeTab, selectedId]);

  // Drill-down: load fleet activity when Fleet tab selected
  useEffect(() => {
    if (activeTab !== 'fleet' || !selectedId) return;
    setFleetLoading(true);
    pilotApi.getActivity(selectedId)
      .then(setFleetData)
      .catch(() => setFleetData(null))
      .finally(() => setFleetLoading(false));
  }, [activeTab, selectedId]);

  // Reset drill-down when switching character
  useEffect(() => {
    setSkillData(null);
    setAssetData(null);
    setIndustryData(null);
    setImplantData(null);
    setFleetData(null);
  }, [selectedId]);

  const tabStyle = (id: TabId) => ({
    padding: '8px 16px',
    fontSize: fontSize.sm,
    fontWeight: 700 as const,
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer' as const,
    background: activeTab === id ? 'rgba(0,212,255,0.15)' : 'transparent',
    color: activeTab === id ? '#00d4ff' : 'var(--text-secondary)',
    borderBottom: activeTab === id ? '2px solid #00d4ff' : '2px solid transparent',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.03em',
  });

  /** Format seconds to human-readable duration */
  function formatDuration(seconds: number): string {
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  /** Time remaining until a future ISO date */
  function timeUntil(isoDate: string | null): string {
    if (!isoDate) return 'Paused';
    const diff = new Date(isoDate).getTime() - Date.now();
    if (diff <= 0) return 'Done';
    return formatDuration(diff / 1000);
  }

  /** Group skills by SDE group_name */
  function groupSkillsByCategory(skills: { skill_id: number; skill_name: string; level: number; trained_level: number; skillpoints: number; group_name: string }[]): Record<string, typeof skills> {
    const groups: Record<string, typeof skills> = {};
    for (const s of skills) {
      const cat = s.group_name || 'Unknown';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(s);
    }
    return groups;
  }

  const toggleSkillGroup = (group: string) => {
    setOpenSkillGroups(prev => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  const toggleAssetLocation = (locId: number) => {
    setOpenAssetLocations(prev => {
      const next = new Set(prev);
      if (next.has(locId)) next.delete(locId);
      else next.add(locId);
      return next;
    });
  };

  /** Group assets by location_id */
  function groupAssetsByLocation(assets: AssetEntry[]): Map<number, AssetEntry[]> {
    const map = new Map<number, AssetEntry[]>();
    for (const a of assets) {
      const list = map.get(a.location_id);
      if (list) list.push(a);
      else map.set(a.location_id, [a]);
    }
    return map;
  }

  /** Render 5 level blocks like EVE skill window */
  function LevelBlocks({ level, trained }: { level: number; trained: number }) {
    return (
      <div style={{ display: 'flex', gap: 2 }}>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} style={{
            width: 14, height: 8, borderRadius: 1,
            background: i <= level
              ? (level === 5 ? '#3fb950' : '#00d4ff')
              : i <= trained
                ? 'rgba(0,212,255,0.25)'
                : 'rgba(255,255,255,0.06)',
            border: `1px solid ${i <= level ? (level === 5 ? 'rgba(63,185,80,0.5)' : 'rgba(0,212,255,0.4)') : 'rgba(255,255,255,0.08)'}`,
          }} />
        ))}
      </div>
    );
  }

  /** Radar chart for skill groups */
  function SkillRadarChart({ groups }: { groups: Record<string, { skill_name: string; level: number; skillpoints: number; group_name: string }[]> }) {
    const entries = Object.entries(groups)
      .map(([name, skills]) => ({
        name,
        avg: skills.reduce((s, x) => s + x.level, 0) / skills.length / 5, // 0..1
        count: skills.length,
        lvl5: skills.filter(s => s.level === 5).length,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    if (entries.length < 3) return null;

    const size = 380;
    const cx = size / 2;
    const cy = size / 2;
    const R = size / 2 - 55;
    const n = entries.length;

    const pointAt = (i: number, r: number) => {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      return { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
    };

    const rings = [0.2, 0.4, 0.6, 0.8, 1.0];

    const dataPoints = entries.map((e, i) => pointAt(i, R * e.avg));

    return (
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.5rem',
      }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Skill Distribution
        </div>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Grid rings */}
          {rings.map(r => (
            <polygon
              key={r}
              points={Array.from({ length: n }, (_, i) => pointAt(i, R * r)).map(p => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={1}
            />
          ))}
          {/* Axes */}
          {entries.map((_, i) => {
            const p = pointAt(i, R);
            return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />;
          })}
          {/* Data polygon */}
          <polygon
            points={dataPoints.map(p => `${p.x},${p.y}`).join(' ')}
            fill="rgba(0,212,255,0.12)"
            stroke="#00d4ff"
            strokeWidth={1.5}
          />
          {/* Data dots */}
          {dataPoints.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={3} fill={entries[i].avg >= 0.9 ? '#3fb950' : '#00d4ff'} />
          ))}
          {/* Labels */}
          {entries.map((e, i) => {
            const labelR = R + 18;
            const p = pointAt(i, labelR);
            const angle = (360 * i) / n - 90;
            const isRight = angle > -90 && angle < 90;
            const isBottom = angle > 0 && angle < 180;
            return (
              <text
                key={i}
                x={p.x}
                y={p.y}
                textAnchor={Math.abs(angle + 90) < 10 || Math.abs(angle - 90) < 10 ? 'middle' : isRight ? 'start' : 'end'}
                dominantBaseline={Math.abs(angle + 90) < 10 ? 'auto' : Math.abs(angle - 90) < 10 ? 'hanging' : isBottom ? 'hanging' : 'auto'}
                fill="var(--text-secondary)"
                fontSize={9}
                fontFamily="system-ui, sans-serif"
              >
                {e.name.length > 14 ? e.name.slice(0, 12) + '..' : e.name}
              </text>
            );
          })}
        </svg>
      </div>
    );
  }

  return (
    <ModuleGate module="character_suite">
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: spacing["2xl"] }}>
          <img src='/icons/128/copilot_pilots.png' alt='' style={{ width: 48, height: 48, borderRadius: '6px' }} />
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
              Character Dashboard
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: fontSize.base, margin: 0 }}>
              Your pilots at a glance — wallet, skills, assets, industry
            </p>
          </div>
        </div>

        {loading ? (
          <div className="skeleton" style={{ height: 500 }} />
        ) : characters.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
            No characters found. Make sure your ESI tokens are configured.
          </div>
        ) : (
          <>
            {/* Aggregated Stats Cards */}
            {accountSummary && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '1rem',
                marginBottom: '2rem',
              }}>
                <div style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>Total ISK</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950' }}>
                    {(accountSummary.total_isk / 1e9).toFixed(1)}B
                  </div>
                </div>
                <div style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>Total SP</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#00d4ff' }}>
                    {(accountSummary.total_sp / 1e6).toFixed(1)}M
                  </div>
                </div>
                <div style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>Skill Queues</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#d29922' }}>
                    {accountSummary.characters.filter(c => c.skill_queue_length > 0).length} / {accountSummary.characters.length}
                  </div>
                </div>
                <div style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1rem',
                  textAlign: 'center',
                }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>Characters</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#e6edf3' }}>
                    {accountSummary.characters.length}
                  </div>
                </div>
              </div>
            )}

            {/* Character Selector */}
            <div style={{
              display: 'flex', gap: spacing.lg, marginBottom: spacing["2xl"],
              padding: '0.75rem 1rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 8, overflowX: 'auto',
            }}>
              {[...characters]
                .sort((a, b) => {
                  const aLinked = account?.characters.find(lc => lc.character_id === a.character_id);
                  const bLinked = account?.characters.find(lc => lc.character_id === b.character_id);
                  if (aLinked?.is_primary && !bLinked?.is_primary) return -1;
                  if (!aLinked?.is_primary && bLinked?.is_primary) return 1;
                  const aSp = a.skills?.total_sp ?? 0;
                  const bSp = b.skills?.total_sp ?? 0;
                  return bSp - aSp;
                })
                .map(c => {
                  const linkedChar = account?.characters.find(lc => lc.character_id === c.character_id);
                  const summaryChar = accountSummary?.characters.find(sc => sc.character_id === c.character_id);
                  return (
                    <div
                      key={c.character_id}
                      onClick={() => setSelectedId(c.character_id)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: spacing.base,
                        padding: '0.5rem 0.75rem',
                        background: selectedId === c.character_id ? 'rgba(0,212,255,0.1)' : 'transparent',
                        border: linkedChar?.is_primary
                          ? '2px solid #d4a017'
                          : `1px solid ${selectedId === c.character_id ? 'rgba(0,212,255,0.4)' : 'transparent'}`,
                        borderRadius: 6, cursor: 'pointer', whiteSpace: 'nowrap',
                      }}
                    >
                      <img
                        src={`https://images.evetech.net/characters/${c.character_id}/portrait?size=64`}
                        alt={c.character_name}
                        style={{
                          width: 36, height: 36, borderRadius: '50%',
                          border: linkedChar?.is_primary ? '2px solid #d4a017' : '2px solid var(--border-color)',
                        }}
                      />
                      <div>
                        <div style={{ fontSize: fontSize.sm, fontWeight: 600 }}>{c.character_name}</div>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)' }}>
                          {c.wallet ? formatISK(c.wallet.balance) : '—'}
                        </div>
                        {summaryChar && (
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', display: 'flex', gap: '0.5rem' }}>
                            <span>{(summaryChar.sp / 1e6).toFixed(0)}M SP</span>
                            <span>{(summaryChar.isk / 1e9).toFixed(1)}B ISK</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>

            {/* Tab Bar */}
            <div style={{
              display: 'flex', gap: spacing.xs,
              padding: '0.35rem 0.5rem',
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.05)',
              marginBottom: spacing["2xl"],
            }}>
              <button onClick={() => setActiveTab('overview')} style={tabStyle('overview')}>Overview</button>
              <button onClick={() => setActiveTab('skills')} style={tabStyle('skills')}>Skills</button>
              <button onClick={() => setActiveTab('assets')} style={tabStyle('assets')}>Assets</button>
              <button onClick={() => setActiveTab('industry')} style={tabStyle('industry')}>Industry</button>
              <button onClick={() => setActiveTab('implants')} style={{
                ...tabStyle('implants'),
                color: activeTab === 'implants' ? '#a855f7' : 'var(--text-secondary)',
                background: activeTab === 'implants' ? 'rgba(168,85,247,0.15)' : 'transparent',
                borderBottom: activeTab === 'implants' ? '2px solid #a855f7' : '2px solid transparent',
              }}>Implants</button>
              <button onClick={() => setActiveTab('wealth')} style={{
                ...tabStyle('wealth'),
                color: activeTab === 'wealth' ? '#3fb950' : 'var(--text-secondary)',
                background: activeTab === 'wealth' ? 'rgba(63,185,80,0.15)' : 'transparent',
                borderBottom: activeTab === 'wealth' ? '2px solid #3fb950' : '2px solid transparent',
              }}>Wealth</button>
              <button onClick={() => setActiveTab("skillfarm")} style={{
                ...tabStyle("skillfarm"),
                color: activeTab === "skillfarm" ? "#d29922" : "var(--text-secondary)",
                background: activeTab === "skillfarm" ? "rgba(210,153,34,0.15)" : "transparent",
                borderBottom: activeTab === "skillfarm" ? "2px solid #d29922" : "2px solid transparent",
              }}>Skillfarm</button>
              <button onClick={() => setActiveTab("mail")} style={{
                ...tabStyle("mail"),
                color: activeTab === "mail" ? "#f0883e" : "var(--text-secondary)",
                background: activeTab === "mail" ? "rgba(240,136,62,0.15)" : "transparent",
                borderBottom: activeTab === "mail" ? "2px solid #f0883e" : "2px solid transparent",
              }}>Mail</button>
              <button onClick={() => setActiveTab("fleet")} style={{
                ...tabStyle("fleet"),
                color: activeTab === "fleet" ? "#e05d44" : "var(--text-secondary)",
                background: activeTab === "fleet" ? "rgba(224,93,68,0.15)" : "transparent",
                borderBottom: activeTab === "fleet" ? "2px solid #e05d44" : "2px solid transparent",
              }}>Fleet</button>
            </div>

            {/* === OVERVIEW TAB === */}
            {activeTab === 'overview' && selected && (
              <div>
                {/* Character Header */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: spacing.xl,
                  padding: spacing.xl,
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8, marginBottom: spacing.xl,
                }}>
                  <img
                    src={`https://images.evetech.net/characters/${selected.character_id}/portrait?size=128`}
                    alt={selected.character_name}
                    style={{ width: 80, height: 80, borderRadius: 8, border: '2px solid var(--border-color)' }}
                  />
                  <div style={{ flex: 1 }}>
                    <h2 style={{ margin: '0 0 0.25rem 0', fontSize: fontSize.h3 }}>{selected.character_name}</h2>
                    <div style={{ display: 'flex', gap: spacing.base, alignItems: 'center', flexWrap: 'wrap' }}>
                      {selected.info?.corporation_id && (
                        <img
                          src={`https://images.evetech.net/corporations/${selected.info.corporation_id}/logo?size=32`}
                          alt="" style={{ width: 20, height: 20, borderRadius: 3 }}
                        />
                      )}
                      {selected.info?.security_status != null && (
                        <span style={{
                          fontSize: fontSize.xxs, padding: '2px 6px',
                          background: selected.info.security_status >= 0 ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
                          border: `1px solid ${selected.info.security_status >= 0 ? 'rgba(63,185,80,0.3)' : 'rgba(248,81,73,0.3)'}`,
                          borderRadius: 3,
                          color: selected.info.security_status >= 0 ? '#3fb950' : '#f85149',
                          fontFamily: 'monospace',
                        }}>
                          Sec: {selected.info.security_status.toFixed(2)}
                        </span>
                      )}
                      {selected.location && (
                        <span style={{ fontSize: fontSize.xxs, color: 'var(--text-secondary)' }}>
                          {selected.location.solar_system_name}
                          {selected.location.station_name ? ` — ${selected.location.station_name}` : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  {selected.ship && (
                    <div style={{ textAlign: 'right' }}>
                      <img
                        src={`https://images.evetech.net/types/${selected.ship.ship_type_id}/icon?size=64`}
                        alt={selected.ship.ship_type_name}
                        style={{ width: 48, height: 48, borderRadius: 6 }}
                      />
                      <div style={{ fontSize: fontSize.xxs, fontWeight: 600, marginTop: '0.2rem' }}>{selected.ship.ship_type_name}</div>
                      <div style={{ fontSize: fontSize.micro, color: 'var(--text-secondary)' }}>{selected.ship.ship_name}</div>
                    </div>
                  )}
                </div>

                {/* Quick Stats Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: spacing.lg, marginBottom: spacing["2xl"],
                }}>
                  {[
                    { label: 'Wallet', value: formatISK(selected.wallet?.balance), color: color.killGreen },
                    { label: 'Skill Points', value: formatNumber(selected.skills?.total_sp), color: color.accentCyan },
                    { label: 'Unallocated SP', value: formatNumber(selected.skills?.unallocated_sp), color: color.accentPurple },
                    { label: 'Skills Trained', value: (selected.skills?.skills?.length ?? 0).toString(), color: 'var(--text-primary)' },
                    { label: 'Active Jobs', value: selected.industry?.active_jobs?.toString() ?? '0', color: color.warningYellow },
                    { label: 'Training Queue', value: (selected.skillqueue?.queue?.length ?? 0).toString(), color: color.accentCyan },
                  ].map(stat => (
                    <div key={stat.label} style={{
                      padding: '0.75rem 1rem',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 8,
                    }}>
                      <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: spacing.sm }}>{stat.label}</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: stat.color, fontFamily: 'monospace' }}>{stat.value}</div>
                    </div>
                  ))}
                </div>

                {/* Skill Queue Preview */}
                {selected.skillqueue && selected.skillqueue.queue.length > 0 && (
                  <div style={{
                    padding: spacing.xl,
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8, marginBottom: spacing.xl,
                  }}>
                    <div style={{ fontSize: fontSize.xs, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: spacing.lg }}>
                      Training Queue
                    </div>
                    {selected.skillqueue.queue.slice(0, 5).map((sq: SkillQueueItem) => (
                      <div key={sq.queue_position} style={{
                        display: 'flex', alignItems: 'center', gap: spacing.lg,
                        padding: '0.4rem 0',
                        borderBottom: '1px solid rgba(255,255,255,0.03)',
                      }}>
                        <div style={{ flex: 1 }}>
                          <span style={{ fontSize: fontSize.sm, fontWeight: 600 }}>{sq.skill_name}</span>
                          <span style={{ fontSize: fontSize.xxs, color: 'var(--text-secondary)', marginLeft: spacing.md }}>
                            → Level {sq.finished_level}
                          </span>
                        </div>
                        <div style={{ width: 100, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{
                            width: `${Math.min(sq.training_progress ?? 0, 100)}%`,
                            height: '100%',
                            background: color.accentCyan,
                            borderRadius: 3,
                          }} />
                        </div>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', minWidth: 60, textAlign: 'right', fontFamily: 'monospace' }}>
                          {timeUntil(sq.finish_date)}
                        </div>
                      </div>
                    ))}
                    {selected.skillqueue.queue.length > 5 && (
                      <div style={{ fontSize: fontSize.xxs, color: 'var(--text-secondary)', marginTop: spacing.base, textAlign: 'center' }}>
                        +{selected.skillqueue.queue.length - 5} more in queue
                      </div>
                    )}
                  </div>
                )}

                {/* Active Industry Jobs Preview */}
                {selected.industry && selected.industry.active_jobs > 0 && (
                  <div style={{
                    padding: spacing.xl,
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                  }}>
                    <div style={{ fontSize: fontSize.xs, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: spacing.lg }}>
                      Active Industry Jobs
                    </div>
                    {selected.industry.jobs.filter(j => j.status === 'active').slice(0, 5).map(job => {
                      const progress = job.end_date && job.start_date
                        ? Math.min(100, Math.max(0, (Date.now() - new Date(job.start_date).getTime()) / (new Date(job.end_date).getTime() - new Date(job.start_date).getTime()) * 100))
                        : 0;
                      return (
                        <div key={job.job_id} style={{
                          display: 'flex', alignItems: 'center', gap: spacing.lg,
                          padding: '0.4rem 0',
                          borderBottom: '1px solid rgba(255,255,255,0.03)',
                        }}>
                          <span style={{
                            fontSize: fontSize.micro, padding: '2px 6px', borderRadius: 3,
                            background: `${ACTIVITY_COLORS[job.activity_id] ?? '#8b949e'}20`,
                            color: ACTIVITY_COLORS[job.activity_id] ?? '#8b949e',
                            fontWeight: 700, whiteSpace: 'nowrap',
                          }}>
                            {ACTIVITY_NAMES[job.activity_id] ?? `Activity ${job.activity_id}`}
                          </span>
                          <div style={{ flex: 1, fontSize: fontSize.sm, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {job.product_type_name || job.blueprint_type_name}
                            {job.runs > 1 && <span style={{ color: 'var(--text-secondary)', marginLeft: spacing.sm }}>x{job.runs}</span>}
                          </div>
                          <div style={{ width: 80, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{
                              width: `${isFinite(progress) ? progress : 0}%`,
                              height: '100%',
                              background: ACTIVITY_COLORS[job.activity_id] ?? '#8b949e',
                              borderRadius: 3,
                            }} />
                          </div>
                          <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', minWidth: 50, textAlign: 'right', fontFamily: 'monospace' }}>
                            {timeUntil(job.end_date)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* === SKILLS TAB === */}
            {activeTab === 'skills' && (
              <div>
                {skillsLoading ? (
                  <div className="skeleton" style={{ height: 400 }} />
                ) : skillData ? (
                  <div>
                    {/* SP Summary Bar */}
                    <div style={{
                      display: 'flex', gap: spacing.lg, marginBottom: spacing.xl,
                      padding: '0.75rem 1rem',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 8,
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Total SP</div>
                        <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.accentCyan, fontFamily: 'monospace' }}>{formatNumber(skillData.total_sp)}</div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Unallocated</div>
                        <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.accentPurple, fontFamily: 'monospace' }}>{formatNumber(skillData.unallocated_sp)}</div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Skills Trained</div>
                        <div style={{ fontSize: fontSize.lg, fontWeight: 700, fontFamily: 'monospace' }}>{skillData.skill_count}</div>
                      </div>
                    </div>

                    {/* Radar Chart */}
                    <div style={{ marginBottom: spacing.xl }}>
                      <SkillRadarChart groups={groupSkillsByCategory(skillData.skills)} />
                    </div>

                    {/* Skill Queue */}
                    {selected?.skillqueue && selected.skillqueue.queue.length > 0 && (
                      <div style={{
                        padding: '0.75rem 1rem',
                        background: 'var(--bg-secondary)',
                        border: '1px solid rgba(0,212,255,0.2)',
                        borderRadius: 8, marginBottom: spacing.xl,
                      }}>
                        <div style={{ fontSize: fontSize.xs, fontWeight: 700, color: color.accentCyan, marginBottom: spacing.md }}>
                          Training Queue ({selected.skillqueue.queue_length})
                        </div>
                        {selected.skillqueue.queue.map((sq: SkillQueueItem) => (
                          <div key={sq.queue_position} style={{
                            display: 'flex', alignItems: 'center', gap: spacing.md,
                            padding: '4px 0',
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                          }}>
                            <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', minWidth: 18, fontFamily: 'monospace' }}>#{sq.queue_position + 1}</span>
                            <span style={{ fontSize: fontSize.sm, fontWeight: 500, flex: 1 }}>{sq.skill_name}</span>
                            <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)' }}>Lv {sq.finished_level}</span>
                            <div style={{ width: 80, height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                              <div style={{ width: `${Math.min(sq.training_progress ?? 0, 100)}%`, height: '100%', background: color.accentCyan, borderRadius: 2 }} />
                            </div>
                            <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', minWidth: 55, textAlign: 'right', fontFamily: 'monospace' }}>
                              {timeUntil(sq.finish_date)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* EVE-style Skill Groups */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {Object.entries(groupSkillsByCategory(skillData.skills))
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([cat, skills]) => {
                          const isOpen = openSkillGroups.has(cat);
                          const groupSP = skills.reduce((s, x) => s + x.skillpoints, 0);
                          const lvl5Count = skills.filter(s => s.level === 5).length;
                          return (
                            <div key={cat}>
                              {/* Group Header */}
                              <div
                                onClick={() => toggleSkillGroup(cat)}
                                style={{
                                  display: 'flex', alignItems: 'center', gap: spacing.md,
                                  padding: '8px 12px',
                                  background: isOpen ? 'rgba(0,212,255,0.06)' : 'var(--bg-secondary)',
                                  border: '1px solid var(--border-color)',
                                  borderRadius: isOpen ? '6px 6px 0 0' : 6,
                                  cursor: 'pointer',
                                  userSelect: 'none',
                                }}
                              >
                                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', width: 12, textAlign: 'center' }}>
                                  {isOpen ? '\u25BC' : '\u25B6'}
                                </span>
                                <span style={{ fontSize: fontSize.sm, fontWeight: 600, flex: 1, color: 'var(--text-primary)' }}>
                                  {cat}
                                </span>
                                <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)' }}>
                                  {skills.length} skills
                                </span>
                                {lvl5Count > 0 && (
                                  <span style={{ fontSize: fontSize.tiny, color: '#3fb950', fontWeight: 600 }}>
                                    {lvl5Count} @ V
                                  </span>
                                )}
                                <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', fontFamily: 'monospace', minWidth: 70, textAlign: 'right' }}>
                                  {formatNumber(groupSP)} SP
                                </span>
                              </div>
                              {/* Expanded Skill List */}
                              {isOpen && (
                                <div style={{
                                  border: '1px solid var(--border-color)',
                                  borderTop: 'none',
                                  borderRadius: '0 0 6px 6px',
                                  background: 'rgba(0,0,0,0.15)',
                                }}>
                                  {skills.sort((a, b) => a.skill_name.localeCompare(b.skill_name)).map(s => (
                                    <div key={s.skill_id} style={{
                                      display: 'flex', alignItems: 'center', gap: spacing.md,
                                      padding: '5px 12px 5px 32px',
                                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                                    }}>
                                      <span style={{
                                        fontSize: fontSize.sm, flex: 1,
                                        color: s.level === 5 ? '#3fb950' : s.level > 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                                        fontWeight: s.level === 5 ? 600 : 400,
                                      }}>
                                        {s.skill_name}
                                      </span>
                                      <LevelBlocks level={s.level} trained={s.trained_level} />
                                      <span style={{
                                        fontSize: fontSize.tiny, fontFamily: 'monospace', minWidth: 65, textAlign: 'right',
                                        color: 'var(--text-secondary)',
                                      }}>
                                        {formatNumber(s.skillpoints)} SP
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    No skill data available.
                  </div>
                )}
              </div>
            )}

            {/* === ASSETS TAB === */}
            {activeTab === 'assets' && (
              <div>
                {assetsLoading ? (
                  <div className="skeleton" style={{ height: 400 }} />
                ) : assetData ? (
                  <div>
                    {/* Asset Summary */}
                    <div style={{
                      display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: spacing.lg,
                      marginBottom: spacing["2xl"],
                    }}>
                      {[
                        { label: 'Total Value', value: formatISK(assetData.total_value), color: color.killGreen },
                        { label: 'Total Volume', value: `${formatNumber(assetData.total_volume)} m³`, color: 'var(--text-primary)' },
                        { label: 'Items', value: assetData.total_items.toLocaleString(), color: 'var(--text-primary)' },
                        { label: 'Types', value: assetData.total_types.toLocaleString(), color: 'var(--text-primary)' },
                      ].map(stat => (
                        <div key={stat.label} style={{ padding: '0.75rem 1rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                          <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: spacing.sm }}>{stat.label}</div>
                          <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: stat.color, fontFamily: 'monospace' }}>{stat.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Collapsible Locations */}
                    {(() => {
                      const itemsByLoc = groupAssetsByLocation(assetData.assets);
                      return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          {assetData.location_summaries
                            .sort((a, b) => b.total_value - a.total_value)
                            .map(loc => {
                              const isOpen = openAssetLocations.has(loc.location_id);
                              const pct = assetData.total_value > 0 ? (loc.total_value / assetData.total_value * 100) : 0;
                              const locItems = (itemsByLoc.get(loc.location_id) || [])
                                .sort((a, b) => b.total_value - a.total_value);
                              return (
                                <div key={loc.location_id}>
                                  {/* Location Header */}
                                  <div
                                    onClick={() => toggleAssetLocation(loc.location_id)}
                                    style={{
                                      display: 'flex', alignItems: 'center', gap: spacing.md,
                                      padding: '8px 12px',
                                      background: isOpen ? 'rgba(63,185,80,0.06)' : 'var(--bg-secondary)',
                                      border: '1px solid var(--border-color)',
                                      borderRadius: isOpen ? '6px 6px 0 0' : 6,
                                      cursor: 'pointer',
                                      userSelect: 'none',
                                    }}
                                  >
                                    <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', width: 12, textAlign: 'center' }}>
                                      {isOpen ? '\u25BC' : '\u25B6'}
                                    </span>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                      <div style={{ fontSize: fontSize.sm, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {loc.location_name}
                                      </div>
                                      <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)' }}>
                                        {loc.item_count} items · {loc.type_count} types
                                      </div>
                                    </div>
                                    <div style={{ width: 80, height: 5, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden', flexShrink: 0 }}>
                                      <div style={{ width: `${isFinite(pct) ? pct : 0}%`, height: '100%', background: color.killGreen, borderRadius: 3 }} />
                                    </div>
                                    <span style={{ fontSize: fontSize.sm, fontWeight: 600, color: color.killGreen, fontFamily: 'monospace', minWidth: 90, textAlign: 'right', flexShrink: 0 }}>
                                      {formatISK(loc.total_value)}
                                    </span>
                                  </div>
                                  {/* Expanded Items */}
                                  {isOpen && (
                                    <div style={{
                                      border: '1px solid var(--border-color)',
                                      borderTop: 'none',
                                      borderRadius: '0 0 6px 6px',
                                      background: 'rgba(0,0,0,0.15)',
                                      maxHeight: 400,
                                      overflowY: 'auto',
                                    }}>
                                      {locItems.map(asset => (
                                        <div key={asset.item_id} style={{
                                          display: 'flex', alignItems: 'center', gap: spacing.md,
                                          padding: '5px 12px 5px 32px',
                                          borderBottom: '1px solid rgba(255,255,255,0.03)',
                                        }}>
                                          <img
                                            src={`https://images.evetech.net/types/${asset.type_id}/icon?size=32`}
                                            alt=""
                                            style={{ width: 28, height: 28, borderRadius: 3, flexShrink: 0 }}
                                          />
                                          <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ fontSize: fontSize.sm, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                              {asset.type_name === 'Unknown' ? `Type #${asset.type_id}` : asset.type_name}
                                              {asset.quantity > 1 && (
                                                <span style={{ color: 'var(--text-secondary)', marginLeft: 4 }}>
                                                  x{asset.quantity.toLocaleString()}
                                                </span>
                                              )}
                                              {asset.is_singleton && (
                                                <span style={{ fontSize: '0.6rem', color: '#d29922', marginLeft: 6, fontStyle: 'italic' }}>assembled</span>
                                              )}
                                            </div>
                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', display: 'flex', gap: 8 }}>
                                              <span>{asset.group_name}</span>
                                              {asset.total_volume > 0 && <span>{formatNumber(asset.total_volume)} m³</span>}
                                            </div>
                                          </div>
                                          <span style={{ fontSize: fontSize.tiny, fontFamily: 'monospace', color: color.killGreen, fontWeight: 600, minWidth: 80, textAlign: 'right', flexShrink: 0 }}>
                                            {formatISK(asset.total_value)}
                                          </span>
                                        </div>
                                      ))}
                                      {locItems.length === 0 && (
                                        <div style={{ padding: '0.75rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: fontSize.tiny }}>
                                          No items found
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    No asset data available.
                  </div>
                )}
              </div>
            )}

            {/* === INDUSTRY TAB === */}
            {activeTab === 'industry' && (
              <div>
                {industryLoading ? (
                  <div className="skeleton" style={{ height: 400 }} />
                ) : industryData ? (
                  <div>
                    {/* Industry Summary */}
                    <div style={{
                      display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: spacing.lg,
                      marginBottom: spacing["2xl"],
                    }}>
                      <div style={{ padding: '0.75rem 1rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: spacing.sm }}>Total Jobs</div>
                        <div style={{ fontSize: fontSize.h4, fontWeight: 700, fontFamily: 'monospace' }}>{industryData.total_jobs}</div>
                      </div>
                      <div style={{ padding: '0.75rem 1rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: spacing.sm }}>Active</div>
                        <div style={{ fontSize: fontSize.h4, fontWeight: 700, color: color.killGreen, fontFamily: 'monospace' }}>{industryData.active_jobs}</div>
                      </div>
                      <div style={{ padding: '0.75rem 1rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                        <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: spacing.sm }}>Total Cost</div>
                        <div style={{ fontSize: fontSize.h4, fontWeight: 700, color: color.warningYellow, fontFamily: 'monospace' }}>
                          {formatISK(industryData.jobs.reduce((s, j) => s + (j.cost || 0), 0))}
                        </div>
                      </div>
                    </div>

                    {/* Jobs Table */}
                    <div style={{
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 8, overflow: 'hidden',
                    }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: fontSize.sm }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                            <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Activity</th>
                            <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Product</th>
                            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Runs</th>
                            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Cost</th>
                            <th style={{ textAlign: 'center', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Status</th>
                            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Remaining</th>
                          </tr>
                        </thead>
                        <tbody>
                          {industryData.jobs
                            .sort((a, b) => {
                              if (a.status === 'active' && b.status !== 'active') return -1;
                              if (a.status !== 'active' && b.status === 'active') return 1;
                              return (a.end_date ?? '').localeCompare(b.end_date ?? '');
                            })
                            .map(job => {
                              const progress = job.end_date && job.start_date
                                ? Math.min(100, Math.max(0, (Date.now() - new Date(job.start_date).getTime()) / (new Date(job.end_date).getTime() - new Date(job.start_date).getTime()) * 100))
                                : 0;
                              return (
                                <tr key={job.job_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                  <td style={{ padding: '6px 12px' }}>
                                    <span style={{
                                      fontSize: fontSize.tiny, padding: '2px 6px', borderRadius: 3,
                                      background: `${ACTIVITY_COLORS[job.activity_id] ?? '#8b949e'}20`,
                                      color: ACTIVITY_COLORS[job.activity_id] ?? '#8b949e',
                                      fontWeight: 700,
                                    }}>
                                      {ACTIVITY_NAMES[job.activity_id] ?? `ID ${job.activity_id}`}
                                    </span>
                                  </td>
                                  <td style={{ padding: '6px 12px', fontWeight: 600, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {job.product_type_name || job.blueprint_type_name}
                                  </td>
                                  <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace' }}>{job.runs}</td>
                                  <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace', color: color.warningYellow }}>{formatISK(job.cost)}</td>
                                  <td style={{ padding: '6px 12px', textAlign: 'center' }}>
                                    {job.status === 'active' ? (
                                      <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md, justifyContent: 'center' }}>
                                        <div style={{ width: 60, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden' }}>
                                          <div style={{
                                            width: `${isFinite(progress) ? progress : 0}%`,
                                            height: '100%',
                                            background: ACTIVITY_COLORS[job.activity_id] ?? '#3fb950',
                                            borderRadius: 3,
                                          }} />
                                        </div>
                                        <span style={{ fontSize: fontSize.micro, color: 'var(--text-secondary)' }}>{isFinite(progress) ? progress.toFixed(0) : 0}%</span>
                                      </div>
                                    ) : (
                                      <span style={{
                                        fontSize: fontSize.tiny, padding: '2px 6px', borderRadius: 3,
                                        background: 'rgba(139,148,158,0.15)',
                                        color: color.textSecondary,
                                      }}>{job.status}</span>
                                    )}
                                  </td>
                                  <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace', fontSize: fontSize.xs, color: 'var(--text-secondary)' }}>
                                    {job.status === 'active' ? timeUntil(job.end_date) : '—'}
                                  </td>
                                </tr>
                              );
                            })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    No industry data available.
                  </div>
                )}
              </div>
            )}

            {/* === IMPLANTS TAB === */}
            {activeTab === 'implants' && (
              <div>
                {implantsLoading ? (
                  <div className="skeleton" style={{ height: 400 }} />
                ) : implantData ? (
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    <h3 style={{ color: 'var(--text-primary)', fontSize: '0.9rem', margin: 0 }}>Attribute Enhancers (Slots 1-5)</h3>
                    {[1,2,3,4,5].map(slot => {
                      const imp = implantData?.implants?.find((i: any) => i.slot === slot);
                      return (
                        <div key={slot} style={{
                          padding: '0.5rem 0.75rem',
                          background: 'var(--bg-secondary)',
                          borderRadius: '6px',
                          border: '1px solid var(--border-color)',
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        }}>
                          <span style={{ color: imp ? 'var(--text-primary)' : 'var(--text-tertiary)', fontSize: '0.8rem' }}>
                            Slot {slot}: {imp ? imp.type_name : 'Empty'}
                          </span>
                          {imp && (
                            <span style={{ fontSize: '0.7rem', color: '#a855f7' }}>
                              {[
                                imp.perception_bonus ? `+${imp.perception_bonus} Per` : null,
                                imp.memory_bonus ? `+${imp.memory_bonus} Mem` : null,
                                imp.willpower_bonus ? `+${imp.willpower_bonus} Wil` : null,
                                imp.intelligence_bonus ? `+${imp.intelligence_bonus} Int` : null,
                                imp.charisma_bonus ? `+${imp.charisma_bonus} Cha` : null,
                              ].filter(Boolean).join(', ')}
                            </span>
                          )}
                        </div>
                      );
                    })}

                    <h3 style={{ color: 'var(--text-primary)', fontSize: '0.9rem', margin: '0.5rem 0 0 0' }}>Hardwirings (Slots 6-10)</h3>
                    {[6,7,8,9,10].map(slot => {
                      const imp = implantData?.implants?.find((i: any) => i.slot === slot);
                      return (
                        <div key={slot} style={{
                          padding: '0.5rem 0.75rem',
                          background: 'var(--bg-secondary)',
                          borderRadius: '6px',
                          border: `1px solid ${imp ? 'rgba(168,85,247,0.3)' : 'var(--border-color)'}`,
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        }}>
                          <span style={{ color: imp ? '#a855f7' : 'var(--text-tertiary)', fontSize: '0.8rem' }}>
                            Slot {slot}: {imp ? imp.type_name : 'Empty'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    No implant data available.
                  </div>
                )}
              </div>
            )}

            {/* === WEALTH TAB === */}
            {activeTab === 'wealth' && selectedId && <WealthDashboard characterId={selectedId} />}
            {activeTab === 'skillfarm' && <SkillfarmTab />}

            {/* === FLEET TAB === */}
            {activeTab === 'fleet' && selectedId && (
              <div>
                {fleetLoading ? (
                  <div className="skeleton" style={{ height: 400 }} />
                ) : fleetData ? (
                  <div>
                    {/* Fleet Summary Stats */}
                    <div style={{
                      display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: spacing.lg,
                      marginBottom: spacing["2xl"],
                    }}>
                      {[
                        { label: 'Total Ops', value: (fleetData.total_ops ?? 0).toString(), color: '#e05d44' },
                        { label: 'Avg PAP%', value: fleetData.avg_participation_pct != null ? `${fleetData.avg_participation_pct.toFixed(1)}%` : '—', color: '#00d4ff' },
                        { label: 'Snapshots', value: (fleetData.total_snapshots ?? 0).toString(), color: 'var(--text-primary)' },
                        { label: 'Last Fleet', value: fleetData.last_fleet_date ? new Date(fleetData.last_fleet_date).toLocaleDateString() : '—', color: '#d29922' },
                      ].map(stat => (
                        <div key={stat.label} style={{
                          padding: '0.75rem 1rem',
                          background: 'var(--bg-secondary)',
                          border: '1px solid var(--border-color)',
                          borderRadius: 8,
                        }}>
                          <div style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: spacing.sm }}>{stat.label}</div>
                          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: stat.color, fontFamily: 'monospace' }}>{stat.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Top Ships */}
                    {fleetData.ships_flown && fleetData.ships_flown.length > 0 && (
                      <div style={{
                        padding: spacing.xl,
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 8, marginBottom: spacing.xl,
                      }}>
                        <div style={{ fontSize: fontSize.xs, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: spacing.lg }}>
                          Top Ships Flown
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          {fleetData.ships_flown.slice(0, 10).map((ship: any) => {
                            const maxCount = fleetData.ships_flown[0]?.count ?? 1;
                            const pct = maxCount > 0 ? (ship.count / maxCount) * 100 : 0;
                            return (
                              <div key={ship.ship_type_id} style={{
                                display: 'flex', alignItems: 'center', gap: spacing.md,
                                padding: '6px 8px',
                                borderBottom: '1px solid rgba(255,255,255,0.03)',
                              }}>
                                <img
                                  src={`https://images.evetech.net/types/${ship.ship_type_id}/icon?size=32`}
                                  alt={ship.ship_name}
                                  style={{ width: 28, height: 28, borderRadius: 4, flexShrink: 0 }}
                                />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{ fontSize: fontSize.sm, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {ship.ship_name}
                                  </div>
                                </div>
                                <div style={{ width: 120, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden', flexShrink: 0 }}>
                                  <div style={{ width: `${pct}%`, height: '100%', background: '#e05d44', borderRadius: 3 }} />
                                </div>
                                <span style={{ fontSize: fontSize.tiny, fontFamily: 'monospace', color: '#e05d44', fontWeight: 600, minWidth: 30, textAlign: 'right' }}>
                                  {ship.count}x
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Recent Ops */}
                    {fleetData.recent_ops && fleetData.recent_ops.length > 0 && (
                      <div style={{
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 8, overflow: 'hidden', marginBottom: spacing.xl,
                      }}>
                        <div style={{ fontSize: fontSize.xs, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-color)' }}>
                          Recent Operations
                        </div>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: fontSize.sm }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                              <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Fleet</th>
                              <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>FC</th>
                              <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Ship</th>
                              <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>PAP%</th>
                              <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Duration</th>
                              <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Date</th>
                            </tr>
                          </thead>
                          <tbody>
                            {fleetData.recent_ops.map((op: any) => (
                              <tr key={op.op_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                <td style={{ padding: '6px 12px', fontWeight: 600, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {op.fleet_name}
                                </td>
                                <td style={{ padding: '6px 12px', color: 'var(--text-secondary)' }}>{op.fc_name || '—'}</td>
                                <td style={{ padding: '6px 12px' }}>{op.ship_name || '—'}</td>
                                <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace' }}>
                                  <span style={{
                                    color: (op.participation_pct ?? 0) >= 80 ? '#3fb950' : (op.participation_pct ?? 0) >= 50 ? '#d29922' : '#f85149',
                                    fontWeight: 600,
                                  }}>
                                    {op.participation_pct != null ? `${op.participation_pct.toFixed(0)}%` : '—'}
                                  </span>
                                </td>
                                <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                                  {op.duration_minutes != null ? formatFleetDuration(op.duration_minutes) : '—'}
                                </td>
                                <td style={{ padding: '6px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)', fontSize: fontSize.tiny }}>
                                  {op.date ? new Date(op.date).toLocaleDateString() : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Monthly Activity */}
                    {fleetData.monthly_breakdown && fleetData.monthly_breakdown.length > 0 && (
                      <div style={{
                        padding: spacing.xl,
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 8,
                      }}>
                        <div style={{ fontSize: fontSize.xs, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: spacing.lg }}>
                          Monthly Activity
                        </div>
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 120 }}>
                          {fleetData.monthly_breakdown.map((m: any) => {
                            const maxOps = Math.max(...fleetData.monthly_breakdown.map((x: any) => x.ops ?? 0), 1);
                            const barH = maxOps > 0 ? ((m.ops ?? 0) / maxOps) * 100 : 0;
                            return (
                              <div key={m.month} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                                <span style={{ fontSize: '0.6rem', color: '#e05d44', fontWeight: 600, fontFamily: 'monospace' }}>
                                  {m.ops ?? 0}
                                </span>
                                <div style={{
                                  width: '100%', maxWidth: 40,
                                  height: `${Math.max(barH, 4)}%`,
                                  background: 'linear-gradient(to top, rgba(224,93,68,0.6), rgba(224,93,68,0.25))',
                                  borderRadius: '3px 3px 0 0',
                                  border: '1px solid rgba(224,93,68,0.4)',
                                  position: 'relative',
                                }}>
                                  {m.avg_pap != null && (
                                    <div style={{
                                      position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)',
                                      fontSize: '0.55rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap',
                                    }}>
                                      {m.avg_pap.toFixed(0)}%
                                    </div>
                                  )}
                                </div>
                                <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                                  {m.month}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: spacing.xl, marginTop: spacing.lg }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                            <div style={{ width: 10, height: 10, background: 'rgba(224,93,68,0.5)', borderRadius: 2 }} />
                            <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)' }}>Ops Count</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                            <span style={{ fontSize: fontSize.tiny, color: 'var(--text-secondary)' }}>Numbers above bars = Avg PAP%</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Empty state for no ops */}
                    {(!fleetData.recent_ops || fleetData.recent_ops.length === 0) && (!fleetData.ships_flown || fleetData.ships_flown.length === 0) && (
                      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                        No fleet operations recorded yet for this pilot.
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    No fleet activity data available.
                  </div>
                )}
              </div>
            )}

            {activeTab === 'mail' && selectedId && <MailTab characterId={selectedId} />}
          </>
        )}
      </div>
    </ModuleGate>
  );
}
