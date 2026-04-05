const PLANET_COLORS: Record<string, string> = {
  'Barren': '#6b7280',
  'Gas': '#22c55e',
  'Ice': '#06b6d4',
  'Lava': '#f97316',
  'Oceanic': '#3b82f6',
  'Plasma': '#a855f7',
  'Storm': '#eab308',
  'Temperate': '#10b981',
};

interface PlanetTypeChipProps {
  type: string;
  selected?: boolean;
  onClick?: () => void;
  size?: 'normal' | 'small';
}

export function PlanetTypeChip({ type, selected, onClick, size = 'normal' }: PlanetTypeChipProps) {
  const color = PLANET_COLORS[type] || '#6b7280';

  return (
    <span
      className={`planet-chip ${selected ? 'selected' : ''} ${onClick ? 'clickable' : ''} ${size === 'small' ? 'planet-chip-small' : ''}`}
      style={{
        backgroundColor: selected ? color : 'transparent',
        borderColor: color,
        color: selected ? 'white' : color,
      }}
      onClick={onClick}
    >
      {type}
    </span>
  );
}

export { PLANET_COLORS };
