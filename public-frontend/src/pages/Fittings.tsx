import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ModuleGate } from '../components/ModuleGate';
import { useAuth } from '../hooks/useAuth';
import { fittingApi } from '../services/api/fittings';
import { ImportDialog } from '../components/fittings/ImportDialog';
import type { ESIFitting, CustomFitting } from '../types/fittings';
import { getShipRenderUrl, SHIP_CLASSES } from '../types/fittings';

type TabType = 'my' | 'shared';

export function Fittings() {
  const { account } = useAuth();
  const [tab, setTab] = useState<TabType>('my');
  const [search, setSearch] = useState('');
  const [shipClass, setShipClass] = useState<string | null>(null);
  const [myFittings, setMyFittings] = useState<ESIFitting[]>([]);
  const [sharedFittings, setSharedFittings] = useState<CustomFitting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);

  // Fetch My Fits on mount
  useEffect(() => {
    if (!account?.primary_character_id) return;
    setLoading(true);
    setError(null);
    fittingApi
      .getCharacterFittings(account.primary_character_id)
      .then((data) => {
        setMyFittings(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load fittings');
        setLoading(false);
      });
  }, [account]);

  // Fetch Shared Fits when tab changes or search updates
  useEffect(() => {
    if (tab !== 'shared') return;
    setLoading(true);
    setError(null);
    fittingApi
      .getSharedFittings({ search: search.trim() || undefined })
      .then((data) => {
        setSharedFittings(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load shared fittings');
        setLoading(false);
      });
  }, [tab, search]);

  // Client-side filtering
  const filteredFittings = tab === 'my'
    ? myFittings.filter((f) => {
        const matchesSearch = !search || f.name.toLowerCase().includes(search.toLowerCase());
        return matchesSearch;
      })
    : sharedFittings.filter((f) => {
        const matchesSearch = !search || f.name.toLowerCase().includes(search.toLowerCase());
        const matchesClass = !shipClass || f.ship_name?.toLowerCase().includes(shipClass.toLowerCase());
        return matchesSearch && matchesClass;
      });

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Hero Section */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
          Fitting System
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0 0 1rem 0' }}>
          Browse, create, and share ship fittings
        </p>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link
            to="/fittings/new"
            style={{
              textDecoration: 'none',
              padding: '0.5rem 1rem',
              background: '#00d4ff',
              color: '#0d1117',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            New Fitting
          </Link>
          <button
            onClick={() => setShowImport(true)}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Import EFT
          </button>
        </div>
      </div>

      <ModuleGate module="character_suite" preview={true}>
        {/* Tab Toggles */}
        <div
          style={{
            display: 'flex',
            gap: '0.25rem',
            marginBottom: '1rem',
            borderBottom: '1px solid var(--border-color)',
            paddingBottom: '0.5rem',
          }}
        >
          <button
            onClick={() => setTab('my')}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: tab === 'my' ? '2px solid #00d4ff' : '2px solid transparent',
              color: tab === 'my' ? '#00d4ff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: tab === 'my' ? 600 : 400,
            }}
          >
            My Fits
          </button>
          <button
            onClick={() => setTab('shared')}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: tab === 'shared' ? '2px solid #00d4ff' : '2px solid transparent',
              color: tab === 'shared' ? '#00d4ff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: tab === 'shared' ? 600 : 400,
            }}
          >
            Shared Fits
          </button>
        </div>

        {/* Search Bar */}
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search fittings by name..."
            style={{
              width: '100%',
              padding: '12px 16px',
              fontSize: '1rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Ship Class Filter */}
        {tab === 'shared' && (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.5rem',
              marginBottom: '1rem',
            }}
          >
            <button
              onClick={() => setShipClass(null)}
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                borderRadius: '4px',
                cursor: 'pointer',
                background: !shipClass ? 'rgba(0,212,255,0.15)' : 'transparent',
                border: !shipClass ? '1px solid rgba(0,212,255,0.4)' : '1px solid var(--border-color)',
                color: !shipClass ? '#00d4ff' : 'var(--text-secondary)',
              }}
            >
              All
            </button>
            {SHIP_CLASSES.map((cls) => (
              <button
                key={cls}
                onClick={() => setShipClass(cls)}
                style={{
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  background: shipClass === cls ? 'rgba(0,212,255,0.15)' : 'transparent',
                  border: shipClass === cls ? '1px solid rgba(0,212,255,0.4)' : '1px solid var(--border-color)',
                  color: shipClass === cls ? '#00d4ff' : 'var(--text-secondary)',
                }}
              >
                {cls}
              </button>
            ))}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading fittings...
          </div>
        )}

        {/* Error State */}
        {error && (
          <div
            style={{
              padding: '1rem',
              background: 'rgba(248, 81, 73, 0.1)',
              border: '1px solid #f85149',
              borderRadius: '8px',
              color: '#f85149',
              fontSize: '0.85rem',
            }}
          >
            {error}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredFittings.length === 0 && (
          <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>No fittings found</p>
            {tab === 'my' && (
              <p style={{ fontSize: '0.85rem' }}>
                Create your first fitting or import from EFT format
              </p>
            )}
          </div>
        )}

        {/* Fitting Cards Grid */}
        {!loading && !error && filteredFittings.length > 0 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '1rem',
            }}
          >
            {filteredFittings.map((fitting) => {
              const isCustom = 'creator_character_id' in fitting;
              const fittingId = isCustom ? (fitting as CustomFitting).id : (fitting as ESIFitting).fitting_id;
              const shipTypeId = fitting.ship_type_id;
              const linkPath = isCustom
                ? `/fittings/custom/${fittingId}`
                : `/fittings/esi/${fittingId}?ship=${shipTypeId}`;

              return (
                <Link
                  key={`${isCustom ? 'custom' : 'esi'}-${fittingId}`}
                  to={linkPath}
                  style={{
                    textDecoration: 'none',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.75rem',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-secondary)')}
                >
                  {/* Ship Render */}
                  <img
                    src={getShipRenderUrl(shipTypeId, 128)}
                    alt=""
                    style={{
                      width: '100%',
                      height: 128,
                      objectFit: 'contain',
                      borderRadius: '4px',
                    }}
                  />

                  {/* Fitting Name */}
                  <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {fitting.name}
                  </div>

                  {/* Ship Name */}
                  {isCustom && (fitting as CustomFitting).ship_name && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {(fitting as CustomFitting).ship_name}
                    </div>
                  )}

                  {/* Tags */}
                  {isCustom && (fitting as CustomFitting).tags.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                      {(fitting as CustomFitting).tags.map((tag) => (
                        <span
                          key={tag}
                          style={{
                            padding: '2px 6px',
                            fontSize: '0.65rem',
                            background: 'rgba(0,212,255,0.1)',
                            border: '1px solid rgba(0,212,255,0.3)',
                            borderRadius: '3px',
                            color: '#00d4ff',
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Slot Counts */}
                  <div
                    style={{
                      display: 'flex',
                      gap: '0.5rem',
                      fontSize: '0.7rem',
                      color: 'var(--text-tertiary)',
                    }}
                  >
                    <span>
                      H: {fitting.items.filter((i) => i.flag >= 27 && i.flag <= 34).length}
                    </span>
                    <span>
                      M: {fitting.items.filter((i) => i.flag >= 19 && i.flag <= 26).length}
                    </span>
                    <span>
                      L: {fitting.items.filter((i) => i.flag >= 11 && i.flag <= 18).length}
                    </span>
                    <span>
                      R: {fitting.items.filter((i) => i.flag >= 92 && i.flag <= 99).length}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </ModuleGate>

      {/* Import Dialog */}
      <ImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  );
}
