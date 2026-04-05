import { useState, useEffect } from 'react';
import { doctrineApi } from '../../services/api/srp';
import type { Doctrine, DoctrineImportEft, DoctrineCategory } from '../../types/srp';
import { formatIsk, DOCTRINE_CATEGORIES, CATEGORY_LABELS, CATEGORY_COLORS } from '../../types/srp';
import { DoctrineStatsPanel } from './DoctrineStatsPanel';
import { DoctrineReadinessPanel } from './DoctrineReadinessPanel';
import { DoctrineBomPanel } from './DoctrineBomPanel';
import { FleetReadinessPanel } from './FleetReadinessPanel';
import { DoctrineChangelogPanel } from './DoctrineChangelogPanel';
import DoctrineEditDialog from './DoctrineEditDialog';
import { useAuth } from '../../hooks/useAuth';
import { fittingApi } from '../../services/api/fittings';
import type { ESIFitting, CustomFitting } from '../../types/fittings';
import type { DoctrineImportFitting } from '../../types/srp';

type DoctrineSubTab = 'fitting' | 'readiness' | 'bom' | 'fleet_readiness' | 'changelog';
type ImportMode = 'eft' | 'dna' | 'fitting';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
};

const SLOT_LABELS: Record<string, string> = {
  high: 'High', med: 'Mid', low: 'Low', rig: 'Rig', drones: 'Drones',
};

const SLOT_COLORS: Record<string, string> = {
  high: '#f85149', med: '#00d4ff', low: '#3fb950', rig: '#d29922', drones: '#a855f7',
};

export function DoctrinesTab({ corpId }: { corpId: number }) {
  const [doctrines, setDoctrines] = useState<Doctrine[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [importMode, setImportMode] = useState<ImportMode>('eft');
  const [eftText, setEftText] = useState('');
  const [basePayout, setBasePayout] = useState('');
  const [importCategory, setImportCategory] = useState<DoctrineCategory>('general');
  const [importing, setImporting] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [subTab, setSubTab] = useState<DoctrineSubTab>('fitting');
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null);
  const [editingDoctrine, setEditingDoctrine] = useState<Doctrine | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<DoctrineCategory | 'all'>('all');
  const [dnaString, setDnaString] = useState('');
  const [dnaName, setDnaName] = useState('');
  const [dnaBasePayout, setDnaBasePayout] = useState('');
  // From Fitting state
  const [esiFittings, setEsiFittings] = useState<ESIFitting[]>([]);
  const [customFittings, setCustomFittings] = useState<CustomFitting[]>([]);
  const [fittingSource, setFittingSource] = useState<'esi' | 'custom'>('esi');
  const [loadingFittings, setLoadingFittings] = useState(false);
  const [selectedFitting, setSelectedFitting] = useState<ESIFitting | CustomFitting | null>(null);
  const [fittingName, setFittingName] = useState('');
  const [fittingBasePayout, setFittingBasePayout] = useState('');
  const [fittingCategory, setFittingCategory] = useState<DoctrineCategory>('general');
  const [fittingSearch, setFittingSearch] = useState('');
  const { account } = useAuth();
  const characters = account?.characters || [];
  const effectiveCharId = selectedCharId ?? account?.primary_character_id ?? 0;

  const loadFittings = async (charId: number) => {
    setLoadingFittings(true);
    try {
      const [esi, custom] = await Promise.all([
        fittingApi.getCharacterFittings(charId).catch(() => [] as ESIFitting[]),
        fittingApi.getCustomFittings(charId).catch(() => [] as CustomFitting[]),
      ]);
      setEsiFittings(esi);
      setCustomFittings(custom);
    } catch (err) {
      console.error('Failed to load fittings:', err);
    } finally {
      setLoadingFittings(false);
    }
  };

  const handleSelectFitting = (fit: ESIFitting | CustomFitting) => {
    setSelectedFitting(fit);
    setFittingName(fit.name);
  };

  const handleFittingImport = async () => {
    if (!selectedFitting || !fittingName.trim()) return;
    setImporting(true);
    try {
      const importData: DoctrineImportFitting = {
        name: fittingName.trim(),
        ship_type_id: selectedFitting.ship_type_id,
        items: selectedFitting.items.map(i => ({ type_id: i.type_id, flag: i.flag, quantity: i.quantity })),
        base_payout: fittingBasePayout ? Number(fittingBasePayout) : undefined,
        category: fittingCategory,
        corporation_id: corpId,
      };
      await doctrineApi.importFromFitting(importData);
      setSelectedFitting(null);
      setFittingName('');
      setFittingBasePayout('');
      setFittingCategory('general');
      setShowImport(false);
      await loadDoctrines();
    } catch (err) {
      console.error('Failed to import doctrine from fitting:', err);
    } finally {
      setImporting(false);
    }
  };

  const filteredFittingList = (fittingSource === 'esi' ? esiFittings : customFittings)
    .filter(f => !fittingSearch || f.name.toLowerCase().includes(fittingSearch.toLowerCase()));

  const loadDoctrines = async () => {
    setLoading(true);
    try {
      const res = await doctrineApi.list(corpId, !showInactive);
      setDoctrines(res.doctrines);
    } catch (err) {
      console.error('Failed to load doctrines:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadDoctrines(); }, [corpId, showInactive]);

  const filteredDoctrines = categoryFilter === 'all'
    ? doctrines
    : doctrines.filter(d => (d.category || 'general') === categoryFilter);

  const handleImport = async () => {
    if (!eftText.trim()) return;
    setImporting(true);
    try {
      const req: DoctrineImportEft = {
        corporation_id: corpId,
        eft_text: eftText,
        base_payout: basePayout ? Number(basePayout) : undefined,
        category: importCategory,
      };
      await doctrineApi.importEft(req);
      setEftText('');
      setBasePayout('');
      setImportCategory('general');
      setShowImport(false);
      await loadDoctrines();
    } catch (err) {
      console.error('Failed to import doctrine:', err);
    } finally {
      setImporting(false);
    }
  };

  const handleDnaImport = async () => {
    if (!dnaString.trim() || !dnaName.trim()) return;
    setImporting(true);
    try {
      await doctrineApi.importDna(
        corpId,
        dnaString.trim(),
        dnaName.trim(),
        dnaBasePayout ? Number(dnaBasePayout) : undefined,
      );
      setDnaString('');
      setDnaName('');
      setDnaBasePayout('');
      setShowImport(false);
      await loadDoctrines();
    } catch (err) {
      console.error('Failed to import DNA doctrine:', err);
    } finally {
      setImporting(false);
    }
  };

  const handleArchive = async (id: number) => {
    try {
      await doctrineApi.archive(id);
      await loadDoctrines();
    } catch (err) {
      console.error('Failed to archive doctrine:', err);
    }
  };

  const handleClone = async (doc: Doctrine) => {
    try {
      await doctrineApi.clone(doc.id, doc.name + ' (Copy)', doc.category);
      await loadDoctrines();
    } catch (err) {
      console.error('Failed to clone doctrine:', err);
    }
  };

  const SUB_TAB_LABELS: Record<DoctrineSubTab, string> = {
    fitting: 'Fitting',
    readiness: 'Readiness',
    bom: 'Fleet BOM',
    fleet_readiness: 'Fleet Readiness',
    changelog: 'Changelog',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Controls */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', padding: '0.75rem 1rem',
        display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap',
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>
          <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)}
            style={{ accentColor: '#00d4ff' }} />
          Show Inactive
        </label>

        {/* Category filter */}
        <select
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value as DoctrineCategory | 'all')}
          style={{
            background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
            borderRadius: '4px', color: '#fff', padding: '0.3rem 0.5rem',
            fontSize: '0.75rem', outline: 'none', cursor: 'pointer',
          }}
        >
          <option value="all">All Categories</option>
          {DOCTRINE_CATEGORIES.map(cat => (
            <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
          ))}
        </select>

        <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)' }}>{filteredDoctrines.length} doctrines</div>
        <div style={{ flex: 1 }} />
        <button onClick={() => setShowImport(!showImport)} style={{
          background: showImport ? 'rgba(255,255,255,0.05)' : 'rgba(0,212,255,0.15)',
          border: '1px solid rgba(0,212,255,0.3)', borderRadius: '6px',
          color: '#00d4ff', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
        }}>
          {showImport ? 'Cancel' : 'Import Doctrine'}
        </button>
      </div>

      {/* Import form */}
      {showImport && (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '1rem',
        }}>
          {/* Import mode toggle */}
          <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.75rem' }}>
            {(['eft', 'dna', 'fitting'] as ImportMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => {
                  setImportMode(mode);
                  if (mode === 'fitting' && effectiveCharId > 0 && esiFittings.length === 0) {
                    loadFittings(effectiveCharId);
                  }
                }}
                style={{
                  background: importMode === mode ? 'rgba(0,212,255,0.15)' : 'transparent',
                  border: `1px solid ${importMode === mode ? 'rgba(0,212,255,0.4)' : 'rgba(255,255,255,0.1)'}`,
                  borderRadius: '4px', padding: '0.3rem 0.75rem',
                  fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                  color: importMode === mode ? '#00d4ff' : 'rgba(255,255,255,0.5)',
                  transition: 'all 0.15s ease',
                }}
              >
                {mode === 'eft' ? 'EFT Format' : mode === 'dna' ? 'DNA String' : 'From Fitting'}
              </button>
            ))}
          </div>

          {importMode === 'eft' ? (
            <>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                Paste EFT Fitting
              </div>
              <textarea
                value={eftText}
                onChange={e => setEftText(e.target.value)}
                placeholder="[Ship Name, Fitting Name]\nModule 1\nModule 2\n..."
                style={{
                  width: '100%', minHeight: '120px', background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-color)', borderRadius: '4px',
                  color: '#fff', padding: '0.6rem', fontSize: '0.8rem', fontFamily: 'monospace',
                  resize: 'vertical', outline: 'none',
                }}
              />
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Base Payout (ISK)</label>
                  <input type="number" value={basePayout} onChange={e => setBasePayout(e.target.value)}
                    placeholder="Optional"
                    style={{
                      background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                      borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                      fontSize: '0.8rem', fontFamily: 'monospace', outline: 'none', width: '180px',
                    }} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Category</label>
                  <select
                    value={importCategory}
                    onChange={e => setImportCategory(e.target.value as DoctrineCategory)}
                    style={{
                      background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                      borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                      fontSize: '0.8rem', outline: 'none', cursor: 'pointer',
                    }}
                  >
                    {DOCTRINE_CATEGORIES.map(cat => (
                      <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1 }} />
                <button onClick={handleImport} disabled={importing || !eftText.trim()} style={{
                  background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
                  borderRadius: '6px', color: '#3fb950', padding: '0.5rem 1.25rem',
                  fontSize: '0.85rem', fontWeight: 600,
                  cursor: importing || !eftText.trim() ? 'not-allowed' : 'pointer',
                  opacity: importing || !eftText.trim() ? 0.5 : 1,
                }}>
                  {importing ? 'Importing...' : 'Import'}
                </button>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                DNA String Import
              </div>
              <input
                type="text"
                value={dnaString}
                onChange={e => setDnaString(e.target.value)}
                placeholder="e.g. 24690:2048;1:3170;3:..."
                style={{
                  width: '100%', background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-color)', borderRadius: '4px',
                  color: '#fff', padding: '0.6rem', fontSize: '0.8rem', fontFamily: 'monospace',
                  outline: 'none',
                }}
              />
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Name</label>
                  <input
                    type="text"
                    value={dnaName}
                    onChange={e => setDnaName(e.target.value)}
                    placeholder="Doctrine name"
                    style={{
                      background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                      borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                      fontSize: '0.8rem', outline: 'none', width: '200px',
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Base Payout (ISK)</label>
                  <input
                    type="number"
                    value={dnaBasePayout}
                    onChange={e => setDnaBasePayout(e.target.value)}
                    placeholder="Optional"
                    style={{
                      background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                      borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                      fontSize: '0.8rem', fontFamily: 'monospace', outline: 'none', width: '180px',
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Category</label>
                  <select
                    value={importCategory}
                    onChange={e => setImportCategory(e.target.value as DoctrineCategory)}
                    style={{
                      background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                      borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                      fontSize: '0.8rem', outline: 'none', cursor: 'pointer',
                    }}
                  >
                    {DOCTRINE_CATEGORIES.map(cat => (
                      <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1 }} />
                <button
                  onClick={handleDnaImport}
                  disabled={importing || !dnaString.trim() || !dnaName.trim()}
                  style={{
                    background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
                    borderRadius: '6px', color: '#3fb950', padding: '0.5rem 1.25rem',
                    fontSize: '0.85rem', fontWeight: 600,
                    cursor: importing || !dnaString.trim() || !dnaName.trim() ? 'not-allowed' : 'pointer',
                    opacity: importing || !dnaString.trim() || !dnaName.trim() ? 0.5 : 1,
                  }}
                >
                  {importing ? 'Importing...' : 'Import DNA'}
                </button>
              </div>
            </>
          )}

          {importMode === 'fitting' && (
            <>
              {/* Character selector */}
              {characters.length > 0 && (
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                    Character
                  </div>
                  <select
                    value={effectiveCharId}
                    onChange={e => {
                      const cid = Number(e.target.value);
                      setSelectedCharId(cid);
                      setSelectedFitting(null);
                      loadFittings(cid);
                    }}
                    style={{
                      background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                      borderRadius: '4px', color: '#fff', padding: '0.3rem 0.5rem',
                      fontSize: '0.75rem', outline: 'none', cursor: 'pointer',
                    }}
                  >
                    {characters.map(c => (
                      <option key={c.character_id} value={c.character_id}>
                        {c.character_name}
                      </option>
                    ))}
                  </select>
                  {/* ESI / Custom toggle */}
                  <div style={{ display: 'flex', gap: '0.25rem', marginLeft: '0.5rem' }}>
                    {(['esi', 'custom'] as const).map(src => (
                      <button
                        key={src}
                        onClick={() => setFittingSource(src)}
                        style={{
                          background: fittingSource === src ? 'rgba(0,212,255,0.12)' : 'transparent',
                          border: `1px solid ${fittingSource === src ? 'rgba(0,212,255,0.35)' : 'rgba(255,255,255,0.08)'}`,
                          borderRadius: '4px', padding: '0.2rem 0.6rem',
                          fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer',
                          color: fittingSource === src ? '#00d4ff' : 'rgba(255,255,255,0.4)',
                        }}
                      >
                        {src === 'esi' ? 'ESI Fittings' : 'Custom Fittings'}
                      </button>
                    ))}
                  </div>
                  {/* Search */}
                  <input
                    type="text"
                    value={fittingSearch}
                    onChange={e => setFittingSearch(e.target.value)}
                    placeholder="Search fittings..."
                    style={{
                      marginLeft: 'auto', background: 'rgba(0,0,0,0.3)',
                      border: '1px solid var(--border-color)', borderRadius: '4px',
                      color: '#fff', padding: '0.3rem 0.6rem', fontSize: '0.75rem',
                      outline: 'none', width: '200px',
                    }}
                  />
                </div>
              )}

              {/* Fitting list */}
              <div style={{
                maxHeight: '240px', overflowY: 'auto', background: 'rgba(0,0,0,0.2)',
                border: '1px solid var(--border-color)', borderRadius: '4px',
                marginBottom: '0.75rem',
              }}>
                {loadingFittings ? (
                  <div style={{ padding: '1.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>
                    Loading fittings...
                  </div>
                ) : filteredFittingList.length === 0 ? (
                  <div style={{ padding: '1.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>
                    {effectiveCharId > 0 ? 'No fittings found' : 'Select a character to load fittings'}
                  </div>
                ) : (
                  filteredFittingList.map((fit, idx) => {
                    const isSelected = selectedFitting && (
                      ('fitting_id' in fit && 'fitting_id' in selectedFitting && fit.fitting_id === (selectedFitting as ESIFitting).fitting_id) ||
                      ('id' in fit && 'id' in selectedFitting && (fit as CustomFitting).id === (selectedFitting as CustomFitting).id)
                    );
                    return (
                      <div
                        key={'fitting_id' in fit ? `esi-${fit.fitting_id}` : `custom-${(fit as CustomFitting).id}`}
                        onClick={() => handleSelectFitting(fit)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '0.6rem',
                          padding: '0.4rem 0.6rem', cursor: 'pointer',
                          background: isSelected ? 'rgba(0,212,255,0.1)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                          borderBottom: '1px solid rgba(255,255,255,0.03)',
                          borderLeft: isSelected ? '2px solid #00d4ff' : '2px solid transparent',
                        }}
                      >
                        <img
                          src={`https://images.evetech.net/types/${fit.ship_type_id}/icon?size=32`}
                          alt=""
                          style={{ width: 32, height: 32, borderRadius: '3px' }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: isSelected ? '#00d4ff' : '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {fit.name}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
                            {'ship_name' in fit && (fit as CustomFitting).ship_name ? (fit as CustomFitting).ship_name : `Type ${fit.ship_type_id}`}
                            {' \u00b7 '}{fit.items.length} items
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Selected fitting details + import controls */}
              {selectedFitting && (
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Doctrine Name</label>
                    <input
                      type="text"
                      value={fittingName}
                      onChange={e => setFittingName(e.target.value)}
                      style={{
                        background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                        borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                        fontSize: '0.8rem', outline: 'none', width: '220px',
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Base Payout (ISK)</label>
                    <input
                      type="number"
                      value={fittingBasePayout}
                      onChange={e => setFittingBasePayout(e.target.value)}
                      placeholder="Optional"
                      style={{
                        background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                        borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                        fontSize: '0.8rem', fontFamily: 'monospace', outline: 'none', width: '180px',
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Category</label>
                    <select
                      value={fittingCategory}
                      onChange={e => setFittingCategory(e.target.value as DoctrineCategory)}
                      style={{
                        background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                        borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem',
                        fontSize: '0.8rem', outline: 'none', cursor: 'pointer',
                      }}
                    >
                      {DOCTRINE_CATEGORIES.map(cat => (
                        <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ flex: 1 }} />
                  <button
                    onClick={handleFittingImport}
                    disabled={importing || !fittingName.trim()}
                    style={{
                      background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
                      borderRadius: '6px', color: '#3fb950', padding: '0.5rem 1.25rem',
                      fontSize: '0.85rem', fontWeight: 600,
                      cursor: importing || !fittingName.trim() ? 'not-allowed' : 'pointer',
                      opacity: importing || !fittingName.trim() ? 0.5 : 1,
                    }}
                  >
                    {importing ? 'Importing...' : 'Import as Doctrine'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Doctrines list */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1.5fr 1fr 90px 100px 90px 110px',
          gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Name</span><span>Ship</span><span>Status</span>
          <span style={{ textAlign: 'right' }}>Base Payout</span><span>Created</span><span></span>
        </div>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
        ) : filteredDoctrines.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No doctrines found</div>
        ) : (
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {filteredDoctrines.map((doc, idx) => {
              const isExpanded = expandedId === doc.id;
              const docCategory = doc.category || 'general';
              return (
                <div key={doc.id}>
                  <div
                    onClick={() => {
                      if (!isExpanded) setSubTab('fitting');
                      setExpandedId(isExpanded ? null : doc.id);
                    }}
                    style={{
                      display: 'grid', gridTemplateColumns: '1.5fr 1fr 90px 100px 90px 110px',
                      gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem', cursor: 'pointer',
                      background: isExpanded ? 'rgba(255,255,255,0.04)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                      borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                    }}
                  >
                    <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {doc.name}
                      <span style={{
                        padding: '1px 6px', borderRadius: '3px', fontSize: '0.65rem', fontWeight: 600,
                        background: `${CATEGORY_COLORS[docCategory]}20`,
                        color: CATEGORY_COLORS[docCategory],
                        border: `1px solid ${CATEGORY_COLORS[docCategory]}40`,
                        whiteSpace: 'nowrap',
                      }}>
                        {CATEGORY_LABELS[docCategory]}
                      </span>
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.6)' }}>{doc.ship_name || `Type ${doc.ship_type_id}`}</span>
                    <span style={{
                      padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                      background: doc.is_active ? 'rgba(63,185,80,0.15)' : 'rgba(255,255,255,0.05)',
                      color: doc.is_active ? '#3fb950' : 'rgba(255,255,255,0.3)',
                      textAlign: 'center',
                    }}>{doc.is_active ? 'Active' : 'Inactive'}</span>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.78rem', color: '#3fb950' }}>
                      {doc.base_payout ? formatIsk(doc.base_payout) : '\u2014'}
                    </span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)' }}>
                      {formatDate(doc.created_at)}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                      {isExpanded ? 'Collapse' : 'Expand'}
                    </span>
                  </div>

                  {/* Expanded fitting */}
                  {isExpanded && (
                    <div style={{
                      padding: '1rem', background: 'rgba(0,0,0,0.15)',
                      borderBottom: '1px solid var(--border-color)',
                    }}>
                      <DoctrineStatsPanel doctrineId={doc.id} />

                      {/* Sub-tabs */}
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '0.25rem',
                        margin: '0.75rem 0 0.5rem',
                      }}>
                        {(['fitting', 'readiness', 'bom', 'fleet_readiness', 'changelog'] as DoctrineSubTab[]).map(tab => (
                          <button
                            key={tab}
                            onClick={() => setSubTab(tab)}
                            style={{
                              background: subTab === tab ? 'rgba(0,212,255,0.15)' : 'transparent',
                              border: `1px solid ${subTab === tab ? 'rgba(0,212,255,0.4)' : 'rgba(255,255,255,0.1)'}`,
                              borderRadius: '4px', padding: '0.3rem 0.75rem',
                              fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                              color: subTab === tab ? '#00d4ff' : 'rgba(255,255,255,0.5)',
                              transition: 'all 0.15s ease',
                            }}
                          >
                            {SUB_TAB_LABELS[tab]}
                          </button>
                        ))}
                        {subTab === 'readiness' && characters.length > 0 && (
                          <select
                            value={effectiveCharId}
                            onChange={e => setSelectedCharId(Number(e.target.value))}
                            style={{
                              marginLeft: 'auto',
                              background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                              borderRadius: '4px', color: '#fff', padding: '0.3rem 0.5rem',
                              fontSize: '0.75rem', outline: 'none', cursor: 'pointer',
                            }}
                          >
                            {characters.map(c => (
                              <option key={c.character_id} value={c.character_id}>
                                {c.character_name}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>

                      {/* Fitting tab */}
                      {subTab === 'fitting' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                          {(Object.keys(SLOT_LABELS) as Array<keyof typeof SLOT_LABELS>).map(slot => {
                            const items = doc.fitting_json?.[slot as keyof typeof doc.fitting_json];
                            if (!items || items.length === 0) return null;
                            return (
                              <div key={slot}>
                                <div style={{
                                  fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
                                  color: SLOT_COLORS[slot] || 'rgba(255,255,255,0.5)',
                                  marginBottom: '0.25rem',
                                }}>
                                  {SLOT_LABELS[slot]} ({items.length})
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                                  {items.map((item, i) => (
                                    <div key={i} style={{
                                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                      padding: '0.2rem 0.5rem', fontSize: '0.8rem',
                                      background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                                    }}>
                                      <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                                        {item.type_name || `Type ${item.type_id}`}
                                      </span>
                                      {item.quantity > 1 && (
                                        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
                                          x{item.quantity}
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Readiness tab */}
                      {subTab === 'readiness' && effectiveCharId > 0 && (
                        <DoctrineReadinessPanel doctrineId={doc.id} characterId={effectiveCharId} />
                      )}

                      {/* Fleet BOM tab */}
                      {subTab === 'bom' && (
                        <DoctrineBomPanel doctrineId={doc.id} />
                      )}

                      {/* Fleet Readiness tab */}
                      {subTab === 'fleet_readiness' && (
                        <FleetReadinessPanel doctrineId={doc.id} corpId={corpId} />
                      )}

                      {/* Changelog tab */}
                      {subTab === 'changelog' && (
                        <DoctrineChangelogPanel doctrineId={doc.id} />
                      )}

                      {/* Actions */}
                      <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.75rem', marginTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                        <button
                          onClick={e => { e.stopPropagation(); setEditingDoctrine(doc); }}
                          style={{
                            background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
                            borderRadius: '6px', color: '#00d4ff', padding: '0.4rem 1rem',
                            fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); handleClone(doc); }}
                          style={{
                            background: 'rgba(188,140,255,0.1)', border: '1px solid rgba(188,140,255,0.3)',
                            borderRadius: '6px', color: '#bc8cff', padding: '0.4rem 1rem',
                            fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                          }}
                        >
                          Clone
                        </button>
                        {doc.is_active && (
                          <button onClick={() => handleArchive(doc.id)} style={{
                            background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                            borderRadius: '6px', color: '#f85149', padding: '0.4rem 1rem',
                            fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                          }}>Archive</button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Edit dialog */}
      {editingDoctrine && (
        <DoctrineEditDialog
          doctrine={editingDoctrine}
          onClose={() => setEditingDoctrine(null)}
          onSaved={loadDoctrines}
        />
      )}
    </div>
  );
}
