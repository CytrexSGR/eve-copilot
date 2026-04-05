import { useState, useEffect } from 'react';
import type { FleetBoostInput, BoostPreset } from '../../types/fittings';
import { boostApi } from '../../services/api/fittings';

interface FleetBoostSectionProps {
  boosts: FleetBoostInput[];
  onBoostsChange: (boosts: FleetBoostInput[]) => void;
}

const PRESET_LABELS: Record<string, string> = {
  shield_t2_max: 'Shield (T2 Max)',
  armor_t2_max: 'Armor (T2 Max)',
  skirmish_t2_max: 'Skirmish (T2 Max)',
  info_t2_max: 'Information (T2 Max)',
};

export default function FleetBoostSection({ boosts, onBoostsChange }: FleetBoostSectionProps) {
  const [presets, setPresets] = useState<Record<string, BoostPreset[]>>({});
  const [selectedPreset, setSelectedPreset] = useState<string>('');

  useEffect(() => { boostApi.getBoostPresets().then(setPresets).catch(() => {}); }, []);

  const boostNames: Record<number, string> = {};
  Object.values(presets).forEach(preset => preset.forEach(p => { boostNames[p.buff_id] = p.name; }));

  const applyPreset = (key: string) => {
    setSelectedPreset(key);
    if (!key) { onBoostsChange([]); return; }
    const preset = presets[key];
    if (preset) onBoostsChange(preset.map(p => ({ buff_id: p.buff_id, value: p.value })));
  };

  const removeBoost = (buffId: number) => {
    onBoostsChange(boosts.filter(b => b.buff_id !== buffId));
    setSelectedPreset('');
  };

  return (
    <div style={{ marginTop: 8, padding: '6px 8px', background: 'var(--bg-secondary)', borderRadius: 4, border: '1px solid var(--border-color)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#00d4ff' }}>Fleet Boosts</span>
        {boosts.length > 0 && (
          <button onClick={() => { onBoostsChange([]); setSelectedPreset(''); }}
            style={{ background: 'none', border: 'none', color: '#f85149', cursor: 'pointer', fontSize: '0.6rem' }}>Clear</button>
        )}
      </div>
      <select value={selectedPreset} onChange={(e) => applyPreset(e.target.value)}
        style={{ width: '100%', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 4, padding: '3px 6px', fontSize: '0.65rem', marginBottom: 4, boxSizing: 'border-box' }}>
        <option value="">No fleet boosts</option>
        {Object.keys(presets).map(key => (
          <option key={key} value={key}>{PRESET_LABELS[key] || key}</option>
        ))}
      </select>
      {boosts.map(b => (
        <div key={b.buff_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1px 0', fontSize: '0.65rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>{boostNames[b.buff_id] || `Buff ${b.buff_id}`}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontFamily: 'monospace', color: b.value > 0 ? '#3fb950' : '#f85149' }}>
              {b.value > 0 ? '+' : ''}{b.value.toFixed(1)}%
            </span>
            <button onClick={() => removeBoost(b.buff_id)}
              style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '0.6rem' }}>x</button>
          </div>
        </div>
      ))}
    </div>
  );
}
