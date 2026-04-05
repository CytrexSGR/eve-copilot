/**
 * Helper functions for EVE Online image URLs from evetech.net
 */

export type ImageType = 'render' | 'icon';

export interface EveImageOptions {
  size?: 32 | 64 | 128 | 256 | 512 | 1024;
  type?: ImageType;
}

/**
 * Get the image URL for a type (ships, items, celestials, etc.)
 */
export function getTypeImageUrl(typeID: number, options: EveImageOptions = {}): string {
  const { size = 128, type = 'render' } = options;
  return `https://images.evetech.net/types/${typeID}/${type}?size=${size}`;
}

/**
 * Get the image URL for a character
 */
export function getCharacterImageUrl(
  characterID: number,
  options: { size?: 32 | 64 | 128 | 256 | 512 | 1024 } = {}
): string {
  const { size = 128 } = options;
  return `https://images.evetech.net/characters/${characterID}/portrait?size=${size}`;
}

/**
 * Get the image URL for a corporation
 */
export function getCorporationImageUrl(
  corporationID: number,
  options: { size?: 32 | 64 | 128 | 256 } = {}
): string {
  const { size = 128 } = options;
  return `https://images.evetech.net/corporations/${corporationID}/logo?size=${size}`;
}

/**
 * Get the image URL for an alliance
 */
export function getAllianceImageUrl(
  allianceID: number,
  options: { size?: 32 | 64 | 128 | 256 } = {}
): string {
  const { size = 128 } = options;
  return `https://images.evetech.net/alliances/${allianceID}/logo?size=${size}`;
}

/**
 * Get star color based on spectral class
 */
export function getStarColor(spectralClass: string): string {
  const mainClass = spectralClass.charAt(0).toUpperCase();

  const colorMap: Record<string, string> = {
    O: '#9BB0FF', // Blue
    B: '#AABFFF', // Blue-white
    A: '#CAD7FF', // White
    F: '#F8F7FF', // Yellow-white
    G: '#FFF4EA', // Yellow (like our Sun)
    K: '#FFD2A1', // Orange
    M: '#FFCC6F', // Red-orange
  };

  return colorMap[mainClass] || '#FFFFFF';
}

/**
 * Get star color for rendering (more saturated for visibility)
 */
export function getStarRenderColor(spectralClass: string): string {
  const mainClass = spectralClass.charAt(0).toUpperCase();

  const colorMap: Record<string, string> = {
    O: '#6B9FFF', // Bright blue
    B: '#9BBFFF', // Blue-white
    A: '#FFFFFF', // White
    F: '#FFFACD', // Light yellow
    G: '#FFD700', // Gold (current default)
    K: '#FFA500', // Orange
    M: '#FF6347', // Red-orange/tomato
  };

  return colorMap[mainClass] || '#FFD700';
}

/**
 * Convert Kelvin temperature to approximate RGB color
 */
export function temperatureToColor(kelvin: number): string {
  if (kelvin >= 30000) return '#9BB0FF'; // Blue
  if (kelvin >= 10000) return '#AABFFF'; // Blue-white
  if (kelvin >= 7500) return '#CAD7FF'; // White
  if (kelvin >= 6000) return '#F8F7FF'; // Yellow-white
  if (kelvin >= 5200) return '#FFD700'; // Yellow
  if (kelvin >= 3700) return '#FFA500'; // Orange
  return '#FF6347'; // Red
}

/**
 * Format large numbers with suffixes (K, M, B, T)
 */
export function formatLargeNumber(num: number): string {
  if (num >= 1e12) return (num / 1e12).toFixed(2) + 'T';
  if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
  if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
  if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
  return num.toFixed(0);
}

/**
 * Convert meters to solar radii
 */
export function metersToSolarRadii(meters: number): number {
  const SOLAR_RADIUS_METERS = 696_000_000; // ~696,000 km
  return meters / SOLAR_RADIUS_METERS;
}

/**
 * Format age in billions of years
 */
export function formatAge(seconds: number): string {
  const years = seconds / (365.25 * 24 * 60 * 60);
  const billions = years / 1e9;
  return billions.toFixed(2);
}

/**
 * Convert seconds to human-readable time
 */
export function formatOrbitalPeriod(seconds: number): string {
  const days = seconds / (24 * 60 * 60);
  const years = days / 365.25;

  if (years >= 1) {
    return `${years.toFixed(2)} years`;
  } else {
    return `${days.toFixed(1)} days`;
  }
}

/**
 * Convert seconds to rotation time
 */
export function formatRotationPeriod(seconds: number): string {
  const hours = seconds / 3600;
  const days = hours / 24;

  if (days >= 1) {
    return `${days.toFixed(2)} days`;
  } else {
    return `${hours.toFixed(1)} hours`;
  }
}

/**
 * Convert meters to AU (Astronomical Units)
 */
export function metersToAU(meters: number): number {
  const AU_METERS = 149597870700; // 1 AU in meters
  return meters / AU_METERS;
}

/**
 * Format temperature in Kelvin or Celsius
 */
export function formatTemperature(kelvin: number, includeCelsius: boolean = true): string {
  if (includeCelsius) {
    const celsius = kelvin - 273.15;
    return `${kelvin.toFixed(0)} K (${celsius.toFixed(0)}°C)`;
  }
  return `${kelvin.toFixed(0)} K`;
}

/**
 * Get planet type color based on temperature
 */
export function getPlanetTypeColor(temperature?: number): string {
  if (!temperature) return '#4169E1';

  if (temperature < 150) return '#87CEEB'; // Ice - Light blue
  if (temperature < 250) return '#4169E1'; // Cold - Blue
  if (temperature < 350) return '#32CD32'; // Temperate - Green
  if (temperature < 450) return '#FFD700'; // Warm - Gold
  if (temperature < 600) return '#FF8C00'; // Hot - Orange
  return '#FF4500'; // Lava - Red-orange
}

/**
 * Format mass in kg to Earth masses or Moon masses
 */
export function formatMass(kg: number, type: 'planet' | 'moon' | 'atmosphere' = 'planet'): string {
  const EARTH_MASS = 5.972e24; // kg
  const MOON_MASS = 7.342e22; // kg (Earth's moon)

  if (type === 'atmosphere') {
    if (kg >= 1e21) {
      return `${(kg / 1e21).toFixed(2)} Zg`; // Zettagrams
    } else if (kg >= 1e18) {
      return `${(kg / 1e18).toFixed(2)} Eg`; // Exagrams
    } else if (kg >= 1e15) {
      return `${(kg / 1e15).toFixed(2)} Pg`; // Petagrams
    } else if (kg >= 1e12) {
      return `${(kg / 1e12).toFixed(2)} Tg`; // Teragrams
    } else if (kg >= 1e9) {
      return `${(kg / 1e9).toFixed(2)} Gg`; // Gigagrams
    } else if (kg >= 1e6) {
      return `${(kg / 1e6).toFixed(2)} Mg`; // Megagrams
    } else {
      return `${(kg / 1e3).toFixed(2)} Mg`; // Megagrams (minimum)
    }
  } else if (type === 'moon') {
    const moonMasses = kg / MOON_MASS;
    return `${moonMasses.toFixed(3)} M☾`;
  } else {
    const earthMasses = kg / EARTH_MASS;
    if (earthMasses < 0.01) {
      return `${earthMasses.toExponential(2)} M⊕`;
    } else {
      return `${earthMasses.toFixed(2)} M⊕`;
    }
  }
}
