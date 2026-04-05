import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { shoppingApi } from '../../services/api/shopping';
import type { ShoppingList, ShoppingItem, CargoSummary } from '../../types/shopping';

interface SdeResolvedItem {
  id: number;
  name: string;
}

export function ListManager() {
  const [lists, setLists] = useState<ShoppingList[]>([]);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [newListName, setNewListName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  // Add item state
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<SdeResolvedItem[]>([]);
  const [selectedType, setSelectedType] = useState<SdeResolvedItem | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [searchLoading, setSearchLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Cargo summary state
  const [showCargo, setShowCargo] = useState(false);
  const [cargoSummary, setCargoSummary] = useState<CargoSummary | null>(null);
  const [cargoLoading, setCargoLoading] = useState(false);

  // Clipboard feedback
  const [copySuccess, setCopySuccess] = useState(false);

  const selectedList = lists.find((l) => l.id === selectedListId) || null;

  // Load lists on mount
  useEffect(() => {
    loadLists();
  }, []);

  // Load items when selected list changes
  useEffect(() => {
    if (selectedListId !== null) {
      loadItems(selectedListId);
      setShowCargo(false);
      setCargoSummary(null);
    } else {
      setItems([]);
    }
  }, [selectedListId]);

  // Debounced search for type names
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    if (searchTerm.length < 2) {
      setSearchResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const { data } = await axios.post(
          '/api/sde/resolve-names',
          { names: [searchTerm] },
          { withCredentials: true }
        );
        const resolved: SdeResolvedItem[] = [];
        if (data && typeof data === 'object') {
          for (const [name, id] of Object.entries(data)) {
            if (typeof id === 'number' && id > 0) {
              resolved.push({ id, name });
            }
          }
        }
        setSearchResults(resolved);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 500);
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [searchTerm]);

  async function loadLists() {
    setLoading(true);
    try {
      const data = await shoppingApi.getLists();
      setLists(data);
    } catch {
      setError('Failed to load shopping lists');
    } finally {
      setLoading(false);
    }
  }

  async function loadItems(listId: number) {
    try {
      const data = await shoppingApi.getItems(listId);
      setItems(data);
    } catch {
      setError('Failed to load list items');
    }
  }

  async function handleCreateList() {
    if (!newListName.trim()) return;
    try {
      const created = await shoppingApi.createList(newListName.trim());
      setLists((prev) => [...prev, created]);
      setSelectedListId(created.id);
      setNewListName('');
    } catch {
      setError('Failed to create list');
    }
  }

  async function handleDeleteList(listId: number) {
    try {
      await shoppingApi.deleteList(listId);
      setLists((prev) => prev.filter((l) => l.id !== listId));
      if (selectedListId === listId) {
        setSelectedListId(null);
        setItems([]);
      }
      setConfirmDeleteId(null);
    } catch {
      setError('Failed to delete list');
    }
  }

  async function handleAddItem() {
    if (!selectedType || !selectedListId || quantity < 1) return;
    try {
      const added = await shoppingApi.addItem(selectedListId, selectedType.id, quantity);
      setItems((prev) => [...prev, added]);
      setSelectedType(null);
      setSearchTerm('');
      setSearchResults([]);
      setQuantity(1);
      // Refresh list metadata
      loadLists();
    } catch {
      setError('Failed to add item');
    }
  }

  async function handleTogglePurchased(item: ShoppingItem) {
    if (!selectedListId) return;
    try {
      await shoppingApi.markPurchased(selectedListId, item.id, !item.purchased);
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, purchased: !i.purchased } : i))
      );
    } catch {
      setError('Failed to update item');
    }
  }

  async function handleDeleteItem(itemId: number) {
    if (!selectedListId) return;
    try {
      await shoppingApi.deleteItem(selectedListId, itemId);
      setItems((prev) => prev.filter((i) => i.id !== itemId));
      loadLists();
    } catch {
      setError('Failed to remove item');
    }
  }

  async function handleExportMultibuy() {
    if (!selectedListId) return;
    try {
      const text = await shoppingApi.exportList(selectedListId, 'eve');
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        // Fallback for HTTP contexts
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch {
      setError('Failed to export list');
    }
  }

  async function handleToggleCargo() {
    if (!selectedListId) return;
    if (showCargo) {
      setShowCargo(false);
      return;
    }
    setCargoLoading(true);
    try {
      const data = await shoppingApi.getCargoSummary(selectedListId);
      setCargoSummary(data);
      setShowCargo(true);
    } catch {
      setError('Failed to load cargo summary');
    } finally {
      setCargoLoading(false);
    }
  }

  function selectSearchResult(item: SdeResolvedItem) {
    setSelectedType(item);
    setSearchTerm(item.name);
    setSearchResults([]);
  }

  function formatIsk(value: number | undefined | null): string {
    if (value === undefined || value === null) return '0 ISK';
    return value.toLocaleString() + ' ISK';
  }

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  const totalValue = items.reduce((sum, i) => sum + (i.total_price || 0), 0);
  const totalPurchased = items.filter((i) => i.purchased).length;

  // -- Styles --
  const containerStyle: React.CSSProperties = {
    display: 'flex',
    gap: '16px',
    height: '100%',
    minHeight: '500px',
  };

  const sidebarStyle: React.CSSProperties = {
    width: '280px',
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  };

  const cardStyle: React.CSSProperties = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '12px',
  };

  const inputStyle: React.CSSProperties = {
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    color: 'inherit',
    padding: '6px 10px',
    fontSize: '0.85rem',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  };

  const buttonStyle: React.CSSProperties = {
    background: '#00d4ff',
    color: '#000',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 14px',
    fontSize: '0.85rem',
    cursor: 'pointer',
    fontWeight: 600,
  };

  const buttonDangerStyle: React.CSSProperties = {
    ...buttonStyle,
    background: '#f85149',
    color: '#fff',
  };

  const buttonSecondaryStyle: React.CSSProperties = {
    ...buttonStyle,
    background: 'var(--bg-primary)',
    color: 'inherit',
    border: '1px solid var(--border-color)',
  };

  const listItemStyle = (isSelected: boolean): React.CSSProperties => ({
    padding: '10px',
    borderRadius: '6px',
    cursor: 'pointer',
    border: isSelected ? '1px solid #00d4ff' : '1px solid transparent',
    background: isSelected ? 'rgba(0, 212, 255, 0.06)' : 'transparent',
    transition: 'border-color 0.15s, background 0.15s',
  });

  const labelStyle: React.CSSProperties = {
    fontSize: '0.7rem',
    opacity: 0.6,
  };

  const monoStyle: React.CSSProperties = {
    fontFamily: 'monospace',
  };

  return (
    <div style={containerStyle}>
      {/* Left Sidebar */}
      <div style={sidebarStyle}>
        {/* Create New List */}
        <div style={cardStyle}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
            Create New List
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              style={{ ...inputStyle, flex: 1 }}
              placeholder="List name..."
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateList()}
            />
            <button style={buttonStyle} onClick={handleCreateList}>
              +
            </button>
          </div>
        </div>

        {/* Shopping Lists */}
        <div style={{ ...cardStyle, flex: 1, overflow: 'auto' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
            Shopping Lists
          </div>
          {loading && <div style={{ ...labelStyle, padding: '8px' }}>Loading...</div>}
          {!loading && lists.length === 0 && (
            <div style={{ ...labelStyle, padding: '8px' }}>No lists yet</div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {lists.map((list) => (
              <div
                key={list.id}
                style={listItemStyle(list.id === selectedListId)}
                onClick={() => setSelectedListId(list.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>{list.name}</span>
                  {list.id === selectedListId && (
                    <span>
                      {confirmDeleteId === list.id ? (
                        <span style={{ display: 'flex', gap: '4px' }}>
                          <button
                            style={{ ...buttonDangerStyle, padding: '2px 8px', fontSize: '0.7rem' }}
                            onClick={(e) => { e.stopPropagation(); handleDeleteList(list.id); }}
                          >
                            Confirm
                          </button>
                          <button
                            style={{ ...buttonSecondaryStyle, padding: '2px 8px', fontSize: '0.7rem' }}
                            onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                          >
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <button
                          style={{ ...buttonDangerStyle, padding: '2px 8px', fontSize: '0.7rem' }}
                          onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(list.id); }}
                        >
                          Delete
                        </button>
                      )}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                  <span style={labelStyle}>{list.item_count} items</span>
                  <span style={labelStyle}>{formatDate(list.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', minWidth: 0 }}>
        {!selectedList ? (
          <div
            style={{
              ...cardStyle,
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: 0.5,
              fontSize: '0.85rem',
            }}
          >
            Select a list or create a new one
          </div>
        ) : (
          <>
            {/* Error Banner */}
            {error && (
              <div
                style={{
                  background: 'rgba(248, 81, 73, 0.1)',
                  border: '1px solid #f85149',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  fontSize: '0.85rem',
                  color: '#f85149',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>{error}</span>
                <button
                  style={{ background: 'none', border: 'none', color: '#f85149', cursor: 'pointer' }}
                  onClick={() => setError(null)}
                >
                  x
                </button>
              </div>
            )}

            {/* Header */}
            <div style={{ ...cardStyle, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 600 }}>{selectedList.name}</div>
                <div style={labelStyle}>
                  {items.length} items
                </div>
              </div>
              <div style={{ ...monoStyle, fontSize: '1rem', fontWeight: 600, color: '#3fb950' }}>
                {formatIsk(totalValue)}
              </div>
            </div>

            {/* Add Item Section */}
            <div style={cardStyle}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
                Add Item
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '180px', position: 'relative' }}>
                  <div style={labelStyle}>Item Name</div>
                  <input
                    style={inputStyle}
                    placeholder="Search item name..."
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value);
                      setSelectedType(null);
                    }}
                  />
                  {searchLoading && (
                    <div
                      style={{
                        position: 'absolute',
                        right: '8px',
                        top: '22px',
                        fontSize: '0.7rem',
                        opacity: 0.5,
                      }}
                    >
                      ...
                    </div>
                  )}
                  {searchResults.length > 0 && !selectedType && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '6px',
                        maxHeight: '200px',
                        overflow: 'auto',
                        zIndex: 10,
                        marginTop: '2px',
                      }}
                    >
                      {searchResults.map((r) => (
                        <div
                          key={r.id}
                          style={{
                            padding: '6px 10px',
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            borderBottom: '1px solid var(--border-color)',
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = 'rgba(0, 212, 255, 0.08)')
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = 'transparent')
                          }
                          onClick={() => selectSearchResult(r)}
                        >
                          <div>{r.name}</div>
                          <div style={{ ...labelStyle, ...monoStyle }}>{r.id}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{ width: '80px' }}>
                  <div style={labelStyle}>Quantity</div>
                  <input
                    style={{ ...inputStyle, textAlign: 'right', fontFamily: 'monospace' }}
                    type="number"
                    min={1}
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  />
                </div>
                <button
                  style={{
                    ...buttonStyle,
                    opacity: selectedType ? 1 : 0.4,
                    pointerEvents: selectedType ? 'auto' : 'none',
                  }}
                  onClick={handleAddItem}
                >
                  Add
                </button>
              </div>
              {selectedType && (
                <div style={{ marginTop: '6px', fontSize: '0.7rem', color: '#3fb950' }}>
                  Selected: {selectedType.name} (ID: {selectedType.id})
                </div>
              )}
            </div>

            {/* Items Table */}
            <div style={{ ...cardStyle, flex: 1, overflow: 'auto' }}>
              {items.length === 0 ? (
                <div style={{ ...labelStyle, padding: '16px', textAlign: 'center' }}>
                  No items in this list. Use the search above to add items.
                </div>
              ) : (
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '0.85rem',
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        borderBottom: '1px solid var(--border-color)',
                        textAlign: 'left',
                      }}
                    >
                      <th style={{ padding: '6px 4px', width: '40px' }}></th>
                      <th style={{ padding: '6px 4px' }}>Name</th>
                      <th style={{ padding: '6px 4px', textAlign: 'right', width: '60px' }}>Qty</th>
                      <th style={{ padding: '6px 4px', textAlign: 'right', width: '110px' }}>Unit Price</th>
                      <th style={{ padding: '6px 4px', textAlign: 'right', width: '110px' }}>Total</th>
                      <th style={{ padding: '6px 4px', textAlign: 'center', width: '36px' }}>
                        <span title="Purchased">P</span>
                      </th>
                      <th style={{ padding: '6px 4px', width: '36px' }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => {
                      const rowOpacity = item.purchased ? 0.45 : 1;
                      const textDecoration = item.purchased ? 'line-through' : 'none';
                      return (
                        <tr
                          key={item.id}
                          style={{
                            borderBottom: '1px solid var(--border-color)',
                            opacity: rowOpacity,
                          }}
                        >
                          <td style={{ padding: '6px 4px' }}>
                            <img
                              src={`https://images.evetech.net/types/${item.type_id}/icon?size=32`}
                              alt=""
                              width={32}
                              height={32}
                              style={{ borderRadius: '4px', display: 'block' }}
                            />
                          </td>
                          <td style={{ padding: '6px 4px', textDecoration }}>
                            {item.type_name}
                          </td>
                          <td style={{ padding: '6px 4px', textAlign: 'right', textDecoration, ...monoStyle }}>
                            {item.quantity.toLocaleString()}
                          </td>
                          <td style={{ padding: '6px 4px', textAlign: 'right', textDecoration, ...monoStyle }}>
                            {formatIsk(item.unit_price)}
                          </td>
                          <td
                            style={{
                              padding: '6px 4px',
                              textAlign: 'right',
                              textDecoration,
                              ...monoStyle,
                              color: '#3fb950',
                            }}
                          >
                            {formatIsk(item.total_price)}
                          </td>
                          <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={item.purchased}
                              onChange={() => handleTogglePurchased(item)}
                              style={{ cursor: 'pointer' }}
                            />
                          </td>
                          <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                            <button
                              style={{
                                background: 'none',
                                border: 'none',
                                color: '#f85149',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                padding: '2px 4px',
                              }}
                              title="Remove item"
                              onClick={() => handleDeleteItem(item.id)}
                            >
                              x
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                style={{
                  ...buttonSecondaryStyle,
                  background: copySuccess ? 'rgba(63, 185, 80, 0.15)' : 'var(--bg-primary)',
                  borderColor: copySuccess ? '#3fb950' : 'var(--border-color)',
                  color: copySuccess ? '#3fb950' : 'inherit',
                }}
                onClick={handleExportMultibuy}
              >
                {copySuccess ? 'Copied!' : 'Export Multibuy'}
              </button>
              <button
                style={{
                  ...buttonSecondaryStyle,
                  background: showCargo ? 'rgba(0, 212, 255, 0.08)' : 'var(--bg-primary)',
                  borderColor: showCargo ? '#00d4ff' : 'var(--border-color)',
                }}
                onClick={handleToggleCargo}
              >
                {cargoLoading ? 'Loading...' : 'Cargo Summary'}
              </button>
            </div>

            {/* Cargo Summary Panel */}
            {showCargo && cargoSummary && (
              <div style={cardStyle}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '10px' }}>
                  Cargo Summary
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '10px',
                    marginBottom: '12px',
                  }}
                >
                  <div>
                    <div style={labelStyle}>Total Volume</div>
                    <div style={monoStyle}>{cargoSummary.total_volume_m3.toLocaleString()} m3</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Weight</div>
                    <div style={monoStyle}>{cargoSummary.weight_kg.toLocaleString()} kg</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Item Count</div>
                    <div style={monoStyle}>{cargoSummary.item_count.toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={labelStyle}>Est. Transport Time</div>
                    <div style={monoStyle}>{cargoSummary.estimated_time_hours.toFixed(1)} hrs</div>
                  </div>
                </div>

                {cargoSummary.transport_ships.length > 0 && (
                  <>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}>
                      Transport Ship Recommendations
                    </div>
                    <table
                      style={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        fontSize: '0.85rem',
                      }}
                    >
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                          <th style={{ padding: '4px' }}>Ship</th>
                          <th style={{ padding: '4px', textAlign: 'right' }}>Cargo (m3)</th>
                          <th style={{ padding: '4px', textAlign: 'center' }}>Security</th>
                          <th style={{ padding: '4px', textAlign: 'right' }}>Est. Cost</th>
                          <th style={{ padding: '4px', textAlign: 'right' }}>Travel (hrs)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cargoSummary.transport_ships.map((ship, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                            <td style={{ padding: '4px' }}>{ship.ship_name}</td>
                            <td style={{ padding: '4px', textAlign: 'right', ...monoStyle }}>
                              {ship.cargo_capacity.toLocaleString()}
                            </td>
                            <td
                              style={{
                                padding: '4px',
                                textAlign: 'center',
                                color:
                                  ship.security_level === 'high'
                                    ? '#3fb950'
                                    : ship.security_level === 'low'
                                    ? '#d29922'
                                    : '#f85149',
                              }}
                            >
                              {ship.security_level}
                            </td>
                            <td style={{ padding: '4px', textAlign: 'right', ...monoStyle }}>
                              {formatIsk(ship.cost_estimate)}
                            </td>
                            <td style={{ padding: '4px', textAlign: 'right', ...monoStyle }}>
                              {ship.travel_time.toFixed(1)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}

            {/* Totals Bar */}
            <div
              style={{
                ...cardStyle,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', gap: '16px' }}>
                <div>
                  <span style={labelStyle}>Total Items: </span>
                  <span style={{ ...monoStyle, fontSize: '0.85rem' }}>{items.length}</span>
                </div>
                <div>
                  <span style={labelStyle}>Purchased: </span>
                  <span
                    style={{
                      ...monoStyle,
                      fontSize: '0.85rem',
                      color: totalPurchased === items.length && items.length > 0 ? '#3fb950' : 'inherit',
                    }}
                  >
                    {totalPurchased}/{items.length}
                  </span>
                </div>
              </div>
              <div style={{ ...monoStyle, fontSize: '0.85rem', fontWeight: 600, color: '#3fb950' }}>
                {formatIsk(totalValue)}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
