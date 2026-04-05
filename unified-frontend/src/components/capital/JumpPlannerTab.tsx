// unified-frontend/src/components/capital/JumpPlannerTab.tsx

import { useState, useEffect } from 'react'
import {
  getJumpShips,
  getJumpRange,
  planCynoAltRoute,
} from '@/api/capital'
import type { JumpShip, JumpRange, CynoAltRoute } from '@/types/capital'

export default function JumpPlannerTab() {
  const [ships, setShips] = useState<JumpShip[]>([])
  const [selectedShip, setSelectedShip] = useState<string>('Rhea')
  const [jdcLevel, setJdcLevel] = useState(5)
  const [jfLevel, setJfLevel] = useState(5)
  const [jumpRange, setJumpRange] = useState<JumpRange | null>(null)

  const [originSystem, setOriginSystem] = useState('')
  const [originId, setOriginId] = useState<number | null>(null)
  const [destSystem, setDestSystem] = useState('')
  const [destId, setDestId] = useState<number | null>(null)

  const [preferStations, setPreferStations] = useState(true)
  const [route, setRoute] = useState<CynoAltRoute | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load ships on mount
  useEffect(() => {
    getJumpShips().then(data => setShips(data.ships))
  }, [])

  // Calculate jump range when ship or skills change
  useEffect(() => {
    if (selectedShip) {
      getJumpRange(selectedShip, jdcLevel, jfLevel)
        .then(setJumpRange)
        .catch(err => console.error('Failed to get jump range:', err))
    }
  }, [selectedShip, jdcLevel, jfLevel])

  const handleCalculateRoute = async () => {
    if (!originId || !destId) {
      setError('Please select both origin and destination systems')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const result = await planCynoAltRoute(
        originId,
        destId,
        selectedShip,
        jdcLevel,
        jfLevel,
        preferStations
      )
      setRoute(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate route')
    } finally {
      setLoading(false)
    }
  }

  const isJumpFreighter = ships.find(s => s.name === selectedShip)?.skill_type === 'jump_freighters'

  return (
    <div className="space-y-6">
      {/* Ship Selection */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Ship Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Ship</label>
            <select
              value={selectedShip}
              onChange={e => setSelectedShip(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              {ships.map(ship => (
                <option key={ship.name} value={ship.name}>
                  {ship.name} ({ship.base_range} LY)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">JDC Level</label>
            <select
              value={jdcLevel}
              onChange={e => setJdcLevel(Number(e.target.value))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              {[0, 1, 2, 3, 4, 5].map(level => (
                <option key={level} value={level}>Level {level}</option>
              ))}
            </select>
          </div>
          {isJumpFreighter && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">JF Level</label>
              <select
                value={jfLevel}
                onChange={e => setJfLevel(Number(e.target.value))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {[0, 1, 2, 3, 4, 5].map(level => (
                  <option key={level} value={level}>Level {level}</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Effective Range</label>
            <div className="bg-gray-900 rounded px-3 py-2 text-green-400 font-mono">
              {jumpRange ? `${jumpRange.effective_range.toFixed(2)} LY` : '...'}
            </div>
          </div>
        </div>
      </div>

      {/* Route Planning */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Route Planning</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Origin System</label>
            <input
              type="text"
              value={originSystem}
              onChange={e => setOriginSystem(e.target.value)}
              placeholder="e.g., Jita (30000142)"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
            <input
              type="number"
              value={originId || ''}
              onChange={e => setOriginId(Number(e.target.value) || null)}
              placeholder="System ID"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white mt-2"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Destination System</label>
            <input
              type="text"
              value={destSystem}
              onChange={e => setDestSystem(e.target.value)}
              placeholder="e.g., 1DQ1-A (30004759)"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
            <input
              type="number"
              value={destId || ''}
              onChange={e => setDestId(Number(e.target.value) || null)}
              placeholder="System ID"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white mt-2"
            />
          </div>
        </div>

        <div className="flex items-center gap-4 mb-4">
          <label className="flex items-center gap-2 text-gray-300">
            <input
              type="checkbox"
              checked={preferStations}
              onChange={e => setPreferStations(e.target.checked)}
              className="rounded"
            />
            Prefer NPC stations
          </label>
        </div>

        <button
          onClick={handleCalculateRoute}
          disabled={loading || !originId || !destId}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-2 rounded font-semibold"
        >
          {loading ? 'Calculating...' : 'Calculate Route'}
        </button>

        {error && (
          <div className="mt-4 bg-red-900/50 border border-red-500 rounded p-3 text-red-300">
            {error}
          </div>
        )}
      </div>

      {/* Route Results */}
      {route && (
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">
                {route.origin.system_name} → {route.destination.system_name}
              </h3>
              <p className="text-gray-400 text-sm">
                {route.route_type === 'direct' ? 'Direct Jump' : `${route.total_jumps} Jumps`}
                {' • '}{route.total_distance.toFixed(1)} LY
                {' • '}{route.total_fuel.toLocaleString()} fuel
              </p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-yellow-400">
                {route.fatigue_clear_time || `${Math.round(route.total_fatigue_minutes)}m`}
              </div>
              <div className="text-xs text-gray-400">Total Fatigue</div>
            </div>
          </div>

          {route.warnings.length > 0 && (
            <div className="mb-4 space-y-2">
              {route.warnings.map((warning, i) => (
                <div key={i} className="bg-yellow-900/50 border border-yellow-500 rounded p-2 text-yellow-300 text-sm">
                  ⚠️ {warning}
                </div>
              ))}
            </div>
          )}

          <div className="space-y-3">
            <div className="text-sm text-gray-400 font-semibold">Cyno Positions:</div>
            {route.cyno_positions.map((pos, i) => (
              <div
                key={i}
                className={`p-3 rounded border ${
                  pos.jammed ? 'bg-red-900/30 border-red-500' : 'bg-gray-700 border-gray-600'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-white font-semibold">
                      {pos.waypoint}. {pos.system_name}
                    </span>
                    <span className="text-gray-400 ml-2">({pos.region})</span>
                    {pos.has_station && (
                      <span className="ml-2 bg-green-900 text-green-300 px-2 py-0.5 rounded text-xs">
                        NPC Station
                      </span>
                    )}
                    {pos.jammed && (
                      <span className="ml-2 bg-red-900 text-red-300 px-2 py-0.5 rounded text-xs">
                        JAMMED
                      </span>
                    )}
                  </div>
                  <div className="text-right text-sm">
                    <div className="text-blue-400">{pos.distance_ly.toFixed(1)} LY</div>
                    <div className="text-gray-400">{pos.fuel_required.toLocaleString()} fuel</div>
                  </div>
                </div>
                <div className="text-gray-400 text-sm mt-1">
                  Security: {pos.security.toFixed(1)} • {pos.recommendation}
                </div>
              </div>
            ))}
          </div>

          {route.cyno_alt_checklist && (
            <div className="mt-4 p-3 bg-gray-900 rounded">
              <div className="text-sm text-gray-400 font-semibold mb-2">Cyno Alt Checklist:</div>
              <ul className="space-y-1">
                {route.cyno_alt_checklist.map((item, i) => (
                  <li key={i} className="text-gray-300 text-sm flex items-center gap-2">
                    <input type="checkbox" className="rounded" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
