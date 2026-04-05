'use client';

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import type { SystemDetailResponse } from '@/lib/sde-types';
import {
  getTypeImageUrl,
  getStarRenderColor,
  metersToSolarRadii,
  getPlanetTypeColor,
} from '@/lib/eve-images';
import { apiFetch } from '@/lib/api';
import type {
  SelectedObject,
  HoveredObject,
  CameraState,
  CoordinateData,
  CelestialObject,
  AdjustedPosition,
  FoundObject,
  PlanetWithNames,
  StargateWithNames,
  StationWithNames,
} from './types';
import type { Star, Planet, Moon, AsteroidBelt, Stargate, Station } from '@/lib/sde-types';

// Sub-components
import SystemHeader from './SystemHeader';
import ObjectCounts from './ObjectCounts';
import HoverTooltip from './HoverTooltip';
import ListPanel from './ListPanel';
import {
  StarDetail,
  PlanetDetail,
  MoonDetail,
  AsteroidBeltDetail,
  StargateDetail,
  StationDetail,
} from './details';

interface SystemDetailProps {
  systemId: number;
  onClose: () => void;
}

export default function SystemDetail({ systemId, onClose }: SystemDetailProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [systemData, setSystemData] = useState<SystemDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });

  // Camera state
  const cameraRef = useRef<CameraState>({ x: 0, y: 0, zoom: 1 });
  const [camera, setCamera] = useState<CameraState>({ x: 0, y: 0, zoom: 1 });
  const [cameraInitialized, setCameraInitialized] = useState(false);

  // Interaction state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [mouseDownPos, setMouseDownPos] = useState({ x: 0, y: 0 });
  const [hoveredObject, setHoveredObject] = useState<HoveredObject | null>(null);
  const [selectedObject, setSelectedObject] = useState<SelectedObject | null>(null);
  const [openListPanel, setOpenListPanel] = useState<'planets' | 'stargates' | 'stations' | null>(null);
  const [openedFromList, setOpenedFromList] = useState<'planets' | 'stargates' | 'stations' | null>(null);

  // Animation and image refs
  const rafId = useRef<number>();
  const renderRequested = useRef(false);
  const imageCache = useRef<Map<number, HTMLImageElement>>(new Map());
  const [imageLoadTrigger, setImageLoadTrigger] = useState(0);
  const imageLoadRafId = useRef<number | null>(null);
  const pendingImageUpdates = useRef(0);
  const adjustedPositions = useRef<Map<CelestialObject, AdjustedPosition>>(new Map());

  // Load image helper
  const loadImage = useCallback((typeID: number): HTMLImageElement | null => {
    if (imageCache.current.has(typeID)) {
      return imageCache.current.get(typeID)!;
    }

    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.src = getTypeImageUrl(typeID, { size: 64, type: 'icon' });

    img.onload = () => {
      imageCache.current.set(typeID, img);
      pendingImageUpdates.current += 1;

      if (imageLoadRafId.current === null) {
        imageLoadRafId.current = requestAnimationFrame(() => {
          setImageLoadTrigger((prev) => prev + pendingImageUpdates.current);
          pendingImageUpdates.current = 0;
          imageLoadRafId.current = null;
        });
      }
    };

    imageCache.current.set(typeID, img);
    return img;
  }, []);

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (imageLoadRafId.current !== null) {
        cancelAnimationFrame(imageLoadRafId.current);
      }
      if (rafId.current) {
        cancelAnimationFrame(rafId.current);
      }
    };
  }, []);

  // Dimension tracking
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

  // Load system data
  useEffect(() => {
    async function loadSystemData() {
      try {
        setLoading(true);
        const response = await apiFetch(`/api/map/system/${systemId}`);
        if (!response.ok) throw new Error('Failed to load system data');
        const data = await response.json();
        setSystemData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    loadSystemData();
  }, [systemId]);

  // Calculate object bounds
  const objectBounds = useMemo(() => {
    if (!systemData) return { minA: 0, minB: 0, maxA: 0, maxB: 0 };

    const { star, planets, moons, stargates, stations } = systemData;

    let minA = Infinity, maxA = -Infinity;
    let minB = Infinity, maxB = -Infinity;

    const processPosition = (pos: { x: number; z: number } | undefined) => {
      if (!pos) return;
      minA = Math.min(minA, pos.x);
      maxA = Math.max(maxA, pos.x);
      minB = Math.min(minB, pos.z);
      maxB = Math.max(maxB, pos.z);
    };

    if (star) processPosition(star.position || { x: 0, z: 0 });
    planets.forEach((p) => processPosition(p.position));
    moons.forEach((m) => processPosition(m.position));
    stargates.forEach((g) => processPosition(g.position));
    stations.forEach((s) => processPosition(s.position));

    if (minA === Infinity) return { minA: 0, minB: 0, maxA: 0, maxB: 0 };
    return { minA, minB, maxA, maxB };
  }, [systemData]);

  // Calculate coordinate data
  const coordinateData = useMemo<CoordinateData>(() => {
    const padding = 100;
    const scaleA = (dimensions.width - padding * 2) / (objectBounds.maxA - objectBounds.minA || 1);
    const scaleB = (dimensions.height - padding * 2) / (objectBounds.maxB - objectBounds.minB || 1);
    const scale = Math.min(scaleA, scaleB);

    return { ...objectBounds, scale, padding };
  }, [objectBounds, dimensions]);

  // Initialize camera
  useEffect(() => {
    if (!systemData) return;

    const { minA, minB, scale, padding } = coordinateData;

    const starCanvasX = (0 - minA) * scale + padding;
    const starCanvasY = dimensions.height - ((0 - minB) * scale + padding);

    const zoom = 1;
    const screenCenterX = dimensions.width / 2;
    const screenCenterY = dimensions.height / 2;

    const initialCamera = {
      x: -(starCanvasX - screenCenterX) * zoom,
      y: -(starCanvasY - screenCenterY) * zoom,
      zoom: zoom,
    };
    setCamera(initialCamera);
    cameraRef.current = { ...initialCamera };
    setCameraInitialized(true);
  }, [systemData, dimensions, coordinateData]);

  // Wheel zoom handling
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cameraInitialized) return;

    let wheelRafId: number | null = null;
    let pendingZoomDelta = 0;
    let lastWheelMouse = { x: 0, y: 0 };

    const handleWheelEvent = (e: WheelEvent) => {
      e.preventDefault();

      pendingZoomDelta += e.deltaY > 0 ? -0.1 : 0.1;
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

        cameraRef.current = { x: newX, y: newY, zoom: newZoom };
        setCamera({ ...cameraRef.current });

        wheelRafId = null;
        pendingZoomDelta = 0;
      });
    };

    canvas.addEventListener('wheel', handleWheelEvent, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheelEvent);
  }, [dimensions, cameraInitialized]);

  // Canvas rendering
  useEffect(() => {
    if (!systemData || !canvasRef.current || !cameraInitialized) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { star, planets, stargates, stations } = systemData;
    const { minA, minB, scale, padding } = coordinateData;

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(dimensions.width / 2 + camera.x, dimensions.height / 2 + camera.y);
    ctx.scale(camera.zoom, camera.zoom);
    ctx.translate(-dimensions.width / 2, -dimensions.height / 2);

    const toCanvasCoords = (pos: { x: number; y: number; z: number }) => ({
      x: (pos.x - minA) * scale + padding,
      y: canvas.height - ((pos.z - minB) * scale + padding),
    });

    // Calculate max distance for AU rings
    let maxDistance = 0;
    const starPos = { x: 0, y: 0, z: 0 };

    [...planets, ...stargates, ...stations].forEach((obj) => {
      if (obj.position) {
        const dx = obj.position.x - starPos.x;
        const dz = obj.position.z - starPos.z;
        const distance = Math.sqrt(dx * dx + dz * dz);
        maxDistance = Math.max(maxDistance, distance);
      }
    });

    // Draw AU rings
    const starCoords = toCanvasCoords(starPos);
    const AU_METERS = 149597870700;
    const maxAU = Math.ceil(maxDistance / AU_METERS);

    ctx.strokeStyle = 'rgba(100, 100, 100, 0.2)';
    ctx.lineWidth = 1 / camera.zoom;

    for (let i = 1; i <= maxAU; i++) {
      const auDistance = i * AU_METERS;
      const radiusInPixels = auDistance * scale;

      ctx.beginPath();
      ctx.arc(starCoords.x, starCoords.y, radiusInPixels, 0, Math.PI * 2);
      ctx.stroke();

      const fontSize = Math.max(8, 10 / camera.zoom);
      ctx.fillStyle = 'rgba(150, 150, 150, 0.5)';
      ctx.font = `${fontSize}px Arial`;
      ctx.textAlign = 'center';
      ctx.fillText(`${i} AU`, starCoords.x, starCoords.y - radiusInPixels - 5 / camera.zoom);
    }

    // Build objects to render
    adjustedPositions.current.clear();

    const objectsToRender: Array<{
      x: number;
      y: number;
      type: 'star' | 'planet' | 'stargate' | 'station';
      label: string;
      color: string;
      radius: number;
      typeID?: number;
      dataRef: CelestialObject;
    }> = [];

    if (star) {
      const coords = toCanvasCoords(star.position || { x: 0, y: 0, z: 0 });
      const starColor = star.statistics?.spectralClass
        ? getStarRenderColor(star.statistics.spectralClass)
        : '#FFD700';

      let starRadius = 12;
      if (star.radius) {
        const solarRadii = metersToSolarRadii(star.radius);
        starRadius = Math.max(8, Math.min(20, 8 + solarRadii * 4));
      }

      objectsToRender.push({
        x: coords.x,
        y: coords.y,
        type: 'star',
        label: star.statistics?.spectralClass ? `Star (${star.statistics.spectralClass})` : 'Star',
        color: starColor,
        radius: starRadius,
        typeID: star.typeID,
        dataRef: star,
      });
    }

    planets.forEach((planet) => {
      if (planet.position) {
        const coords = toCanvasCoords(planet.position);
        const planetColor = getPlanetTypeColor(planet.statistics?.temperature);
        const planetWithNames = planet as PlanetWithNames;

        objectsToRender.push({
          x: coords.x,
          y: coords.y,
          type: 'planet',
          label: planetWithNames.fullName || `Planet ${planet.celestialIndex || planet._key}`,
          color: planetColor,
          radius: 6,
          typeID: planet.typeID,
          dataRef: planet,
        });
      }
    });

    stargates.forEach((gate) => {
      if (gate.position) {
        const coords = toCanvasCoords(gate.position);
        const gateWithNames = gate as StargateWithNames;
        objectsToRender.push({
          x: coords.x,
          y: coords.y,
          type: 'stargate',
          label: gateWithNames.fullName || `Stargate ${gate._key}`,
          color: '#00FFFF',
          radius: 5,
          dataRef: gate,
        });
      }
    });

    stations.forEach((station) => {
      if (station.position) {
        const coords = toCanvasCoords(station.position);
        const stationWithNames = station as StationWithNames;
        objectsToRender.push({
          x: coords.x,
          y: coords.y,
          type: 'station',
          label: stationWithNames.fullName || `Station ${station._key}`,
          color: '#FF00FF',
          radius: 4,
          dataRef: station,
        });
      }
    });

    // Collision detection and separation
    const minSeparation = 15;
    const maxIterations = 5;
    const cellSize = minSeparation * 2;

    for (let iteration = 0; iteration < maxIterations; iteration++) {
      let hadCollision = false;

      type IndexedObject = { obj: (typeof objectsToRender)[number]; index: number };
      const grid = new Map<string, IndexedObject[]>();

      const getCellKey = (x: number, y: number): string => {
        const cellX = Math.floor(x / cellSize);
        const cellY = Math.floor(y / cellSize);
        return `${cellX},${cellY}`;
      };

      objectsToRender.forEach((obj, index) => {
        const key = getCellKey(obj.x, obj.y);
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key)!.push({ obj, index });
      });

      const checkedPairs = new Set<string>();

      objectsToRender.forEach((obj1, i) => {
        const cellX = Math.floor(obj1.x / cellSize);
        const cellY = Math.floor(obj1.y / cellSize);

        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            const neighborKey = `${cellX + dx},${cellY + dy}`;
            const neighbors = grid.get(neighborKey);
            if (!neighbors) continue;

            for (const { obj: obj2, index: j } of neighbors) {
              if (i === j) continue;

              const pairKey = i < j ? `${i},${j}` : `${j},${i}`;
              if (checkedPairs.has(pairKey)) continue;
              checkedPairs.add(pairKey);

              const dxPos = obj2.x - obj1.x;
              const dyPos = obj2.y - obj1.y;
              const distance = Math.sqrt(dxPos * dxPos + dyPos * dyPos);

              if (distance < minSeparation && distance > 0) {
                hadCollision = true;
                const pushStrength = (minSeparation - distance) / 2;
                const angle = Math.atan2(dyPos, dxPos);

                obj1.x -= Math.cos(angle) * pushStrength;
                obj1.y -= Math.sin(angle) * pushStrength;
                obj2.x += Math.cos(angle) * pushStrength;
                obj2.y += Math.sin(angle) * pushStrength;
              }
            }
          }
        }
      });

      if (!hadCollision) break;
    }

    // Store adjusted positions
    objectsToRender.forEach((obj) => {
      adjustedPositions.current.set(obj.dataRef, { x: obj.x, y: obj.y, radius: obj.radius });
    });

    // Render objects
    for (const obj of objectsToRender) {
      const size = obj.radius / camera.zoom;

      ctx.fillStyle = obj.color;
      ctx.strokeStyle = obj.color;
      ctx.lineWidth = 2 / camera.zoom;

      switch (obj.type) {
        case 'star':
          if (obj.typeID) {
            const img = loadImage(obj.typeID);
            if (img && img.complete) {
              ctx.globalAlpha = 0.3;
              ctx.fillStyle = obj.color;
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size * 1.5, 0, Math.PI * 2);
              ctx.fill();
              ctx.globalAlpha = 1.0;

              ctx.save();
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size, 0, Math.PI * 2);
              ctx.closePath();
              ctx.clip();
              ctx.drawImage(img, obj.x - size, obj.y - size, size * 2, size * 2);
              ctx.restore();

              ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
              ctx.lineWidth = 1 / camera.zoom;
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size, 0, Math.PI * 2);
              ctx.stroke();
            } else {
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size, 0, Math.PI * 2);
              ctx.fill();
            }
          }
          break;

        case 'planet':
          if (obj.typeID) {
            const img = loadImage(obj.typeID);
            if (img && img.complete) {
              ctx.save();
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size, 0, Math.PI * 2);
              ctx.closePath();
              ctx.clip();
              ctx.drawImage(img, obj.x - size, obj.y - size, size * 2, size * 2);
              ctx.restore();

              ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
              ctx.lineWidth = 1 / camera.zoom;
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size, 0, Math.PI * 2);
              ctx.stroke();
            } else {
              ctx.beginPath();
              ctx.arc(obj.x, obj.y, size, 0, Math.PI * 2);
              ctx.fill();
              ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
              ctx.stroke();
            }
          }
          break;

        case 'stargate':
          ctx.beginPath();
          ctx.moveTo(obj.x, obj.y - size);
          ctx.lineTo(obj.x + size, obj.y);
          ctx.lineTo(obj.x, obj.y + size);
          ctx.lineTo(obj.x - size, obj.y);
          ctx.closePath();
          ctx.fill();
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
          ctx.stroke();
          break;

        case 'station':
          ctx.beginPath();
          ctx.moveTo(obj.x, obj.y - size);
          ctx.lineTo(obj.x + size * 0.866, obj.y + size * 0.5);
          ctx.lineTo(obj.x - size * 0.866, obj.y + size * 0.5);
          ctx.closePath();
          ctx.fill();
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
          ctx.stroke();
          break;
      }
    }

    ctx.restore();
  }, [systemData, camera, coordinateData, cameraInitialized, imageLoadTrigger, loadImage, dimensions]);

  // Find object at position
  const findObjectAtPosition = useCallback(
    (mouseX: number, mouseY: number, detectionBuffer: number): FoundObject | null => {
      if (!systemData || !canvasRef.current) return null;

      const cam = cameraRef.current;
      const worldX = (mouseX - dimensions.width / 2 - cam.x) / cam.zoom + dimensions.width / 2;
      const worldY = (mouseY - dimensions.height / 2 - cam.y) / cam.zoom + dimensions.height / 2;

      const { star, planets, stargates, stations } = systemData;

      let nearestObject: FoundObject | null = null;
      let nearestDistance = Infinity;

      const checkObject = <T extends CelestialObject>(
        obj: T,
        type: 'star' | 'planet' | 'stargate' | 'station'
      ) => {
        const adjusted = adjustedPositions.current.get(obj);
        if (adjusted) {
          const actualSize = adjusted.radius / cam.zoom;
          const detectionRadius = actualSize + detectionBuffer;

          const dx = worldX - adjusted.x;
          const dy = worldY - adjusted.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < detectionRadius && distance < nearestDistance) {
            nearestDistance = distance;
            nearestObject = { [type]: obj, distance } as FoundObject;
          }
        }
      };

      if (star) checkObject(star, 'star');
      planets.forEach((p) => checkObject(p, 'planet'));
      stargates.forEach((g) => checkObject(g, 'stargate'));
      stations.forEach((s) => checkObject(s, 'station'));

      return nearestObject;
    },
    [systemData, dimensions]
  );

  // Mouse handlers
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

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const found = findObjectAtPosition(mouseX, mouseY, 3);

    let newHoveredObject: HoveredObject | null = null;

    if (found && systemData) {
      if (found.star) {
        newHoveredObject = {
          type: 'Star',
          label: systemData.star?.statistics?.spectralClass
            ? `${systemData.star.statistics.spectralClass} Class`
            : 'Star',
          x: mouseX,
          y: mouseY,
        };
      } else if (found.planet) {
        const planetWithNames = found.planet as PlanetWithNames;
        newHoveredObject = {
          type: 'Planet',
          label: planetWithNames.fullName || `Planet ${found.planet.celestialIndex || found.planet._key}`,
          x: mouseX,
          y: mouseY,
        };
      } else if (found.stargate) {
        const gateWithNames = found.stargate as StargateWithNames;
        newHoveredObject = {
          type: 'Stargate',
          label: gateWithNames.fullName || `Stargate ${found.stargate._key}`,
          x: mouseX,
          y: mouseY,
        };
      } else if (found.station) {
        const stationWithNames = found.station as StationWithNames;
        newHoveredObject = {
          type: 'Station',
          label: stationWithNames.fullName || `Station ${found.station._key}`,
          x: mouseX,
          y: mouseY,
        };
      }
    }

    setHoveredObject(newHoveredObject);
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setCamera({ ...cameraRef.current });
    }
    setIsDragging(false);

    const dx = e.clientX - mouseDownPos.x;
    const dy = e.clientY - mouseDownPos.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < 5 && systemData && canvasRef.current) {
      const canvas = canvasRef.current;
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const found = findObjectAtPosition(mouseX, mouseY, 5);

      if (found) {
        if (found.star) {
          setSelectedObject({ type: 'star', data: found.star });
        } else if (found.planet) {
          setSelectedObject({ type: 'planet', data: found.planet });
        } else if (found.stargate) {
          setSelectedObject({ type: 'stargate', data: found.stargate });
        } else if (found.station) {
          setSelectedObject({ type: 'station', data: found.station });
        }
      }
    }
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setHoveredObject(null);
  };

  // Loading state
  if (loading || !cameraInitialized) {
    return (
      <div ref={containerRef} className="fixed inset-0 bg-black flex items-center justify-center z-50">
        <div className="text-white">Loading system data...</div>
      </div>
    );
  }

  // Error state
  if (error || !systemData) {
    return (
      <div ref={containerRef} className="fixed inset-0 bg-black flex items-center justify-center z-50">
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-white">Error</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
          </div>
          <div className="text-red-500">{error || 'Failed to load system data'}</div>
        </div>
      </div>
    );
  }

  const { system, region, star, planets, stargates, stations } = systemData;

  // Handler helpers
  const handleCloseSelectedObject = () => {
    setSelectedObject(null);
    setOpenedFromList(null);
  };

  const handleBackToList = (listType: 'planets' | 'stargates' | 'stations') => {
    setSelectedObject(null);
    setOpenListPanel(listType);
    setOpenedFromList(null);
  };

  return (
    <div ref={containerRef} className="fixed inset-0 bg-black z-50">
      {/* Canvas */}
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

      {/* Header */}
      <SystemHeader
        systemName={system.name.en}
        regionName={region.name.en}
        securityStatus={system.securityStatus}
        onClose={onClose}
      />

      {/* Object counts */}
      <ObjectCounts
        star={star}
        planets={planets}
        stargates={stargates}
        stations={stations}
        onSelectStar={() => {
          if (star) {
            setSelectedObject({ type: 'star', data: star });
            setOpenListPanel(null);
          }
        }}
        onSelectPlanets={() => {
          if (planets.length === 1) {
            setSelectedObject({ type: 'planet', data: planets[0] });
            setOpenListPanel(null);
          } else if (planets.length > 1) {
            setOpenListPanel('planets');
            setSelectedObject(null);
          }
        }}
        onSelectStargates={() => {
          if (stargates.length === 1) {
            setSelectedObject({ type: 'stargate', data: stargates[0] });
            setOpenListPanel(null);
          } else if (stargates.length > 1) {
            setOpenListPanel('stargates');
            setSelectedObject(null);
          }
        }}
        onSelectStations={() => {
          if (stations.length === 1) {
            setSelectedObject({ type: 'station', data: stations[0] });
            setOpenListPanel(null);
          } else if (stations.length > 1) {
            setOpenListPanel('stations');
            setSelectedObject(null);
          }
        }}
      />

      {/* Hover tooltip */}
      <HoverTooltip hoveredObject={hoveredObject} />

      {/* List panels */}
      {openListPanel === 'planets' && (
        <ListPanel<Planet>
          title="Planets"
          items={planets}
          onClose={() => { setOpenListPanel(null); setOpenedFromList(null); }}
          onSelectItem={(planet) => {
            setSelectedObject({ type: 'planet', data: planet });
            setOpenListPanel(null);
            setOpenedFromList('planets');
          }}
          getItemName={(p) => (p as PlanetWithNames).fullName || `Planet ${p.celestialIndex || p._key}`}
          getItemSubtitle={(p) => (p as PlanetWithNames).typeName || 'Planet'}
        />
      )}

      {openListPanel === 'stargates' && (
        <ListPanel<Stargate>
          title="Stargates"
          items={stargates}
          onClose={() => { setOpenListPanel(null); setOpenedFromList(null); }}
          onSelectItem={(stargate) => {
            setSelectedObject({ type: 'stargate', data: stargate });
            setOpenListPanel(null);
            setOpenedFromList('stargates');
          }}
          getItemName={(g) => (g as StargateWithNames).fullName || `Stargate ${g._key}`}
          getItemSubtitle={(g) => `Jump to: ${(g as StargateWithNames).destinationName || 'Unknown'}`}
        />
      )}

      {openListPanel === 'stations' && (
        <ListPanel<Station>
          title="Stations"
          items={stations}
          onClose={() => { setOpenListPanel(null); setOpenedFromList(null); }}
          onSelectItem={(station) => {
            setSelectedObject({ type: 'station', data: station });
            setOpenListPanel(null);
            setOpenedFromList('stations');
          }}
          getItemName={(s) => (s as StationWithNames).fullName || `Station ${s._key}`}
          getItemSubtitle={(s) => (s as StationWithNames).typeName || 'Station'}
        />
      )}

      {/* Detail panels */}
      {selectedObject?.type === 'star' && (
        <StarDetail data={selectedObject.data as Star} onClose={handleCloseSelectedObject} />
      )}

      {selectedObject?.type === 'planet' && (
        <PlanetDetail
          data={selectedObject.data as Planet}
          onClose={handleCloseSelectedObject}
          onBack={() => handleBackToList('planets')}
          showBackButton={openedFromList === 'planets'}
          systemData={systemData}
          setSelectedObject={setSelectedObject}
        />
      )}

      {selectedObject?.type === 'moon' && (
        <MoonDetail
          data={selectedObject.data as Moon}
          onClose={handleCloseSelectedObject}
          systemData={systemData}
          setSelectedObject={setSelectedObject}
        />
      )}

      {selectedObject?.type === 'asteroidBelt' && (
        <AsteroidBeltDetail
          data={selectedObject.data as AsteroidBelt}
          onClose={handleCloseSelectedObject}
          systemData={systemData}
          setSelectedObject={setSelectedObject}
        />
      )}

      {selectedObject?.type === 'stargate' && (
        <StargateDetail
          data={selectedObject.data as Stargate}
          onClose={handleCloseSelectedObject}
          onBack={() => handleBackToList('stargates')}
          showBackButton={openedFromList === 'stargates'}
          currentSystemName={system.name.en}
        />
      )}

      {selectedObject?.type === 'station' && (
        <StationDetail
          data={selectedObject.data as Station}
          onClose={handleCloseSelectedObject}
          onBack={() => handleBackToList('stations')}
          showBackButton={openedFromList === 'stations'}
        />
      )}
    </div>
  );
}
