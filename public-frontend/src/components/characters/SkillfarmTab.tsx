import { useState, useEffect, useCallback } from 'react';
import { formatISK, formatNumber } from '../../utils/format';

interface SkillfarmCharacter {
  character_id: number;
  character_name: string;
  is_skillfarm: boolean;
  total_sp: number;
  sp_per_hour: number;
  sp_per_month: number;
  extractors_per_month: number;
  profit_per_month: number;
  queue_active: boolean;
  training_skill: string | null;
  training_level: number | null;
  queue_ends: string | null;
}

interface MarketPrices {
  injector_price: number;
  extractor_price: number;
  profit_per_extractor: number;
}

interface SkillfarmData {
  characters: SkillfarmCharacter[];
  prices: MarketPrices;
}

interface SkillfarmSummary {
  total_farms: number;
  total_sp_month: number;
  total_profit_month: number;
  extractors_month: number;
  prices: MarketPrices;
}

import axios from 'axios';

const api = axios.create({
  baseURL: '/api/skills/skillfarm',
  timeout: 30000,
  withCredentials: true,
});

const skillfarmApi = {
  getCharacters: async (): Promise<SkillfarmData> => {
    const { data } = await api.get('/characters');
    return data;
  },
  toggleSkillfarm: async (characterId: number) => {
    const { data } = await api.put(`/characters/${characterId}/toggle`);
    return data;
  },
  getSummary: async (): Promise<SkillfarmSummary> => {
    const { data } = await api.get('/summary');
    return data;
  },
};

export function SkillfarmTab() {
  const [data, setData] = useState<SkillfarmData | null>(null);
  const [summary, setSummary] = useState<SkillfarmSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [charData, summaryData] = await Promise.all([
        skillfarmApi.getCharacters(),
        skillfarmApi.getSummary(),
      ]);
      setData(charData);
      setSummary(summaryData);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleFarm = async (characterId: number) => {
    try {
      await skillfarmApi.toggleSkillfarm(characterId);
      load();
    } catch { /* ignore */ }
  };

  if (loading) {
    return <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>Loading skillfarm data...</div>;
  }

  if (!data) {
    return <div style={{ color: 'var(--text-secondary)', padding: '2rem', textAlign: 'center' }}>Failed to load skillfarm data.</div>;
  }

  const cards = summary ? [
    { label: 'Skillfarm Chars', value: String(summary.total_farms), color: '#d29922' },
    { label: 'SP / Month', value: formatNumber(summary.total_sp_month), color: '#00d4ff' },
    { label: 'ISK / Month', value: formatISK(summary.total_profit_month), color: '#3fb950' },
    { label: 'Injector Price', value: formatISK(data.prices.injector_price), color: '#a855f7' },
    { label: 'Extractor Price', value: formatISK(data.prices.extractor_price), color: '#f85149' },
    { label: 'Profit / Extract', value: formatISK(data.prices.profit_per_extractor), color: '#3fb950' },
  ] : [];

  return (
    <div>
      {/* Summary cards */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {cards.map(c => (
            <div key={c.label} style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 8,
              padding: '0.75rem',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: c.color }}>{c.value}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 2 }}>{c.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Character table */}
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              {['', 'Character', 'Total SP', 'SP/h', 'Training', 'Extractors/Mo', 'Profit/Mo', 'Farm'].map(h => (
                <th key={h} style={{
                  padding: '0.75rem 0.5rem',
                  textAlign: h === 'Farm' || h === '' ? 'center' : 'left',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.characters.map(c => (
              <tr key={c.character_id} style={{
                borderBottom: '1px solid var(--border-color)',
                background: c.is_skillfarm ? 'rgba(210,153,34,0.05)' : 'transparent',
              }}>
                <td style={{ padding: '0.5rem', textAlign: 'center', width: 40 }}>
                  <img
                    src={`https://images.evetech.net/characters/${c.character_id}/portrait?size=32`}
                    alt=""
                    style={{ width: 28, height: 28, borderRadius: '50%' }}
                  />
                </td>
                <td style={{ padding: '0.5rem', color: 'var(--text-primary)', fontSize: '0.85rem', fontWeight: 500 }}>
                  {c.character_name}
                </td>
                <td style={{ padding: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {formatNumber(c.total_sp)}
                </td>
                <td style={{ padding: '0.5rem', fontSize: '0.8rem', color: c.sp_per_hour > 0 ? '#00d4ff' : 'var(--text-secondary)' }}>
                  {c.sp_per_hour > 0 ? `${formatNumber(Math.round(c.sp_per_hour))}` : '\u2014'}
                </td>
                <td style={{ padding: '0.5rem' }}>
                  {c.queue_active ? (
                    <div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                        {c.training_skill} {c.training_level ? `L${c.training_level}` : ''}
                      </div>
                      {c.queue_ends && (
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                          {new Date(c.queue_ends).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span style={{ fontSize: '0.8rem', color: '#f85149' }}>Idle</span>
                  )}
                </td>
                <td style={{ padding: '0.5rem', fontSize: '0.8rem', color: c.extractors_per_month > 0 ? '#d29922' : 'var(--text-secondary)' }}>
                  {c.extractors_per_month > 0 ? c.extractors_per_month.toFixed(1) : '\u2014'}
                </td>
                <td style={{ padding: '0.5rem', fontSize: '0.8rem', color: c.profit_per_month > 0 ? '#3fb950' : 'var(--text-secondary)' }}>
                  {c.profit_per_month > 0 ? formatISK(c.profit_per_month) : '\u2014'}
                </td>
                <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                  <button
                    onClick={() => toggleFarm(c.character_id)}
                    title={c.is_skillfarm ? 'Remove from skillfarm' : 'Mark as skillfarm'}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '1.2rem',
                      color: c.is_skillfarm ? '#d29922' : 'var(--text-secondary)',
                      opacity: c.is_skillfarm ? 1 : 0.4,
                    }}
                  >
                    {c.is_skillfarm ? '\u2605' : '\u2606'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
