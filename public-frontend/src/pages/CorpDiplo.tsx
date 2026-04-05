import { useState, useEffect, useCallback } from 'react';
import { CorpPageHeader } from '../components/corp/CorpPageHeader';
import { useAuth } from '../hooks/useAuth';
import { diplomacyApi, type StandingEntry, type ContactsSummary, type AlumniMember } from '../services/api/diplomacy';

type DiploTab = 'standings' | 'contacts' | 'alumni';

function standingColor(standing: number): string {
  if (standing > 0) return '#3fb950';
  if (standing < 0) return '#f85149';
  return '#8b949e';
}

function standingBar(standing: number) {
  const pct = Math.min(Math.abs(standing) * 10, 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <div style={{ width: 80, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: standingColor(standing), borderRadius: 3 }} />
      </div>
      <span style={{ color: standingColor(standing), fontSize: '0.8rem', fontWeight: 600, minWidth: 36, textAlign: 'right' }}>
        {standing > 0 ? '+' : ''}{standing.toFixed(1)}
      </span>
    </div>
  );
}

function eveImageUrl(contactType: string, contactId: number): string {
  const folder = contactType === 'character' ? 'characters' : contactType === 'corporation' ? 'corporations' : contactType === 'alliance' ? 'alliances' : 'corporations';
  const suffix = contactType === 'character' ? 'portrait' : 'logo';
  return `https://images.evetech.net/${folder}/${contactId}/${suffix}?size=32`;
}

function typeBadge(type: string) {
  const colors: Record<string, string> = {
    character: '#00d4ff',
    corporation: '#3fb950',
    alliance: '#a855f7',
    faction: '#d29922',
  };
  return (
    <span style={{
      background: `${colors[type] || '#8b949e'}22`,
      color: colors[type] || '#8b949e',
      padding: '2px 8px',
      borderRadius: 4,
      fontSize: '0.75rem',
      fontWeight: 600,
      textTransform: 'capitalize',
    }}>
      {type}
    </span>
  );
}

const thStyle: React.CSSProperties = {
  padding: '0.75rem',
  textAlign: 'left',
  fontSize: '0.75rem',
  color: 'var(--text-secondary)',
  fontWeight: 600,
};

function StandingsTab(_props: { corpId: number }) {
  const [entries, setEntries] = useState<StandingEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await diplomacyApi.getStandings({ contact_type: filter || undefined, limit: 300 });
      setEntries(data.entries);
    } catch { /* ignore */ }
    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {['', 'character', 'corporation', 'alliance', 'faction'].map(t => (
          <button key={t} onClick={() => setFilter(t)} style={{
            background: filter === t ? 'rgba(63,185,80,0.15)' : 'transparent',
            border: filter === t ? '1px solid rgba(63,185,80,0.4)' : '1px solid var(--border-color)',
            color: filter === t ? '#3fb950' : 'var(--text-secondary)',
            padding: '4px 12px', borderRadius: 4, cursor: 'pointer', fontSize: '0.8rem',
          }}>
            {t || 'All'}
          </button>
        ))}
      </div>
      {loading ? (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>Loading standings...</div>
      ) : entries.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>No standings data found.</div>
      ) : (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={thStyle}>Entity</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Standing</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr key={`${e.contact_id}-${e.contact_type}`} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '0.6rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <img
                      src={eveImageUrl(e.contact_type, e.contact_id)}
                      alt=""
                      style={{ width: 28, height: 28, borderRadius: e.contact_type === 'character' ? '50%' : 4 }}
                    />
                    <span style={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}>{e.contact_name || `ID ${e.contact_id}`}</span>
                  </td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>{typeBadge(e.contact_type)}</td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>{standingBar(e.standing)}</td>
                  <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                    {e.is_watched && <span title="Watched" style={{ marginRight: 4 }}>&#128065;</span>}
                    {e.is_blocked && <span title="Blocked" style={{ color: '#f85149' }}>&#9940;</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ContactsTab(_props: { corpId: number }) {
  const [summary, setSummary] = useState<ContactsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [watchedOnly, setWatchedOnly] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await diplomacyApi.getContacts({
        contact_type: filter || undefined,
        watched_only: watchedOnly || undefined,
        limit: 300,
      });
      setSummary(data);
    } catch { /* ignore */ }
    setLoading(false);
  }, [filter, watchedOnly]);

  useEffect(() => { load(); }, [load]);

  const cards = summary ? [
    { label: 'Total', value: summary.total, color: '#00d4ff' },
    { label: 'Positive', value: summary.positive, color: '#3fb950' },
    { label: 'Negative', value: summary.negative, color: '#f85149' },
    { label: 'Watched', value: summary.watched, color: '#d29922' },
    { label: 'Blocked', value: summary.blocked, color: '#f85149' },
  ] : [];

  return (
    <div>
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
          {cards.map(c => (
            <div key={c.label} style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, padding: '0.75rem', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: c.color }}>{c.value}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{c.label}</div>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {['', 'character', 'corporation', 'alliance', 'faction'].map(t => (
          <button key={t} onClick={() => setFilter(t)} style={{
            background: filter === t ? 'rgba(0,212,255,0.15)' : 'transparent',
            border: filter === t ? '1px solid rgba(0,212,255,0.4)' : '1px solid var(--border-color)',
            color: filter === t ? '#00d4ff' : 'var(--text-secondary)',
            padding: '4px 12px', borderRadius: 4, cursor: 'pointer', fontSize: '0.8rem',
          }}>
            {t || 'All'}
          </button>
        ))}
        <button onClick={() => setWatchedOnly(!watchedOnly)} style={{
          background: watchedOnly ? 'rgba(210,153,34,0.15)' : 'transparent',
          border: watchedOnly ? '1px solid rgba(210,153,34,0.4)' : '1px solid var(--border-color)',
          color: watchedOnly ? '#d29922' : 'var(--text-secondary)',
          padding: '4px 12px', borderRadius: 4, cursor: 'pointer', fontSize: '0.8rem',
        }}>
          Watched Only
        </button>
      </div>
      {loading ? (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>Loading contacts...</div>
      ) : !summary || summary.contacts.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>No contacts found.</div>
      ) : (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={thStyle}>Entity</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Standing</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {summary.contacts.map(e => (
                <tr key={`${e.contact_id}-${e.contact_type}`} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '0.6rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <img
                      src={eveImageUrl(e.contact_type, e.contact_id)}
                      alt=""
                      style={{ width: 28, height: 28, borderRadius: e.contact_type === 'character' ? '50%' : 4 }}
                    />
                    <span style={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}>{e.contact_name || `ID ${e.contact_id}`}</span>
                  </td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>{typeBadge(e.contact_type)}</td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>{standingBar(e.standing)}</td>
                  <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                    {e.is_watched && <span title="Watched" style={{ marginRight: 4 }}>&#128065;</span>}
                    {e.is_blocked && <span title="Blocked" style={{ color: '#f85149' }}>&#9940;</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AlumniTab(_props: { corpId: number }) {
  const [alumni, setAlumni] = useState<AlumniMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [noteText, setNoteText] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await diplomacyApi.getAlumni({ limit: 100 });
      setAlumni(data.alumni);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveNote = async (member: AlumniMember) => {
    try {
      await diplomacyApi.upsertAlumniNote({
        character_id: member.character_id,
        character_name: member.character_name,
        note: noteText,
      });
      setEditingId(null);
      load();
    } catch { /* ignore */ }
  };

  return (
    <div>
      {loading ? (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>Loading alumni...</div>
      ) : alumni.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>No alumni records found.</div>
      ) : (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={thStyle}>Character</th>
                <th style={thStyle}>Left</th>
                <th style={thStyle}>Destination</th>
                <th style={thStyle}>Note</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alumni.map(m => (
                <tr key={m.character_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '0.6rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <img
                      src={`https://images.evetech.net/characters/${m.character_id}/portrait?size=32`}
                      alt=""
                      style={{ width: 28, height: 28, borderRadius: '50%' }}
                    />
                    <span style={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}>{m.character_name}</span>
                  </td>
                  <td style={{ padding: '0.6rem 0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {m.left_at ? new Date(m.left_at).toLocaleDateString() : '\u2014'}
                  </td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>
                    {m.destination_corp_name ? (
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{m.destination_corp_name}</span>
                    ) : (
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Unknown</span>
                    )}
                  </td>
                  <td style={{ padding: '0.6rem 0.75rem' }}>
                    {editingId === m.character_id ? (
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <input
                          value={noteText}
                          onChange={e => setNoteText(e.target.value)}
                          style={{ flex: 1, background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 4, padding: '4px 8px', color: 'var(--text-primary)', fontSize: '0.8rem' }}
                          placeholder="Add note..."
                        />
                        <button onClick={() => saveNote(m)} style={{ background: '#3fb950', color: '#000', border: 'none', borderRadius: 4, padding: '4px 10px', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}>Save</button>
                        <button onClick={() => setEditingId(null)} style={{ background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: 4, padding: '4px 10px', cursor: 'pointer', fontSize: '0.8rem' }}>Cancel</button>
                      </div>
                    ) : (
                      <span style={{ fontSize: '0.8rem', color: m.note ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {m.note || '\u2014'}
                        {m.noted_by_name && <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginLeft: 4 }}>({m.noted_by_name})</span>}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                    <button
                      onClick={() => { setEditingId(m.character_id); setNoteText(m.note || ''); }}
                      style={{ background: 'transparent', border: '1px solid var(--border-color)', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '0.8rem' }}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function CorpDiplo() {
  const [activeTab, setActiveTab] = useState<DiploTab>('standings');
  const { account } = useAuth();
  const corpId = account?.corporation_id;

  const tabs: { id: DiploTab; label: string; color: string }[] = [
    { id: 'standings', label: 'Standings', color: '#3fb950' },
    { id: 'contacts', label: 'Contacts', color: '#00d4ff' },
    { id: 'alumni', label: 'Alumni', color: '#d29922' },
  ];

  return (
    <div>
      {corpId && <CorpPageHeader corpId={corpId} title="Diplomacy" subtitle="Corp standings, contacts, and alumni tracking" />}

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

          {activeTab === 'standings' && <StandingsTab corpId={corpId} />}
          {activeTab === 'contacts' && <ContactsTab corpId={corpId} />}
          {activeTab === 'alumni' && <AlumniTab corpId={corpId} />}
        </>
      )}
    </div>
  );
}
