import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Upload, FileText, AlertCircle, Check } from 'lucide-react'
import { resolveTypeNames } from '@/api/fittings'
import { parseEft, blocksToFittingItems } from '@/lib/eft-parser'
import type { EftParseResult } from '@/lib/eft-parser'
import { getShipRenderUrl, getModuleIconUrl } from '@/types/fittings'

interface ImportDialogProps {
  open: boolean
  onClose: () => void
}

type ImportStep = 'paste' | 'preview' | 'error'

interface ResolvedFitting {
  shipName: string
  shipTypeId: number
  fittingName: string
  parsed: EftParseResult
  resolvedNames: Map<string, number>
  unresolvedNames: string[]
}

export function ImportDialog({ open, onClose }: ImportDialogProps) {
  const navigate = useNavigate()
  const [step, setStep] = useState<ImportStep>('paste')
  const [eftText, setEftText] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [resolved, setResolved] = useState<ResolvedFitting | null>(null)

  if (!open) return null

  function handleClose() {
    setStep('paste')
    setEftText('')
    setError('')
    setResolved(null)
    onClose()
  }

  async function handleParse() {
    const parsed = parseEft(eftText)
    if (!parsed) {
      setError('Invalid EFT format. First line must be [Ship Name, Fitting Name]')
      setStep('error')
      return
    }

    if (parsed.blocks.length === 0) {
      setError('No modules found in the fitting.')
      setStep('error')
      return
    }

    setLoading(true)
    try {
      // Collect all unique names to resolve
      const allNames = new Set<string>()
      allNames.add(parsed.shipName)
      for (const block of parsed.blocks) {
        for (const mod of block) {
          allNames.add(mod.name)
        }
      }

      // Resolve names via API
      const resolveResult = await resolveTypeNames([...allNames])
      const nameMap = new Map<string, number>()
      for (const r of resolveResult) {
        nameMap.set(r.type_name, r.type_id)
      }

      // Also try case-insensitive matching for names that weren't found
      for (const name of allNames) {
        if (!nameMap.has(name)) {
          const match = resolveResult.find(
            (r) => r.type_name.toLowerCase() === name.toLowerCase()
          )
          if (match) nameMap.set(name, match.type_id)
        }
      }

      const shipTypeId = nameMap.get(parsed.shipName)
      if (!shipTypeId) {
        setError(`Ship "${parsed.shipName}" not found in database.`)
        setStep('error')
        setLoading(false)
        return
      }

      // Find unresolved module names
      const unresolvedNames: string[] = []
      for (const block of parsed.blocks) {
        for (const mod of block) {
          if (!nameMap.has(mod.name)) unresolvedNames.push(mod.name)
        }
      }

      setResolved({
        shipName: parsed.shipName,
        shipTypeId,
        fittingName: parsed.fittingName,
        parsed,
        resolvedNames: nameMap,
        unresolvedNames,
      })
      setStep('preview')
    } catch (err) {
      setError('Failed to resolve type names. Check your connection.')
      setStep('error')
    } finally {
      setLoading(false)
    }
  }

  async function handleImport() {
    if (!resolved) return
    setLoading(true)
    try {
      const items = blocksToFittingItems(resolved.parsed.blocks, resolved.resolvedNames)

      handleClose()
      navigate('/fittings/new', {
        state: {
          shipTypeId: resolved.shipTypeId,
          items,
          name: resolved.fittingName,
        },
      })
    } catch {
      setError('Failed to load ship details.')
      setStep('error')
    } finally {
      setLoading(false)
    }
  }

  const slotLabels = ['Low Slots', 'Mid Slots', 'High Slots', 'Rig Slots', 'Drones/Cargo']

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={handleClose}>
      <div
        className="w-full max-w-lg rounded-lg border border-border bg-card shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Import EFT Fitting
          </h2>
          <button onClick={handleClose} className="p-1 rounded hover:bg-accent">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4">
          {step === 'paste' && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Paste an EFT format fitting from pyfa, EVE client, or other tools.
              </p>
              <textarea
                value={eftText}
                onChange={(e) => setEftText(e.target.value)}
                placeholder={`[Drake, PvE Tank Fit]\n\nBallistic Control System II\nBallistic Control System II\nDamage Control II\n\nLarge Shield Extender II\nAdaptive Invulnerability Field II\n10MN Afterburner II\n\nHeavy Assault Missile Launcher II\nHeavy Assault Missile Launcher II\n\nMedium Core Defense Field Purger I`}
                rows={12}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                autoFocus
              />
              <div className="flex justify-end">
                <button
                  onClick={handleParse}
                  disabled={!eftText.trim() || loading}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Resolving...' : 'Parse & Preview'}
                </button>
              </div>
            </div>
          )}

          {step === 'error' && (
            <div className="space-y-3">
              <div className="flex items-start gap-2 rounded-md bg-red-500/10 border border-red-500/20 p-3">
                <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
                <p className="text-sm text-red-400">{error}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setStep('paste')}
                  className="flex-1 h-9 rounded-md border border-border text-sm font-medium hover:bg-accent transition-colors"
                >
                  Back
                </button>
              </div>
            </div>
          )}

          {step === 'preview' && resolved && (
            <div className="space-y-4">
              {/* Ship */}
              <div className="flex items-center gap-3 rounded-md bg-background/50 p-3">
                <img
                  src={getShipRenderUrl(resolved.shipTypeId, 64)}
                  alt=""
                  className="h-10 w-10 rounded-md"
                />
                <div>
                  <p className="text-sm font-medium">{resolved.fittingName}</p>
                  <p className="text-xs text-muted-foreground">{resolved.shipName}</p>
                </div>
                <Check className="h-4 w-4 text-green-400 ml-auto" />
              </div>

              {/* Module blocks */}
              <div className="max-h-[280px] overflow-y-auto space-y-3">
                {resolved.parsed.blocks.map((block, blockIdx) => (
                  <div key={blockIdx}>
                    <p className="text-[10px] text-muted-foreground font-medium uppercase mb-1">
                      {slotLabels[blockIdx] || `Block ${blockIdx + 1}`}
                    </p>
                    <div className="space-y-0.5">
                      {block.map((mod, modIdx) => {
                        const typeId = resolved.resolvedNames.get(mod.name)
                        return (
                          <div
                            key={modIdx}
                            className="flex items-center gap-2 py-0.5 px-2 rounded text-xs"
                          >
                            {typeId ? (
                              <img
                                src={getModuleIconUrl(typeId)}
                                alt=""
                                className="h-5 w-5 rounded"
                              />
                            ) : (
                              <div className="h-5 w-5 rounded bg-red-500/20 flex items-center justify-center">
                                <X className="h-3 w-3 text-red-400" />
                              </div>
                            )}
                            <span className={typeId ? '' : 'text-red-400 line-through'}>
                              {mod.name}
                            </span>
                            {mod.quantity > 1 && (
                              <span className="text-muted-foreground">x{mod.quantity}</span>
                            )}
                            {!typeId && (
                              <span className="text-[10px] text-red-400 ml-auto">not found</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Warnings */}
              {resolved.unresolvedNames.length > 0 && (
                <div className="flex items-start gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/20 p-2">
                  <AlertCircle className="h-3.5 w-3.5 text-yellow-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-yellow-400">
                    {resolved.unresolvedNames.length} module(s) could not be resolved and will be skipped.
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => setStep('paste')}
                  className="flex-1 h-9 rounded-md border border-border text-sm font-medium hover:bg-accent transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={handleImport}
                  disabled={loading}
                  className="flex-1 h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Upload className="h-3.5 w-3.5" />
                  {loading ? 'Loading...' : 'Import to Editor'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
