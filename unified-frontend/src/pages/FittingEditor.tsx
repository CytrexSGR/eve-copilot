import { useReducer, useEffect, useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { ArrowLeft, Save, Trash2, Upload } from 'lucide-react'
import { saveCustomFitting, getShipDetail } from '@/api/fittings'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { ShipSelector } from '@/components/fittings/ShipSelector'
import { SlotEditor } from '@/components/fittings/SlotEditor'
import { ModulePicker } from '@/components/fittings/ModulePicker'
import { LiveStats } from '@/components/fittings/LiveStats'
import { FittingNameDialog } from '@/components/fittings/FittingNameDialog'
import { ImportDialog } from '@/components/fittings/ImportDialog'
import { getShipRenderUrl } from '@/types/fittings'
import type { FittingItem, ShipDetail, SlotType } from '@/types/fittings'

// --- State management ---

interface FittingState {
  shipTypeId: number | null
  shipDetail: ShipDetail | null
  items: FittingItem[]
  name: string
  pickerSlotType: SlotType | null
  pickerSlotFlag: number | null
  showSaveDialog: boolean
}

type FittingAction =
  | { type: 'SET_SHIP'; shipDetail: ShipDetail }
  | { type: 'ADD_MODULE'; typeId: number }
  | { type: 'REMOVE_MODULE'; flag: number }
  | { type: 'OPEN_PICKER'; slotType: SlotType; flag: number }
  | { type: 'CLOSE_PICKER' }
  | { type: 'LOAD_FITTING'; items: FittingItem[]; shipDetail: ShipDetail; name: string }
  | { type: 'TOGGLE_SAVE_DIALOG' }
  | { type: 'CLEAR' }

const initialState: FittingState = {
  shipTypeId: null,
  shipDetail: null,
  items: [],
  name: '',
  pickerSlotType: null,
  pickerSlotFlag: null,
  showSaveDialog: false,
}

function fittingReducer(state: FittingState, action: FittingAction): FittingState {
  switch (action.type) {
    case 'SET_SHIP':
      return {
        ...initialState,
        shipTypeId: action.shipDetail.type_id,
        shipDetail: action.shipDetail,
      }
    case 'ADD_MODULE':
      if (state.pickerSlotFlag === null) return state
      return {
        ...state,
        items: [...state.items, { type_id: action.typeId, flag: state.pickerSlotFlag, quantity: 1 }],
        pickerSlotType: null,
        pickerSlotFlag: null,
      }
    case 'REMOVE_MODULE':
      return {
        ...state,
        items: state.items.filter((i) => i.flag !== action.flag),
      }
    case 'OPEN_PICKER':
      return {
        ...state,
        pickerSlotType: action.slotType,
        pickerSlotFlag: action.flag,
      }
    case 'CLOSE_PICKER':
      return { ...state, pickerSlotType: null, pickerSlotFlag: null }
    case 'LOAD_FITTING':
      return {
        ...state,
        shipTypeId: action.shipDetail.type_id,
        shipDetail: action.shipDetail,
        items: action.items,
        name: action.name,
      }
    case 'TOGGLE_SAVE_DIALOG':
      return { ...state, showSaveDialog: !state.showSaveDialog }
    case 'CLEAR':
      return { ...initialState }
    default:
      return state
  }
}

// --- Location state for loading existing fittings ---

interface LocationState {
  shipTypeId?: number
  items?: FittingItem[]
  name?: string
}

// --- Component ---

export default function FittingEditor() {
  const navigate = useNavigate()
  const location = useLocation()
  const { characters, selectedCharacter } = useCharacterContext()
  const charId = selectedCharacter?.character_id || characters[0]?.character_id

  const [state, dispatch] = useReducer(fittingReducer, initialState)
  const [saving, setSaving] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [showImport, setShowImport] = useState(false)

  // Load fitting from location state (e.g. "Edit" from detail page or EFT import)
  // Uses location.key so re-navigating to /fittings/new with new state triggers reload
  const [lastKey, setLastKey] = useState('')
  useEffect(() => {
    if (location.key === lastKey) return
    setLastKey(location.key)
    const ls = location.state as LocationState | null
    if (ls?.shipTypeId && ls?.items) {
      setLoaded(true)
      getShipDetail(ls.shipTypeId).then((detail) => {
        dispatch({
          type: 'LOAD_FITTING',
          items: ls.items!,
          shipDetail: detail,
          name: ls.name || '',
        })
      })
    } else if (!loaded) {
      setLoaded(true)
    }
  }, [location.key, lastKey, loaded])

  const moduleCount = state.items.filter(
    (i) => i.flag !== 5 && i.flag !== 87 && i.flag !== 158
  ).length

  async function handleSave(data: { name: string; description: string; tags: string[]; isPublic: boolean }) {
    if (!state.shipTypeId || !charId) return
    setSaving(true)
    try {
      await saveCustomFitting({
        name: data.name,
        description: data.description,
        ship_type_id: state.shipTypeId,
        items: state.items,
        tags: data.tags,
        is_public: data.isPublic,
        creator_character_id: charId,
      })
      navigate('/fittings')
    } catch {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/fittings"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          {state.shipDetail ? (
            <div className="flex items-center gap-3">
              <img
                src={getShipRenderUrl(state.shipTypeId!, 64)}
                alt=""
                className="h-10 w-10 rounded-lg"
              />
              <div>
                <h1 className="text-lg font-bold">
                  {state.name || 'New Fitting'}
                </h1>
                <p className="text-xs text-muted-foreground">
                  {state.shipDetail.type_name} &mdash; {moduleCount} modules
                </p>
              </div>
            </div>
          ) : (
            <h1 className="text-lg font-bold">New Fitting</h1>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
          >
            <Upload className="h-3.5 w-3.5" />
            Import EFT
          </button>
          {state.items.length > 0 && (
            <button
              onClick={() => dispatch({ type: 'CLEAR' })}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
          <button
            onClick={() => dispatch({ type: 'TOGGLE_SAVE_DIALOG' })}
            disabled={!state.shipTypeId || state.items.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" />
            Save
          </button>
        </div>
      </div>

      {/* Ship Selector */}
      <ShipSelector
        selectedShip={state.shipDetail}
        onSelect={(ship) => dispatch({ type: 'SET_SHIP', shipDetail: ship })}
      />

      {/* Two-panel layout */}
      <div className="grid gap-4 lg:grid-cols-[1fr,340px]">
        {/* Left: Slot Editor */}
        <SlotEditor
          shipDetail={state.shipDetail}
          items={state.items}
          activeSlot={
            state.pickerSlotType && state.pickerSlotFlag !== null
              ? { type: state.pickerSlotType, flag: state.pickerSlotFlag }
              : null
          }
          onSlotClick={(slotType, flag) =>
            dispatch({ type: 'OPEN_PICKER', slotType, flag })
          }
          onRemoveModule={(flag) => dispatch({ type: 'REMOVE_MODULE', flag })}
        />

        {/* Right: Module Picker + Live Stats */}
        <div className="space-y-4">
          <ModulePicker
            slotType={state.pickerSlotType}
            onSelectModule={(typeId) => dispatch({ type: 'ADD_MODULE', typeId })}
          />
          <LiveStats shipTypeId={state.shipTypeId} items={state.items} />
        </div>
      </div>

      {/* Save Dialog */}
      <FittingNameDialog
        open={state.showSaveDialog}
        onClose={() => dispatch({ type: 'TOGGLE_SAVE_DIALOG' })}
        onSave={handleSave}
        initialName={state.name}
        saving={saving}
      />

      {/* Import Dialog */}
      <ImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  )
}
