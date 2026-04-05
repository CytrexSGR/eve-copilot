import { useState } from 'react';
import { localScanApi } from '../../services/api/military';
import type { LocalScanResult, LocalPilot } from '../../types/military';
import { THREAT_COLORS } from '../../types/military';

const THREAT_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  unknown: 4,
};

interface GroupEntry {
  name: string;
  count: number;
}

export function LocalScan() {
  const [rawText, setRawText] = useState('');
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LocalScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAllAlliances, setShowAllAlliances] = useState(false);
  const [showAllCorps, setShowAllCorps] = useState(false);

  const pilotCount = rawText.split('\n').filter((l) => l.trim()).length;

  async function handleAnalyze() {
    if (!rawText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await localScanApi.analyze(rawText, days);
      setResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Analysis failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setRawText('');
    setResult(null);
    setError(null);
    setShowAllAlliances(false);
    setShowAllCorps(false);
  }

  const sortedPilots = result
    ? [...result.pilots].sort(
        (a, b) => (THREAT_ORDER[a.threatLevel] ?? 99) - (THREAT_ORDER[b.threatLevel] ?? 99),
      )
    : [];

  // --- Threat Summary color ---
  function summaryColor(): string {
    if (!result) return 'var(--border-color)';
    if (result.redListed > 0) return '#f85149';
    if (result.hostiles > 0) return '#d29922';
    return '#3fb950';
  }

  // --- Group breakdown helpers ---
  function buildAllianceBreakdown(): GroupEntry[] {
    if (!result) return [];
    return result.allianceBreakdown
      .map((g) => ({ name: g.allianceName ?? 'Unknown', count: g.count }))
      .sort((a, b) => b.count - a.count);
  }

  function buildCorpBreakdown(): GroupEntry[] {
    if (!result) return [];
    return result.corporationBreakdown
      .map((g) => ({ name: g.corporationName ?? 'Unknown', count: g.count }))
      .sort((a, b) => b.count - a.count);
  }

  const allianceEntries = buildAllianceBreakdown();
  const corpEntries = buildCorpBreakdown();
  const maxAllianceCount = allianceEntries[0]?.count ?? 1;
  const maxCorpCount = corpEntries[0]?.count ?? 1;

  // --- Render ---
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Paste Area */}
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 16 }}>
        <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>
          Local Chat Members
        </label>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Paste local chat members here (one per line)..."
          style={{
            width: '100%',
            minHeight: 150,
            background: 'var(--bg-primary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 6,
            padding: 12,
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            resize: 'vertical',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />

        {/* Options Row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10 }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Days:
            <input
              type="number"
              min={1}
              max={90}
              value={days}
              onChange={(e) => setDays(Math.max(1, Math.min(90, Number(e.target.value))))}
              style={{
                width: 56,
                marginLeft: 6,
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '4px 8px',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
          </label>

          <button
            onClick={handleAnalyze}
            disabled={loading || !rawText.trim()}
            style={{
              background: '#238636',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              padding: '6px 18px',
              fontSize: '0.85rem',
              cursor: loading || !rawText.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !rawText.trim() ? 0.5 : 1,
            }}
          >
            Analyze
          </button>

          <button
            onClick={handleClear}
            style={{
              background: 'transparent',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>

          {rawText.trim() && (
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
              {pilotCount} pilot{pilotCount !== 1 ? 's' : ''} detected
            </span>
          )}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 24, fontSize: '0.85rem' }}>
          Analyzing {pilotCount} pilots...
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: 'rgba(248, 81, 73, 0.1)', border: '1px solid #f85149', borderRadius: 8, padding: 12, color: '#f85149', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Threat Summary Banner */}
          <div
            style={{
              background: summaryColor(),
              borderRadius: 8,
              padding: '12px 18px',
              display: 'flex',
              gap: 24,
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            {[
              { label: 'Total', value: result.totalPilots },
              { label: 'Identified', value: result.identified },
              { label: 'Unidentified', value: result.unidentified },
              { label: 'Red-Listed', value: result.redListed },
              { label: 'Hostiles', value: result.hostiles },
            ].map((s) => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: 'monospace', fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                  {s.value}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.85)' }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Threat Breakdown Cards */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {(['critical', 'high', 'medium', 'low', 'unknown'] as const).map((level) => {
              const count = result.threatBreakdown[level];
              const color = THREAT_COLORS[level];
              return (
                <div
                  key={level}
                  style={{
                    flex: '1 1 100px',
                    minWidth: 100,
                    background: 'var(--bg-secondary)',
                    border: `1px solid ${color}`,
                    borderRadius: 8,
                    padding: '10px 14px',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontFamily: 'monospace', fontSize: '1.2rem', fontWeight: 700, color }}>
                    {count}
                  </div>
                  <div style={{ fontSize: '0.7rem', color, textTransform: 'capitalize' }}>{level}</div>
                </div>
              );
            })}
          </div>

          {/* Alliance Breakdown */}
          {allianceEntries.length > 0 && (
            <BreakdownSection
              title="Alliance Breakdown"
              entries={allianceEntries}
              maxCount={maxAllianceCount}
              showAll={showAllAlliances}
              onToggle={() => setShowAllAlliances((v) => !v)}
            />
          )}

          {/* Corporation Breakdown */}
          {corpEntries.length > 0 && (
            <BreakdownSection
              title="Corporation Breakdown"
              entries={corpEntries}
              maxCount={maxCorpCount}
              showAll={showAllCorps}
              onToggle={() => setShowAllCorps((v) => !v)}
            />
          )}

          {/* Pilot List */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Pilot List ({sortedPilots.length})
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    {['Character Name', 'Corp', 'Alliance', 'Threat', 'Kills', 'Losses', 'Last Ship', 'Red List'].map(
                      (h) => (
                        <th
                          key={h}
                          style={{
                            padding: '8px 10px',
                            textAlign: 'left',
                            fontSize: '0.7rem',
                            color: 'var(--text-secondary)',
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {sortedPilots.map((pilot, idx) => (
                    <PilotRow key={pilot.characterId} pilot={pilot} idx={idx} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// --- Breakdown Section ---
function BreakdownSection({
  title,
  entries,
  maxCount,
  showAll,
  onToggle,
}: {
  title: string;
  entries: GroupEntry[];
  maxCount: number;
  showAll: boolean;
  onToggle: () => void;
}) {
  const visible = showAll ? entries : entries.slice(0, 10);
  const hasMore = entries.length > 10;

  return (
    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 16 }}>
      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 10 }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {visible.map((entry) => {
          const pct = maxCount > 0 ? (entry.count / maxCount) * 100 : 0;
          return (
            <div key={entry.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 140,
                  fontSize: '0.85rem',
                  color: 'var(--text-primary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
                title={entry.name}
              >
                {entry.name}
              </div>
              <div style={{ flex: 1, height: 16, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                <div
                  style={{
                    width: `${pct}%`,
                    height: '100%',
                    background: 'rgba(88, 166, 255, 0.35)',
                    borderRadius: 4,
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
              <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)', minWidth: 32, textAlign: 'right' }}>
                {entry.count}
              </div>
            </div>
          );
        })}
      </div>
      {hasMore && (
        <button
          onClick={onToggle}
          style={{
            marginTop: 8,
            background: 'transparent',
            border: 'none',
            color: '#58a6ff',
            fontSize: '0.7rem',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          {showAll ? 'Show less' : `Show ${entries.length - 10} more`}
        </button>
      )}
    </div>
  );
}

// --- Pilot Row ---
function PilotRow({ pilot, idx }: { pilot: LocalPilot; idx: number }) {
  const isRedListed = pilot.isRedListed;
  const threatColor = THREAT_COLORS[pilot.threatLevel] ?? THREAT_COLORS.unknown;

  const rowBg = isRedListed
    ? 'rgba(248, 81, 73, 0.08)'
    : idx % 2 === 0
      ? 'transparent'
      : 'rgba(255, 255, 255, 0.02)';

  return (
    <tr
      style={{ background: rowBg, borderBottom: '1px solid var(--border-color)' }}
      onMouseEnter={(e) => { (e.currentTarget.style.background = 'rgba(255,255,255,0.05)'); }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = isRedListed
          ? 'rgba(248, 81, 73, 0.08)'
          : idx % 2 === 0
            ? 'transparent'
            : 'rgba(255, 255, 255, 0.02)';
      }}
    >
      {/* Character Name */}
      <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
        <a
          href={`https://evewho.com/character/${pilot.characterId}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#58a6ff', textDecoration: 'none' }}
        >
          {pilot.characterName}
        </a>
      </td>

      {/* Corp */}
      <td style={{ padding: '7px 10px', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
        {pilot.corporationName}
      </td>

      {/* Alliance */}
      <td style={{ padding: '7px 10px', whiteSpace: 'nowrap', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
        {pilot.allianceName ?? '\u2014'}
      </td>

      {/* Threat */}
      <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
        <span
          style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: 4,
            fontSize: '0.7rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            color: threatColor,
            background: `${threatColor}22`,
            border: `1px solid ${threatColor}44`,
          }}
        >
          {pilot.threatLevel}
        </span>
      </td>

      {/* Kills */}
      <td style={{ padding: '7px 10px', fontFamily: 'monospace', color: '#3fb950', textAlign: 'right' }}>
        {pilot.recentKills}
      </td>

      {/* Losses */}
      <td style={{ padding: '7px 10px', fontFamily: 'monospace', color: '#f85149', textAlign: 'right' }}>
        {pilot.recentLosses}
      </td>

      {/* Last Ship */}
      <td style={{ padding: '7px 10px', whiteSpace: 'nowrap', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
        {pilot.lastShipType ?? '\u2014'}
      </td>

      {/* Red List */}
      <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
        {isRedListed ? (
          <span
            style={{
              display: 'inline-block',
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: '0.7rem',
              fontWeight: 600,
              color: '#f85149',
              background: 'rgba(248, 81, 73, 0.15)',
              border: '1px solid rgba(248, 81, 73, 0.3)',
            }}
            title={pilot.redListReason ?? undefined}
          >
            {pilot.redListReason ?? 'RED'}
          </span>
        ) : (
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>{'\u2014'}</span>
        )}
      </td>
    </tr>
  );
}
