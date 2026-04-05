import { NextRequest, NextResponse } from 'next/server';
import { findRecordByKey, findRecords } from '@/lib/sde-loader';
import type {
  SolarSystem,
  Region,
  Star,
  Planet,
  Moon,
  AsteroidBelt,
  Stargate,
  Station,
  SystemDetailResponse,
} from '@/lib/sde-types';

function toRoman(num: number): string {
  const romanNumerals: Record<number, string> = {
    1: 'I',
    2: 'II',
    3: 'III',
    4: 'IV',
    5: 'V',
    6: 'VI',
    7: 'VII',
    8: 'VIII',
    9: 'IX',
    10: 'X',
    11: 'XI',
    12: 'XII',
    13: 'XIII',
    14: 'XIV',
    15: 'XV',
  };
  return romanNumerals[num] || String(num);
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const systemId = parseInt(id, 10);

    if (isNaN(systemId)) {
      return NextResponse.json({ error: 'Invalid system ID' }, { status: 400 });
    }

    const system = await findRecordByKey<SolarSystem>('mapSolarSystems.jsonl', systemId);

    if (!system) {
      return NextResponse.json({ error: 'System not found' }, { status: 404 });
    }

    const [region, star, planets, moons, asteroidBelts, stargates, stations] = await Promise.all([
      findRecordByKey<Region>('mapRegions.jsonl', system.regionID),

      system.starID
        ? findRecordByKey<Star>('mapStars.jsonl', system.starID)
        : Promise.resolve(null),

      system.planetIDs && system.planetIDs.length > 0
        ? findRecords<Planet>('mapPlanets.jsonl', (p) => p.solarSystemID === systemId)
        : Promise.resolve([]),

      system.planetIDs && system.planetIDs.length > 0
        ? findRecords<Moon>('mapMoons.jsonl', (m) => m.solarSystemID === systemId)
        : Promise.resolve([]),

      system.planetIDs && system.planetIDs.length > 0
        ? findRecords<AsteroidBelt>('mapAsteroidBelts.jsonl', (ab) => ab.solarSystemID === systemId)
        : Promise.resolve([]),

      system.stargateIDs && system.stargateIDs.length > 0
        ? findRecords<Stargate>('mapStargates.jsonl', (sg) => sg.solarSystemID === systemId)
        : Promise.resolve([]),

      findRecords<Station>('npcStations.jsonl', (s) => s.solarSystemID === systemId),
    ]);

    const allTypeIDs = new Set<number>();
    planets.forEach((p) => allTypeIDs.add(p.typeID));
    moons.forEach((m) => allTypeIDs.add(m.typeID));
    asteroidBelts.forEach((ab) => allTypeIDs.add(ab.typeID));
    stations.forEach((s) => allTypeIDs.add(s.typeID));

    const [types, corporations, operations, services] = await Promise.all([
      findRecords<{ _key: number; name: { en: string } }>('types.jsonl', (t) =>
        allTypeIDs.has(t._key)
      ),

      stations.length > 0
        ? findRecords<{ _key: number; name: { en: string } }>('npcCorporations.jsonl', (c) =>
            stations.some((s) => s.ownerID === c._key)
          )
        : Promise.resolve([]),

      stations.length > 0
        ? findRecords<{
            _key: number;
            operationName: { en: string };
            services?: number[];
          }>('stationOperations.jsonl', (op) =>
            stations.some((s) => s.useOperationName && s.operationID === op._key)
          )
        : Promise.resolve([]),

      stations.length > 0
        ? findRecords<{ _key: number; serviceName: { en: string } }>(
            'stationServices.jsonl',
            () => true
          )
        : Promise.resolve([]),
    ]);

    const typeMap = new Map(types.map((t) => [t._key, t]));
    const corporationMap = new Map(corporations.map((c) => [c._key, c]));
    const operationMap = new Map(operations.map((op) => [op._key, op]));
    const serviceMap = new Map(services.map((s) => [s._key, s]));

    const enrichedPlanets = planets.map((planet) => {
      const planetType = typeMap.get(planet.typeID);

      const planetRoman = planet.celestialIndex ? toRoman(planet.celestialIndex) : '';
      const fullName = planetRoman
        ? `${system.name.en} ${planetRoman}`
        : `${system.name.en} - Planet`;

      return {
        ...planet,
        fullName,
        typeName: planetType?.name.en || 'Planet',
      };
    });

    const enrichedMoons = moons.map((moon) => {
      const moonType = typeMap.get(moon.typeID);

      const parentPlanet = planets.find((p) => p._key === moon.orbitID);

      let fullName = '';
      if (parentPlanet?.celestialIndex && moon.orbitIndex) {
        const planetRoman = toRoman(parentPlanet.celestialIndex);
        fullName = `${system.name.en} ${planetRoman} - Moon ${moon.orbitIndex}`;
      } else {
        fullName = `${system.name.en} - Moon`;
      }

      return {
        ...moon,
        fullName,
        typeName: moonType?.name.en || 'Moon',
      };
    });

    const enrichedAsteroidBelts = asteroidBelts.map((belt) => {
      const beltType = typeMap.get(belt.typeID);

      const parentPlanet = planets.find((p) => p._key === belt.orbitID);

      let fullName = '';
      if (parentPlanet?.celestialIndex && belt.orbitIndex) {
        const planetRoman = toRoman(parentPlanet.celestialIndex);
        fullName = `${system.name.en} ${planetRoman} - Asteroid Belt ${belt.orbitIndex}`;
      } else {
        fullName = `${system.name.en} - Asteroid Belt`;
      }

      return {
        ...belt,
        fullName,
        typeName: beltType?.name.en || 'Asteroid Belt',
      };
    });

    const enrichedStations = stations.map((station) => {
      const corporationName = station.ownerID
        ? corporationMap.get(station.ownerID)?.name.en || ''
        : '';

      let stationName = '';
      let stationServices: string[] = [];

      if (station.useOperationName && station.operationID) {
        const operation = operationMap.get(station.operationID);
        stationName = operation?.operationName.en || 'Unknown Operation';

        if (operation?.services && operation.services.length > 0) {
          stationServices = operation.services
            .map((serviceId) => serviceMap.get(serviceId)?.serviceName.en || '')
            .filter((name) => name !== '');
        }
      } else {
        stationName = typeMap.get(station.typeID)?.name.en || 'Unknown Type';
      }

      const moon = enrichedMoons.find((m) => m._key === station.orbitID);

      let fullName = '';
      if (station.celestialIndex && moon?.orbitIndex) {
        const planetRoman = toRoman(station.celestialIndex);
        const moonNumber = moon.orbitIndex;
        const corpPart = corporationName ? `${corporationName} ` : '';
        fullName = `${system.name.en} ${planetRoman} - Moon ${moonNumber} - ${corpPart}${stationName}`;
      } else {
        const corpPart = corporationName ? `${corporationName} ` : '';
        fullName = `${system.name.en} - ${corpPart}${stationName}`;
      }

      return {
        ...station,
        fullName,
        typeName: stationName,
        services: stationServices,
      };
    });

    const destinationSystemIDs = new Set(
      stargates.map((sg) => sg.destination.solarSystemID)
    );
    const destinationSystems =
      destinationSystemIDs.size > 0
        ? await findRecords<SolarSystem>('mapSolarSystems.jsonl', (sys) =>
            destinationSystemIDs.has(sys._key)
          )
        : [];
    const destSystemMap = new Map(destinationSystems.map((sys) => [sys._key, sys]));

    const enrichedStargates = stargates.map((stargate) => {
      const destSystem = destSystemMap.get(stargate.destination.solarSystemID);

      const fullName = destSystem
        ? `Stargate (${destSystem.name.en})`
        : `Stargate ${stargate._key}`;

      return {
        ...stargate,
        fullName,
        destinationName: destSystem?.name.en || 'Unknown',
      };
    });

    if (!region) {
      return NextResponse.json({ error: 'Region not found' }, { status: 404 });
    }

    const response: SystemDetailResponse = {
      system,
      region,
      star,
      planets: enrichedPlanets,
      moons: enrichedMoons,
      asteroidBelts: enrichedAsteroidBelts,
      stargates: enrichedStargates,
      stations: enrichedStations,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading system detail:', error);
    return NextResponse.json({ error: 'Failed to load system detail' }, { status: 500 });
  }
}
