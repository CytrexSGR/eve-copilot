export interface LocalizedName {
  en: string;
  de?: string;
  es?: string;
  fr?: string;
  ja?: string;
  ko?: string;
  ru?: string;
  zh?: string;
}

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface Position2D {
  x: number;
  y: number;
}

export interface Region {
  _key: number;
  name: LocalizedName;
  constellationIDs: number[];
  position: Position3D;
  description?: LocalizedName;
  factionID?: number;
  nebulaID?: number;
  wormholeClassID?: number;
  [key: string]: unknown;
}

export interface Constellation {
  _key: number;
  name: LocalizedName;
  regionID: number;
  solarSystemIDs: number[];
  position: Position3D;
  factionID?: number;
  wormholeClassID?: number;
  [key: string]: unknown;
}

export interface SolarSystem {
  _key: number;
  name: LocalizedName;
  constellationID: number;
  regionID: number;
  position: Position3D;
  position2D: Position2D;
  securityStatus: number;
  securityClass?: string;
  planetIDs?: number[];
  stargateIDs?: number[];
  starID?: number;
  radius?: number;
  border?: boolean;
  hub?: boolean;
  international?: boolean;
  regional?: boolean;
  luminosity?: number;
  [key: string]: unknown;
}

export interface Stargate {
  _key: number;
  solarSystemID: number;
  position: Position3D;
  typeID: number;
  destination: {
    solarSystemID: number;
    stargateID: number;
  };
  [key: string]: unknown;
}

export interface Planet {
  _key: number;
  celestialIndex?: number;
  position: Position3D;
  radius?: number;
  solarSystemID: number;
  typeID: number;
  moonIDs?: number[];
  asteroidBeltIDs?: number[];
  orbitID?: number;
  attributes?: {
    heightMap1?: number;
    heightMap2?: number;
    population?: boolean;
    shaderPreset?: number;
  };
  statistics?: {
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
  };
  [key: string]: unknown;
}

export interface Moon {
  _key: number;
  orbitID?: number;
  orbitIndex?: number;
  position: Position3D;
  radius?: number;
  solarSystemID: number;
  typeID: number;
  attributes?: {
    heightMap1?: number;
    heightMap2?: number;
    population?: boolean;
    shaderPreset?: number;
  };
  statistics?: {
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
  };
  [key: string]: unknown;
}

export interface AsteroidBelt {
  _key: number;
  celestialIndex?: number;
  orbitID?: number;
  orbitIndex?: number;
  position: Position3D;
  radius?: number;
  solarSystemID: number;
  typeID: number;
  statistics?: {
    density?: number;
    eccentricity?: number;
    escapeVelocity?: number;
    locked?: boolean;
    massDust?: number;
    massGas?: number;
    orbitPeriod?: number;
    orbitRadius?: number;
    rotationRate?: number;
    spectralClass?: string;
    surfaceGravity?: number;
    temperature?: number;
  };
  [key: string]: unknown;
}

export interface Star {
  _key: number;
  position?: Position3D;
  radius?: number;
  solarSystemID: number;
  typeID: number;
  statistics?: {
    age?: number;
    life?: number;
    luminosity?: number;
    spectralClass?: string;
    temperature?: number;
  };
  [key: string]: unknown;
}

export interface Station {
  _key: number;
  celestialIndex?: number;
  corporationID?: number;
  operationID?: number;
  orbitID?: number;
  orbitIndex?: number;
  ownerID?: number;
  position: Position3D;
  reprocessingEfficiency?: number;
  reprocessingStationsTake?: number;
  security?: number;
  solarSystemID: number;
  typeID: number;
  useOperationName?: boolean;
  [key: string]: unknown;
}

export interface MapDataResponse {
  regions: Region[];
  constellations: Constellation[];
  systems: SolarSystem[];
  stargateConnections: Array<{
    from: number;
    to: number;
  }>;
}

export interface SystemDetailResponse {
  system: SolarSystem;
  region: Region;
  star: Star | null;
  planets: Planet[];
  moons: Moon[];
  asteroidBelts: AsteroidBelt[];
  stargates: Stargate[];
  stations: Station[];
}
