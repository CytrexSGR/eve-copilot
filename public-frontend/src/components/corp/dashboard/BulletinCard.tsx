import { useState, useEffect, useCallback } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { SectionCard } from './SectionCard';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/auth/public/org/bulletins',
  timeout: 30000,
  withCredentials: true,
});

interface Bulletin {
  id: number;
  title: string;
  body: string;
  priority: string;
  is_pinned: boolean;
  author_name: string;
  expires_at: string | null;
  created_at: string | null;
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#f85149',
  normal: '#00d4ff',
  low: '#8b949e',
};

interface BulletinCardProps {
  corpId: number;
}

export function BulletinCard(_props: BulletinCardProps) {
  const [bulletins, setBulletins] = useState<Bulletin[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formBody, setFormBody] = useState('');
  const [formPriority, setFormPriority] = useState('normal');
  const [formPinned, setFormPinned] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('', { params: { limit: 5 } });
      setBulletins(data.bulletins || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const submitPost = async () => {
    if (!formTitle.trim() || !formBody.trim()) return;
    try {
      await api.post('', {
        title: formTitle,
        body: formBody,
        priority: formPriority,
        is_pinned: formPinned,
      });
      setShowForm(false);
      setFormTitle('');
      setFormBody('');
      setFormPriority('normal');
      setFormPinned(false);
      load();
    } catch { /* ignore */ }
  };

  return (
    <SectionCard
      title="Bulletin Board"
      borderColor="#d29922"
      linkTo="/corp"
      linkLabel="Corp Dashboard"
      loading={loading}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {bulletins.length === 0 ? (
          <div style={{ fontSize: fontSize.sm, color: color.textSecondary, padding: '0.5rem 0' }}>
            No announcements yet.
          </div>
        ) : (
          bulletins.map(b => (
            <div key={b.id} style={{
              padding: '0.5rem',
              background: b.is_pinned ? 'rgba(210,153,34,0.08)' : 'rgba(255,255,255,0.02)',
              borderRadius: 4,
              borderLeft: `2px solid ${PRIORITY_COLORS[b.priority] || '#8b949e'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: 2 }}>
                {b.is_pinned && <span style={{ fontSize: '0.7rem', color: '#d29922' }}>&#128204;</span>}
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: PRIORITY_COLORS[b.priority] || '#8b949e',
                  textTransform: 'uppercase',
                }}>
                  {b.priority}
                </span>
                <span style={{ fontSize: fontSize.sm, fontWeight: 600, color: color.textPrimary }}>
                  {b.title}
                </span>
              </div>
              <div style={{
                fontSize: fontSize.tiny,
                color: color.textSecondary,
                lineHeight: 1.4,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}>
                {b.body}
              </div>
              <div style={{ fontSize: '0.65rem', color: color.textSecondary, marginTop: 3 }}>
                {b.author_name} &middot; {b.created_at ? new Date(b.created_at).toLocaleDateString() : ''}
              </div>
            </div>
          ))
        )}

        {/* New Announcement button/form */}
        {!showForm ? (
          <button
            onClick={() => setShowForm(true)}
            style={{
              background: 'transparent',
              border: '1px dashed rgba(210,153,34,0.4)',
              borderRadius: 4,
              color: '#d29922',
              padding: '0.4rem',
              cursor: 'pointer',
              fontSize: fontSize.tiny,
              fontWeight: 600,
            }}
          >
            + New Announcement
          </button>
        ) : (
          <div style={{
            padding: '0.5rem',
            background: 'rgba(210,153,34,0.05)',
            borderRadius: 4,
            border: '1px solid rgba(210,153,34,0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.4rem',
          }}>
            <input
              value={formTitle}
              onChange={e => setFormTitle(e.target.value)}
              placeholder="Title"
              style={{
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                padding: '4px 8px',
                color: 'var(--text-primary)',
                fontSize: fontSize.sm,
              }}
            />
            <textarea
              value={formBody}
              onChange={e => setFormBody(e.target.value)}
              placeholder="Announcement body..."
              rows={3}
              style={{
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                padding: '4px 8px',
                color: 'var(--text-primary)',
                fontSize: fontSize.sm,
                resize: 'vertical',
              }}
            />
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <select
                value={formPriority}
                onChange={e => setFormPriority(e.target.value)}
                style={{
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 4,
                  padding: '4px 8px',
                  color: 'var(--text-primary)',
                  fontSize: fontSize.tiny,
                }}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="urgent">Urgent</option>
              </select>
              <label style={{ fontSize: fontSize.tiny, color: color.textSecondary, display: 'flex', alignItems: 'center', gap: 4 }}>
                <input type="checkbox" checked={formPinned} onChange={e => setFormPinned(e.target.checked)} />
                Pin
              </label>
              <div style={{ flex: 1 }} />
              <button onClick={() => setShowForm(false)} style={{
                background: 'transparent',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                padding: '3px 10px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: fontSize.tiny,
              }}>Cancel</button>
              <button onClick={submitPost} style={{
                background: '#d29922',
                border: 'none',
                borderRadius: 4,
                padding: '3px 10px',
                color: '#000',
                cursor: 'pointer',
                fontSize: fontSize.tiny,
                fontWeight: 600,
              }}>Post</button>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
