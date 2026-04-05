/**
 * SVG icon definitions for battle status levels.
 * Each icon is loaded as a data URL and drawn on the canvas.
 */

export interface BattleIconRefs {
  skull: HTMLImageElement | null;
  gank: HTMLImageElement | null;
  brawl: HTMLImageElement | null;
  battle: HTMLImageElement | null;
  hellcamp: HTMLImageElement | null;
}

const SKULL_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g fill="none" stroke="#ff4444" stroke-width="2" filter="url(#glow)">
    <path d="M32 8 C18 8 10 18 10 30 C10 38 14 44 18 48 L18 56 L26 56 L26 52 L30 56 L34 56 L38 52 L38 56 L46 56 L46 48 C50 44 54 38 54 30 C54 18 46 8 32 8Z"/>
    <circle cx="24" cy="30" r="6"/>
    <circle cx="40" cy="30" r="6"/>
    <path d="M32 38 L28 44 L36 44 Z"/>
    <line x1="4" y1="30" x2="10" y2="30"/>
    <line x1="54" y1="30" x2="60" y2="30"/>
    <circle cx="4" cy="30" r="2" fill="#ff4444"/>
    <circle cx="60" cy="30" r="2" fill="#ff4444"/>
  </g>
</svg>`;

const GANK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <filter id="gankglow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g fill="none" stroke="#ff4444" stroke-width="2.5" filter="url(#gankglow)">
    <path d="M32 8 L38 44 L32 52 L26 44 Z" fill="#ff4444" fill-opacity="0.3"/>
    <path d="M32 8 L38 44 L32 52 L26 44 Z"/>
    <line x1="22" y1="44" x2="42" y2="44" stroke-width="3"/>
    <line x1="32" y1="44" x2="32" y2="58"/>
    <circle cx="32" cy="58" r="3" fill="#ff4444"/>
  </g>
</svg>`;

const BRAWL_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <filter id="brawlglow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g fill="none" stroke="#ff8800" stroke-width="2.5" filter="url(#brawlglow)">
    <line x1="12" y1="52" x2="42" y2="12" stroke-width="3"/>
    <line x1="8" y1="48" x2="16" y2="56"/>
    <line x1="10" y1="44" x2="18" y2="48"/>
    <line x1="52" y1="52" x2="22" y2="12" stroke-width="3"/>
    <line x1="56" y1="48" x2="48" y2="56"/>
    <line x1="54" y1="44" x2="46" y2="48"/>
    <circle cx="32" cy="32" r="4" fill="#ff8800"/>
  </g>
</svg>`;

const BATTLE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <filter id="battleglow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="1.5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g fill="none" stroke="#ffcc00" stroke-width="2" filter="url(#battleglow)">
    <polygon points="32,4 56,18 56,46 32,60 8,46 8,18"/>
    <line x1="18" y1="46" x2="46" y2="18" stroke-width="3"/>
    <line x1="46" y1="46" x2="18" y2="18" stroke-width="3"/>
    <line x1="14" y1="50" x2="22" y2="42"/>
    <line x1="50" y1="50" x2="42" y2="42"/>
    <line x1="14" y1="14" x2="22" y2="22"/>
    <line x1="50" y1="14" x2="42" y2="22"/>
    <polygon points="32,26 38,32 32,38 26,32" fill="#ffcc00"/>
  </g>
</svg>`;

const HELLCAMP_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <filter id="hellglow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g fill="none" stroke="#00ffff" stroke-width="2" filter="url(#hellglow)">
    <polygon points="32,2 58,17 58,47 32,62 6,47 6,17"/>
    <polygon points="32,12 48,22 48,42 32,52 16,42 16,22" fill="#00ffff" fill-opacity="0.2"/>
    <path d="M20 8 Q18 16 22 20 Q16 18 20 8" stroke-width="1.5"/>
    <path d="M44 8 Q46 16 42 20 Q48 18 44 8" stroke-width="1.5"/>
    <path d="M8 32 Q14 28 16 32 Q12 26 8 32" stroke-width="1.5"/>
    <path d="M56 32 Q50 28 48 32 Q52 26 56 32" stroke-width="1.5"/>
    <path d="M20 56 Q18 48 22 44 Q16 46 20 56" stroke-width="1.5"/>
    <path d="M44 56 Q46 48 42 44 Q48 46 44 56" stroke-width="1.5"/>
    <circle cx="32" cy="32" r="6" fill="#00ffff"/>
    <circle cx="32" cy="32" r="3" fill="#ffffff"/>
  </g>
</svg>`;

function loadSvgImage(svg: string): HTMLImageElement {
  const img = new Image();
  img.src = 'data:image/svg+xml,' + encodeURIComponent(svg);
  return img;
}

export function loadBattleIcons(): Promise<BattleIconRefs> {
  const refs: BattleIconRefs = { skull: null, gank: null, brawl: null, battle: null, hellcamp: null };

  const entries: [keyof BattleIconRefs, string][] = [
    ['skull', SKULL_SVG],
    ['gank', GANK_SVG],
    ['brawl', BRAWL_SVG],
    ['battle', BATTLE_SVG],
    ['hellcamp', HELLCAMP_SVG],
  ];

  return new Promise((resolve) => {
    let loaded = 0;
    for (const [key, svg] of entries) {
      const img = loadSvgImage(svg);
      img.onload = () => {
        refs[key] = img;
        loaded++;
        if (loaded === entries.length) resolve(refs);
      };
      img.onerror = () => {
        loaded++;
        if (loaded === entries.length) resolve(refs);
      };
    }
  });
}

/** Tooltip SVGs for battle status levels (inline in JSX) */
export const STATUS_COLORS: Record<string, { border: string; glow: string; color: string }> = {
  hellcamp: { border: 'border-cyan-500', glow: '#00ffff', color: '#00ffff' },
  battle: { border: 'border-yellow-500', glow: '#ffcc00', color: '#ffcc00' },
  brawl: { border: 'border-orange-500', glow: '#ff8800', color: '#ff8800' },
  gank: { border: 'border-red-500', glow: '#ff4444', color: '#ff4444' },
};
