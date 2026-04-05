/**
 * EVE Co-Pilot Theme Constants
 *
 * Centralised design tokens for the EVE Online dark theme.
 * Import individual objects where needed:
 *
 *   import { fontSize, color, spacing, panel } from '../styles/theme';
 *
 * These constants map the hardcoded values already used across the
 * codebase into semantic, reusable tokens.  CSS custom-properties
 * (var(--...)) are still the source of truth for base colours and
 * backgrounds; the `color` object re-exports their raw values so
 * inline styles can reference them without duplicating hex codes.
 */

// ---------------------------------------------------------------------------
// Font Sizes  (7 semantic tiers covering the 17 unique sizes in use)
// ---------------------------------------------------------------------------

export const fontSize = {
  // Headings
  h1: '2rem',       // Page titles
  h2: '1.75rem',    // Section headings
  h3: '1.25rem',    // Panel headers
  h4: '1.2rem',     // Sub-headers

  // Body text
  lg: '1rem',       // Large body
  md: '0.95rem',    // Medium body
  base: '0.85rem',  // Default body text
  sm: '0.8rem',     // Small body

  // Small text
  xs: '0.75rem',    // Small labels
  xxs: '0.7rem',    // Tiny labels

  // Micro text
  tiny: '0.65rem',  // Very small
  micro: '0.6rem',  // Micro text
  nano: '0.55rem',  // Nano text
  pico: '0.5rem',   // Pico
  min: '0.4rem',    // Minimum readable
} as const;

// ---------------------------------------------------------------------------
// Spacing Scale  (common gap / padding / margin values)
// ---------------------------------------------------------------------------

export const spacing = {
  '2xs': '0.15rem',  // ~2.4px
  xs: '0.25rem',     // 4px
  sm: '0.3rem',      // ~5px
  md: '0.4rem',      // ~6px
  base: '0.5rem',    // 8px  - DEFAULT
  lg: '0.75rem',     // 12px
  xl: '1rem',        // 16px
  '2xl': '1.5rem',   // 24px
  '3xl': '2rem',     // 32px
} as const;

// ---------------------------------------------------------------------------
// Colours
// ---------------------------------------------------------------------------

export const color = {
  // Status / Performance  (EVE combat colours)
  killGreen: '#3fb950',     // kills, positive
  lossRed: '#f85149',       // losses, negative
  dangerRed: '#ff4444',     // critical
  warningYellow: '#ffcc00', // caution
  warningOrange: '#ff8800', // brawl
  accentCyan: '#00d4ff',    // highlights
  accentPurple: '#a855f7',  // special
  linkBlue: '#58a6ff',      // links
  safeGreen: '#00ff88',     // safe status

  // Neutral text  (mirror CSS vars)
  textPrimary: '#e6edf3',   // var(--text-primary)
  textSecondary: '#8b949e', // var(--text-secondary)
  textTertiary: '#6e7681',  // var(--text-tertiary)
  textWhite: '#ffffff',

  // Backgrounds  (mirror CSS vars)
  bgPrimary: '#0d1117',     // var(--bg-primary)
  bgSecondary: '#161b22',   // var(--bg-secondary)
  bgElevated: '#21262d',    // var(--bg-elevated)
  bgHover: '#2d333b',       // var(--bg-hover)
  border: '#30363d',        // var(--border-color)

  // Additional common colours
  orange: '#d29922',        // warning variant
  brightOrange: '#ff6600',
  pureRed: '#ff0000',
  teal: '#00bcd4',
  lightOrange: '#ffa657',
  emerald: '#10b981',

  // Damage types  (EVE standard)
  em: '#00d4ff',
  thermal: '#ff4444',
  kinetic: '#888888',
  explosive: '#ff8800',

  // Security status
  highsec: '#00ff88',
  lowsec: '#ffcc00',
  nullsec: '#ff4444',
  wormhole: '#a855f7',
} as const;

// ---------------------------------------------------------------------------
// Panel Styles  (common reusable style objects)
// ---------------------------------------------------------------------------

export const panel = {
  card: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    padding: spacing.lg,
  },
  elevated: {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    padding: spacing.base,
  },
} as const;
