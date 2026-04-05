import { useState, useEffect } from 'react';
import type { FighterInput } from '../../types/fittings';
import { resolveTypeNames } from '../../services/api/fittings';

const getTypeIconUrl = (typeId: number) =>
  `https://images.evetech.net/types/${typeId}/icon?size=32`;

interface FighterSectionProps {
  fighters: FighterInput[];
  onFightersChange: (fighters: FighterInput[]) => void;
}

export default function FighterSection({ fighters, onFightersChange }: FighterSectionProps) {
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ type_id: number; type_name: string }>>([]);
  const [fighterNames, setFighterNames] = useState<Record<number, string>>({});

  useEffect(() => {
    const ids = fighters.map(f => f.type_id).filter(id => !fighterNames[id]);
    if (ids.length === 0) return;
    resolveTypeNames(ids).then(names => {
      const updated = { ...fighterNames };
      names.forEach((name, id) => { updated[id] = name; });
      setFighterNames(updated);
    });
  }, [fighters]);

  const handleSearch = async (query: string) => {
    setSearch(query);
    if (query.length < 2) { setSearchResults([]); return; }
    try {
      const res = await fetch(`/api/sde/modules?search=${encodeURIComponent(query)}&category=fighter&limit=10`);
      const data = await res.json();
      setSearchResults(data.map((d: any) => ({ type_id: d.type_id, type_name: d.type_name })));
    } catch { setSearchResults([]); }
  };

  const addFighter = (typeId: number, typeName: string) => {
    const existing = fighters.find(f => f.type_id === typeId);
    if (existing) {
      onFightersChange(fighters.map(f => f.type_id === typeId ? { ...f, quantity: f.quantity + 1 } : f));
    } else {
      onFightersChange([...fighters, { type_id: typeId, quantity: 1 }]);
      setFighterNames(prev => ({ ...prev, [typeId]: typeName }));
    }
    setSearch('');
    setSearchResults([]);
  };

  const removeFighter = (typeId: number) => onFightersChange(fighters.filter(f => f.type_id !== typeId));

  const updateQuantity = (typeId: number, qty: number) => {
    if (qty < 1) { removeFighter(typeId); return; }
    onFightersChange(fighters.map(f => f.type_id === typeId ? { ...f, quantity: qty } : f));
  };

  return (
    <div style={{ marginTop: 8, padding: '6px 8px', background: 'var(--bg-secondary)', borderRadius: 4, border: '1px solid var(--border-color)' }}>
      <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#a855f7', marginBottom: 4 }}>Fighters</div>
      {fighters.map(f => (
        <div key={f.type_id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', fontSize: '0.7rem' }}>
          <img src={getTypeIconUrl(f.type_id)} width={20} height={20} style={{ borderRadius: 2 }} />
          <span style={{ flex: 1, color: 'var(--text-primary)' }}>{fighterNames[f.type_id] || `Type ${f.type_id}`}</span>
          <button onClick={() => updateQuantity(f.type_id, f.quantity - 1)} style={{ background: 'none', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', borderRadius: 2, cursor: 'pointer', padding: '0 4px', fontSize: '0.65rem' }}>-</button>
          <span style={{ fontFamily: 'monospace', minWidth: 16, textAlign: 'center' }}>{f.quantity}</span>
          <button onClick={() => updateQuantity(f.type_id, f.quantity + 1)} style={{ background: 'none', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', borderRadius: 2, cursor: 'pointer', padding: '0 4px', fontSize: '0.65rem' }}>+</button>
          <button onClick={() => removeFighter(f.type_id)} style={{ background: 'none', border: 'none', color: '#f85149', cursor: 'pointer', fontSize: '0.7rem' }}>x</button>
        </div>
      ))}
      <div style={{ position: 'relative', marginTop: 4 }}>
        <input type="text" placeholder="Search fighters..." value={search} onChange={(e) => handleSearch(e.target.value)}
          style={{ width: '100%', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 4, padding: '3px 6px', fontSize: '0.65rem', boxSizing: 'border-box' }} />
        {searchResults.length > 0 && (
          <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 4, maxHeight: 150, overflowY: 'auto' }}>
            {searchResults.map(r => (
              <div key={r.type_id} onClick={() => addFighter(r.type_id, r.type_name)}
                style={{ padding: '4px 8px', cursor: 'pointer', fontSize: '0.65rem', display: 'flex', alignItems: 'center', gap: 4 }}
                onMouseOver={e => (e.currentTarget.style.background = 'var(--bg-tertiary)')}
                onMouseOut={e => (e.currentTarget.style.background = 'transparent')}>
                <img src={getTypeIconUrl(r.type_id)} width={16} height={16} style={{ borderRadius: 2 }} />
                {r.type_name}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
