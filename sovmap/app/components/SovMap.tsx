'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { MapDataResponse, SolarSystem } from '@/lib/sde-types';

interface SystemADM {
  solar_system_id: number;
  solar_system_name: string;
  region_id: number;
  region_name: string;
  alliance_id: number;
  alliance_name: string;
  adm_level: number;
}

interface ADMResponse {
  systems: SystemADM[];
  count: number;
}

interface JammedSystemsResponse {
  system_ids: number[];
  count: number;
}

interface SovMapProps {
  initialColorMode?: 'adm' | 'alliance' | 'region';
  initialShowJammers?: boolean;
  initialRegion?: string;
  snapshotMode?: boolean;
}

export default function SovMap({
  initialColorMode,
  initialShowJammers = true,
  initialRegion,
  snapshotMode = false,
}: SovMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapData, setMapData] = useState<MapDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });

  const cameraRef = useRef({ x: 0, y: 0, zoom: 2 });
  const [, setCamera] = useState({ x: 0, y: 0, zoom: 2 });
  const rafId = useRef<number>();

  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [cameraInitialized, setCameraInitialized] = useState(false);

  const [admData, setAdmData] = useState<Map<number, SystemADM>>(new Map());
  const [jammedSystems, setJammedSystems] = useState<Set<number>>(new Set());
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const [colorMode, setColorMode] = useState<'adm' | 'alliance' | 'region'>(initialColorMode || 'adm');
  const [showJammers, setShowJammers] = useState(initialShowJammers);

  const [hoveredSystem, setHoveredSystem] = useState<{
    name: string;
    x: number;
    y: number;
    adm?: number;
    alliance?: string;
    isJammed?: boolean;
  } | null>(null);

  const systemMap = useMemo(() => {
    if (!mapData) return new Map<number, SolarSystem>();
    return new Map(mapData.systems.map((s) => [s._key, s]));
  }, [mapData]);


  const getADMColor = useCallback((adm: number) => {
    if (adm <= 2) return 'hsl(0, 80%, ' + (40 + adm * 5) + '%)';
    if (adm <= 4) return 'hsl(' + ((adm - 2) * 30) + ', 80%, 50%)';
    return 'hsl(' + (60 + (adm - 4) * 30) + ', 80%, 45%)';
  }, []);

  const getAllianceColor = useCallback((allianceId: number) => {
    const colors: Record<number, string> = {
      99002685: '#00FFFF',
      1354830081: '#FFD700',
      99003214: '#1E90FF',
      386292982: '#4169E1',
      99005065: '#00CED1',
      99009082: '#7B68EE',
    };
    if (colors[allianceId]) return colors[allianceId];
    const hue = (allianceId * 137.508) % 360;
    return 'hsl(' + hue + ', 70%, 55%)';
  }, []);

  const getRegionColor = useCallback((regionId: number) => {
    const hue = (regionId * 137.508) % 360;
    return 'hsl(' + hue + ', 60%, 50%)';
  }, []);

  const fetchSovData = useCallback(async () => {
    try {
      const [admRes, jammerRes] = await Promise.all([
        fetch('/api/sovereignty'),
        fetch('/api/cynojammers'),
      ]);
      if (admRes.ok) {
        const admJson: ADMResponse = await admRes.json();
        const admMap = new Map<number, SystemADM>();
        admJson.systems.forEach(s => admMap.set(s.solar_system_id, s));
        setAdmData(admMap);
      }
      if (jammerRes.ok) {
        const jammerJson: JammedSystemsResponse = await jammerRes.json();
        setJammedSystems(new Set(jammerJson.system_ids));
      }
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to fetch sovereignty data:', err);
    }
  }, []);

  useEffect(() => {
    const loadMapData = async () => {
      try {
        const res = await fetch('/api/map/data');
        if (!res.ok) throw new Error('Failed to load map data');
        const data = await res.json();
        setMapData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };
    loadMapData();
    fetchSovData();
    const interval = setInterval(fetchSovData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchSovData]);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (mapData && !cameraInitialized) {
      const systems = mapData.systems;
      if (systems.length > 0) {
        let minX = Infinity, maxX = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;
        systems.forEach(s => {
          const x = s.position2D?.x ?? s.position.x;
          const z = s.position2D?.y ?? s.position.z;
          minX = Math.min(minX, x);
          maxX = Math.max(maxX, x);
          minZ = Math.min(minZ, z);
          maxZ = Math.max(maxZ, z);
        });
        const centerX = (minX + maxX) / 2;
        const centerZ = (minZ + maxZ) / 2;
        cameraRef.current = { x: centerX, y: centerZ, zoom: 1.5 };
        setCamera({ ...cameraRef.current });
        setCameraInitialized(true);
      }
    }
  }, [mapData, cameraInitialized]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !mapData) return;

    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const { x: camX, y: camY, zoom } = cameraRef.current;
    const scale = zoom * Math.min(dimensions.width, dimensions.height) / 200000000000;
    const offsetX = dimensions.width / 2;
    const offsetY = dimensions.height / 2;

    ctx.strokeStyle = 'rgba(50, 50, 70, 0.3)';
    ctx.lineWidth = 0.5;
    mapData.stargateConnections.forEach(conn => {
      const from = systemMap.get(conn.from);
      const to = systemMap.get(conn.to);
      if (from && to) {
        const fromX = from.position2D?.x ?? from.position.x;
        const fromZ = from.position2D?.y ?? from.position.z;
        const toX = to.position2D?.x ?? to.position.x;
        const toZ = to.position2D?.y ?? to.position.z;
        const p1x = (fromX - camX) * scale + offsetX;
        const p1y = (fromZ - camY) * scale + offsetY;
        const p2x = (toX - camX) * scale + offsetX;
        const p2y = (toZ - camY) * scale + offsetY;
        ctx.beginPath();
        ctx.moveTo(p1x, p1y);
        ctx.lineTo(p2x, p2y);
        ctx.stroke();
      }
    });

    mapData.systems.forEach(system => {
      const sysX = system.position2D?.x ?? system.position.x;
      const sysZ = system.position2D?.y ?? system.position.z;
      const screenX = (sysX - camX) * scale + offsetX;
      const screenY = (sysZ - camY) * scale + offsetY;
      if (screenX < -10 || screenX > dimensions.width + 10 ||
          screenY < -10 || screenY > dimensions.height + 10) return;

      const admInfo = admData.get(system._key);
      const isJammed = jammedSystems.has(system._key);
      const isNullsec = system.securityStatus < 0.0;

      let color = 'rgba(100, 100, 100, 0.5)';
      if (isNullsec && admInfo) {
        if (colorMode === 'adm') color = getADMColor(admInfo.adm_level);
        else if (colorMode === 'alliance') color = getAllianceColor(admInfo.alliance_id);
        else color = getRegionColor(admInfo.region_id);
      } else if (isNullsec) {
        color = 'rgba(80, 80, 80, 0.6)';
      }

      const radius = isNullsec ? 2 + zoom * 0.5 : 1;
      ctx.beginPath();
      ctx.arc(screenX, screenY, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      if (showJammers && isJammed) {
        ctx.beginPath();
        ctx.arc(screenX, screenY, radius + 4, 0, Math.PI * 2);
        ctx.strokeStyle = '#FF0000';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  }, [mapData, dimensions, admData, jammedSystems, colorMode, showJammers, systemMap, getADMColor, getAllianceColor, getRegionColor]);

  useEffect(() => {
    const animate = () => {
      render();
      rafId.current = requestAnimationFrame(animate);
    };
    rafId.current = requestAnimationFrame(animate);
    return () => { if (rafId.current) cancelAnimationFrame(rafId.current); };
  }, [render]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      const scale = cameraRef.current.zoom * Math.min(dimensions.width, dimensions.height) / 200000000000;
      cameraRef.current.x -= dx / scale;
      cameraRef.current.y -= dy / scale;
      setDragStart({ x: e.clientX, y: e.clientY });
      setCamera({ ...cameraRef.current });
    } else {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect || !mapData) return;
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const { x: camX, y: camY, zoom } = cameraRef.current;
      const scale = zoom * Math.min(dimensions.width, dimensions.height) / 200000000000;
      const offsetX = dimensions.width / 2;
      const offsetY = dimensions.height / 2;

      let closest: typeof hoveredSystem = null;
      let closestDist = 20;

      mapData.systems.forEach(system => {
        const sysX = system.position2D?.x ?? system.position.x;
        const sysZ = system.position2D?.y ?? system.position.z;
        const screenX = (sysX - camX) * scale + offsetX;
        const screenY = (sysZ - camY) * scale + offsetY;
        const dist = Math.sqrt((mouseX - screenX) ** 2 + (mouseY - screenY) ** 2);
        if (dist < closestDist) {
          closestDist = dist;
          const admInfo = admData.get(system._key);
          closest = {
            name: system.name.en,
            x: screenX,
            y: screenY,
            adm: admInfo?.adm_level,
            alliance: admInfo?.alliance_name,
            isJammed: jammedSystems.has(system._key),
          };
        }
      });
      setHoveredSystem(closest);
    }
  };

  const handleMouseUp = () => setIsDragging(false);
  const handleMouseLeave = () => { setIsDragging(false); setHoveredSystem(null); };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    cameraRef.current.zoom = Math.max(0.5, Math.min(20, cameraRef.current.zoom * zoomFactor));
    setCamera({ ...cameraRef.current });
  };

  if (loading) return <div className="flex items-center justify-center h-full text-white">Loading map data...</div>;
  if (error) return <div className="flex items-center justify-center h-full text-red-500">Error: {error}</div>;

  return (
    <div ref={containerRef} className="relative w-full h-full bg-[#0a0a0f]" data-map-ready={!loading && mapData ? 'true' : 'false'}>
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onWheel={handleWheel}
        className="cursor-grab active:cursor-grabbing"
      />

      {!snapshotMode && (
        <div className="absolute top-4 left-4 bg-black/80 p-3 rounded-lg text-white text-sm space-y-2">
          <div className="font-bold text-cyan-400">Sovereignty Map</div>
          <div className="flex gap-2">
            <button onClick={() => setColorMode('adm')} className={'px-2 py-1 rounded ' + (colorMode === 'adm' ? 'bg-cyan-600' : 'bg-gray-700')}>ADM</button>
            <button onClick={() => setColorMode('alliance')} className={'px-2 py-1 rounded ' + (colorMode === 'alliance' ? 'bg-cyan-600' : 'bg-gray-700')}>Alliance</button>
            <button onClick={() => setColorMode('region')} className={'px-2 py-1 rounded ' + (colorMode === 'region' ? 'bg-cyan-600' : 'bg-gray-700')}>Region</button>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={showJammers} onChange={(e) => setShowJammers(e.target.checked)} className="accent-red-500" />
            <span className="text-red-400">Cyno Jammers ({jammedSystems.size})</span>
          </label>
          <div className="text-xs text-gray-400">Systems with ADM: {admData.size}</div>
          {lastUpdate && <div className="text-xs text-gray-500">Updated: {lastUpdate.toLocaleTimeString()}</div>}
        </div>
      )}

      {!snapshotMode && colorMode === 'adm' && (
        <div className="absolute bottom-4 left-4 bg-black/80 p-2 rounded text-white text-xs">
          <div className="font-bold mb-1">ADM Level</div>
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full" style={{ background: getADMColor(1) }} /><span>1-2 (Vulnerable)</span></div>
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full" style={{ background: getADMColor(3) }} /><span>3-4 (Medium)</span></div>
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full" style={{ background: getADMColor(6) }} /><span>5-6 (Strong)</span></div>
        </div>
      )}

      {!snapshotMode && hoveredSystem && (
        <div className="absolute bg-black/90 text-white text-xs p-2 rounded pointer-events-none z-10" style={{ left: hoveredSystem.x + 15, top: hoveredSystem.y - 10 }}>
          <div className="font-bold">{hoveredSystem.name}</div>
          {hoveredSystem.adm && <div>ADM: {hoveredSystem.adm.toFixed(1)}</div>}
          {hoveredSystem.alliance && <div>Alliance: {hoveredSystem.alliance}</div>}
          {hoveredSystem.isJammed && <div className="text-red-400 font-bold">CYNO JAMMED</div>}
        </div>
      )}
    </div>
  );
}
