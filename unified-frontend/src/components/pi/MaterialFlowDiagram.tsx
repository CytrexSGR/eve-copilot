import { Pickaxe, Factory, Package, ArrowRight } from 'lucide-react'

interface CharacterData {
  character_id: number
  character_name: string
  colonies: number
  extractors: number
  factories: number
}

interface MaterialFlowProps {
  characters: CharacterData[]
  targetProduct?: string
}

/**
 * Visual representation of material flow in the PI empire.
 * Shows extractors → factories → market pipeline.
 */
export function MaterialFlowDiagram({ characters, targetProduct }: MaterialFlowProps) {
  // Classify characters by their primary role based on extractor/factory ratio
  const classifiedCharacters = characters.map(c => {
    const total = c.extractors + c.factories
    if (total === 0) return { ...c, role: 'unknown' as const }

    const extractorRatio = c.extractors / total
    if (extractorRatio >= 0.7) return { ...c, role: 'extractor' as const }
    if (extractorRatio <= 0.3) return { ...c, role: 'factory' as const }
    return { ...c, role: 'hybrid' as const }
  })

  const extractors = classifiedCharacters.filter(c => c.role === 'extractor' || c.role === 'hybrid')
  const factories = classifiedCharacters.filter(c => c.role === 'factory' || c.role === 'hybrid')

  const totalExtractors = characters.reduce((sum, c) => sum + c.extractors, 0)
  const totalFactories = characters.reduce((sum, c) => sum + c.factories, 0)

  return (
    <div className="bg-[#0d1117] rounded-lg p-6">
      <h3 className="text-sm font-medium text-[#8b949e] mb-4">Material Flow</h3>

      <div className="flex items-center justify-center gap-4 overflow-x-auto">
        {/* Extractors */}
        <div className="flex flex-col items-center gap-2 p-4 bg-[#161b22] rounded-lg border border-green-500/30 min-w-[140px]">
          <Pickaxe className="w-8 h-8 text-green-400" />
          <span className="text-sm font-medium text-[#e6edf3]">Extraction</span>
          <div className="text-xs text-[#8b949e] text-center">
            {extractors.map(c => (
              <div key={c.character_id} className="truncate max-w-[120px]">
                {c.character_name}
              </div>
            ))}
          </div>
          <div className="text-lg font-bold text-green-400">{totalExtractors} units</div>
          <div className="text-xs text-[#6e7681]">P0 → P1</div>
        </div>

        {/* Arrow */}
        <div className="flex flex-col items-center shrink-0">
          <ArrowRight className="w-8 h-8 text-[#8b949e]" />
          <span className="text-xs text-[#6e7681]">Transfer</span>
        </div>

        {/* Factories */}
        <div className="flex flex-col items-center gap-2 p-4 bg-[#161b22] rounded-lg border border-blue-500/30 min-w-[140px]">
          <Factory className="w-8 h-8 text-blue-400" />
          <span className="text-sm font-medium text-[#e6edf3]">Factory</span>
          <div className="text-xs text-[#8b949e] text-center">
            {factories.map(c => (
              <div key={c.character_id} className="truncate max-w-[120px]">
                {c.character_name}
              </div>
            ))}
          </div>
          <div className="text-lg font-bold text-blue-400">{totalFactories} units</div>
          <div className="text-xs text-[#6e7681]">P1 → P4</div>
        </div>

        {/* Arrow */}
        <div className="flex flex-col items-center shrink-0">
          <ArrowRight className="w-8 h-8 text-[#8b949e]" />
          <span className="text-xs text-[#6e7681]">Export</span>
        </div>

        {/* Market */}
        <div className="flex flex-col items-center gap-2 p-4 bg-[#161b22] rounded-lg border border-yellow-500/30 min-w-[140px]">
          <Package className="w-8 h-8 text-yellow-400" />
          <span className="text-sm font-medium text-[#e6edf3]">Market</span>
          {targetProduct ? (
            <div className="text-xs text-yellow-400 text-center truncate max-w-[120px]">
              {targetProduct}
            </div>
          ) : (
            <div className="text-xs text-[#8b949e]">P4 Products</div>
          )}
          <div className="text-lg font-bold text-yellow-400">ISK</div>
          <div className="text-xs text-[#6e7681]">Jita</div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center gap-6 text-xs text-[#8b949e]">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span>Extraction (P0→P1)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-blue-400" />
          <span>Processing (P1→P4)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-yellow-400" />
          <span>Export & Sale</span>
        </div>
      </div>
    </div>
  )
}
