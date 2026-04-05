import type { FittingItem } from '../types/fittings';
import { SLOT_RANGES } from '../types/fittings';

interface ParsedModule {
  name: string;
  quantity: number;
  ammo?: string;
}

export interface EftParseResult {
  shipName: string;
  fittingName: string;
  blocks: ParsedModule[][];
}

export function parseEft(text: string): EftParseResult | null {
  const lines = text.trim().split('\n').map(l => l.trim());
  if (lines.length < 2) return null;

  const headerMatch = lines[0].match(/^\[(.+?),\s*(.+?)\]$/);
  if (!headerMatch) return null;

  const shipName = headerMatch[1].trim();
  const fittingName = headerMatch[2].trim();

  const blocks: ParsedModule[][] = [];
  let currentBlock: ParsedModule[] = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];

    if (line === '' || line.startsWith('[Empty ')) {
      if (line === '' && currentBlock.length > 0) {
        blocks.push(currentBlock);
        currentBlock = [];
      }
      continue;
    }

    const quantityMatch = line.match(/^(.+?)\s+x(\d+)$/);
    if (quantityMatch) {
      currentBlock.push({ name: quantityMatch[1].trim(), quantity: parseInt(quantityMatch[2]) });
    } else {
      const parts = line.split(',').map(p => p.trim());
      currentBlock.push({
        name: parts[0],
        quantity: 1,
        ammo: parts[1] || undefined,
      });
    }
  }
  if (currentBlock.length > 0) blocks.push(currentBlock);

  return { shipName, fittingName, blocks };
}

export function blocksToFittingItems(
  blocks: ParsedModule[][],
  nameToTypeId: Map<string, number>,
): { items: FittingItem[]; charges: Record<number, number>; cargo: { name: string; typeId: number; quantity: number }[] } {
  const items: FittingItem[] = [];
  const charges: Record<number, number> = {};
  const cargo: { name: string; typeId: number; quantity: number }[] = [];
  const slotOrder: (keyof typeof SLOT_RANGES)[] = ['low', 'mid', 'high', 'rig'];

  for (let blockIdx = 0; blockIdx < blocks.length; blockIdx++) {
    const block = blocks[blockIdx];

    if (blockIdx < 4) {
      // Slot blocks: low, mid, high, rig
      const slotType = slotOrder[blockIdx];
      const range = SLOT_RANGES[slotType];
      let flagIdx = 0;

      for (const mod of block) {
        const typeId = nameToTypeId.get(mod.name) || nameToTypeId.get(mod.name.toLowerCase());
        if (!typeId) continue;

        for (let q = 0; q < mod.quantity; q++) {
          const flag = range.start + flagIdx;
          items.push({ type_id: typeId, flag, quantity: 1 });

          if (mod.ammo) {
            const chargeTypeId = nameToTypeId.get(mod.ammo) || nameToTypeId.get(mod.ammo.toLowerCase());
            if (chargeTypeId) {
              charges[flag] = chargeTypeId;
            }
          }

          flagIdx++;
        }
      }
    } else if (blockIdx === 4) {
      // Drone block
      for (const mod of block) {
        const typeId = nameToTypeId.get(mod.name) || nameToTypeId.get(mod.name.toLowerCase());
        if (!typeId) continue;
        items.push({ type_id: typeId, flag: 87, quantity: mod.quantity });
      }
    } else {
      // Cargo block(s) — charges/scripts, not fitted
      for (const mod of block) {
        const typeId = nameToTypeId.get(mod.name) || nameToTypeId.get(mod.name.toLowerCase());
        if (typeId) {
          cargo.push({ name: mod.name, typeId, quantity: mod.quantity });
        }
      }
    }
  }

  return { items, charges, cargo };
}

export function generateEft(
  shipName: string,
  fittingName: string,
  modulesBySlot: Record<string, { name: string; quantity: number; charge?: string }[]>,
  drones?: { name: string; quantity: number }[],
  cargo?: { name: string; quantity: number }[],
): string {
  const lines: string[] = [`[${shipName}, ${fittingName}]`];

  for (const slot of ['low', 'mid', 'high', 'rig']) {
    const modules = modulesBySlot[slot] || [];
    if (modules.length === 0) {
      lines.push(`[Empty ${slot.charAt(0).toUpperCase() + slot.slice(1)} slot]`);
    } else {
      for (const mod of modules) {
        if (mod.charge) {
          lines.push(`${mod.name}, ${mod.charge}`);
        } else {
          lines.push(mod.name);
        }
      }
    }
    lines.push('');
  }

  // Extra blank line before drones/cargo
  lines.push('');

  if (drones && drones.length > 0) {
    for (const drone of drones) {
      lines.push(`${drone.name} x${drone.quantity}`);
    }
    lines.push('');
  }

  if (cargo && cargo.length > 0) {
    for (const item of cargo) {
      lines.push(`${item.name} x${item.quantity}`);
    }
  }

  return lines.join('\n').trimEnd();
}
