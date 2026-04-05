'use client'

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { getCynoJammers, getUpcomingTimers, CynoJammer, StructureTimer } from '@/lib/api'

interface CapitalMapProps {
  initialShowJammers?: boolean;
  initialShowTimers?: boolean;
  initialRegion?: string;
  snapshotMode?: boolean;
}

interface MapSystem {
  _key: number
  name: { en: string }
  position: { x: number; y: number; z: number }
  position2D?: { x: number; y: number }
  regionID: number
  securityStatus: number
}

interface MapData {
  systems: MapSystem[]
  regions: Array<{ _key: number; name: { en: string } }>
  stargateConnections: Array<{ from: number; to: number }>
}

export default function CapitalMap({
  initialShowJammers = true,
  initialShowTimers = true,
  initialRegion,
  snapshotMode = false,
}: CapitalMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const [mapData, setMapData] = useState<MapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 })

  const [jammers, setJammers] = useState<CynoJammer[]>([])
  const [timers, setTimers] = useState<StructureTimer[]>([])
  const [showJammers, setShowJammers] = useState(initialShowJammers)
  const [showTimers, setShowTimers] = useState(initialShowTimers)

  const cameraRef = useRef({ x: 0, y: 0, zoom: 2 })
  const [camera, setCamera] = useState({ x: 0, y: 0, zoom: 2 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [cameraInitialized, setCameraInitialized] = useState(false)

  const jammedSystemIds = useMemo(
    () => new Set(jammers.map(j => j.solar_system_id)),
    [jammers]
  )

  const timerSystemIds = useMemo(
    () => new Set(timers.map(t => t.system_id)),
    [timers]
  )

  const systemMap = useMemo(() => {
    if (!mapData) return new Map()
    return new Map(mapData.systems.map(s => [s._key, s]))
  }, [mapData])

  const bounds = useMemo(() => {
    if (!mapData || mapData.systems.length === 0) {
      return { minX: 0, minY: 0, maxX: 0, maxY: 0 }
    }
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    for (const system of mapData.systems) {
      const x = system.position2D?.x || system.position.x
      const y = system.position2D?.y || system.position.y
      minX = Math.min(minX, x)
      maxX = Math.max(maxX, x)
      minY = Math.min(minY, y)
      maxY = Math.max(maxY, y)
    }
    return { minX, minY, maxX, maxY }
  }, [mapData])

  const coordinateData = useMemo(() => {
    const padding = 50
    const scaleX = (dimensions.width - padding * 2) / (bounds.maxX - bounds.minX || 1)
    const scaleY = (dimensions.height - padding * 2) / (bounds.maxY - bounds.minY || 1)
    const scale = Math.min(scaleX, scaleY)
    return { ...bounds, scale, padding }
  }, [bounds, dimensions])

  const toCanvasX = useCallback(
    (x: number) => (x - coordinateData.minX) * coordinateData.scale + coordinateData.padding,
    [coordinateData]
  )

  const toCanvasY = useCallback(
    (y: number) =>
      dimensions.height - ((y - coordinateData.minY) * coordinateData.scale + coordinateData.padding),
    [coordinateData, dimensions.height]
  )

  // Load map data from ectmap
  useEffect(() => {
    async function loadMap() {
      try {
        const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
        const response = await fetch(`http://${host}:3001/api/map/data`)
        if (!response.ok) throw new Error('Failed to load map data')
        const data = await response.json()
        setMapData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    loadMap()
  }, [])

  // Load jammers and timers
  useEffect(() => {
    async function loadOverlays() {
      try {
        const [jammerData, timerData] = await Promise.all([
          getCynoJammers(),
          getUpcomingTimers(72),
        ])
        setJammers(jammerData.jammers)
        setTimers(timerData.timers)
      } catch (err) {
        console.error('Failed to load overlays:', err)
      }
    }
    loadOverlays()
    const interval = setInterval(loadOverlays, 30000)
    return () => clearInterval(interval)
  }, [])

  // Handle resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // Initialize camera
  useEffect(() => {
    if (!mapData || mapData.systems.length === 0) return
    const { minX, minY, maxX, maxY, scale, padding } = coordinateData
    const renderedMinX = padding
    const renderedMaxX = (maxX - minX) * scale + padding
    const renderedMinY = dimensions.height - ((maxY - minY) * scale + padding)
    const renderedMaxY = dimensions.height - padding
    const mapCenterX = (renderedMinX + renderedMaxX) / 2
    const mapCenterY = (renderedMinY + renderedMaxY) / 2
    const zoom = 2
    const screenCenterX = dimensions.width / 2
    const screenCenterY = dimensions.height / 2
    const initialCamera = {
      x: -(mapCenterX - screenCenterX) * zoom,
      y: -(mapCenterY - screenCenterY) * zoom,
      zoom,
    }
    setCamera(initialCamera)
    cameraRef.current = { ...initialCamera }
    setCameraInitialized(true)
  }, [mapData, dimensions, coordinateData])

  // Render map
  useEffect(() => {
    if (!mapData || !canvasRef.current || !cameraInitialized) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, dimensions.width, dimensions.height)

    ctx.save()
    ctx.translate(dimensions.width / 2 + camera.x, dimensions.height / 2 + camera.y)
    ctx.scale(camera.zoom, camera.zoom)
    ctx.translate(-dimensions.width / 2, -dimensions.height / 2)

    // Draw connections
    ctx.strokeStyle = 'rgba(100, 150, 255, 0.15)'
    ctx.lineWidth = 0.5 / camera.zoom
    ctx.beginPath()
    for (const conn of mapData.stargateConnections) {
      const fromSystem = systemMap.get(conn.from)
      const toSystem = systemMap.get(conn.to)
      if (fromSystem && toSystem) {
        const x1 = toCanvasX(fromSystem.position2D?.x || fromSystem.position.x)
        const y1 = toCanvasY(fromSystem.position2D?.y || fromSystem.position.y)
        const x2 = toCanvasX(toSystem.position2D?.x || toSystem.position.x)
        const y2 = toCanvasY(toSystem.position2D?.y || toSystem.position.y)
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
      }
    }
    ctx.stroke()

    // Draw systems
    for (const system of mapData.systems) {
      const x = toCanvasX(system.position2D?.x || system.position.x)
      const y = toCanvasY(system.position2D?.y || system.position.y)

      const isJammed = showJammers && jammedSystemIds.has(system._key)
      const hasTimer = showTimers && timerSystemIds.has(system._key)

      // Base color
      let color = 'rgba(100, 100, 100, 0.5)'
      let size = 1.5 / camera.zoom

      if (isJammed) {
        color = '#ef4444'
        size = 4 / camera.zoom
        // Draw glow
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, size * 3)
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.8)')
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)')
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(x, y, size * 3, 0, Math.PI * 2)
        ctx.fill()
      }

      if (hasTimer) {
        const timer = timers.find(t => t.system_id === system._key)
        if (timer) {
          let timerColor = '#22c55e' // green - planned
          if (timer.urgency === 'critical') timerColor = '#ef4444'
          else if (timer.urgency === 'urgent') timerColor = '#f97316'
          else if (timer.urgency === 'upcoming') timerColor = '#eab308'

          color = timerColor
          size = 5 / camera.zoom

          // Pulsing ring
          ctx.strokeStyle = timerColor
          ctx.lineWidth = 2 / camera.zoom
          ctx.beginPath()
          ctx.arc(x, y, size + 3 / camera.zoom, 0, Math.PI * 2)
          ctx.stroke()
        }
      }

      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(x, y, size, 0, Math.PI * 2)
      ctx.fill()
    }

    ctx.restore()
  }, [mapData, camera, dimensions, systemMap, toCanvasX, toCanvasY, cameraInitialized, jammers, timers, showJammers, showTimers, jammedSystemIds, timerSystemIds])

  // Mouse handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX - cameraRef.current.x, y: e.clientY - cameraRef.current.y })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    cameraRef.current.x = e.clientX - dragStart.x
    cameraRef.current.y = e.clientY - dragStart.y
    setCamera({ ...cameraRef.current })
  }

  const handleMouseUp = () => setIsDragging(false)

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    const newZoom = Math.max(0.5, Math.min(10, cameraRef.current.zoom * (1 + delta)))
    cameraRef.current.zoom = newZoom
    setCamera({ ...cameraRef.current })
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

  if (loading) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center bg-black">
        <p className="text-white">Loading Capital Operations Map...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center bg-black">
        <p className="text-red-500">Error: {error}</p>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative w-full h-full" data-map-ready={cameraInitialized}>
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        className="cursor-move block"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />

      {/* Layer Controls - hidden in snapshot mode */}
      {!snapshotMode && (
        <div className="absolute top-4 right-4 bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
          <div className="text-white text-sm font-semibold mb-2">Layers</div>
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-gray-300 text-sm">
              <input
                type="checkbox"
                checked={showJammers}
                onChange={e => setShowJammers(e.target.checked)}
                className="rounded"
              />
              <span className="text-red-400">●</span> Cyno Jammers ({jammers.length})
            </label>
            <label className="flex items-center gap-2 text-gray-300 text-sm">
              <input
                type="checkbox"
                checked={showTimers}
                onChange={e => setShowTimers(e.target.checked)}
                className="rounded"
              />
              <span className="text-yellow-400">●</span> Structure Timers ({timers.length})
            </label>
          </div>
        </div>
      )}

      {/* Legend - hidden in snapshot mode */}
      {!snapshotMode && (
        <div className="absolute bottom-4 left-4 bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
          <div className="text-white text-sm font-semibold mb-2">Capital Ops Map</div>
          <div className="space-y-1 text-xs text-gray-400">
            <div><span className="text-red-400">●</span> Cyno Jammed</div>
            <div><span className="text-red-500">◯</span> Critical Timer (&lt;1h)</div>
            <div><span className="text-orange-500">◯</span> Urgent Timer (&lt;3h)</div>
            <div><span className="text-yellow-500">◯</span> Upcoming Timer (&lt;24h)</div>
            <div><span className="text-green-500">◯</span> Planned Timer</div>
          </div>
        </div>
      )}
    </div>
  )
}
