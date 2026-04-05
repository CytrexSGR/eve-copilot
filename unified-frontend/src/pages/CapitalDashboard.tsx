// unified-frontend/src/pages/CapitalDashboard.tsx

import { useState, Suspense, lazy } from 'react'

const JumpPlannerTab = lazy(() => import('@/components/capital/JumpPlannerTab'))
const CynoNetworkTab = lazy(() => import('@/components/capital/CynoNetworkTab'))
const StructureTimersTab = lazy(() => import('@/components/capital/StructureTimersTab'))

type TabId = 'jump-planner' | 'cyno-network' | 'structure-timers'

interface Tab {
  id: TabId
  label: string
  icon: string
}

const TABS: Tab[] = [
  { id: 'jump-planner', label: 'Jump Planner', icon: '🚀' },
  { id: 'cyno-network', label: 'Cyno Network', icon: '📡' },
  { id: 'structure-timers', label: 'Structure Timers', icon: '⏱️' },
]

export default function CapitalDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('jump-planner')

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-white">Capital Operations</h1>
              <p className="text-gray-400 text-sm">
                Jump planning, cyno network monitoring, and structure timers
              </p>
            </div>
            <a
              href="/capitalmap"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded flex items-center gap-2"
            >
              <span>🗺️</span>
              <span>Open Galaxy Map</span>
            </a>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-white bg-gray-700'
                    : 'border-transparent text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading...</div>
            </div>
          }
        >
          {activeTab === 'jump-planner' && <JumpPlannerTab />}
          {activeTab === 'cyno-network' && <CynoNetworkTab />}
          {activeTab === 'structure-timers' && <StructureTimersTab />}
        </Suspense>
      </div>
    </div>
  )
}
