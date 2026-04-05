'use client';

import type { HoveredObject } from './types';

interface HoverTooltipProps {
  hoveredObject: HoveredObject | null;
}

export default function HoverTooltip({ hoveredObject }: HoverTooltipProps) {
  if (!hoveredObject) return null;

  return (
    <div
      className="absolute pointer-events-none bg-gray-900 border border-gray-700 rounded px-3 py-2 shadow-lg z-20"
      style={{
        left: `${hoveredObject.x + 15}px`,
        top: `${hoveredObject.y + 15}px`,
      }}
    >
      <div className="text-white font-semibold text-sm">{hoveredObject.type}</div>
      <div className="text-gray-400 text-xs">{hoveredObject.label}</div>
    </div>
  );
}
