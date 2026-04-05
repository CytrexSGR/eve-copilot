'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { MapDataResponse } from '@/lib/sde-types';
import type { BattlesResponse } from '@/app/api/battles/route';
import { apiFetch } from '@/lib/api';

import type {
  ColorMode, Battle, SovCampaign, LiveKill, LiveKillsResponse,
  HoveredSystem, HoveredBattle, HoveredKill, HoveredCampaign,
  HuntingHeatmapData, CapitalActivityData, LogiPresenceData,
  TheraConnection, HoveredTheraConnection,
} from './starmap/types';
import {
  getSecurityColor, getRegionColor, getFactionColor, getAllianceColor,
  getActivityColor as getActivityColorFn, getAdmColor as getAdmColorFn,
  getHuntingColor as getHuntingColorFn,
  FACTION_NAMES,
} from './starmap/lib/colorFunctions';
import { loadBattleIcons, type BattleIconRefs } from './starmap/lib/battleIcons';
import { ColorModeButtons, OverlayControls, HeatmapLegend } from './starmap/MapControls';
import { BattleTooltip, KillTooltip, SystemTooltip, CampaignTooltip, TheraTooltip } from './starmap/MapTooltips';

interface StarMapProps {
  initialColorMode?: string;
  initialShowCampaigns?: boolean;
  initialKillsMinutes?: number;
  initialActivityMinutes?: number;
  initialRegion?: string;
  snapshotMode?: boolean;
  externalFilters?: boolean;
  enabledStatusLevels?: string[];
  entityType?: string;
  entityId?: string;
  entityDays?: number;
}

export default function StarMap({
  initialColorMode,
  initialShowCampaigns = true,
  initialKillsMinutes,
  initialActivityMinutes,
  initialRegion,
  snapshotMode = false,
  externalFilters = false,
  enabledStatusLevels,
  entityType,
  entityId,
  entityDays = 30,
}: StarMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapData, setMapData] = useState<MapDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });

  const cameraRef = useRef({
    x: 0,
    y: 0,
    zoom: 2,
  });
  const [camera, setCamera] = useState({
    x: 0,
    y: 0,
    zoom: 2,
  });

  const rafId = useRef<number>();
  const renderRequested = useRef(false);
  const iconRefs = useRef<BattleIconRefs>({ skull: null, gank: null, brawl: null, battle: null, hellcamp: null });

  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [mouseDownPos, setMouseDownPos] = useState({ x: 0, y: 0 });
  const [colorMode, setColorMode] = useState<ColorMode>(
    (initialColorMode as ColorMode) || 'alliance'
  );
  const [cameraInitialized, setCameraInitialized] = useState(false);
  const [sovereigntyData, setSovereigntyData] = useState<Record<number, number> | null>(null);
  const [allianceData, setAllianceData] = useState<Record<
    number,
    { alliance_id: number; alliance_name: string }
  > | null>(null);

  // DOTLAN data layers
  const [activityData, setActivityData] = useState<Record<number, { value: number; normalized: number }> | null>(null);
  const [admData, setAdmData] = useState<Record<number, number> | null>(null);

  // Entity activity data (for entity_activity color mode)
  const [entityActivityData, setEntityActivityData] = useState<import('./starmap/types').EntityActivityData | null>(null);
  const [campaigns, setCampaigns] = useState<SovCampaign[]>([]);
  const [showCampaigns, setShowCampaigns] = useState(initialShowCampaigns);

  // Intel overlay data
  const [huntingData, setHuntingData] = useState<HuntingHeatmapData | null>(null);
  const [capitalActivityData, setCapitalActivityData] = useState<CapitalActivityData | null>(null);
  const [logiPresenceData, setLogiPresenceData] = useState<LogiPresenceData | null>(null);
  const [showCapitalActivity, setShowCapitalActivity] = useState(false);
  const [showLogiPresence, setShowLogiPresence] = useState(false);
  const [intelDays, setIntelDays] = useState(30);

  // Thera/Turnur wormhole connections
  const [theraConnections, setTheraConnections] = useState<TheraConnection[]>([]);
  const [showWormholes, setShowWormholes] = useState(false);
  const [hoveredTheraConnection, setHoveredTheraConnection] = useState<HoveredTheraConnection | null>(null);

  const [hoveredCampaign, setHoveredCampaign] = useState<HoveredCampaign | null>(null);
  const [hoveredSystem, setHoveredSystem] = useState<HoveredSystem | null>(null);

  const [hoveredBattle, setHoveredBattle] = useState<HoveredBattle | null>(null);
  const [hoveredKill, setHoveredKill] = useState<HoveredKill | null>(null);

  // Battle layer state
  const [battles, setBattles] = useState<Battle[]>([]);

  // Live kills layer state
  const [liveKills, setLiveKills] = useState<LiveKill[]>([]);
  const [activityMinutes, setActivityMinutes] = useState(initialActivityMinutes || initialKillsMinutes || 60);

  // Status level filters — battles show when at least one filter is active
  type StatusLevel = 'gank' | 'brawl' | 'battle' | 'hellcamp';
  const [statusFilters, setStatusFilters] = useState<Record<StatusLevel, boolean>>({
    gank: true,
    brawl: true,
    battle: true,
    hellcamp: true,
  });
  const showBattles = Object.values(statusFilters).some(v => v);

  // Flash effect for new kills/battles
  const knownKillIds = useRef<Set<number>>(new Set());
  const knownBattleIds = useRef<Set<number>>(new Set());
  const [flashingKills, setFlashingKills] = useState<Map<number, number>>(new Map()); // killId -> timestamp
  const [flashingBattles, setFlashingBattles] = useState<Map<number, number>>(new Map());

  // Count battles per status level
  const statusCounts = useMemo(() => {
    const counts: Record<StatusLevel, number> = { gank: 0, brawl: 0, battle: 0, hellcamp: 0 };
    for (const b of battles) {
      const level = (b.status_level || 'gank') as StatusLevel;
      if (level in counts) counts[level]++;
    }
    return counts;
  }, [battles]);

  // Filter battles by status level
  const filteredBattles = useMemo(() => {
    let filtered = battles;

    // In entity_activity mode, filter battles to entity's active systems or involving entity
    if (colorMode === 'entity_activity' && entityActivityData && entityType) {
      filtered = filtered.filter(b => {
        const inActiveSystem = !!entityActivityData.systems[b.system_id];
        // Check if entity's alliance is involved in the battle
        const targetAllianceId = entityType === 'corporation'
          ? entityActivityData.allianceId
          : Number(entityId);
        const allianceInvolved = targetAllianceId
          ? (b.top_alliances?.some(a => a.alliance_id === targetAllianceId) ?? false)
          : false;
        return inActiveSystem || allianceInvolved;
      });
    }

    // External filters take precedence (from parent page)
    if (externalFilters && enabledStatusLevels && enabledStatusLevels.length > 0) {
      return filtered.filter(b => {
        const level = b.status_level || 'gank';
        return enabledStatusLevels.includes(level);
      });
    }
    // Local filters (from OverlayControls)
    return filtered.filter(b => {
      const level = (b.status_level || 'gank') as StatusLevel;
      return statusFilters[level];
    });
  }, [battles, externalFilters, enabledStatusLevels, statusFilters, colorMode, entityActivityData, entityType, entityId]);

  // Notify parent window when activity filter changes
  useEffect(() => {
    if (window.parent !== window) {
      window.parent.postMessage({ type: 'ectmap-activity-change', minutes: activityMinutes }, '*');
    }
  }, [activityMinutes]);

  // Clean up expired flash effects and trigger re-render for animation
  useEffect(() => {
    if (flashingKills.size === 0 && flashingBattles.size === 0) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const flashDuration = 2000; // 2 seconds

      setFlashingKills(prev => {
        const updated = new Map(prev);
        for (const [id, timestamp] of updated) {
          if (now - timestamp > flashDuration) updated.delete(id);
        }
        return updated.size !== prev.size ? updated : prev;
      });

      setFlashingBattles(prev => {
        const updated = new Map(prev);
        for (const [id, timestamp] of updated) {
          if (now - timestamp > flashDuration) updated.delete(id);
        }
        return updated.size !== prev.size ? updated : prev;
      });
    }, 50); // Update at ~20fps for smooth animation

    return () => clearInterval(interval);
  }, [flashingKills.size, flashingBattles.size]);

  // Color functions from starmap/lib/colorFunctions (now pure functions, no useCallback needed)
  const getActivityColorLocal = useCallback(
    (systemId: number) => getActivityColorFn(systemId, activityData),
    [activityData]
  );
  const getAdmColorLocal = useCallback(
    (systemId: number) => getAdmColorFn(systemId, admData),
    [admData]
  );

  const getEntityActivityColor = useCallback(
    (systemId: number): string => {
      if (!entityActivityData?.systems[systemId]) return 'rgba(255, 255, 255, 0.08)';
      const sys = entityActivityData.systems[systemId];
      const norm = entityActivityData.maxActivity > 0 ? sys.activity / entityActivityData.maxActivity : 0;
      // Heatmap: blue (low) -> cyan -> green -> yellow -> red (high)
      if (norm < 0.25) return `hsl(${200 - norm * 4 * 80}, 80%, ${40 + norm * 4 * 20}%)`;
      if (norm < 0.5) return `hsl(${120}, 80%, ${50 + (norm - 0.25) * 4 * 10}%)`;
      if (norm < 0.75) return `hsl(${60 - (norm - 0.5) * 4 * 20}, 90%, ${55}%)`;
      return `hsl(${0 + (1 - norm) * 40}, 95%, 55%)`;
    },
    [entityActivityData]
  );

  const getHuntingColorLocal = useCallback(
    (systemId: number): string => getHuntingColorFn(systemId, huntingData),
    [huntingData]
  );

  const systemMap = useMemo(() => {
    if (!mapData) return new Map();
    return new Map(mapData.systems.map((s) => [s._key, s]));
  }, [mapData]);

  const regionMap = useMemo(() => {
    if (!mapData) return new Map();
    return new Map(mapData.regions.map((r) => [r._key, r]));
  }, [mapData]);

  const bounds = useMemo(() => {
    if (!mapData || mapData.systems.length === 0) {
      return { minX: 0, minY: 0, maxX: 0, maxY: 0 };
    }

    let minX = Infinity,
      maxX = -Infinity;
    let minY = Infinity,
      maxY = -Infinity;

    for (const system of mapData.systems) {
      const x = system.position2D?.x || system.position.x;
      const y = system.position2D?.y || system.position.y;
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }

    return { minX, minY, maxX, maxY };
  }, [mapData]);

  const coordinateData = useMemo(() => {
    const padding = 50;
    const scaleX = (dimensions.width - padding * 2) / (bounds.maxX - bounds.minX || 1);
    const scaleY = (dimensions.height - padding * 2) / (bounds.maxY - bounds.minY || 1);
    const scale = Math.min(scaleX, scaleY);

    return {
      ...bounds,
      scale,
      padding,
    };
  }, [bounds, dimensions]);

  const toCanvasX = useCallback(
    (x: number) => (x - coordinateData.minX) * coordinateData.scale + coordinateData.padding,
    [coordinateData]
  );

  const toCanvasY = useCallback(
    (y: number) =>
      dimensions.height -
      ((y - coordinateData.minY) * coordinateData.scale + coordinateData.padding),
    [coordinateData, dimensions.height]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width, height });
        }
      }
    });
    ro.observe(el);
    // initial read
    if (el.clientWidth > 0 && el.clientHeight > 0) {
      setDimensions({ width: el.clientWidth, height: el.clientHeight });
    }
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    return () => {
      if (rafId.current) {
        cancelAnimationFrame(rafId.current);
      }
    };
  }, []);

  // Listen for focus-system messages from parent window
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'ectmap-focus-system' && typeof event.data.systemId === 'number') {
        const system = systemMap.get(event.data.systemId);
        if (system && mapData) {
          // Get canvas coordinates for the system
          const sysX = system.position2D?.x || system.position.x;
          const sysY = system.position2D?.y || system.position.y;
          const canvasX = toCanvasX(sysX);
          const canvasY = toCanvasY(sysY);

          // Calculate camera position to center on system
          // Camera x/y is the offset, so we need to center the system in the viewport
          const targetZoom = Math.max(camera.zoom, 4); // Zoom in a bit
          const newCamera = {
            x: dimensions.width / 2 - canvasX * targetZoom,
            y: dimensions.height / 2 - canvasY * targetZoom,
            zoom: targetZoom,
          };

          setCamera(newCamera);
          cameraRef.current = { ...newCamera };
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [systemMap, mapData, dimensions, camera.zoom, toCanvasX, toCanvasY]);

  // Load SVG battle icons from starmap/lib/battleIcons
  useEffect(() => {
    loadBattleIcons().then(refs => { iconRefs.current = refs; });
  }, []);

  useEffect(() => {
    async function loadMap(retries = 3) {
      for (let attempt = 0; attempt <= retries; attempt++) {
        try {
          const response = await apiFetch('/api/map/data');
          if (!response.ok) throw new Error('Failed to load map data');
          const data = await response.json();
          setMapData(data);
          setLoading(false);
          return;
        } catch (err) {
          if (attempt === retries) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            setLoading(false);
          } else {
            await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
          }
        }
      }
    }
    loadMap();
  }, []);

  useEffect(() => {
    async function loadSovereignty() {
      try {
        const response = await apiFetch('/api/sovereignty');
        if (!response.ok) throw new Error('Failed to load sovereignty data');
        const data = await response.json();
        setSovereigntyData(data);
      } catch (err) {
        console.error('Error loading sovereignty data:', err);
        setSovereigntyData({});
      }
    }

    if (!sovereigntyData) {
      loadSovereignty();
    }
  }, [sovereigntyData]);

  useEffect(() => {
    async function loadAllianceSovereignty() {
      try {
        const response = await apiFetch('/api/alliance-sovereignty');
        if (!response.ok) throw new Error('Failed to load alliance sovereignty data');
        const data = await response.json();
        setAllianceData(data);
      } catch (err) {
        console.error('Error loading alliance sovereignty data:', err);
        setAllianceData({});
      }
    }

    if (!allianceData) {
      loadAllianceSovereignty();
    }
  }, [allianceData]);

  // Load DOTLAN activity heatmap data
  useEffect(() => {
    const isActivityMode = ['npc_kills', 'ship_kills', 'jumps'].includes(colorMode);
    if (!isActivityMode) { setActivityData(null); return; }

    async function load() {
      try {
        const res = await apiFetch(`/api/dotlan-activity?metric=${colorMode}&hours=24`);
        if (res.ok) setActivityData(await res.json());
      } catch (err) {
        console.error('Error loading DOTLAN activity:', err);
      }
    }
    load();
    const interval = setInterval(load, 300_000);
    return () => clearInterval(interval);
  }, [colorMode]);

  // Load DOTLAN ADM data (always, used in tooltip for all modes)
  useEffect(() => {
    async function load() {
      try {
        const res = await apiFetch('/api/dotlan-adm');
        if (res.ok) setAdmData(await res.json());
      } catch (err) {
        console.error('Error loading DOTLAN ADM:', err);
      }
    }
    load();
    const interval = setInterval(load, 600_000);
    return () => clearInterval(interval);
  }, []);

  // Fetch entity activity data
  useEffect(() => {
    if (colorMode !== 'entity_activity' || !entityType || !entityId) return;
    const fetchEntityData = async () => {
      try {
        const res = await apiFetch(`/api/entity-geography?entityType=${entityType}&entityId=${entityId}&days=${entityDays}`);
        const data = await res.json();
        setEntityActivityData(data);
      } catch (err) {
        console.error('Failed to fetch entity geography:', err);
      }
    };
    fetchEntityData();
  }, [colorMode, entityType, entityId, entityDays]);

  // Fetch hunting heatmap data when hunting color mode is active
  useEffect(() => {
    if (colorMode !== 'hunting') { setHuntingData(null); return; }
    async function load() {
      try {
        const res = await apiFetch(`/api/intel-hunting?days=${intelDays}`);
        const data = await res.json();
        setHuntingData(data);
      } catch (err) { console.error('Failed to fetch hunting data:', err); }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [colorMode, intelDays]);

  // Fetch capital activity data when overlay is active
  useEffect(() => {
    if (!showCapitalActivity) { setCapitalActivityData(null); return; }
    async function load() {
      try {
        const res = await apiFetch(`/api/intel-capitals?days=${intelDays}`);
        const data = await res.json();
        setCapitalActivityData(data);
      } catch (err) { console.error('Failed to fetch capital data:', err); }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [showCapitalActivity, intelDays]);

  // Fetch logi presence data when overlay is active
  useEffect(() => {
    if (!showLogiPresence) { setLogiPresenceData(null); return; }
    async function load() {
      try {
        const res = await apiFetch(`/api/intel-logi?days=${intelDays}`);
        const data = await res.json();
        setLogiPresenceData(data);
      } catch (err) { console.error('Failed to fetch logi data:', err); }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [showLogiPresence, intelDays]);

  // Fetch Thera/Turnur wormhole connections from Eve-Scout
  useEffect(() => {
    if (!showWormholes) { setTheraConnections([]); return; }
    async function load() {
      try {
        const res = await apiFetch('/api/thera-connections');
        const data = await res.json();
        setTheraConnections(Array.isArray(data) ? data : []);
      } catch (err) { console.error('Failed to fetch Thera connections:', err); }
    }
    load();
    const interval = setInterval(load, 300000); // Refresh every 5 min
    return () => clearInterval(interval);
  }, [showWormholes]);

  // Load DOTLAN sov campaigns
  useEffect(() => {
    if (!showCampaigns) { setCampaigns([]); return; }

    async function load() {
      try {
        const res = await apiFetch('/api/dotlan-campaigns');
        if (res.ok) setCampaigns(await res.json());
      } catch (err) {
        console.error('Error loading DOTLAN campaigns:', err);
      }
    }
    load();
    const interval = setInterval(load, 120_000);
    return () => clearInterval(interval);
  }, [showCampaigns]);

  // Load battles
  useEffect(() => {
    async function loadBattles() {
      try {
        const response = await apiFetch(`/api/battles?minutes=${activityMinutes}`);
        if (!response.ok) {
          console.error('Failed to load battles');
          return;
        }
        const data: BattlesResponse = await response.json();

        // Detect new battles and trigger flash
        const now = Date.now();
        const newFlashing = new Map<number, number>();
        for (const battle of data.battles) {
          if (!knownBattleIds.current.has(battle.battle_id)) {
            newFlashing.set(battle.battle_id, now);
            knownBattleIds.current.add(battle.battle_id);
          }
        }
        if (newFlashing.size > 0) {
          setFlashingBattles(prev => new Map([...prev, ...newFlashing]));
        }

        setBattles(data.battles);
      } catch (err) {
        console.error('Error loading battles:', err);
      }
    }

    loadBattles();
    const interval = setInterval(loadBattles, 5000);
    return () => clearInterval(interval);
  }, [activityMinutes]);

  // Load live kills (always active)
  useEffect(() => {
    async function loadLiveKills() {
      try {
        const response = await apiFetch(`/api/live-kills?minutes=${activityMinutes}`);
        if (!response.ok) {
          console.error('Failed to load live kills:', response.status);
          return;
        }
        const data: LiveKillsResponse = await response.json();

        // Detect new kills and trigger flash
        const now = Date.now();
        const newFlashing = new Map<number, number>();
        for (const kill of data.kills) {
          if (!knownKillIds.current.has(kill.killmail_id)) {
            newFlashing.set(kill.killmail_id, now);
            knownKillIds.current.add(kill.killmail_id);
          }
        }
        if (newFlashing.size > 0) {
          setFlashingKills(prev => new Map([...prev, ...newFlashing]));
        }

        setLiveKills(data.kills);
      } catch (err) {
        console.error('Error loading live kills:', err);
      }
    }

    loadLiveKills();
    const interval = setInterval(loadLiveKills, 5000);
    return () => clearInterval(interval);
  }, [activityMinutes]);


  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cameraInitialized) return;

    let wheelRafId: number | null = null;
    let pendingZoomDelta = 0;
    let lastWheelMouse = { x: 0, y: 0 };

    const handleWheelEvent = (e: WheelEvent) => {
      e.preventDefault();

      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      pendingZoomDelta += delta;
      lastWheelMouse = { x: e.clientX, y: e.clientY };

      if (wheelRafId !== null) return;

      wheelRafId = requestAnimationFrame(() => {
        const canvasRect = canvas.getBoundingClientRect();
        const mouseX = lastWheelMouse.x - canvasRect.left;
        const mouseY = lastWheelMouse.y - canvasRect.top;

        const cam = cameraRef.current;
        const newZoom = Math.max(0.1, Math.min(10, cam.zoom * (1 + pendingZoomDelta)));

        const worldX = (mouseX - dimensions.width / 2 - cam.x) / cam.zoom;
        const worldY = (mouseY - dimensions.height / 2 - cam.y) / cam.zoom;

        const newX = mouseX - dimensions.width / 2 - worldX * newZoom;
        const newY = mouseY - dimensions.height / 2 - worldY * newZoom;

        cameraRef.current = {
          x: newX,
          y: newY,
          zoom: newZoom,
        };

        setCamera({ ...cameraRef.current });

        wheelRafId = null;
        pendingZoomDelta = 0;
      });
    };

    canvas.addEventListener('wheel', handleWheelEvent, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheelEvent);
  }, [dimensions, cameraInitialized]);

  useEffect(() => {
    if (!mapData || mapData.systems.length === 0) return;

    const { minX, minY, maxX, maxY, scale, padding } = coordinateData;

    const renderedMinX = padding;
    const renderedMaxX = (maxX - minX) * scale + padding;
    const renderedMinY = dimensions.height - ((maxY - minY) * scale + padding);
    const renderedMaxY = dimensions.height - padding;

    const mapCenterX = (renderedMinX + renderedMaxX) / 2;
    const mapCenterY = (renderedMinY + renderedMaxY) / 2;

    const zoom = 2;
    const screenCenterX = dimensions.width / 2;
    const screenCenterY = dimensions.height / 2;

    const initialCamera = {
      x: -(mapCenterX - screenCenterX) * zoom,
      y: -(mapCenterY - screenCenterY) * zoom,
      zoom: zoom,
    };
    setCamera(initialCamera);
    cameraRef.current = { ...initialCamera };
    setCameraInitialized(true);
  }, [mapData, dimensions, coordinateData]);

  // Focus on entity activity center
  useEffect(() => {
    if (colorMode !== 'entity_activity' || !entityActivityData || !mapData || !cameraInitialized) return;
    if (Object.keys(entityActivityData.systems).length === 0) return;

    const activeSystems = Object.keys(entityActivityData.systems).map(Number);
    let sumX = 0, sumY = 0, count = 0;
    for (const sysId of activeSystems) {
      const sys = systemMap.get(sysId);
      if (sys) {
        sumX += sys.position2D?.x || sys.position.x;
        sumY += sys.position2D?.y || sys.position.y;
        count++;
      }
    }
    if (count > 0) {
      const cx = toCanvasX(sumX / count);
      const cy = toCanvasY(sumY / count);
      const zoom = 3;
      const screenCenterX = dimensions.width / 2;
      const screenCenterY = dimensions.height / 2;
      const newCamera = {
        x: -(cx - screenCenterX) * zoom,
        y: -(cy - screenCenterY) * zoom,
        zoom: zoom,
      };
      setCamera(newCamera);
      cameraRef.current = { ...newCamera };
    }
  }, [colorMode, entityActivityData, mapData, cameraInitialized, systemMap, toCanvasX, toCanvasY, dimensions]);

  // Focus on initial region if provided (for snapshot mode)
  useEffect(() => {
    if (!initialRegion || !mapData || !cameraInitialized) return;

    // Find region by name (case-insensitive)
    const region = mapData.regions.find(
      (r) => r.name.en.toLowerCase() === initialRegion.toLowerCase()
    );
    if (!region) return;

    const regionSystems = mapData.systems.filter((s) => s.regionID === region._key);
    if (regionSystems.length === 0) return;

    let sumX = 0,
      sumY = 0;

    for (const system of regionSystems) {
      sumX += system.position2D?.x || system.position.x;
      sumY += system.position2D?.y || system.position.y;
    }

    const centerX = sumX / regionSystems.length;
    const centerY = sumY / regionSystems.length;

    const canvasX = toCanvasX(centerX);
    const canvasY = toCanvasY(centerY);

    const zoom = 4;
    const screenCenterX = dimensions.width / 2;
    const screenCenterY = dimensions.height / 2;

    const newCamera = {
      x: -(canvasX - screenCenterX) * zoom,
      y: -(canvasY - screenCenterY) * zoom,
      zoom: zoom,
    };

    setCamera(newCamera);
    cameraRef.current = { ...newCamera };
  }, [initialRegion, mapData, cameraInitialized, toCanvasX, toCanvasY, dimensions]);

  useEffect(() => {
    if (!mapData || !canvasRef.current || !cameraInitialized) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, dimensions.width, dimensions.height);

    ctx.save();
    ctx.translate(dimensions.width / 2 + camera.x, dimensions.height / 2 + camera.y);
    ctx.scale(camera.zoom, camera.zoom);
    ctx.translate(-dimensions.width / 2, -dimensions.height / 2);

    ctx.strokeStyle = 'rgba(100, 150, 255, 0.3)';
    ctx.lineWidth = 1 / camera.zoom;
    ctx.beginPath();

    for (const conn of mapData.stargateConnections) {
      const fromSystem = systemMap.get(conn.from);
      const toSystem = systemMap.get(conn.to);

      if (fromSystem && toSystem) {
        const x1 = toCanvasX(fromSystem.position2D?.x || fromSystem.position.x);
        const y1 = toCanvasY(fromSystem.position2D?.y || fromSystem.position.y);
        const x2 = toCanvasX(toSystem.position2D?.x || toSystem.position.x);
        const y2 = toCanvasY(toSystem.position2D?.y || toSystem.position.y);

        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
    }
    ctx.stroke();

    // Pre-compute top-10 hunting systems for numbered markers
    const huntingRankMap = new Map<number, number>();
    if (colorMode === 'hunting' && huntingData) {
      const sorted = Object.entries(huntingData.systems)
        .sort(([, a], [, b]) => b.score - a.score)
        .slice(0, 10);
      sorted.forEach(([id], i) => huntingRankMap.set(Number(id), i + 1));
    }

    for (const system of mapData.systems) {
      const x = toCanvasX(system.position2D?.x || system.position.x);
      const y = toCanvasY(system.position2D?.y || system.position.y);

      let color: string;
      if (colorMode === 'region') {
        color = getRegionColor(system.regionID);
      } else if (colorMode === 'security') {
        color = getSecurityColor(system.securityStatus);
      } else if (colorMode === 'faction') {
        const factionId = sovereigntyData?.[system._key];

        if (factionId) {
          color = getFactionColor(factionId);
        } else {
          color = 'hsl(0, 0%, 30%)';
        }
      } else if (colorMode === 'alliance') {
        const allianceInfo = allianceData?.[system._key];

        if (allianceInfo) {
          color = getAllianceColor(allianceInfo.alliance_id);
        } else {
          color = 'hsl(0, 0%, 30%)';
        }
      } else if (['npc_kills', 'ship_kills', 'jumps'].includes(colorMode)) {
        color = getActivityColorLocal(system._key);
      } else if (colorMode === 'adm') {
        color = getAdmColorLocal(system._key);
      } else if (colorMode === 'entity_activity') {
        color = getEntityActivityColor(system._key);
      } else if (colorMode === 'hunting') {
        color = getHuntingColorLocal(system._key);
      } else {
        color = getRegionColor(system.regionID);
      }

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, 2 / camera.zoom, 0, Math.PI * 2);
      ctx.fill();

      // Home system golden ring for entity_activity mode
      if (colorMode === 'entity_activity' && entityActivityData?.systems[system._key]?.isHome) {
        ctx.strokeStyle = '#d4a017';
        ctx.lineWidth = 3 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, 5 / camera.zoom, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Capital umbrella warning ring for hunting mode
      if (colorMode === 'hunting' && huntingData?.systems[system._key]?.has_capitals) {
        ctx.strokeStyle = '#ff4444';
        ctx.lineWidth = 2 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, 4 / camera.zoom, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Top-10 hunting score markers (numbered 1-10)
      if (colorMode === 'hunting' && huntingRankMap.has(system._key)) {
        const rank = huntingRankMap.get(system._key)!;
        const fontSize = Math.max(4, 6 / camera.zoom);
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${fontSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${rank}`, x, y);
      }
    }

    // Draw battles/events layer (icon based on status_level)
    if (showBattles && filteredBattles.length > 0) {
      const now = Date.now();
      for (const battle of filteredBattles) {
        const system = systemMap.get(battle.system_id);
        if (!system) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        // Icon, size, and color based on status_level
        const statusLevel = battle.status_level || 'gank';
        let iconRef: HTMLImageElement | null = null;
        let iconSize = 12 / camera.zoom;
        let glowColor = '#ff4444';

        switch (statusLevel) {
          case 'hellcamp':
            iconRef = iconRefs.current.hellcamp;
            iconSize = 28 / camera.zoom;
            glowColor = '#00ffff';
            break;
          case 'battle':
            iconRef = iconRefs.current.battle;
            iconSize = 22 / camera.zoom;
            glowColor = '#ffcc00';
            break;
          case 'brawl':
            iconRef = iconRefs.current.brawl;
            iconSize = 16 / camera.zoom;
            glowColor = '#ff8800';
            break;
          default: // gank
            iconRef = iconRefs.current.gank;
            iconSize = 12 / camera.zoom;
            glowColor = '#ff4444';
        }

        // Flash effect for new battles
        const flashTime = flashingBattles.get(battle.battle_id);
        let flashMultiplier = 1;
        if (flashTime) {
          const elapsed = now - flashTime;
          const flashDuration = 2000;
          const progress = Math.min(elapsed / flashDuration, 1);
          flashMultiplier = 1 + (1 - progress) * (1 + Math.sin(elapsed / 100) * 0.5);
        }

        // Draw flash ring for new battles
        if (flashTime) {
          const elapsed = now - flashTime;
          const flashDuration = 2000;
          const progress = Math.min(elapsed / flashDuration, 1);
          const ringSize = iconSize * (1 + progress * 2);
          const ringAlpha = (1 - progress) * 0.8;

          ctx.strokeStyle = `rgba(255, 255, 255, ${ringAlpha})`;
          ctx.lineWidth = 3 / camera.zoom;
          ctx.beginPath();
          ctx.arc(x, y, ringSize, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Draw glow behind icon
        const glowSize = iconSize * 1.5 * flashMultiplier;
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, glowSize);
        gradient.addColorStop(0, glowColor);
        gradient.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, glowSize, 0, Math.PI * 2);
        ctx.fill();

        // Draw icon
        if (iconRef) {
          const drawSize = iconSize * 2 * flashMultiplier;
          ctx.drawImage(iconRef, x - drawSize / 2, y - drawSize / 2, drawSize, drawSize);
        }
      }
    }

    // Draw live kills layer (skull icon, size based on ISK value)
    // NOTE: Only render kills WITHOUT battle_id - kills WITH battle_id are shown as events (gank/brawl/battle/hellcamp)
    if (liveKills.length > 0 && iconRefs.current.skull) {
      const now = Date.now();
      const skullImg = iconRefs.current.skull;

      for (const kill of liveKills) {
        // Skip kills that have a battle_id - they're already shown as events
        if (kill.battle_id) continue;

        // In entity_activity mode, show kills involving the entity OR in entity's active systems
        if (colorMode === 'entity_activity' && entityActivityData && entityType) {
          const inActiveSystem = !!entityActivityData.systems[kill.solar_system_id];
          const isCorpVictim = entityType === 'corporation' && kill.victim_corporation_id === Number(entityId);
          if (!inActiveSystem && !isCorpVictim) continue;
        }

        const system = systemMap.get(kill.solar_system_id);
        if (!system) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        // Size based on ISK value
        let iconSize = 10 / camera.zoom; // base size for < 100M
        if (kill.ship_value >= 1_000_000_000) {
          iconSize = 18 / camera.zoom; // large for > 1B
        } else if (kill.ship_value >= 100_000_000) {
          iconSize = 14 / camera.zoom; // medium for 100M-1B
        }

        // Flash effect for new kills
        const flashTime = flashingKills.get(kill.killmail_id);
        let flashMultiplier = 1;
        if (flashTime) {
          const elapsed = now - flashTime;
          const flashDuration = 2000;
          const progress = Math.min(elapsed / flashDuration, 1);
          flashMultiplier = 1 + (1 - progress) * (1 + Math.sin(elapsed / 100) * 0.5);
        }

        // Draw flash ring for new kills
        if (flashTime) {
          const elapsed = now - flashTime;
          const flashDuration = 2000;
          const progress = Math.min(elapsed / flashDuration, 1);
          const ringSize = iconSize * (1 + progress * 2);
          const ringAlpha = (1 - progress) * 0.8;

          ctx.strokeStyle = `rgba(0, 255, 255, ${ringAlpha})`; // cyan glow
          ctx.lineWidth = 2 / camera.zoom;
          ctx.beginPath();
          ctx.arc(x, y, ringSize, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Draw glow for valuable kills or flashing kills
        if (kill.ship_value >= 100_000_000 || flashTime) {
          let glowColor = 'rgba(107, 114, 128, 0.6)'; // gray
          if (kill.ship_value >= 1_000_000_000) {
            glowColor = 'rgba(239, 68, 68, 0.6)'; // red
          } else if (kill.ship_value >= 100_000_000) {
            glowColor = 'rgba(234, 179, 8, 0.6)'; // yellow
          }
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, iconSize * 1.5 * flashMultiplier);
          gradient.addColorStop(0, glowColor);
          gradient.addColorStop(1, 'rgba(0,0,0,0)');
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(x, y, iconSize * 1.5 * flashMultiplier, 0, Math.PI * 2);
          ctx.fill();
        }

        // Draw skull icon
        const drawSize = iconSize * flashMultiplier;
        ctx.drawImage(skullImg, x - drawSize / 2, y - drawSize / 2, drawSize, drawSize);
      }
    }

    // Draw sov campaign overlay (small markers)
    if (showCampaigns && campaigns.length > 0) {
      for (const campaign of campaigns) {
        const system = systemMap.get(campaign.solar_system_id);
        if (!system) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        const size = 8 / camera.zoom;

        // Color: magenta/pink for visibility (distinct from battles)
        const markerColor = '#ff00ff';

        // Small pulsing ring
        ctx.strokeStyle = markerColor;
        ctx.lineWidth = 1.5 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.stroke();

        // Inner filled circle
        ctx.fillStyle = markerColor + '60';
        ctx.beginPath();
        ctx.arc(x, y, size * 0.6, 0, Math.PI * 2);
        ctx.fill();

        // Structure type letter (I=IHUB, T=TCU, S=Station)
        const letter = campaign.structure_type?.toUpperCase().startsWith('IHUB') ? 'I'
          : campaign.structure_type?.toUpperCase().startsWith('TCU') ? 'T' : 'S';
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${Math.max(3, 4 / camera.zoom)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(letter, x, y);
      }
    }

    // Draw capital activity overlay (pulsing orange/red circles)
    if (showCapitalActivity && capitalActivityData) {
      for (const [sysIdStr, capData] of Object.entries(capitalActivityData.systems)) {
        const sysId = Number(sysIdStr);
        const system = systemMap.get(sysId);
        if (!system) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        const norm = capitalActivityData.max_sightings > 0
          ? capData.sightings / capitalActivityData.max_sightings : 0;
        const size = (6 + norm * 10) / camera.zoom;

        // Orange-to-red based on intensity
        const hue = 30 - norm * 30; // 30 (orange) -> 0 (red)
        const color = `hsla(${hue}, 100%, 50%, ${0.3 + norm * 0.4})`;

        // Outer ring
        ctx.strokeStyle = `hsl(${hue}, 100%, 50%)`;
        ctx.lineWidth = 1.5 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.stroke();

        // Inner glow
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Draw logi presence overlay (cyan shield circles)
    if (showLogiPresence && logiPresenceData) {
      for (const [sysIdStr, logiData] of Object.entries(logiPresenceData.systems)) {
        const sysId = Number(sysIdStr);
        const system = systemMap.get(sysId);
        if (!system) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        const norm = logiPresenceData.max_ratio > 0
          ? logiData.logi_ratio / logiPresenceData.max_ratio : 0;
        const size = (5 + norm * 8) / camera.zoom;
        const opacity = 0.2 + norm * 0.5;

        // Cyan ring
        ctx.strokeStyle = `rgba(0, 212, 255, ${opacity})`;
        ctx.lineWidth = 1.5 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.stroke();

        // Inner glow
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, size * 0.8);
        gradient.addColorStop(0, `rgba(0, 212, 255, ${opacity * 0.5})`);
        gradient.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, size * 0.8, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Draw Thera/Turnur wormhole exit markers (purple portal rings)
    if (showWormholes && theraConnections.length > 0) {
      const whSizeColors: Record<string, string> = {
        small: '#00ccff',
        medium: '#00ccff',
        large: '#ffcc00',
        xlarge: '#ff8800',
        capital: '#ff4444',
      };

      for (const conn of theraConnections) {
        const system = systemMap.get(conn.in_system_id);
        if (!system) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);
        const size = 8 / camera.zoom;
        const color = whSizeColors[conn.max_ship_size] || '#9333ea';

        // Outer purple portal ring
        ctx.strokeStyle = '#9333ea';
        ctx.lineWidth = 2 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.stroke();

        // Inner colored ring (ship size indicator)
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5 / camera.zoom;
        ctx.beginPath();
        ctx.arc(x, y, size * 0.65, 0, Math.PI * 2);
        ctx.stroke();

        // Portal glow
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
        gradient.addColorStop(0, 'rgba(147, 51, 234, 0.35)');
        gradient.addColorStop(1, 'rgba(147, 51, 234, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();

        // Hub label at higher zoom (T = Thera, TR = Turnur)
        if (camera.zoom > 3) {
          const label = conn.out_system_name === 'Thera' ? 'T' : 'TR';
          ctx.fillStyle = '#9333ea';
          ctx.font = `bold ${Math.max(6, 8 / camera.zoom)}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(label, x, y + size + 5 / camera.zoom);
        }
      }
    }

    const centerMap = new Map<
      number,
      { x: number; y: number; count: number; name: string; allianceId?: number }
    >();

    if (colorMode === 'faction' && sovereigntyData) {
      for (const system of mapData.systems) {
        const factionId = sovereigntyData[system._key];
        if (!factionId) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        if (!centerMap.has(factionId)) {
          centerMap.set(factionId, {
            x,
            y,
            count: 1,
            name: FACTION_NAMES[factionId] || `Faction ${factionId}`,
          });
        } else {
          const center = centerMap.get(factionId)!;
          center.x += x;
          center.y += y;
          center.count += 1;
        }
      }
    } else if (colorMode === 'alliance' && allianceData) {
      const allianceSystems = new Map<number, Array<{ x: number; y: number; name: string }>>();

      for (const system of mapData.systems) {
        const allianceInfo = allianceData[system._key];
        if (!allianceInfo) continue;

        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        if (!allianceSystems.has(allianceInfo.alliance_id)) {
          allianceSystems.set(allianceInfo.alliance_id, []);
        }
        allianceSystems.get(allianceInfo.alliance_id)!.push({
          x,
          y,
          name: allianceInfo.alliance_name,
        });
      }

      let clusterIndex = 0;
      const proximityThreshold = 150;

      for (const [allianceId, systems] of allianceSystems) {
        const clusters: Array<Array<{ x: number; y: number }>> = [];
        const visited = new Set<number>();

        for (let i = 0; i < systems.length; i++) {
          if (visited.has(i)) continue;

          const cluster: Array<{ x: number; y: number }> = [systems[i]];
          visited.add(i);

          for (let j = i + 1; j < systems.length; j++) {
            if (visited.has(j)) continue;

            const isNearby = cluster.some((clusterSystem) => {
              const dx = clusterSystem.x - systems[j].x;
              const dy = clusterSystem.y - systems[j].y;
              const distance = Math.sqrt(dx * dx + dy * dy);
              return distance < proximityThreshold;
            });

            if (isNearby) {
              cluster.push(systems[j]);
              visited.add(j);
              j = i;
            }
          }

          clusters.push(cluster);
        }

        for (const cluster of clusters) {
          const centerX = cluster.reduce((sum, s) => sum + s.x, 0) / cluster.length;
          const centerY = cluster.reduce((sum, s) => sum + s.y, 0) / cluster.length;

          centerMap.set(clusterIndex++, {
            x: centerX * cluster.length,
            y: centerY * cluster.length,
            count: cluster.length,
            name: systems[0].name,
            allianceId: allianceId,
          });
        }
      }
    } else {
      for (const system of mapData.systems) {
        const x = toCanvasX(system.position2D?.x || system.position.x);
        const y = toCanvasY(system.position2D?.y || system.position.y);

        if (!centerMap.has(system.regionID)) {
          const region = mapData.regions.find((r) => r._key === system.regionID);
          centerMap.set(system.regionID, {
            x,
            y,
            count: 1,
            name: region?.name.en || 'Unknown',
          });
        } else {
          const center = centerMap.get(system.regionID)!;
          center.x += x;
          center.y += y;
          center.count += 1;
        }
      }
    }

    const maxScreenSize = 16;
    const minScreenSize = 8;
    const screenSize = Math.max(minScreenSize, maxScreenSize - Math.log(camera.zoom) * 8);

    const fontSize = screenSize / camera.zoom;

    ctx.font = `bold ${fontSize}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const opacity = camera.zoom < 5 ? 1 : Math.max(0.2, 1 - (camera.zoom - 5) / 10);

    for (const [id, data] of centerMap) {
      const centerX = data.x / data.count;
      const centerY = data.y / data.count;

      const text = data.name;
      const metrics = ctx.measureText(text);
      const padding = Math.max(1.5, 4 / camera.zoom);

      ctx.fillStyle = `rgba(0, 0, 0, ${0.7 * opacity})`;
      ctx.fillRect(
        centerX - metrics.width / 2 - padding,
        centerY - fontSize / 2 - padding,
        metrics.width + padding * 2,
        fontSize + padding * 2
      );

      let color: string;
      if (colorMode === 'faction') {
        color = getFactionColor(id);
      } else if (colorMode === 'alliance') {
        color = getAllianceColor(data.allianceId);
      } else {
        color = getRegionColor(id);
      }

      const hslMatch = color.match(/hsl\(([\d.]+),\s*(\d+)%,\s*(\d+)%\)/);
      const hexMatch = color.match(/^#([A-Fa-f0-9]{6})$/);
      if (hslMatch) {
        ctx.fillStyle = `hsla(${hslMatch[1]}, ${hslMatch[2]}%, ${hslMatch[3]}%, ${opacity})`;
      } else if (hexMatch) {
        // Convert hex to rgba with opacity
        const hex = hexMatch[1];
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
      } else {
        ctx.fillStyle = color;
      }
      ctx.fillText(text, centerX, centerY);
    }

    ctx.restore();
  }, [
    mapData,
    camera,
    dimensions,
    systemMap,
    toCanvasX,
    toCanvasY,
    getActivityColorLocal,
    getAdmColorLocal,
    colorMode,
    cameraInitialized,
    sovereigntyData,
    allianceData,
    filteredBattles,
    showBattles,
    liveKills,
    flashingBattles,
    flashingKills,
    activityData,
    admData,
    campaigns,
    showCampaigns,
  ]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - cameraRef.current.x, y: e.clientY - cameraRef.current.y });
    setMouseDownPos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      cameraRef.current.x = e.clientX - dragStart.x;
      cameraRef.current.y = e.clientY - dragStart.y;

      if (!renderRequested.current) {
        renderRequested.current = true;
        rafId.current = requestAnimationFrame(() => {
          renderRequested.current = false;
          setCamera({ ...cameraRef.current });
        });
      }
      return;
    }

    if (!mapData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const cam = cameraRef.current;
    const worldX = (mouseX - dimensions.width / 2 - cam.x) / cam.zoom + dimensions.width / 2;
    const worldY = (mouseY - dimensions.height / 2 - cam.y) / cam.zoom + dimensions.height / 2;

    // Check for campaign hover
    let nearestCampaignHover: { campaign: SovCampaign; x: number; y: number } | null = null;
    if (showCampaigns && campaigns.length > 0) {
      let nearestCampaignDistance = Infinity;
      for (const campaign of campaigns) {
        const system = systemMap.get(campaign.solar_system_id);
        if (!system) continue;
        const cx = toCanvasX(system.position2D?.x || system.position.x);
        const cy = toCanvasY(system.position2D?.y || system.position.y);
        const dx = worldX - cx;
        const dy = worldY - cy;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const hoverRadius = 14 / cam.zoom * 1.5;
        if (distance < hoverRadius && distance < nearestCampaignDistance) {
          nearestCampaignDistance = distance;
          nearestCampaignHover = { campaign, x: mouseX, y: mouseY };
        }
      }
    }
    if (nearestCampaignHover) {
      setHoveredCampaign(nearestCampaignHover);
    } else if (hoveredCampaign) {
      setHoveredCampaign(null);
    }

    // Check for battle hover first (higher priority)
    let nearestBattle: { battle: Battle; x: number; y: number } | null = null;
    if (showBattles && filteredBattles.length > 0) {
      let nearestBattleDistance = Infinity;
      for (const battle of filteredBattles) {
        const system = systemMap.get(battle.system_id);
        if (!system) continue;

        const battleX = toCanvasX(system.position2D?.x || system.position.x);
        const battleY = toCanvasY(system.position2D?.y || system.position.y);

        const dx = worldX - battleX;
        const dy = worldY - battleY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Size based on status_level (must match render code!)
        const statusLevel = battle.status_level || 'gank';
        let iconSize = 12 / cam.zoom;
        if (statusLevel === 'hellcamp') iconSize = 28 / cam.zoom;
        else if (statusLevel === 'battle') iconSize = 22 / cam.zoom;
        else if (statusLevel === 'brawl') iconSize = 16 / cam.zoom;
        // gank stays at 12

        const hoverRadius = iconSize * 1.5;

        if (distance < hoverRadius && distance < nearestBattleDistance) {
          nearestBattleDistance = distance;
          nearestBattle = {
            battle,
            x: mouseX,
            y: mouseY,
          };
        }
      }
    }

    if (nearestBattle) {
      if (hoveredBattle?.battle.battle_id !== nearestBattle.battle.battle_id) {
        setHoveredBattle(nearestBattle);
      }
      setHoveredSystem(null);
      setHoveredKill(null);
      return;
    } else if (hoveredBattle) {
      setHoveredBattle(null);
    }

    // Check for kill hover (second priority after battles)
    // NOTE: Only check kills WITHOUT battle_id - kills WITH battle_id are hovered as events
    let nearestKill: { kill: LiveKill; systemName: string; regionName: string; x: number; y: number } | null = null;
    if (liveKills.length > 0) {
      let nearestKillDistance = Infinity;
      for (const kill of liveKills) {
        // Skip kills that have a battle_id - they're hovered as events
        if (kill.battle_id) continue;

        const system = systemMap.get(kill.solar_system_id);
        if (!system) continue;

        const killX = toCanvasX(system.position2D?.x || system.position.x);
        const killY = toCanvasY(system.position2D?.y || system.position.y);

        const dx = worldX - killX;
        const dy = worldY - killY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        const killSize = 3 / cam.zoom;
        const hoverRadius = killSize * 3; // Slightly larger hover area for kills

        if (distance < hoverRadius && distance < nearestKillDistance) {
          nearestKillDistance = distance;
          const region = regionMap.get(system.regionID);
          nearestKill = {
            kill,
            systemName: system.name.en,
            regionName: region?.name.en || 'Unknown',
            x: mouseX,
            y: mouseY,
          };
        }
      }
    }

    if (nearestKill) {
      if (hoveredKill?.kill.killmail_id !== nearestKill.kill.killmail_id) {
        setHoveredKill(nearestKill);
      }
      setHoveredSystem(null);
      setHoveredTheraConnection(null);
      return;
    } else if (hoveredKill) {
      setHoveredKill(null);
    }

    // Check for Thera/WH connection hover (third priority)
    let nearestWh: HoveredTheraConnection | null = null;
    if (showWormholes && theraConnections.length > 0) {
      let nearestWhDistance = Infinity;
      for (const conn of theraConnections) {
        const system = systemMap.get(conn.in_system_id);
        if (!system) continue;
        const cx = toCanvasX(system.position2D?.x || system.position.x);
        const cy = toCanvasY(system.position2D?.y || system.position.y);
        const dx = worldX - cx;
        const dy = worldY - cy;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const whHoverRadius = 12 / cam.zoom;
        if (distance < whHoverRadius && distance < nearestWhDistance) {
          nearestWhDistance = distance;
          nearestWh = { connection: conn, x: mouseX, y: mouseY };
        }
      }
    }
    if (nearestWh) {
      setHoveredTheraConnection(nearestWh);
      setHoveredSystem(null);
      return;
    } else if (hoveredTheraConnection) {
      setHoveredTheraConnection(null);
    }

    const hoverRadius = 10 / cam.zoom;
    let nearestSystem: HoveredSystem | null = null;
    let nearestDistance = hoverRadius;
    let nearestSystemData: (typeof mapData.systems)[0] | null = null;

    for (const system of mapData.systems) {
      const systemX = toCanvasX(system.position2D?.x || system.position.x);
      const systemY = toCanvasY(system.position2D?.y || system.position.y);

      const dx = worldX - systemX;
      const dy = worldY - systemY;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestSystemData = system;
      }
    }

    if (nearestSystemData) {
      const region = regionMap.get(nearestSystemData.regionID);
      const regionName = region?.name.en;

      let factionName: string | undefined;
      if (sovereigntyData) {
        const factionId = sovereigntyData[nearestSystemData._key];
        if (factionId) {
          factionName = FACTION_NAMES[factionId] || `Faction ${factionId}`;
        }
      }

      let allianceName: string | undefined;
      if (allianceData) {
        const allianceInfo = allianceData[nearestSystemData._key];
        if (allianceInfo) {
          allianceName = allianceInfo.alliance_name;
        }
      }

      // Activity/ADM data for tooltip
      let activityValue: number | undefined;
      let activityMetric: string | undefined;
      let admLevel: number | undefined;
      if (['npc_kills', 'ship_kills', 'jumps'].includes(colorMode) && activityData) {
        const entry = activityData[nearestSystemData._key];
        if (entry) { activityValue = entry.value; activityMetric = colorMode; }
      }
      if (admData) {
        admLevel = admData[nearestSystemData._key];
      }

      // Hunting data for tooltip
      let huntingScore: number | undefined;
      let huntingDeaths: number | undefined;
      let huntingAvgIsk: number | undefined;
      let huntingCapitals: boolean | undefined;
      if (colorMode === 'hunting' && huntingData) {
        const hEntry = huntingData.systems[nearestSystemData._key];
        if (hEntry) {
          huntingScore = hEntry.score;
          huntingDeaths = hEntry.deaths;
          huntingAvgIsk = hEntry.avg_isk;
          huntingCapitals = hEntry.has_capitals;
        }
      }

      nearestSystem = {
        systemId: nearestSystemData._key,
        name: nearestSystemData.name.en,
        security: nearestSystemData.securityStatus,
        x: mouseX,
        y: mouseY,
        regionName,
        factionName,
        allianceName,
        activityValue,
        activityMetric,
        admLevel,
        huntingScore,
        huntingDeaths,
        huntingAvgIsk,
        huntingCapitals,
      };
    }

    if (nearestSystem?.systemId !== hoveredSystem?.systemId) {
      setHoveredSystem(nearestSystem);
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setCamera({ ...cameraRef.current });
    }
    setIsDragging(false);

    const dx = e.clientX - mouseDownPos.x;
    const dy = e.clientY - mouseDownPos.y;
    const dragDistance = Math.sqrt(dx * dx + dy * dy);

    // Only process clicks, not drags
    if (dragDistance < 5) {
      // Helper to navigate to public-frontend routes (battle pages)
      const navigateToPublicFrontend = (path: string) => {
        // Determine target URL based on environment
        const hostname = window.location.hostname;
        const currentPort = window.location.port;
        const protocol = window.location.protocol;

        // Ectmap runs on port 3001, public-frontend on 5173 (dev) or same domain (prod)
        let targetUrl: string;
        if (currentPort === '3001') {
          // Dev: redirect to public-frontend on port 5173
          targetUrl = `${protocol}//${hostname}:5173${path}`;
        } else if (currentPort === '5173' || currentPort === '') {
          // Already on public-frontend or prod (no port), use relative path
          targetUrl = path;
        } else {
          // Unknown port, assume dev and try 5173
          targetUrl = `${protocol}//${hostname}:5173${path}`;
        }

        console.log('[ectmap] Navigating to:', targetUrl, 'from port:', currentPort);

        if (window.parent !== window) {
          // In iframe: use postMessage to navigate parent (cross-origin safe)
          window.parent.postMessage({ type: 'ectmap-navigate', url: targetUrl }, '*');
        } else {
          // Standalone: direct navigation - try multiple methods for reliability
          try {
            window.location.assign(targetUrl);
          } catch (e) {
            console.error('[ectmap] location.assign failed, trying href:', e);
            window.location.href = targetUrl;
          }
        }
      };

      // Use hover state for click detection - much more reliable
      // Battle click (highest priority)
      if (hoveredBattle) {
        navigateToPublicFrontend(`/battle/${hoveredBattle.battle.battle_id}`);
        return;
      }

      // Kill click - navigate to battle
      if (hoveredKill && hoveredKill.kill.battle_id) {
        navigateToPublicFrontend(`/battle/${hoveredKill.kill.battle_id}`);
        return;
      }

      // System click - navigate to public-frontend system detail
      if (hoveredSystem) {
        navigateToPublicFrontend(`/system/${hoveredSystem.systemId}`);
        return;
      }
    }
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setHoveredSystem(null);
    setHoveredBattle(null);
    setHoveredKill(null);
    setHoveredCampaign(null);
    setHoveredTheraConnection(null);
  };

  if (loading || !cameraInitialized) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center">
        <p className="text-white">Loading map data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center">
        <p className="text-red-500">Error: {error}</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full" data-map-ready={cameraInitialized ? 'true' : 'false'}>
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        className="cursor-move block"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />

      {!snapshotMode && hoveredBattle && <BattleTooltip hovered={hoveredBattle} />}
      {!snapshotMode && hoveredKill && <KillTooltip hovered={hoveredKill} />}
      {!snapshotMode && hoveredTheraConnection && <TheraTooltip hovered={hoveredTheraConnection} />}
      {!snapshotMode && hoveredSystem && !hoveredBattle && !hoveredKill && !hoveredTheraConnection && <SystemTooltip hovered={hoveredSystem} />}
      {!snapshotMode && hoveredCampaign && <CampaignTooltip hovered={hoveredCampaign} />}

      {!snapshotMode && !externalFilters && (
        <ColorModeButtons
          colorMode={colorMode} setColorMode={setColorMode}
          showCampaigns={showCampaigns} setShowCampaigns={setShowCampaigns} campaignCount={campaigns.length}
          showCapitalActivity={showCapitalActivity} setShowCapitalActivity={setShowCapitalActivity}
          capitalCount={capitalActivityData ? Object.keys(capitalActivityData.systems).length : 0}
          showLogiPresence={showLogiPresence} setShowLogiPresence={setShowLogiPresence}
          logiCount={logiPresenceData ? Object.keys(logiPresenceData.systems).length : 0}
          intelDays={intelDays} setIntelDays={setIntelDays}
          showWormholes={showWormholes} setShowWormholes={setShowWormholes}
          wormholeCount={theraConnections.length}
        />
      )}
      {!snapshotMode && <HeatmapLegend colorMode={colorMode} />}
      {!snapshotMode && !externalFilters && (
        <OverlayControls
          statusFilters={statusFilters} setStatusFilters={setStatusFilters} statusCounts={statusCounts}
          activityMinutes={activityMinutes} setActivityMinutes={setActivityMinutes}
        />
      )}
    </div>
  );
}
