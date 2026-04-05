// unified-frontend/src/components/capital/CynoNetworkTab.tsx

import { useState, useEffect } from 'react'
import { getCynoJammers } from '@/api/capital'
import type { CynoJammer, CynoJammerResponse } from '@/types/capital'

export default function CynoNetworkTab() {
  const [jammers, setJammers] = useState<CynoJammer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRegion, setSelectedRegion] = useState<string>('all')

  useEffect(() => {
    loadJammers()
  }, [])

  const loadJammers = async () => {
    setLoading(true)
    try {
      const data = await getCynoJammers()
      setJammers(data.jammers)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jammers')
    } finally {
      setLoading(false)
    }
  }

  // Get unique regions
  const regions = [...new Set(jammers.map(j => j.region_name))].sort()

  // Filter jammers
  const filteredJammers = jammers.filter(jammer => {
    const matchesSearch = searchQuery === '' ||
      jammer.solar_system_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      jammer.region_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (jammer.alliance_name?.toLowerCase().includes(searchQuery.toLowerCase()))

    const matchesRegion = selectedRegion === 'all' || jammer.region_name === selectedRegion

    return matchesSearch && matchesRegion
  })

  // Group by region
  const jammersByRegion = filteredJammers.reduce((acc, jammer) => {
    const region = jammer.region_name
    if (!acc[region]) acc[region] = []
    acc[region].push(jammer)
    return acc
  }, {} as Record<string, CynoJammer[]>)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading cyno jammers...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-500 rounded p-4 text-red-300">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-red-400">{jammers.length}</div>
          <div className="text-gray-400 text-sm">Total Jammed Systems</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-blue-400">{regions.length}</div>
          <div className="text-gray-400 text-sm">Regions Affected</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold text-yellow-400">
            {[...new Set(jammers.map(j => j.alliance_name).filter(Boolean))].length}
          </div>
          <div className="text-gray-400 text-sm">Alliances with Jammers</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <button
            onClick={loadJammers}
            className="w-full h-full flex items-center justify-center gap-2 text-green-400 hover:text-green-300"
          >
            <span className="text-2xl">🔄</span>
            <span>Refresh Data</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Search</label>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search system, region, or alliance..."
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Region</label>
            <select
              value={selectedRegion}
              onChange={e => setSelectedRegion(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="all">All Regions ({jammers.length})</option>
              {regions.map(region => (
                <option key={region} value={region}>
                  {region} ({jammers.filter(j => j.region_name === region).length})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Jammer List */}
      <div className="space-y-4">
        {Object.entries(jammersByRegion)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([region, regionJammers]) => (
            <div key={region} className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="bg-gray-700 px-4 py-2 flex justify-between items-center">
                <h3 className="text-white font-semibold">{region}</h3>
                <span className="bg-red-900 text-red-300 px-2 py-0.5 rounded text-sm">
                  {regionJammers.length} jammed
                </span>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {regionJammers.map(jammer => (
                    <div
                      key={jammer.solar_system_id}
                      className="bg-gray-700 rounded p-3 border border-red-800"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="text-white font-semibold">{jammer.solar_system_name}</div>
                          {jammer.alliance_name && (
                            <div className="text-gray-400 text-sm">{jammer.alliance_name}</div>
                          )}
                        </div>
                        <span className="bg-red-600 text-white px-2 py-0.5 rounded text-xs">
                          JAMMED
                        </span>
                      </div>
                      <div className="text-gray-500 text-xs mt-2">
                        Updated: {new Date(jammer.last_updated).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
      </div>

      {filteredJammers.length === 0 && (
        <div className="bg-gray-800 rounded-lg p-8 text-center">
          <div className="text-gray-400">No jammed systems found</div>
        </div>
      )}
    </div>
  )
}
