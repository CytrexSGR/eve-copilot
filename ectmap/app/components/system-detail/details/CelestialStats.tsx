'use client';

import { formatTemperature, formatOrbitalPeriod, formatRotationPeriod, formatMass } from '@/lib/eve-images';
import type { CelestialStatistics } from '../types';

interface CelestialStatsProps {
  statistics: CelestialStatistics | undefined;
  radius?: number;
  type?: 'planet' | 'moon' | 'asteroidBelt';
}

/**
 * Shared component for displaying celestial body statistics.
 * Used by PlanetDetail, MoonDetail, and AsteroidBeltDetail.
 */
export default function CelestialStats({ statistics, radius, type = 'planet' }: CelestialStatsProps) {
  return (
    <div className="space-y-3">
      {/* Temperature */}
      {statistics?.temperature && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Temperature</div>
          <div className="text-white">{formatTemperature(statistics.temperature)}</div>
        </div>
      )}

      {/* Radius */}
      {radius && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Radius</div>
          <div className="text-white">{(radius / 1000).toLocaleString()} km</div>
        </div>
      )}

      {/* Orbital Period */}
      {statistics?.orbitPeriod && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Orbital Period</div>
          <div className="text-white">{formatOrbitalPeriod(statistics.orbitPeriod)}</div>
        </div>
      )}

      {/* Orbital Radius */}
      {statistics?.orbitRadius && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Orbital Distance</div>
          <div className="text-white">
            {type === 'planet' ? (
              <>
                {(statistics.orbitRadius / 149597870700).toFixed(3)} AU
                <span className="text-gray-500 text-sm ml-2">
                  ({(statistics.orbitRadius / 1000000).toLocaleString()} Mm)
                </span>
              </>
            ) : (
              <>{(statistics.orbitRadius / 1000).toLocaleString()} km</>
            )}
          </div>
        </div>
      )}

      {/* Rotation Period */}
      {statistics?.rotationRate && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Rotation Period</div>
          <div className="text-white">
            {formatRotationPeriod(statistics.rotationRate)}
            {statistics.locked && (
              <span className="text-yellow-400 text-sm ml-2">(Tidally Locked)</span>
            )}
          </div>
        </div>
      )}

      {/* Surface Gravity */}
      {statistics?.surfaceGravity && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Surface Gravity</div>
          <div className="text-white">
            {statistics.surfaceGravity.toFixed(2)} m/s²
            <span className="text-gray-500 text-sm ml-2">
              ({(statistics.surfaceGravity / 9.81).toFixed(2)}g)
            </span>
          </div>
        </div>
      )}

      {/* Escape Velocity */}
      {statistics?.escapeVelocity && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Escape Velocity</div>
          <div className="text-white">{(statistics.escapeVelocity / 1000).toFixed(2)} km/s</div>
        </div>
      )}

      {/* Atmospheric Pressure */}
      {statistics?.pressure !== undefined && statistics.pressure > 0 && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Atmospheric Pressure</div>
          <div className="text-white">{statistics.pressure.toFixed(2)} atm</div>
        </div>
      )}

      {/* Mass */}
      {statistics?.massDust && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Mass</div>
          <div className="text-white">
            {formatMass(statistics.massDust, type === 'asteroidBelt' ? 'atmosphere' : type)}
            {statistics.massGas && statistics.massGas > 0 && (
              <div className="text-gray-500 text-sm mt-1">
                {type === 'asteroidBelt' ? 'Gas: ' : 'Atmosphere: '}
                {formatMass(statistics.massGas, 'atmosphere')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Density */}
      {statistics?.density && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Density</div>
          <div className="text-white">{statistics.density.toFixed(2)} kg/m³</div>
        </div>
      )}

      {/* Eccentricity */}
      {statistics?.eccentricity !== undefined && (
        <div>
          <div className="text-gray-400 text-xs uppercase">Orbital Eccentricity</div>
          <div className="text-white">{statistics.eccentricity.toFixed(4)}</div>
        </div>
      )}
    </div>
  );
}
