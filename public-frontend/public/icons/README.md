# EVE Co-Pilot Icons

Optimized icons for homepage use, skaliert aus den originalen 1536x1024 Bildern.

## Verfügbare Icons

| Icon | Beschreibung |
|------|--------------|
| `copilot_activity.png` | Activity Analytics |
| `copilot_capitals.png` | Capital Fleet Intelligence |
| `copilot_defensive.png` | Defensive Operations |
| `copilot_geography.png` | Geographic Spread |
| `copilot_hunting.png` | Hunting Operations |
| `copilot_isk.png` | ISK Analysis |
| `copilot_offensive.png` | Offensive Operations |
| `copilot_overview.png` | Alliance Overview |
| `copilot_pilots.png` | Pilot Intelligence |
| `copilot_wormhole.png` | Wormhole Empire |

## Größen

- **64x64**: ~5-7KB pro Icon (klein, für Listen/Badges)
- **128x128**: ~17-23KB pro Icon (mittel, für Cards/Buttons)
- **256x256**: ~49-82KB pro Icon (groß, für Hero-Sections)

## Verwendung in React

```tsx
// Beispiel: 128px Icon
<img
  src="/icons/128/copilot_activity.png"
  alt="Activity Analytics"
  style={{ width: '128px', height: '128px' }}
/>

// Beispiel: 64px Icon für Button
<button style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
  <img src="/icons/64/copilot_offensive.png" alt="" style={{ width: '24px', height: '24px' }} />
  Offensive Intel
</button>

// Beispiel: Responsive Icon
<img
  srcSet="/icons/64/copilot_capitals.png 1x, /icons/128/copilot_capitals.png 2x"
  src="/icons/64/copilot_capitals.png"
  alt="Capital Intelligence"
  style={{ width: '64px', height: '64px' }}
/>
```

## Optimierung

Von Original-Größe reduziert:
- Original: 1.6-3.2 MB (1536x1024)
- 64px: 5-7KB (~99.8% kleiner)
- 128px: 17-23KB (~99.4% kleiner)
- 256px: 49-82KB (~97% kleiner)

Komprimierung: PNG mit Quality 90
