// frontend/src/utils/pi.ts
import type { PIChainNode } from '../api/pi';
import { P0_PLANET_MAP } from '../constants/pi';

/**
 * Flattened material for tier column display.
 */
export interface FlatMaterial {
  type_id: number;
  type_name: string;
  tier: number;
  quantity_needed: number;
  schematic_id?: number;
  planet_types?: string[]; // Only populated for P0 (tier 0)
}

/**
 * Flatten a nested PIChainNode tree into tier-grouped materials.
 * Aggregates quantities for duplicate materials at the same tier.
 *
 * @param node - Root node of the production chain tree
 * @returns Record mapping tier (0-4) to array of materials at that tier
 */
export function flattenChainByTier(
  node: PIChainNode
): Record<number, FlatMaterial[]> {
  const result: Record<number, FlatMaterial[]> = {
    0: [],
    1: [],
    2: [],
    3: [],
    4: [],
  };

  function traverse(n: PIChainNode): void {
    // Check if material already exists at this tier
    const existing = result[n.tier]?.find((m) => m.type_id === n.type_id);

    if (existing) {
      // Aggregate quantities
      existing.quantity_needed += n.quantity_needed;
    } else {
      const material: FlatMaterial = {
        type_id: n.type_id,
        type_name: n.type_name,
        tier: n.tier,
        quantity_needed: n.quantity_needed,
        schematic_id: n.schematic_id,
      };

      // Add planet types for P0 materials
      if (n.tier === 0) {
        material.planet_types = P0_PLANET_MAP[n.type_name] || [];
      }

      if (result[n.tier]) {
        result[n.tier].push(material);
      }
    }

    // Recursively process children
    n.children?.forEach(traverse);
  }

  traverse(node);
  return result;
}

/**
 * Extract all unique planet types needed for P0 extraction.
 *
 * @param tierMap - Result from flattenChainByTier
 * @returns Array of unique planet type names (capitalized)
 */
export function getRequiredPlanetTypes(
  tierMap: Record<number, FlatMaterial[]>
): string[] {
  const planetSet = new Set<string>();

  for (const material of tierMap[0] || []) {
    // Add the first available planet type for each P0 material
    // (simplest extraction option)
    if (material.planet_types && material.planet_types.length > 0) {
      planetSet.add(material.planet_types[0]);
    }
  }

  return Array.from(planetSet).sort();
}
