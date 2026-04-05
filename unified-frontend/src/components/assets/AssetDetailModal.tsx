import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import type { Asset, ValuedAsset } from '@/types/character'
import { MapPin, Package, Layers, Box, Hash, Coins } from 'lucide-react'

interface AssetDetailModalProps {
  asset: Asset | ValuedAsset | null
  characterName?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Check if asset has valuation fields
 */
function isValuedAsset(asset: Asset | ValuedAsset): asset is ValuedAsset {
  return 'total_value' in asset && 'unit_price' in asset
}

/**
 * Format ISK value with appropriate suffix (K, M, B)
 */
function formatISK(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return value.toFixed(0)
}

function getItemIconUrl(typeId: number, size: 64 | 128 = 64): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

function formatNumber(value: number): string {
  return value.toLocaleString()
}

function getLocationTypeLabel(locationType: string | null): string {
  switch (locationType) {
    case 'station': return 'Station'
    case 'item': return 'Ship/Container'
    case 'other': return 'Other'
    default: return 'Unknown'
  }
}

function getLocationFlagLabel(flag: string | null): string {
  if (!flag) return 'Unknown'
  const flagMap: Record<string, string> = {
    Hangar: 'Hangar', HangarAll: 'Hangar', Cargo: 'Cargo Hold',
    DroneBay: 'Drone Bay', FighterBay: 'Fighter Bay', ShipHangar: 'Ship Hangar',
    SpecializedAmmoHold: 'Ammo Hold', SpecializedFuelBay: 'Fuel Bay',
    SpecializedOreHold: 'Ore Hold', SpecializedMineralHold: 'Mineral Hold',
    Unlocked: 'Container', Locked: 'Container (Locked)',
  }
  if (flag.startsWith('LoSlot')) return `Low Slot ${parseInt(flag.slice(6), 10) + 1}`
  if (flag.startsWith('MedSlot')) return `Mid Slot ${parseInt(flag.slice(7), 10) + 1}`
  if (flag.startsWith('HiSlot')) return `High Slot ${parseInt(flag.slice(6), 10) + 1}`
  if (flag.startsWith('RigSlot')) return `Rig Slot ${parseInt(flag.slice(7), 10) + 1}`
  if (flag.startsWith('SubSystemSlot')) return `Subsystem ${parseInt(flag.slice(13), 10) + 1}`
  return flagMap[flag] || flag
}

export function AssetDetailModal({ asset, characterName, open, onOpenChange }: AssetDetailModalProps) {
  if (!asset) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="flex items-start gap-4">
            <img
              src={getItemIconUrl(asset.type_id, 64)}
              alt={asset.type_name}
              className="w-16 h-16 rounded-lg border border-border"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
            <div className="flex-1 min-w-0">
              <DialogTitle className="text-xl">{asset.type_name}</DialogTitle>
              <DialogDescription className="sr-only">
                Details for {asset.type_name} including location, quantity, and properties
              </DialogDescription>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="secondary">{asset.group_name}</Badge>
                {asset.is_singleton && <Badge variant="outline">Assembled</Badge>}
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30">
            <Hash className="h-5 w-5 text-muted-foreground" />
            <div>
              <div className="text-sm text-muted-foreground">Quantity</div>
              <div className="font-mono text-lg font-semibold">{formatNumber(asset.quantity)}</div>
            </div>
          </div>

          {isValuedAsset(asset) && asset.total_value > 0 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-primary/10 border border-primary/20">
              <Coins className="h-5 w-5 text-primary" />
              <div className="flex-1">
                <div className="text-sm text-muted-foreground">Estimated Value</div>
                <div className="font-mono text-lg font-semibold text-primary">{formatISK(asset.total_value)} ISK</div>
                {asset.quantity > 1 && (
                  <div className="text-xs text-muted-foreground">
                    {formatISK(asset.unit_price)} ISK each
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30">
              <Layers className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="text-sm text-muted-foreground">Category</div>
                <div className="font-medium">{asset.category_name}</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30">
              <Package className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="text-sm text-muted-foreground">Group</div>
                <div className="font-medium truncate">{asset.group_name}</div>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-secondary/30">
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="h-5 w-5 text-primary" />
              <span className="text-sm text-muted-foreground">Location</span>
            </div>
            <div className="font-medium">{asset.location_name}</div>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span>{getLocationTypeLabel(asset.location_type)}</span>
              {asset.location_flag && (
                <>
                  <span>•</span>
                  <span>{getLocationFlagLabel(asset.location_flag)}</span>
                </>
              )}
            </div>
          </div>

          {characterName && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30">
              <Box className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="text-sm text-muted-foreground">Owner</div>
                <div className="font-medium">{characterName}</div>
              </div>
            </div>
          )}

          <div className="text-xs text-muted-foreground text-center pt-2 border-t border-border">
            Type ID: {asset.type_id} • Item ID: {asset.item_id}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
