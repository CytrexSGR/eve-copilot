import { useState, useEffect } from 'react';
import type { ProjectedEffectInput } from '../../types/fittings';
import { boostApi } from '../../services/api/fittings';

interface ProjectedEffectsSectionProps {
  effects: ProjectedEffectInput[];
  onEffectsChange: (effects: ProjectedEffectInput[]) => void;
  label: string;
  color: string;
}

const EFFECT_LABELS: Record<string, string> = {
  web: 'Stasis Web', paint: 'Target Painter', neut: 'Energy Neutralizer',
  remote_shield: 'Remote Shield Rep', remote_armor: 'Remote Armor Rep',
};

const EFFECT_UNITS: Record<string, string> = {
  web: '%', paint: '%', neut: ' GJ', remote_shield: ' HP/s', remote_armor: ' HP/s',
};

const PRESET_LABELS: Record<string, string> = {
  single_web: '1x Web (60%)', double_web: '2x Web (60%)', web_paint: 'Web + Paint',
  heavy_neut: 'Heavy Neut (600 GJ)', double_paint: '2x Paint (30%)',
  logi_shield: '2x Shield Logi (350 HP)', logi_armor: '2x Armor Logi (350 HP)',
};

export default function ProjectedEffectsSection({ effects, onEffectsChange, label, color }: ProjectedEffectsSectionProps) {
  const [presets, setPresets] = useState<Record<string, ProjectedEffectInput[]>>({});
  const [selectedPreset, setSelectedPreset] = useState<string>('');

  useEffect(() => { boostApi.getProjectedPresets().then(setPresets).catch(() => {}); }, []);

  const applyPreset = (key: string) => {
    setSelectedPreset(key);
    if (!key) { onEffectsChange([]); return; }
    const preset = presets[key];
    if (preset) onEffectsChange(preset.map(p => ({
      effect_type: p.effect_type as ProjectedEffectInput['effect_type'],
      strength: p.strength, count: p.count,
    })));
  };

  return (
    <div style={{ marginTop: 8, padding: '6px 8px', background: 'var(--bg-secondary)', borderRadius: 4, border: '1px solid var(--border-color)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 600, color }}>{label}</span>
        {effects.length > 0 && (
          <button onClick={() => { onEffectsChange([]); setSelectedPreset(''); }}
            style={{ background: 'none', border: 'none', color: '#f85149', cursor: 'pointer', fontSize: '0.6rem' }}>Clear</button>
        )}
      </div>
      <select value={selectedPreset} onChange={(e) => applyPreset(e.target.value)}
        style={{ width: '100%', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: 4, padding: '3px 6px', fontSize: '0.65rem', marginBottom: 4, boxSizing: 'border-box' }}>
        <option value="">No projected effects</option>
        {Object.keys(presets).map(key => (
          <option key={key} value={key}>{PRESET_LABELS[key] || key}</option>
        ))}
      </select>
      {effects.map((e, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1px 0', fontSize: '0.65rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            {e.count > 1 ? `${e.count}x ` : ''}{EFFECT_LABELS[e.effect_type] || e.effect_type}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontFamily: 'monospace', color }}>{e.strength}{EFFECT_UNITS[e.effect_type] || ''}</span>
            <button onClick={() => { onEffectsChange(effects.filter((_, idx) => idx !== i)); setSelectedPreset(''); }}
              style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '0.6rem' }}>x</button>
          </div>
        </div>
      ))}
    </div>
  );
}
