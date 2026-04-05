import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { orgApi } from '../services/api/auth';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import type {
  OrgMember,
  OrgOverview,
  OrgPermissionsResponse,
  AuditLogEntry,
} from '../types/auth';

type Tab = 'members' | 'permissions' | 'audit';

// ── Helpers ──────────────────────────────────────────


function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

const PERMISSION_LABELS: Record<string, string> = {
  'members.view': 'View Members',
  'members.manage': 'Manage Members',
  'roles.assign': 'Assign Roles',
  'permissions.manage': 'Manage Permissions',
  'audit.view': 'View Audit Log',
  'audit.export': 'Export Audit Log',
  'finance.view': 'View Finance',
  'finance.manage': 'Manage Finance',
  'srp.view': 'View SRP',
  'srp.manage': 'Manage SRP',
  'fleet.view': 'View Fleet',
  'fleet.manage': 'Manage Fleet',
  'hr.view': 'View HR',
  'hr.manage': 'Manage HR',
  'timers.view': 'View Timers',
  'timers.manage': 'Manage Timers',
  'tools.view': 'View Tools',
  'tools.manage': 'Manage Tools',
};

const ACTION_COLORS: Record<string, string> = {
  'permission.updated': '#3fb950',
  'member.removed': '#f85149',
  'role.changed': '#58a6ff',
  'member.added': '#3fb950',
  'member.invited': '#d29922',
};

// ── Styles ───────────────────────────────────────────

const cardStyle: React.CSSProperties = {
  background: '#16213e',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '8px',
  padding: '1rem 1.25rem',
  flex: '1 1 0',
  minWidth: '160px',
};

const cardLabelStyle: React.CSSProperties = {
  color: '#8b949e',
  fontSize: '0.75rem',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: '0.35rem',
};

const cardValueStyle: React.CSSProperties = {
  color: '#e6edf3',
  fontSize: '1.5rem',
  fontWeight: 700,
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '0.85rem',
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '0.6rem 0.75rem',
  color: '#8b949e',
  fontSize: '0.75rem',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  borderBottom: '1px solid rgba(255,255,255,0.08)',
};

const tdStyle: React.CSSProperties = {
  padding: '0.6rem 0.75rem',
  color: '#e0e0e0',
  borderBottom: '1px solid rgba(255,255,255,0.04)',
  verticalAlign: 'middle',
};

const btnPrimary: React.CSSProperties = {
  background: 'linear-gradient(135deg, #0f3460, #1a3a5c)',
  border: '1px solid rgba(0, 212, 255, 0.3)',
  color: '#00d4ff',
  padding: '0.45rem 1rem',
  borderRadius: '6px',
  fontSize: '0.8rem',
  fontWeight: 600,
  cursor: 'pointer',
};

const btnDanger: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid rgba(248, 81, 73, 0.4)',
  color: '#f85149',
  padding: '0.3rem 0.65rem',
  borderRadius: '4px',
  fontSize: '0.75rem',
  fontWeight: 500,
  cursor: 'pointer',
};

const selectStyle: React.CSSProperties = {
  background: '#1a1a2e',
  border: '1px solid rgba(255,255,255,0.12)',
  color: '#e0e0e0',
  padding: '0.3rem 0.5rem',
  borderRadius: '4px',
  fontSize: '0.8rem',
  cursor: 'pointer',
};

const inputStyle: React.CSSProperties = {
  background: '#1a1a2e',
  border: '1px solid rgba(255,255,255,0.12)',
  color: '#e0e0e0',
  padding: '0.35rem 0.6rem',
  borderRadius: '4px',
  fontSize: '0.8rem',
};

// ── Toast ────────────────────────────────────────────

function Toast({ message, type, onClose }: { message: string; type: 'success' | 'error'; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div style={{
      position: 'fixed',
      bottom: '1.5rem',
      right: '1.5rem',
      background: type === 'success' ? '#0d2f1b' : '#2d0d0d',
      border: `1px solid ${type === 'success' ? '#3fb95066' : '#f8514966'}`,
      color: type === 'success' ? '#3fb950' : '#f85149',
      padding: '0.75rem 1.25rem',
      borderRadius: '8px',
      fontSize: '0.85rem',
      fontWeight: 500,
      zIndex: 9999,
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    }}>
      {message}
    </div>
  );
}

// ── Members Tab ──────────────────────────────────────

function MembersTab({ userRole }: { userRole: string | null }) {
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [overview, setOverview] = useState<OrgOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, o] = await Promise.all([orgApi.getMembers(), orgApi.getOverview()]);
      setMembers(m);
      setOverview(o);
    } catch {
      setToast({ message: 'Failed to load member data', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRoleChange = async (charId: number, newRole: string) => {
    try {
      await orgApi.changeRole(charId, newRole);
      setMembers(prev => prev.map(m =>
        m.primary_character_id === charId ? { ...m, role: newRole } : m
      ));
      setToast({ message: 'Role updated successfully', type: 'success' });
    } catch {
      setToast({ message: 'Failed to update role', type: 'error' });
    }
  };

  const handleRemove = async (charId: number) => {
    try {
      await orgApi.removeMember(charId);
      setMembers(prev => prev.filter(m => m.primary_character_id !== charId));
      setConfirmRemove(null);
      setToast({ message: 'Member removed', type: 'success' });
    } catch {
      setToast({ message: 'Failed to remove member', type: 'error' });
    }
  };

  const tokenDot = (status: string) => {
    const color = status === 'valid' ? '#4caf50' : status === 'expired' ? '#f44336' : '#666';
    return (
      <span style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: color,
        boxShadow: status === 'valid' ? '0 0 6px #4caf5066' : undefined,
      }} title={status} />
    );
  };

  if (loading) {
    return <div style={{ color: '#8b949e', padding: '2rem', textAlign: 'center' }}>Loading members...</div>;
  }

  return (
    <div>
      {/* Overview Cards */}
      {overview && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <div style={cardStyle}>
            <div style={cardLabelStyle}>Member Count</div>
            <div style={cardValueStyle}>{overview.member_count}</div>
          </div>
          <div style={cardStyle}>
            <div style={cardLabelStyle}>Token Coverage</div>
            <div style={cardValueStyle}>{overview.token_coverage_pct.toFixed(0)}%</div>
          </div>
          <div style={cardStyle}>
            <div style={cardLabelStyle}>Active (7d)</div>
            <div style={cardValueStyle}>{overview.active_7d}</div>
          </div>
          <div style={cardStyle}>
            <div style={cardLabelStyle}>Role Distribution</div>
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem', flexWrap: 'wrap' }}>
              {Object.entries(overview.role_distribution).map(([role, count]) => (
                <span key={role} style={{ color: '#e0e0e0', fontSize: '0.8rem' }}>
                  <span style={{ color: '#00d4ff', fontWeight: 600 }}>{count}</span>{' '}
                  <span style={{ color: '#8b949e' }}>{role}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Members Table */}
      <div style={{
        background: '#16213e',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Pilot</th>
              <th style={thStyle}>Role</th>
              <th style={thStyle}>Token</th>
              <th style={thStyle}>Last Login</th>
              {userRole === 'admin' && <th style={thStyle}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {members.map(member => (
              <tr key={member.primary_character_id}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={tdStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <img
                      src={`https://images.evetech.net/characters/${member.primary_character_id}/portrait?size=32`}
                      alt=""
                      style={{ width: 32, height: 32, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)' }}
                    />
                    <span style={{ fontWeight: 500 }}>{member.primary_character_name}</span>
                  </div>
                </td>
                <td style={tdStyle}>
                  <select
                    value={member.role || 'member'}
                    onChange={e => handleRoleChange(member.primary_character_id, e.target.value)}
                    style={selectStyle}
                    disabled={userRole !== 'admin' && userRole !== 'officer'}
                  >
                    <option value="admin">Admin</option>
                    <option value="officer">Officer</option>
                    <option value="member">Member</option>
                  </select>
                </td>
                <td style={tdStyle}>{tokenDot(member.token_status)}</td>
                <td style={tdStyle}>{formatDate(member.last_login)}</td>
                {userRole === 'admin' && (
                  <td style={tdStyle}>
                    {confirmRemove === member.primary_character_id ? (
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        <span style={{ color: '#f85149', fontSize: '0.75rem' }}>Confirm?</span>
                        <button
                          onClick={() => handleRemove(member.primary_character_id)}
                          style={{ ...btnDanger, background: '#f8514922' }}
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => setConfirmRemove(null)}
                          style={{ ...btnDanger, color: '#8b949e', borderColor: 'rgba(255,255,255,0.12)' }}
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmRemove(member.primary_character_id)}
                        style={btnDanger}
                      >
                        Remove
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {members.length === 0 && (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e' }}>
            No members found.
          </div>
        )}
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ── Permissions Tab ──────────────────────────────────

function PermissionsTab() {
  const [permData, setPermData] = useState<OrgPermissionsResponse | null>(null);
  const [changes, setChanges] = useState<Map<string, boolean>>(new Map());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    orgApi.getPermissions()
      .then(data => setPermData(data))
      .catch(() => setToast({ message: 'Failed to load permissions', type: 'error' }))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !permData) {
    return <div style={{ color: '#8b949e', padding: '2rem', textAlign: 'center' }}>Loading permissions...</div>;
  }

  const { permissions, all_permissions, all_roles } = permData;

  const isGranted = (role: string, perm: string): boolean => {
    const key = `${role}:${perm}`;
    if (changes.has(key)) return changes.get(key)!;
    const entry = permissions.find(p => p.role === role && p.permission === perm);
    return entry?.granted ?? false;
  };

  const togglePerm = (role: string, perm: string) => {
    if (role === 'admin') return; // admin always has all
    const key = `${role}:${perm}`;
    const current = isGranted(role, perm);
    setChanges(prev => {
      const next = new Map(prev);
      next.set(key, !current);
      return next;
    });
  };

  const handleSave = async () => {
    if (changes.size === 0) return;
    setSaving(true);
    try {
      const updates = Array.from(changes.entries()).map(([key, granted]) => {
        const [role, permission] = key.split(':');
        return { role, permission, granted };
      });
      await orgApi.updatePermissions(updates);
      // Reload to get fresh state
      const fresh = await orgApi.getPermissions();
      setPermData(fresh);
      setChanges(new Map());
      setToast({ message: 'Permissions saved successfully', type: 'success' });
    } catch {
      setToast({ message: 'Failed to save permissions', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div style={{
        background: '#16213e',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Permission</th>
              {all_roles.map(role => (
                <th key={role} style={{ ...thStyle, textAlign: 'center' }}>
                  {role.charAt(0).toUpperCase() + role.slice(1)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {all_permissions.map(perm => (
              <tr key={perm}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={tdStyle}>
                  {PERMISSION_LABELS[perm] || perm}
                </td>
                {all_roles.map(role => {
                  const checked = role === 'admin' ? true : isGranted(role, perm);
                  const key = `${role}:${perm}`;
                  const hasChange = changes.has(key);
                  return (
                    <td key={role} style={{ ...tdStyle, textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={role === 'admin'}
                        onChange={() => togglePerm(role, perm)}
                        style={{
                          cursor: role === 'admin' ? 'not-allowed' : 'pointer',
                          accentColor: '#00d4ff',
                          width: 16,
                          height: 16,
                          outline: hasChange ? '2px solid #d29922' : undefined,
                          outlineOffset: '2px',
                        }}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '1rem',
      }}>
        <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>
          {changes.size > 0
            ? `${changes.size} unsaved change${changes.size > 1 ? 's' : ''}`
            : 'No changes'}
        </span>
        <button
          onClick={handleSave}
          disabled={changes.size === 0 || saving}
          style={{
            ...btnPrimary,
            opacity: changes.size === 0 || saving ? 0.5 : 1,
            cursor: changes.size === 0 || saving ? 'not-allowed' : 'pointer',
          }}
        >
          {saving ? 'Saving...' : 'Save Permissions'}
        </button>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ── Audit Log Tab ────────────────────────────────────

function AuditLogTab() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const PAGE_SIZE = 50;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
      if (actionFilter) params.action = actionFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const data = await orgApi.getAuditLog(params as Parameters<typeof orgApi.getAuditLog>[0]);
      setEntries(data.entries);
      setTotal(data.total);
    } catch {
      setToast({ message: 'Failed to load audit log', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const handleExportCsv = async () => {
    try {
      const blob = await orgApi.exportAuditCsv();
      const url = URL.createObjectURL(blob as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setToast({ message: 'CSV exported', type: 'success' });
    } catch {
      setToast({ message: 'Failed to export CSV', type: 'error' });
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const actionBadge = (action: string) => {
    const bg = ACTION_COLORS[action] || '#8b949e';
    return (
      <span style={{
        display: 'inline-block',
        padding: '0.15rem 0.5rem',
        borderRadius: '4px',
        fontSize: '0.7rem',
        fontWeight: 600,
        background: `${bg}22`,
        color: bg,
        border: `1px solid ${bg}44`,
        whiteSpace: 'nowrap',
      }}>
        {action}
      </span>
    );
  };

  // Collect unique actions for filter dropdown
  const knownActions = ['role.changed', 'member.removed', 'member.added', 'permission.updated', 'member.invited'];

  return (
    <div>
      {/* Filters */}
      <div style={{
        display: 'flex',
        gap: '0.75rem',
        marginBottom: '1rem',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        <select
          value={actionFilter}
          onChange={e => { setActionFilter(e.target.value); setPage(0); }}
          style={selectStyle}
        >
          <option value="">All Actions</option>
          {knownActions.map(a => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={e => { setDateFrom(e.target.value); setPage(0); }}
          style={inputStyle}
          placeholder="From"
        />
        <input
          type="date"
          value={dateTo}
          onChange={e => { setDateTo(e.target.value); setPage(0); }}
          style={inputStyle}
          placeholder="To"
        />
        <div style={{ marginLeft: 'auto' }}>
          <button onClick={handleExportCsv} style={btnPrimary}>
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{
        background: '#16213e',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Timestamp</th>
              <th style={thStyle}>Actor</th>
              <th style={thStyle}>Action</th>
              <th style={thStyle}>Target</th>
              <th style={thStyle}>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: '#8b949e', padding: '2rem' }}>
                  Loading...
                </td>
              </tr>
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: '#8b949e', padding: '2rem' }}>
                  No audit entries found.
                </td>
              </tr>
            ) : entries.map(entry => (
              <tr key={entry.id}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ ...tdStyle, whiteSpace: 'nowrap', fontSize: '0.8rem' }}>
                  {formatTimestamp(entry.created_at)}
                </td>
                <td style={tdStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <img
                      src={`https://images.evetech.net/characters/${entry.actor_character_id}/portrait?size=32`}
                      alt=""
                      style={{ width: 24, height: 24, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)' }}
                    />
                    <span style={{ fontSize: '0.8rem' }}>{entry.actor_name}</span>
                  </div>
                </td>
                <td style={tdStyle}>{actionBadge(entry.action)}</td>
                <td style={{ ...tdStyle, fontSize: '0.8rem' }}>{entry.target_name || '—'}</td>
                <td style={{ ...tdStyle, fontSize: '0.75rem', color: '#8b949e', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {entry.details && Object.keys(entry.details).length > 0
                    ? JSON.stringify(entry.details)
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '1rem',
      }}>
        <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>
          {total} total entries
        </span>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{
              ...btnPrimary,
              opacity: page === 0 ? 0.4 : 1,
              cursor: page === 0 ? 'not-allowed' : 'pointer',
              padding: '0.35rem 0.75rem',
            }}
          >
            Previous
          </button>
          <span style={{ color: '#e0e0e0', fontSize: '0.8rem' }}>
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page + 1 >= totalPages}
            style={{
              ...btnPrimary,
              opacity: page + 1 >= totalPages ? 0.4 : 1,
              cursor: page + 1 >= totalPages ? 'not-allowed' : 'pointer',
              padding: '0.35rem 0.75rem',
            }}
          >
            Next
          </button>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ── Main Component ───────────────────────────────────

export default function CorpMembers() {
  const [activeTab, setActiveTab] = useState<Tab>('members');
  const { account } = useAuth();

  const corpId = account?.corporation_id;

  // Determine user role from account — assume the primary character's org role
  // We fetch members and check current user's role
  const [userRole, setUserRole] = useState<string | null>(null);
  useEffect(() => {
    if (!account) return;
    orgApi.getMembers().then(members => {
      const me = members.find(m => m.primary_character_id === account.primary_character_id);
      setUserRole(me?.role || 'member');
    }).catch(() => setUserRole('member'));
  }, [account]);

  const tabs: { id: Tab; label: string; color: string }[] = [
    { id: 'members', label: 'Members', color: '#00d4ff' },
    { id: 'permissions', label: 'Permissions', color: '#d29922' },
    { id: 'audit', label: 'Audit Log', color: '#a855f7' },
  ];

  return (
    <div>
      {corpId && (
        <CorpPageHeader
          corpId={corpId}
          title="Members"
          subtitle="Member management, permissions, and audit log"
        />
      )}

      {!corpId ? (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '2rem',
          textAlign: 'center',
          color: 'var(--text-secondary)',
        }}>
          No corporation found. Please ensure your character is in a corporation.
        </div>
      ) : (
        <>
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            marginBottom: '1.5rem',
            borderBottom: '1px solid var(--border-color)',
            paddingBottom: '0.5rem',
          }}>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: activeTab === tab.id ? `${tab.color}15` : 'transparent',
                  border: activeTab === tab.id ? `1px solid ${tab.color}44` : '1px solid transparent',
                  color: activeTab === tab.id ? tab.color : 'var(--text-secondary)',
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: activeTab === tab.id ? 600 : 400,
                  transition: 'all 0.2s',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'members' && <MembersTab userRole={userRole} />}
          {activeTab === 'permissions' && <PermissionsTab />}
          {activeTab === 'audit' && <AuditLogTab />}
        </>
      )}
    </div>
  );
}
