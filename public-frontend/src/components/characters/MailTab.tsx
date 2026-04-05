import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/character',
  timeout: 30000,
  withCredentials: true,
});

interface MailHeader {
  mail_id: number;
  subject: string;
  from_id: number;
  from_name: string;
  timestamp: string;
  labels: number[];
  is_read: boolean;
}

interface MailBody {
  mail_id: number;
  subject: string;
  from_id: number;
  from_name: string;
  body: string;
  timestamp: string;
  labels: number[];
  is_read: boolean;
  recipients: { recipient_id: number; recipient_name: string; recipient_type: string }[];
}

interface MailLabel {
  label_id: number;
  name: string;
  color: string | null;
  unread_count: number;
}

interface MailTabProps {
  characterId: number;
}

export function MailTab({ characterId }: MailTabProps) {
  const [mails, setMails] = useState<MailHeader[]>([]);
  const [labels, setLabels] = useState<MailLabel[]>([]);
  const [totalUnread, setTotalUnread] = useState(0);
  const [selectedMail, setSelectedMail] = useState<MailBody | null>(null);
  const [loading, setLoading] = useState(true);
  const [bodyLoading, setBodyLoading] = useState(false);
  const [activeLabel, setActiveLabel] = useState<number | null>(null);

  const loadMails = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      if (activeLabel !== null) params.labels = activeLabel;
      const { data } = await api.get(`/mail/${characterId}`, { params });
      setMails(data.mails || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, [characterId, activeLabel]);

  const loadLabels = useCallback(async () => {
    try {
      const { data } = await api.get(`/mail/${characterId}/labels`);
      setLabels(data.labels || []);
      setTotalUnread(data.total_unread || 0);
    } catch { /* ignore */ }
  }, [characterId]);

  useEffect(() => { loadMails(); loadLabels(); }, [loadMails, loadLabels]);

  const openMail = async (mailId: number) => {
    setBodyLoading(true);
    try {
      const { data } = await api.get(`/mail/${characterId}/${mailId}`);
      setSelectedMail(data);
    } catch { /* ignore */ }
    setBodyLoading(false);
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = diffMs / (1000 * 60 * 60);
    if (diffH < 24) return `${Math.floor(diffH)}h ago`;
    if (diffH < 48) return 'Yesterday';
    return d.toLocaleDateString();
  };

  const labelName = (id: number) => {
    const l = labels.find(lb => lb.label_id === id);
    return l?.name || `Label ${id}`;
  };

  return (
    <div style={{ display: 'flex', gap: '1rem', minHeight: 400 }}>
      {/* Left panel - mail list */}
      <div style={{ width: 380, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {/* Label filters */}
        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          <button
            onClick={() => setActiveLabel(null)}
            style={{
              background: activeLabel === null ? 'rgba(0,212,255,0.15)' : 'transparent',
              border: activeLabel === null ? '1px solid rgba(0,212,255,0.4)' : '1px solid var(--border-color)',
              color: activeLabel === null ? '#00d4ff' : 'var(--text-secondary)',
              padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: '0.7rem',
            }}
          >
            All {totalUnread > 0 && `(${totalUnread})`}
          </button>
          {labels.map(l => (
            <button
              key={l.label_id}
              onClick={() => setActiveLabel(l.label_id)}
              style={{
                background: activeLabel === l.label_id ? 'rgba(0,212,255,0.15)' : 'transparent',
                border: activeLabel === l.label_id ? '1px solid rgba(0,212,255,0.4)' : '1px solid var(--border-color)',
                color: activeLabel === l.label_id ? '#00d4ff' : 'var(--text-secondary)',
                padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: '0.7rem',
              }}
            >
              {l.name} {l.unread_count > 0 && `(${l.unread_count})`}
            </button>
          ))}
        </div>

        {/* Mail list */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 8,
          overflow: 'auto',
          maxHeight: 500,
        }}>
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading mail...</div>
          ) : mails.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No mail found.</div>
          ) : (
            mails.map(m => (
              <div
                key={m.mail_id}
                onClick={() => openMail(m.mail_id)}
                style={{
                  padding: '0.6rem 0.75rem',
                  borderBottom: '1px solid var(--border-color)',
                  cursor: 'pointer',
                  background: selectedMail?.mail_id === m.mail_id ? 'rgba(0,212,255,0.08)' : 'transparent',
                  transition: 'background 0.15s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {!m.is_read && (
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: '#00d4ff', flexShrink: 0,
                    }} />
                  )}
                  <img
                    src={`https://images.evetech.net/characters/${m.from_id}/portrait?size=32`}
                    alt=""
                    style={{ width: 24, height: 24, borderRadius: '50%', flexShrink: 0 }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '0.8rem',
                      color: 'var(--text-primary)',
                      fontWeight: m.is_read ? 400 : 600,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {m.subject}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      {m.from_name}
                    </div>
                  </div>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', flexShrink: 0 }}>
                    {formatDate(m.timestamp)}
                  </span>
                </div>
                {m.labels.length > 0 && (
                  <div style={{ display: 'flex', gap: '0.25rem', marginTop: 3, marginLeft: 30 }}>
                    {m.labels.map(lid => (
                      <span key={lid} style={{
                        fontSize: '0.6rem',
                        background: 'rgba(168,85,247,0.15)',
                        color: '#a855f7',
                        padding: '1px 5px',
                        borderRadius: 3,
                      }}>
                        {labelName(lid)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right panel - mail body */}
      <div style={{
        flex: 1,
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: '1rem',
        overflow: 'auto',
        maxHeight: 560,
      }}>
        {bodyLoading ? (
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '3rem' }}>Loading...</div>
        ) : !selectedMail ? (
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '3rem' }}>
            Select a mail to read.
          </div>
        ) : (
          <div>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: 'var(--text-primary)' }}>
              {selectedMail.subject}
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <img
                src={`https://images.evetech.net/characters/${selectedMail.from_id}/portrait?size=32`}
                alt=""
                style={{ width: 28, height: 28, borderRadius: '50%' }}
              />
              <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                  {selectedMail.from_name}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  {new Date(selectedMail.timestamp).toLocaleString()}
                  {selectedMail.recipients.length > 0 && (
                    <span> &middot; To: {selectedMail.recipients.map(r => r.recipient_name).join(', ')}</span>
                  )}
                </div>
              </div>
            </div>
            <div style={{
              borderTop: '1px solid var(--border-color)',
              paddingTop: '0.75rem',
              fontSize: '0.85rem',
              color: 'var(--text-primary)',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
              dangerouslySetInnerHTML={{ __html: selectedMail.body }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
