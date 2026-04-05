import { useState, useEffect } from 'react';
import { redListApi } from '../../services/api/hr';
import type { RedListEntity, RedListCreateRequest } from '../../types/hr';
import { getSeverityColor } from '../../types/hr';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
};

export function RedListTab({ corpId: _corpId }: { corpId: number }) {
  const [entries, setEntries] = useState<RedListEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<RedListCreateRequest>({
    entity_id: 0, entity_name: '', category: 'character', severity: 3, reason: '', added_by: '',
  });

  const loadEntries = async () => {
    setLoading(true);
    try {
      const data = await redListApi.getEntries({ active_only: true });
      setEntries(data);
    } catch (err) {
      console.error('Failed to load red list:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadEntries(); }, []);

  const filtered = categoryFilter === 'all' ? entries : entries.filter(e => e.category === categoryFilter);

  const handleAdd = async () => {
    if (!form.entity_id || !form.entity_name || !form.reason || !form.added_by) return;
    setSubmitting(true);
    try {
      await redListApi.addEntry(form);
      setForm({ entity_id: 0, entity_name: '', category: 'character', severity: 3, reason: '', added_by: '' });
      setShowForm(false);
      await loadEntries();
    } catch (err) {
      console.error('Failed to add entry:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (id: number) => {
    try {
      await redListApi.removeEntry(id);
      await loadEntries();
    } catch (err) {
      console.error('Failed to remove entry:', err);
    }
  };

  const inputStyle = {
    background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
    borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem', fontSize: '0.8rem', outline: 'none',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Controls */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', padding: '0.75rem 1rem',
        display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap',
      }}>
        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          style={{ ...inputStyle, cursor: 'pointer' }}>
          <option value="all">All Categories</option>
          <option value="character">Character</option>
          <option value="corporation">Corporation</option>
          <option value="alliance">Alliance</option>
        </select>
        <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)' }}>{filtered.length} entries</div>
        <div style={{ flex: 1 }} />
        <button onClick={() => setShowForm(!showForm)} style={{
          background: showForm ? 'rgba(255,255,255,0.05)' : 'rgba(63,185,80,0.15)',
          border: '1px solid rgba(63,185,80,0.3)', borderRadius: '6px',
          color: '#3fb950', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
        }}>
          {showForm ? 'Cancel' : 'Add Entry'}
        </button>
      </div>

      {/* Add Form */}
      {showForm && (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '1rem',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Entity ID</label>
            <input type="number" value={form.entity_id || ''} onChange={e => setForm({ ...form, entity_id: Number(e.target.value) })} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Entity Name</label>
            <input value={form.entity_name} onChange={e => setForm({ ...form, entity_name: e.target.value })} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Category</label>
            <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value as 'character' | 'corporation' | 'alliance' })} style={{ ...inputStyle, cursor: 'pointer' }}>
              <option value="character">Character</option>
              <option value="corporation">Corporation</option>
              <option value="alliance">Alliance</option>
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Severity</label>
            <select value={form.severity} onChange={e => setForm({ ...form, severity: Number(e.target.value) })} style={{ ...inputStyle, cursor: 'pointer' }}>
              {[1,2,3,4,5].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', gridColumn: 'span 2' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Reason</label>
            <input value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Added By</label>
            <input value={form.added_by} onChange={e => setForm({ ...form, added_by: e.target.value })} style={inputStyle} />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button onClick={handleAdd} disabled={submitting} style={{
              background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
              borderRadius: '6px', color: '#3fb950', padding: '0.4rem 1.25rem',
              fontSize: '0.8rem', fontWeight: 600, cursor: submitting ? 'not-allowed' : 'pointer',
            }}>
              {submitting ? 'Adding...' : 'Add'}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1.5fr 100px 60px 2fr 120px 90px 70px',
          gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Name</span><span>Category</span><span>Sev</span><span>Reason</span><span>Added By</span><span>Date</span><span></span>
        </div>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No entries found</div>
        ) : (
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {filtered.map((entry, idx) => (
              <div key={entry.id} style={{
                display: 'grid', gridTemplateColumns: '1.5fr 100px 60px 2fr 120px 90px 70px',
                gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem',
                background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
              }}>
                <span style={{ fontWeight: 600, color: '#fff' }}>{entry.entity_name}</span>
                <span style={{
                  padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem',
                  background: 'rgba(0,212,255,0.1)', color: '#00d4ff', textTransform: 'capitalize',
                }}>{entry.category}</span>
                <span style={{
                  width: '24px', height: '24px', borderRadius: '4px', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.75rem',
                  background: getSeverityColor(entry.severity), color: '#fff',
                }}>{entry.severity}</span>
                <span style={{ color: 'rgba(255,255,255,0.6)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={entry.reason}>{entry.reason}</span>
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>{entry.added_by}</span>
                <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>{formatDate(entry.added_at)}</span>
                <button onClick={() => handleRemove(entry.id)} style={{
                  background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                  borderRadius: '4px', color: '#f85149', padding: '2px 8px', fontSize: '0.7rem',
                  cursor: 'pointer',
                }}>Remove</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
