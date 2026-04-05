/**
 * EFT (EVE Fitting Tool) format parser and generator.
 *
 * EFT format:
 *   [Ship Name, Fitting Name]
 *
 *   Low Slot Module
 *   Low Slot Module
 *
 *   Mid Slot Module
 *   Mid Slot Module
 *
 *   High Slot Module, Ammo Name
 *   High Slot Module, Ammo Name
 *
 *   Rig Module
 *
 *   Drone Name x5
 */

export interface ParsedModule {
  name: string
  quantity: number
  ammo?: string
}

export interface EftParseResult {
  shipName: string
  fittingName: string
  blocks: ParsedModule[][]
}

/**
 * Parse EFT format text into structured data.
 * Returns null if the text doesn't match EFT format.
 */
export function parseEft(text: string): EftParseResult | null {
  const lines = text.trim().split('\n')
  if (lines.length === 0) return null

  // Parse header: [Ship Name, Fitting Name]
  const header = lines[0].trim()
  const headerMatch = header.match(/^\[(.+?),\s*(.+?)\]$/)
  if (!headerMatch) return null

  const shipName = headerMatch[1].trim()
  const fittingName = headerMatch[2].trim()

  // Split remaining lines by empty lines into blocks
  const blocks: ParsedModule[][] = []
  let currentBlock: ParsedModule[] = []

  for (let i = 1; i < lines.length; i++) {
    const trimmed = lines[i].trim()

    if (trimmed === '') {
      if (currentBlock.length > 0) {
        blocks.push(currentBlock)
        currentBlock = []
      }
      continue
    }

    // Skip [Empty ...] placeholder lines
    if (trimmed.startsWith('[Empty ')) continue

    const parsed = parseLine(trimmed)
    if (parsed) currentBlock.push(parsed)
  }

  if (currentBlock.length > 0) {
    blocks.push(currentBlock)
  }

  return { shipName, fittingName, blocks }
}

function parseLine(line: string): ParsedModule | null {
  if (!line) return null

  // Split by comma: "Module Name, Ammo/Charge Name"
  const commaIdx = line.indexOf(',')
  let modulePart = commaIdx >= 0 ? line.slice(0, commaIdx).trim() : line.trim()
  const ammoPart = commaIdx >= 0 ? line.slice(commaIdx + 1).trim() : undefined

  // Handle quantity suffix: "Hammerhead II x5"
  let quantity = 1
  const qtyMatch = modulePart.match(/^(.+?)\s+x(\d+)$/i)
  if (qtyMatch) {
    modulePart = qtyMatch[1].trim()
    quantity = parseInt(qtyMatch[2], 10)
  }

  if (!modulePart) return null

  return {
    name: modulePart,
    quantity,
    ammo: ammoPart || undefined,
  }
}

/**
 * Slot block order in EFT format and their flag ranges.
 */
const SLOT_BLOCK_CONFIG = [
  { slot: 'low' as const, startFlag: 11 },
  { slot: 'mid' as const, startFlag: 19 },
  { slot: 'high' as const, startFlag: 27 },
  { slot: 'rig' as const, startFlag: 92 },
]

/**
 * Convert parsed EFT blocks + resolved type IDs into FittingItems.
 * Blocks 0-3 map to low/mid/high/rig slots.
 * Block 4+ treated as drones (flag 87) / cargo (flag 5).
 */
export function blocksToFittingItems(
  blocks: ParsedModule[][],
  nameToTypeId: Map<string, number>,
): { type_id: number; flag: number; quantity: number }[] {
  const items: { type_id: number; flag: number; quantity: number }[] = []

  for (let blockIdx = 0; blockIdx < blocks.length; blockIdx++) {
    const block = blocks[blockIdx]

    if (blockIdx < 4) {
      // Slot blocks: low, mid, high, rig
      const config = SLOT_BLOCK_CONFIG[blockIdx]
      let flagOffset = 0

      for (const mod of block) {
        const typeId = nameToTypeId.get(mod.name)
        if (!typeId) continue

        for (let q = 0; q < mod.quantity; q++) {
          items.push({
            type_id: typeId,
            flag: config.startFlag + flagOffset,
            quantity: 1,
          })
          flagOffset++
        }
      }
    } else {
      // Drone/cargo blocks — use flag 87 (drone bay)
      for (const mod of block) {
        const typeId = nameToTypeId.get(mod.name)
        if (!typeId) continue
        items.push({
          type_id: typeId,
          flag: 87,
          quantity: mod.quantity,
        })
      }
    }
  }

  return items
}

/**
 * Generate EFT format string from fitting data.
 */
export function generateEft(
  shipName: string,
  fittingName: string,
  modulesBySlot: {
    low: string[]
    mid: string[]
    high: string[]
    rig: string[]
  },
  drones?: { name: string; quantity: number }[],
): string {
  const lines: string[] = [`[${shipName}, ${fittingName}]`]

  const slotOrder = ['low', 'mid', 'high', 'rig'] as const
  for (const slot of slotOrder) {
    const modules = modulesBySlot[slot]
    lines.push('')
    if (modules.length > 0) {
      for (const mod of modules) {
        lines.push(mod)
      }
    } else {
      lines.push(`[Empty ${slot === 'rig' ? 'Rig' : slot.charAt(0).toUpperCase() + slot.slice(1)} slot]`)
    }
  }

  if (drones && drones.length > 0) {
    lines.push('')
    for (const d of drones) {
      lines.push(`${d.name} x${d.quantity}`)
    }
  }

  return lines.join('\n')
}
