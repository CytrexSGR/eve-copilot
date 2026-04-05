import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { projectApi } from '../services/api/production';
import type { ProductionProject } from '../types/production';

type StatusFilter = 'all' | 'draft' | 'active' | 'complete';

const STATUS_COLORS: Record<string, string> = {
  draft: '#8b949e',
  active: '#3fb950',
  complete: '#00d4ff',
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

export function ProjectList() {
  const navigate = useNavigate();
  const { account } = useAuth();
  const [projects, setProjects] = useState<ProductionProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newIsCorp, setNewIsCorp] = useState(false);
  const [creating, setCreating] = useState(false);

  const characterId = account?.characters?.[0]?.character_id;
  const corporationId = account?.corporation_id;

  const loadProjects = useCallback(async () => {
    if (!characterId) return;
    setLoading(true);
    try {
      const data = await projectApi.list(characterId, corporationId ?? undefined);
      setProjects(data);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [characterId, corporationId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleCreate = async () => {
    if (!characterId || !newName.trim()) return;
    setCreating(true);
    try {
      const project = await projectApi.create({
        creator_character_id: characterId,
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        corporation_id: newIsCorp && corporationId ? corporationId : undefined,
      });
      setShowCreate(false);
      setNewName('');
      setNewDesc('');
      setNewIsCorp(false);
      navigate(`/production/projects/${project.id}`);
    } catch {
      // stay on form
    } finally {
      setCreating(false);
    }
  };

  const filtered = filter === 'all' ? projects : projects.filter(p => p.status === filter);

  const FILTERS: { id: StatusFilter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'draft', label: 'Draft' },
    { id: 'active', label: 'Active' },
    { id: 'complete', label: 'Complete' },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
            Production Projects
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
            Organize manufacturing plans for multiple items
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            padding: '8px 16px',
            fontSize: '0.82rem',
            fontWeight: 600,
            background: 'rgba(0,212,255,0.1)',
            border: '1px solid rgba(0,212,255,0.3)',
            borderRadius: 6,
            color: '#00d4ff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
          }}
        >
          + New Project
        </button>
      </div>

      {/* Create Form (inline) */}
      {showCreate && (
        <div style={{
          marginBottom: '1.5rem',
          padding: '1rem',
          background: '#12121a',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: 8,
        }}>
          <div style={{ display: 'flex', gap: '0.75rem', flexDirection: 'column' }}>
            <div>
              <label style={labelStyle}>Project Name</label>
              <input
                type="text"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="e.g. Doctrine Drakes"
                autoFocus
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Description (optional)</label>
              <textarea
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                placeholder="Notes about this project..."
                rows={2}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                checked={newIsCorp}
                onChange={e => setNewIsCorp(e.target.checked)}
                id="corp-project"
                style={{ accentColor: '#00d4ff' }}
              />
              <label htmlFor="corp-project" style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                Corporation project (visible to corp members)
              </label>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setShowCreate(false); setNewName(''); setNewDesc(''); setNewIsCorp(false); }}
                style={{
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 4,
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || creating}
                style={{
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  background: 'rgba(0,212,255,0.15)',
                  border: '1px solid rgba(0,212,255,0.4)',
                  borderRadius: 4,
                  color: '#00d4ff',
                  cursor: !newName.trim() || creating ? 'not-allowed' : 'pointer',
                  opacity: !newName.trim() || creating ? 0.5 : 1,
                }}
              >
                {creating ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div style={{
        display: 'flex',
        gap: '0.25rem',
        marginBottom: '1rem',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '0.5rem',
      }}>
        {FILTERS.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: filter === f.id ? '2px solid #00d4ff' : '2px solid transparent',
              color: filter === f.id ? '#00d4ff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: filter === f.id ? 600 : 400,
            }}
          >
            {f.label}
            {f.id !== 'all' && (
              <span style={{
                marginLeft: '0.35rem',
                fontSize: '0.7rem',
                opacity: 0.6,
              }}>
                {projects.filter(p => p.status === f.id).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '1rem' }}>
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton" style={{ height: 120, borderRadius: 8 }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
          <p style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>
            {filter === 'all' ? 'No projects yet' : `No ${filter} projects`}
          </p>
          <p style={{ fontSize: '0.82rem' }}>
            Create a project to organize your manufacturing plans.
          </p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: '1rem',
        }}>
          {filtered.map(project => (
            <div
              key={project.id}
              onClick={() => navigate(`/production/projects/${project.id}`)}
              style={{
                padding: '1rem',
                background: '#12121a',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 8,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'rgba(0,212,255,0.2)';
                e.currentTarget.style.background = '#16161f';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
                e.currentTarget.style.background = '#12121a';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {project.name}
                </h3>
                <span style={{
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 3,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  background: `${STATUS_COLORS[project.status]}18`,
                  border: `1px solid ${STATUS_COLORS[project.status]}44`,
                  color: STATUS_COLORS[project.status],
                }}>
                  {project.status}
                </span>
              </div>
              {project.description && (
                <p style={{
                  margin: '0 0 0.5rem 0',
                  fontSize: '0.78rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.4,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {project.description}
                </p>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                <span>{project.item_count} item{project.item_count !== 1 ? 's' : ''}</span>
                <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
                {project.corporation_id ? (
                  <span style={{
                    fontSize: '0.6rem',
                    fontWeight: 600,
                    padding: '1px 6px',
                    borderRadius: 2,
                    background: 'rgba(255,204,0,0.1)',
                    color: '#ffcc00',
                    border: '1px solid rgba(255,204,0,0.2)',
                  }}>CORP</span>
                ) : (
                  <span style={{
                    fontSize: '0.6rem',
                    fontWeight: 600,
                    padding: '1px 6px',
                    borderRadius: 2,
                    background: 'rgba(88,166,255,0.1)',
                    color: '#58a6ff',
                    border: '1px solid rgba(88,166,255,0.2)',
                  }}>PERSONAL</span>
                )}
                <span style={{ marginLeft: 'auto' }}>Updated {timeAgo(project.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.65rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  marginBottom: '0.3rem',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  fontSize: '0.85rem',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 6,
  color: 'var(--text-primary)',
  outline: 'none',
  boxSizing: 'border-box',
};
