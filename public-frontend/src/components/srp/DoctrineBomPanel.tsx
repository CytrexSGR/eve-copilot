import { useState, useEffect, useRef } from 'react';
import { doctrineStatsApi } from '../../services/api/srp';
import { shoppingApi } from '../../services/api/shopping';

interface BomItem {
  type_id: number;
  type_name: string;
  quantity: number;
}

export function DoctrineBomPanel({ doctrineId }: { doctrineId: number }) {
  const [items, setItems] = useState<BomItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(30);
  const [debouncedQty, setDebouncedQty] = useState(30);
  const [copied, setCopied] = useState(false);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [showListPicker, setShowListPicker] = useState(false);
  const [shoppingLists, setShoppingLists] = useState<{ id: number; name: string }[]>([]);
  const [selectedListId, setSelectedListId] = useState(0);
  const [addingToList, setAddingToList] = useState(false);
  const [addedToList, setAddedToList] = useState(false);

  // Debounce quantity changes by 500ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQty(quantity);
    }, 500);
    return () => clearTimeout(timer);
  }, [quantity]);

  // Fetch BOM when doctrineId or debounced quantity changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    doctrineStatsApi.getBom(doctrineId, debouncedQty)
      .then((data: BomItem[]) => {
        if (!cancelled) setItems(data);
      })
      .catch(err => console.error('Failed to load BOM:', err))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [doctrineId, debouncedQty]);

  const handleCopy = async () => {
    const text = items.map(i => `${i.type_name}\t${i.quantity}`).join('\n');

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for HTTP
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }

      setCopied(true);
      if (copiedTimer.current) clearTimeout(copiedTimer.current);
      copiedTimer.current = setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  const handleToggleListPicker = async () => {
    if (!showListPicker) {
      try {
        const lists = await shoppingApi.getLists();
        const mapped = lists.map((l: any) => ({ id: l.id, name: l.name }));
        setShoppingLists(mapped);
        if (mapped.length > 0 && !selectedListId) setSelectedListId(mapped[0].id);
      } catch (err) {
        console.error('Failed to load shopping lists:', err);
      }
    }
    setShowListPicker(!showListPicker);
  };

  const handleAddToList = async () => {
    if (!selectedListId) return;
    setAddingToList(true);
    try {
      await shoppingApi.addDoctrine(selectedListId, doctrineId, debouncedQty);
      setAddedToList(true);
      setTimeout(() => setAddedToList(false), 2000);
      setShowListPicker(false);
    } catch (err) {
      console.error('Failed to add to shopping list:', err);
    } finally {
      setAddingToList(false);
    }
  };

  const totalItems = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.15)', border: '1px solid var(--border-color)',
      borderRadius: '8px', padding: '1rem',
    }}>
      {/* Header row */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem',
        flexWrap: 'wrap',
      }}>
        <div style={{
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
          color: 'rgba(255,255,255,0.45)', letterSpacing: '0.05em',
        }}>
          Fleet BOM
        </div>

        <input
          type="number"
          min={1}
          max={100}
          value={quantity}
          onChange={e => {
            const val = Math.max(1, Math.min(100, Number(e.target.value) || 1));
            setQuantity(val);
          }}
          style={{
            background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
            borderRadius: '4px', color: '#fff', padding: '0.3rem 0.5rem',
            fontSize: '0.8rem', fontFamily: 'monospace', outline: 'none',
            width: '70px', textAlign: 'center',
          }}
        />

        <div style={{ flex: 1 }} />

        <button
          onClick={handleCopy}
          disabled={loading || items.length === 0}
          style={{
            background: copied ? 'rgba(63,185,80,0.2)' : 'rgba(0,212,255,0.15)',
            border: `1px solid ${copied ? 'rgba(63,185,80,0.4)' : 'rgba(0,212,255,0.3)'}`,
            borderRadius: '6px',
            color: copied ? '#3fb950' : '#00d4ff',
            padding: '0.35rem 0.85rem', fontSize: '0.78rem', fontWeight: 600,
            cursor: loading || items.length === 0 ? 'not-allowed' : 'pointer',
            opacity: loading || items.length === 0 ? 0.5 : 1,
            transition: 'all 0.2s ease',
          }}
        >
          {copied ? 'Copied!' : 'Copy Multibuy'}
        </button>
        <button
          onClick={handleToggleListPicker}
          disabled={loading || items.length === 0}
          style={{
            background: addedToList ? 'rgba(63,185,80,0.2)' : 'rgba(210,153,34,0.15)',
            border: `1px solid ${addedToList ? 'rgba(63,185,80,0.4)' : 'rgba(210,153,34,0.3)'}`,
            borderRadius: '6px',
            color: addedToList ? '#3fb950' : '#d29922',
            padding: '0.35rem 0.85rem', fontSize: '0.78rem', fontWeight: 600,
            cursor: loading || items.length === 0 ? 'not-allowed' : 'pointer',
            opacity: loading || items.length === 0 ? 0.5 : 1,
            transition: 'all 0.2s ease',
          }}
        >
          {addedToList ? 'Added!' : '\u2192 Shopping List'}
        </button>
      </div>

      {/* Shopping list picker */}
      {showListPicker && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.5rem 0', marginBottom: '0.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap' }}>
            Add to:
          </span>
          {shoppingLists.length === 0 ? (
            <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>
              No lists found. Create one in Shopping first.
            </span>
          ) : (
            <>
              <select
                value={selectedListId}
                onChange={e => setSelectedListId(Number(e.target.value))}
                style={{
                  flex: 1, background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-color)', borderRadius: '4px',
                  color: '#fff', padding: '0.3rem 0.5rem',
                  fontSize: '0.75rem', outline: 'none',
                }}
              >
                {shoppingLists.map(l => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
              <button
                onClick={handleAddToList}
                disabled={addingToList || !selectedListId}
                style={{
                  background: 'rgba(63,185,80,0.15)',
                  border: '1px solid rgba(63,185,80,0.3)',
                  borderRadius: '4px', color: '#3fb950',
                  padding: '0.3rem 0.75rem', fontSize: '0.75rem', fontWeight: 600,
                  cursor: addingToList || !selectedListId ? 'not-allowed' : 'pointer',
                  opacity: addingToList || !selectedListId ? 0.5 : 1,
                  whiteSpace: 'nowrap',
                }}
              >
                {addingToList ? 'Adding...' : 'Add'}
              </button>
            </>
          )}
        </div>
      )}

      {/* Items table */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{
              height: '28px', borderRadius: '4px',
              background: 'rgba(255,255,255,0.04)',
              animation: 'pulse 1.5s ease-in-out infinite',
            }} />
          ))}
          <style>{`@keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 0.8; } }`}</style>
        </div>
      ) : items.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>
          No items in BOM
        </div>
      ) : (
        <>
          {/* Table header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '28px 1fr 80px',
            gap: '0.5rem', padding: '0.35rem 0.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.45)',
          }}>
            <span></span>
            <span>Item</span>
            <span style={{ textAlign: 'right' }}>Qty</span>
          </div>

          {/* Table rows */}
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {items.map((item, idx) => (
              <div key={item.type_id} style={{
                display: 'grid', gridTemplateColumns: '28px 1fr 80px',
                gap: '0.5rem', padding: '0.3rem 0.5rem', alignItems: 'center',
                background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
              }}>
                <img
                  src={`https://images.evetech.net/types/${item.type_id}/icon?size=32`}
                  alt=""
                  width={24}
                  height={24}
                  style={{ borderRadius: '2px' }}
                  loading="lazy"
                />
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.type_name}
                </span>
                <span style={{
                  textAlign: 'right', fontFamily: 'monospace', fontSize: '0.8rem',
                  color: 'rgba(255,255,255,0.8)',
                }}>
                  {item.quantity.toLocaleString()}
                </span>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '0.5rem 0.5rem 0', marginTop: '0.5rem',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)',
          }}>
            <span>{items.length} unique items</span>
            <span style={{ fontFamily: 'monospace' }}>{totalItems.toLocaleString()} total</span>
          </div>
        </>
      )}
    </div>
  );
}
