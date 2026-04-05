/**
 * Shared types for SystemDetail components.
 */

import type {
  SystemDetailResponse,
  Star,
  Planet,
  Moon,
  AsteroidBelt,
  Stargate,
  Station
} from '@/lib/sde-types';

export type ObjectType = 'star' | 'planet' | 'moon' | 'asteroidBelt' | 'stargate' | 'station';

// Union type for all celestial objects
export type CelestialObject = Star | Planet | Moon | AsteroidBelt | Stargate | Station;

// Extended types with computed properties from backend API
export interface PlanetWithNames extends Planet {
  fullName?: string;
  typeName?: string;
}

export interface StargateWithNames extends Stargate {
  fullName?: string;
  destinationName?: string;
}

export interface StationWithNames extends Station {
  fullName?: string;
  typeName?: string;
  services?: string[];
}

export interface MoonWithNames extends Moon {
  fullName?: string;
  typeName?: string;
}

export interface AsteroidBeltWithNames extends AsteroidBelt {
  fullName?: string;
  typeName?: string;
}

// Renderable object for canvas
export interface RenderableObject {
  x: number;
  y: number;
  type: 'star' | 'planet' | 'stargate' | 'station';
  label: string;
  color: string;
  radius: number;
  typeID?: number;
  dataRef: CelestialObject;
}

// Adjusted position after collision detection
export interface AdjustedPosition {
  x: number;
  y: number;
  radius: number;
}

// Found object from click/hover detection
export interface FoundObject {
  star?: Star;
  planet?: Planet;
  stargate?: Stargate;
  station?: Station;
  distance: number;
}

// Base props for detail panels
export interface DetailPanelProps {
  data: CelestialObject;
  onClose: () => void;
  onBack?: () => void;
  showBackButton?: boolean;
}

export interface SelectedObject {
  type: ObjectType;
  data: CelestialObject;
}

export interface HoveredObject {
  type: string;
  label: string;
  x: number;
  y: number;
}

export interface CameraState {
  x: number;
  y: number;
  zoom: number;
}

export interface CoordinateData {
  minA: number;
  minB: number;
  maxA: number;
  maxB: number;
  scale: number;
  padding: number;
}

// Statistics type shared by planets, moons, and asteroid belts
export interface CelestialStatistics {
  density?: number;
  eccentricity?: number;
  escapeVelocity?: number;
  locked?: boolean;
  massDust?: number;
  massGas?: number;
  orbitPeriod?: number;
  orbitRadius?: number;
  pressure?: number;
  rotationRate?: number;
  spectralClass?: string;
  surfaceGravity?: number;
  temperature?: number;
}

export interface SystemDetailContextValue {
  systemData: SystemDetailResponse | null;
  selectedObject: SelectedObject | null;
  setSelectedObject: (obj: SelectedObject | null) => void;
  openListPanel: 'planets' | 'stargates' | 'stations' | null;
  setOpenListPanel: (panel: 'planets' | 'stargates' | 'stations' | null) => void;
  openedFromList: 'planets' | 'stargates' | 'stations' | null;
  setOpenedFromList: (list: 'planets' | 'stargates' | 'stations' | null) => void;
}

// Re-export types for convenience
export type { Star, Planet, Moon, AsteroidBelt, Stargate, Station, SystemDetailResponse };
