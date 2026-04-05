import { useState, useEffect } from 'react';

interface CorpPageHeaderProps {
  corpId: number;
  title: string;
  subtitle: string;
}

interface CorpEsiInfo {
  name: string;
  ticker: string;
  member_count: number;
  alliance_id?: number;
}

const cache: Record<number, CorpEsiInfo> = {};

export function CorpPageHeader({ corpId, title, subtitle }: CorpPageHeaderProps) {
  const [info, setInfo] = useState<CorpEsiInfo | null>(cache[corpId] || null);

  useEffect(() => {
    if (cache[corpId]) {
      setInfo(cache[corpId]);
      return;
    }
    fetch(`https://esi.evetech.net/latest/corporations/${corpId}/`)
      .then(r => r.json())
      .then(data => {
        const parsed: CorpEsiInfo = {
          name: data.name || `Corporation ${corpId}`,
          ticker: data.ticker || '???',
          member_count: data.member_count || 0,
          alliance_id: data.alliance_id,
        };
        cache[corpId] = parsed;
        setInfo(parsed);
      })
      .catch(() => {
        setInfo({ name: `Corporation ${corpId}`, ticker: '???', member_count: 0 });
      });
  }, [corpId]);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      marginBottom: '1.25rem',
    }}>
      <img
        src={`https://images.evetech.net/corporations/${corpId}/logo?size=64`}
        alt=""
        style={{ width: 44, height: 44, borderRadius: '4px' }}
      />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: '1.3rem', fontWeight: 700, margin: 0 }}>
            {info?.name || '...'}
          </h1>
          {info?.ticker && (
            <span style={{ fontSize: '0.85rem', color: '#8b949e', fontWeight: 600 }}>
              [{info.ticker}]
            </span>
          )}
          <span style={{
            fontSize: '0.7rem',
            color: '#00d4ff',
            background: 'rgba(0,212,255,0.08)',
            border: '1px solid rgba(0,212,255,0.2)',
            padding: '1px 6px',
            borderRadius: '3px',
            fontWeight: 600,
          }}>
            {title}
          </span>
        </div>
        <p style={{ color: '#8b949e', fontSize: '0.78rem', margin: '0.15rem 0 0 0' }}>
          {subtitle}
          {info && info.member_count > 0 && (
            <span style={{ marginLeft: '0.75rem', color: '#6e7681' }}>
              {info.member_count} members
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
