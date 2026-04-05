import { useReducer, useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { ModuleGate } from '../components/ModuleGate';
import { FittingBrowser } from '../components/fittings';
import { ShipDisplay } from '../components/fittings/ShipDisplay';
import { CollapsibleStats } from '../components/fittings/CollapsibleStats';
import { EnrichedModuleList } from '../components/fittings/EnrichedModuleList';
import { FittingNameDialog } from '../components/fittings/FittingNameDialog';
import { ImportDialog } from '../components/fittings/ImportDialog';
import { useAuth } from '../hooks/useAuth';
import { sdeApi, fittingApi, resolveTypeNames } from '../services/api/fittings';
import { generateEft } from '../lib/eft-parser';
import type { ShipDetail, FittingItem, FittingStats, SlotType, PickerMode, FittingChargeMap, DroneEntry, BrowserTab, ModuleState, T3DMode, FighterInput, FleetBoostInput, ProjectedEffectInput } from '../types/fittings';
import { SLOT_RANGES } from '../types/fittings';
import FighterSection from '../components/fittings/FighterSection';
import FleetBoostSection from '../components/fittings/FleetBoostSection';
import ProjectedEffectsSection from '../components/fittings/ProjectedEffectsSection';

// --- State ---

interface FittingState {
  shipTypeId: number | null;
  shipDetail: ShipDetail | null;
  items: FittingItem[];
  charges: FittingChargeMap;
  drones: DroneEntry[];
  name: string;
  pickerMode: PickerMode | null;
  showSaveDialog: boolean;
  activeTab: BrowserTab;
  slotFilter: SlotType | null;
  /** Tracks hardpoint type per slot flag: flag → 'turret' | 'launcher' | null */
  hardpointMap: Record<number, string | null>;
  moduleStates: Record<number, ModuleState>;
}

type FittingAction =
  | { type: 'SET_SHIP'; shipDetail: ShipDetail }
  | { type: 'ADD_MODULE'; typeId: number; flag: number; hardpointType?: string | null }
  | { type: 'REMOVE_MODULE'; flag: number }
  | { type: 'SET_CHARGE'; flag: number; chargeTypeId: number }
  | { type: 'REMOVE_CHARGE'; flag: number }
  | { type: 'ADD_DRONE'; typeId: number; count: number }
  | { type: 'REMOVE_DRONE'; typeId: number }
  | { type: 'OPEN_PICKER'; mode: PickerMode }
  | { type: 'CLOSE_PICKER' }
  | { type: 'LOAD_FITTING'; shipDetail: ShipDetail; items: FittingItem[]; name: string; charges?: FittingChargeMap }
  | { type: 'TOGGLE_SAVE_DIALOG' }
  | { type: 'CLEAR' }
  | { type: 'SET_TAB'; tab: BrowserTab }
  | { type: 'SET_SLOT_FILTER'; slotFilter: SlotType | null }
  | { type: 'SET_MODULE_STATE'; flag: number; state: ModuleState }
  | { type: 'TOGGLE_OVERHEAT'; flag: number };

function fittingReducer(state: FittingState, action: FittingAction): FittingState {
  switch (action.type) {
    case 'SET_SHIP':
      return {
        ...state,
        shipTypeId: action.shipDetail.type_id,
        shipDetail: action.shipDetail,
        items: [],
        charges: {},
        drones: [],
        pickerMode: null,
        hardpointMap: {},
        moduleStates: {},
      };
    case 'ADD_MODULE': {
      // Replace if a module already exists in this slot
      const filtered = state.items.filter(i => i.flag !== action.flag);
      const newHpMap = { ...state.hardpointMap };
      if (action.hardpointType !== undefined) {
        newHpMap[action.flag] = action.hardpointType ?? null;
      }
      return {
        ...state,
        items: [...filtered, { type_id: action.typeId, flag: action.flag, quantity: 1 }],
        pickerMode: null,
        hardpointMap: newHpMap,
      };
    }
    case 'REMOVE_MODULE': {
      // Also remove charge, hardpoint tracking, and module state for the removed module's slot
      const newCharges = { ...state.charges };
      delete newCharges[action.flag];
      const newHpMap2 = { ...state.hardpointMap };
      delete newHpMap2[action.flag];
      const newStates = { ...state.moduleStates };
      delete newStates[action.flag];
      return {
        ...state,
        items: state.items.filter(i => i.flag !== action.flag),
        charges: newCharges,
        hardpointMap: newHpMap2,
        moduleStates: newStates,
      };
    }
    case 'SET_CHARGE':
      return {
        ...state,
        charges: { ...state.charges, [action.flag]: action.chargeTypeId },
      };
    case 'REMOVE_CHARGE': {
      const newCharges = { ...state.charges };
      delete newCharges[action.flag];
      return { ...state, charges: newCharges };
    }
    case 'ADD_DRONE': {
      const existing = state.drones.find(d => d.type_id === action.typeId);
      if (existing) {
        return {
          ...state,
          drones: state.drones.map(d =>
            d.type_id === action.typeId ? { ...d, count: d.count + action.count } : d
          ),
        };
      }
      return {
        ...state,
        drones: [...state.drones, { type_id: action.typeId, count: action.count }],
      };
    }
    case 'REMOVE_DRONE':
      return {
        ...state,
        drones: state.drones.filter(d => d.type_id !== action.typeId),
      };
    case 'OPEN_PICKER':
      return { ...state, pickerMode: action.mode };
    case 'CLOSE_PICKER':
      return { ...state, pickerMode: null };
    case 'LOAD_FITTING': {
      // Extract drones (flag=87) from items into DroneEntry[]
      const droneItems = action.items.filter(i => i.flag === 87);
      const nonDroneItems = action.items.filter(i => i.flag !== 87);
      const loadedDrones: DroneEntry[] = droneItems.map(i => ({ type_id: i.type_id, count: i.quantity }));
      return {
        ...state,
        shipTypeId: action.shipDetail.type_id,
        shipDetail: action.shipDetail,
        items: nonDroneItems,
        charges: action.charges || {},
        drones: loadedDrones,
        name: action.name,
        pickerMode: null,
        hardpointMap: {},
        moduleStates: {},
      };
    }
    case 'SET_TAB':
      return { ...state, activeTab: action.tab };
    case 'SET_SLOT_FILTER':
      return { ...state, slotFilter: action.slotFilter };
    case 'TOGGLE_SAVE_DIALOG':
      return { ...state, showSaveDialog: !state.showSaveDialog };
    case 'CLEAR':
      return { ...initialState };
    case 'SET_MODULE_STATE':
      return { ...state, moduleStates: { ...state.moduleStates, [action.flag]: action.state } };
    case 'TOGGLE_OVERHEAT': {
      const current = state.moduleStates[action.flag] || 'active';
      const next = current === 'overheated' ? 'active' : 'overheated';
      return { ...state, moduleStates: { ...state.moduleStates, [action.flag]: next } };
    }
    default:
      return state;
  }
}

const initialState: FittingState = {
  shipTypeId: null,
  shipDetail: null,
  items: [],
  charges: {},
  drones: [],
  name: '',
  pickerMode: null,
  showSaveDialog: false,
  activeTab: 'hulls' as BrowserTab,
  slotFilter: null as SlotType | null,
  hardpointMap: {},
  moduleStates: {},
};

// --- Component ---

export function FittingEditor() {
  const [state, dispatch] = useReducer(fittingReducer, initialState);
  const [saving, setSaving] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [copied, setCopied] = useState(false);
  const [weaponTypeIds, setWeaponTypeIds] = useState<Set<number>>(new Set());
  const [stats, setStats] = useState<FittingStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [selectedCharacterId, setSelectedCharacterId] = useState<number | undefined>(undefined);
  const [selectedTarget, setSelectedTarget] = useState<string>('cruiser');
  const [simulationMode, setSimulationMode] = useState(true);
  const [includeImplants, setIncludeImplants] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const location = useLocation();
  const navigate = useNavigate();
  const { account } = useAuth();
  const [lastKey, setLastKey] = useState('');
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [editingFittingId, setEditingFittingId] = useState<number | null>(null);
  const [availableModes, setAvailableModes] = useState<T3DMode[]>([]);
  const [selectedModeId, setSelectedModeId] = useState<number | undefined>(undefined);
  const [fighters, setFighters] = useState<FighterInput[]>([]);
  const [fleetBoosts, setFleetBoosts] = useState<FleetBoostInput[]>([]);
  const [projectedEffects, setProjectedEffects] = useState<ProjectedEffectInput[]>([]);
  const [targetProjected, setTargetProjected] = useState<ProjectedEffectInput[]>([]);

  // Load fitting from location.state on mount and navigation
  useEffect(() => {
    if (location.key !== lastKey) {
      setLastKey(location.key);
      const navState = location.state as { shipTypeId?: number; items?: FittingItem[]; charges?: FittingChargeMap; name?: string; sourceUrl?: string; fittingId?: number } | null;
      if (navState?.sourceUrl) setSourceUrl(navState.sourceUrl);
      if (navState?.fittingId) setEditingFittingId(navState.fittingId);
      else setEditingFittingId(null);
      if (navState?.shipTypeId) {
        sdeApi.getShipDetail(navState.shipTypeId).then(ship => {
          dispatch({
            type: 'LOAD_FITTING',
            shipDetail: ship,
            items: navState.items || [],
            name: navState.name || '',
            charges: navState.charges,
          });
        });
      }
    }
  }, [location.key, lastKey]);

  // Detect weapons by checking if modules have compatible charges
  useEffect(() => {
    const moduleTypeIds = state.items.map(i => i.type_id);
    const unchecked = moduleTypeIds.filter(id => !weaponTypeIds.has(id));
    if (unchecked.length === 0) return;

    // Check each unchecked module for charge compatibility
    const uniqueUnchecked = [...new Set(unchecked)];
    Promise.all(
      uniqueUnchecked.map(async (typeId) => {
        try {
          const charges = await sdeApi.getCharges(typeId);
          return charges.length > 0 ? typeId : null;
        } catch {
          return null;
        }
      })
    ).then(results => {
      const newWeapons = results.filter((id): id is number => id !== null);
      if (newWeapons.length > 0) {
        setWeaponTypeIds(prev => {
          const next = new Set(prev);
          newWeapons.forEach(id => next.add(id));
          return next;
        });
      }
    });
  }, [state.items, weaponTypeIds]);

  // Fetch T3D modes when ship changes
  useEffect(() => {
    if (!state.shipDetail) {
      setAvailableModes([]);
      setSelectedModeId(undefined);
      return;
    }
    sdeApi.getModes(state.shipDetail.type_id).then(modes => {
      setAvailableModes(modes);
      setSelectedModeId(modes.length > 0 ? modes[0].type_id : undefined);
    }).catch(() => {
      setAvailableModes([]);
      setSelectedModeId(undefined);
    });
  }, [state.shipDetail?.type_id]);

  // Carrier detection
  const isCarrier = state.shipDetail ? ['Carrier', 'Supercarrier', 'Force Auxiliary'].includes(state.shipDetail.group_name) : false;

  // Activatable flags (modules with activation cycle, not passive)
  const activatableFlags = useMemo(() => new Set(stats?.activatable_flags ?? []), [stats?.activatable_flags]);

  // Clear fighters when ship changes
  useEffect(() => { setFighters([]); }, [state.shipTypeId]);

  // Debounced stats fetching
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const droneItems: FittingItem[] = state.drones.map(d => ({ type_id: d.type_id, flag: 87, quantity: d.count }));
    const allItemsForStats = [...state.items, ...droneItems];
    const fittingItems = allItemsForStats.filter(i => i.flag !== 5 && i.flag !== 158);
    if (!state.shipTypeId || fittingItems.length === 0) {
      setStats(null);
      return;
    }
    setStatsLoading(true);
    debounceRef.current = setTimeout(() => {
      fittingApi.getFittingStats(state.shipTypeId!, fittingItems, state.charges, selectedCharacterId, selectedTarget, simulationMode, includeImplants, state.moduleStates, undefined, selectedModeId, fighters, fleetBoosts, projectedEffects, targetProjected)
        .then(setStats)
        .catch(() => setStats(null))
        .finally(() => setStatsLoading(false));
    }, 150);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [state.shipTypeId, state.items, state.drones, state.charges, state.moduleStates, selectedCharacterId, selectedTarget, simulationMode, includeImplants, selectedModeId, fighters, fleetBoosts, projectedEffects, targetProjected]);

  const isWeapon = useCallback((typeId: number) => weaponTypeIds.has(typeId), [weaponTypeIds]);

  const handleSelectModule = (typeId: number, slotType?: string, hardpointType?: string | null) => {
    if (state.pickerMode?.kind === 'module') {
      const pickerFlag = state.pickerMode.flag;
      // Enforce hardpoint limits when fitting via slot picker
      if ((hardpointType === 'turret' || hardpointType === 'launcher') && state.shipDetail) {
        const maxHardpoints = hardpointType === 'turret'
          ? (state.shipDetail.turret_hardpoints ?? 0)
          : (state.shipDetail.launcher_hardpoints ?? 0);
        // Count existing hardpoints, excluding the slot being replaced
        const usedHardpoints = Object.entries(state.hardpointMap)
          .filter(([flag, h]) => h === hardpointType && Number(flag) !== pickerFlag)
          .length;
        if (usedHardpoints >= maxHardpoints) return;
      }
      dispatch({ type: 'ADD_MODULE', typeId, flag: pickerFlag, hardpointType });
    } else if (state.pickerMode?.kind === 'drone') {
      dispatch({ type: 'ADD_DRONE', typeId, count: 1 });
      dispatch({ type: 'CLOSE_PICKER' });
    } else if (slotType && state.shipDetail) {
      // Auto-fit: find next empty slot for this module's slot type
      if (slotType === 'drone') {
        dispatch({ type: 'ADD_DRONE', typeId, count: 1 });
      } else {
        // Enforce hardpoint limits for turrets/launchers
        if (hardpointType === 'turret' || hardpointType === 'launcher') {
          const maxHardpoints = hardpointType === 'turret'
            ? (state.shipDetail.turret_hardpoints ?? 0)
            : (state.shipDetail.launcher_hardpoints ?? 0);
          const usedHardpoints = Object.values(state.hardpointMap).filter(h => h === hardpointType).length;
          if (usedHardpoints >= maxHardpoints) return;
        }
        const slotKey = slotType as SlotType;
        const range = SLOT_RANGES[slotKey];
        if (range) {
          const maxSlots = slotKey === 'high' ? (state.shipDetail.hi_slots ?? 0)
            : slotKey === 'mid' ? (state.shipDetail.med_slots ?? 0)
            : slotKey === 'low' ? (state.shipDetail.low_slots ?? 0)
            : (state.shipDetail.rig_slots ?? 0);
          for (let flag = range.start; flag < range.start + maxSlots; flag++) {
            if (!state.items.some(i => i.flag === flag)) {
              dispatch({ type: 'ADD_MODULE', typeId, flag, hardpointType });
              return;
            }
          }
        }
      }
    }
  };

  const handleAutoFitModule = (typeId: number, slotType?: string, hardpointType?: string | null) => {
    if (!slotType || !state.shipDetail) return;
    if (slotType === 'drone') {
      dispatch({ type: 'ADD_DRONE', typeId, count: 1 });
      return;
    }
    // Enforce hardpoint limits
    if (hardpointType === 'turret' || hardpointType === 'launcher') {
      const maxHardpoints = hardpointType === 'turret'
        ? (state.shipDetail.turret_hardpoints ?? 0)
        : (state.shipDetail.launcher_hardpoints ?? 0);
      const usedHardpoints = Object.values(state.hardpointMap).filter(h => h === hardpointType).length;
      if (usedHardpoints >= maxHardpoints) return;
    }
    const slotKey = slotType as SlotType;
    const range = SLOT_RANGES[slotKey];
    if (!range) return;
    const maxSlots = slotKey === 'high' ? (state.shipDetail.hi_slots ?? 0)
      : slotKey === 'mid' ? (state.shipDetail.med_slots ?? 0)
      : slotKey === 'low' ? (state.shipDetail.low_slots ?? 0)
      : (state.shipDetail.rig_slots ?? 0);
    for (let flag = range.start; flag < range.start + maxSlots; flag++) {
      if (!state.items.some(i => i.flag === flag)) {
        dispatch({ type: 'ADD_MODULE', typeId, flag, hardpointType });
        return;
      }
    }
  };

  const handleSelectCharge = (chargeTypeId: number) => {
    if (state.pickerMode?.kind === 'charge') {
      dispatch({ type: 'SET_CHARGE', flag: state.pickerMode.flag, chargeTypeId });
      dispatch({ type: 'CLOSE_PICKER' });
    } else {
      // Browsing Ammo tab without active charge picker — assign to all fitted weapons
      for (const item of state.items) {
        if (weaponTypeIds.has(item.type_id)) {
          dispatch({ type: 'SET_CHARGE', flag: item.flag, chargeTypeId });
        }
      }
    }
  };

  const handleSlotClick = (type: SlotType, flag: number) => {
    dispatch({ type: 'OPEN_PICKER', mode: { kind: 'module', slotType: type, flag } });
    dispatch({ type: 'SET_TAB', tab: 'modules' });
    dispatch({ type: 'SET_SLOT_FILTER', slotFilter: type });
  };

  const handleChargeClick = (flag: number, weaponTypeId: number) => {
    dispatch({ type: 'OPEN_PICKER', mode: { kind: 'charge', flag, weaponTypeId } });
    dispatch({ type: 'SET_TAB', tab: 'charges' });
  };

  const handleShipSelect = (typeId: number) => {
    sdeApi.getShipDetail(typeId).then(ship => {
      dispatch({ type: 'SET_SHIP', shipDetail: ship });
    });
  };

  const handleSave = async (data: { name: string; description: string; tags: string[]; isPublic: boolean; overwrite?: boolean }) => {
    if (!state.shipTypeId || !account?.primary_character_id) return;
    setSaving(true);
    try {
      // Include drone items in saved fitting
      const droneItems: FittingItem[] = state.drones.map(d => ({ type_id: d.type_id, flag: 87, quantity: d.count }));
      const allItems = [...state.items, ...droneItems];

      const payload = {
        creator_character_id: account.primary_character_id,
        name: data.name,
        description: data.description,
        ship_type_id: state.shipTypeId,
        items: allItems,
        charges: state.charges,
        tags: data.tags,
        is_public: data.isPublic,
      };

      if (data.overwrite && editingFittingId) {
        await fittingApi.updateCustomFitting(editingFittingId, payload);
      } else {
        await fittingApi.saveCustomFitting(payload);
      }
      navigate(sourceUrl || '/fittings');
    } catch (err) {
      console.error('Failed to save fitting:', err);
      alert('Failed to save fitting. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    if (!state.shipDetail || !state.items.length) return;

    const allTypeIds = new Set<number>([state.shipDetail.type_id]);
    for (const item of state.items) allTypeIds.add(item.type_id);
    for (const drone of state.drones) allTypeIds.add(drone.type_id);
    for (const chargeId of Object.values(state.charges)) allTypeIds.add(chargeId);

    const nameMap = await resolveTypeNames(Array.from(allTypeIds));

    const modulesBySlot: Record<string, { name: string; quantity: number; charge?: string }[]> = {};
    for (const [slotType, range] of Object.entries(SLOT_RANGES)) {
      const slotItems = state.items.filter(i => i.flag >= range.start && i.flag <= range.end);
      modulesBySlot[slotType] = slotItems.map(item => ({
        name: nameMap.get(item.type_id) || `Type #${item.type_id}`,
        quantity: 1,
        charge: state.charges[item.flag]
          ? nameMap.get(state.charges[item.flag]) || undefined
          : undefined,
      }));
    }

    const drones = state.drones.map(d => ({
      name: nameMap.get(d.type_id) || `Type #${d.type_id}`,
      quantity: d.count,
    }));

    const chargeQuantities = new Map<number, number>();
    for (const chargeId of Object.values(state.charges)) {
      chargeQuantities.set(chargeId, (chargeQuantities.get(chargeId) || 0) + 1);
    }
    const cargo = Array.from(chargeQuantities.entries()).map(([typeId, count]) => ({
      name: nameMap.get(typeId) || `Type #${typeId}`,
      quantity: count,
    }));

    const shipName = nameMap.get(state.shipDetail.type_id) || state.shipDetail.type_name || 'Unknown';
    const eftText = generateEft(shipName, state.name || 'Untitled', modulesBySlot, drones, cargo);

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(eftText);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = eftText;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* silent */ }
  };

  const hasModules = state.items.length > 0 || state.drones.length > 0;

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto', padding: '1.5rem 1rem' }}>
      <ModuleGate module="character_suite" preview={true}>
        {/* Header */}
        <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
                Fitting Editor
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
                {sourceUrl ? (
                  <Link to={sourceUrl} style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.8rem' }}>← Back to Fitting</Link>
                ) : (
                  <Link to="/fittings" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.8rem' }}>← Fittings</Link>
                )}
              </p>
            </div>
            {account?.characters && account.characters.length > 0 && (
              <select
                value={selectedCharacterId ?? ''}
                onChange={e => setSelectedCharacterId(e.target.value ? Number(e.target.value) : undefined)}
                style={{
                  padding: '0.4rem 0.6rem',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                }}
              >
                <option value="">All Skills V</option>
                {account.characters.map(c => (
                  <option key={c.character_id} value={c.character_id}>
                    {c.character_name}
                  </option>
                ))}
              </select>
            )}
            <select
              value={selectedTarget}
              onChange={e => setSelectedTarget(e.target.value)}
              style={{
                padding: '0.4rem 0.6rem',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              <option value="frigate">vs Frigate</option>
              <option value="destroyer">vs Destroyer</option>
              <option value="cruiser">vs Cruiser</option>
              <option value="battlecruiser">vs Battlecruiser</option>
              <option value="battleship">vs Battleship</option>
              <option value="capital">vs Capital</option>
              <option value="structure">vs Structure</option>
            </select>
            <button
              onClick={() => setSimulationMode(m => !m)}
              title={simulationMode ? 'Simulation: All modules active' : 'Fitting: Passive modules only'}
              style={{
                padding: '0.4rem 0.6rem',
                background: simulationMode ? 'rgba(0,212,255,0.15)' : 'var(--bg-secondary)',
                border: `1px solid ${simulationMode ? 'rgba(0,212,255,0.4)' : 'var(--border-color)'}`,
                borderRadius: '6px',
                color: simulationMode ? '#00d4ff' : 'var(--text-secondary)',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: simulationMode ? 600 : 400,
                whiteSpace: 'nowrap',
              }}
            >
              {simulationMode ? 'SIM' : 'FIT'}
            </button>
            <button
              onClick={() => setIncludeImplants(v => !v)}
              disabled={!selectedCharacterId}
              title={includeImplants ? 'Implants: Active (character implants applied)' : 'Implants: Off (no implant bonuses)'}
              style={{
                padding: '0.4rem 0.6rem',
                background: includeImplants && selectedCharacterId ? 'rgba(168,85,247,0.15)' : 'var(--bg-secondary)',
                border: `1px solid ${includeImplants && selectedCharacterId ? 'rgba(168,85,247,0.4)' : 'var(--border-color)'}`,
                borderRadius: '6px',
                color: includeImplants && selectedCharacterId ? '#a855f7' : 'var(--text-secondary)',
                fontSize: '0.75rem',
                cursor: selectedCharacterId ? 'pointer' : 'not-allowed',
                fontWeight: includeImplants ? 600 : 400,
                whiteSpace: 'nowrap',
                opacity: selectedCharacterId ? 1 : 0.5,
              }}
            >
              {includeImplants ? 'IMP' : 'NO IMP'}
            </button>
            {availableModes.length > 0 && (
              <select
                value={selectedModeId || ''}
                onChange={(e) => setSelectedModeId(Number(e.target.value))}
                style={{
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                }}
              >
                {availableModes.map(mode => (
                  <option key={mode.type_id} value={mode.type_id}>
                    {mode.name.replace(/^.+\s-\s/, '')}
                  </option>
                ))}
              </select>
            )}
            {stats?.active_implants && stats.active_implants.filter(i => i.slot >= 6).length > 0 && (
              <div style={{ fontSize: '0.7rem', color: '#a855f7', whiteSpace: 'nowrap' }}>
                {stats.active_implants.filter(i => i.slot >= 6).length} hardwiring(s) active
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => dispatch({ type: 'CLEAR' })}
              disabled={!state.shipDetail}
              style={{
                padding: '0.5rem 1rem',
                background: 'transparent',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: 'var(--text-secondary)',
                cursor: state.shipDetail ? 'pointer' : 'not-allowed',
                fontSize: '0.85rem',
                opacity: state.shipDetail ? 1 : 0.4,
              }}
            >
              Clear
            </button>
            <button
              onClick={() => setShowImport(true)}
              style={{
                padding: '0.5rem 1rem',
                background: 'transparent',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.85rem',
              }}
            >
              Import
            </button>
            <button
              onClick={handleExport}
              disabled={!state.shipDetail || !hasModules}
              style={{
                padding: '0.5rem 1rem',
                background: 'transparent',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: !state.shipDetail || !hasModules ? 'var(--text-tertiary)' : 'var(--text-secondary)',
                cursor: !state.shipDetail || !hasModules ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                opacity: !state.shipDetail || !hasModules ? 0.4 : 1,
              }}
            >
              {copied ? 'Copied!' : 'Export'}
            </button>
            <button
              onClick={() => dispatch({ type: 'TOGGLE_SAVE_DIALOG' })}
              disabled={!state.shipDetail || !hasModules}
              style={{
                padding: '0.5rem 1rem',
                background: state.shipDetail && hasModules ? '#00d4ff' : 'var(--bg-secondary)',
                border: 'none',
                borderRadius: '6px',
                color: state.shipDetail && hasModules ? '#000' : 'var(--text-tertiary)',
                cursor: state.shipDetail && hasModules ? 'pointer' : 'not-allowed',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              Save
            </button>
          </div>
        </div>

        {/* 3-Column Layout */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '340px 1fr 320px',
          gap: '1rem',
          height: 'calc(100vh - 140px)',
        }}>
          {/* Left: Tree Browser */}
          <div style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <FittingBrowser
              activeTab={state.activeTab}
              onTabChange={tab => dispatch({ type: 'SET_TAB', tab })}
              slotFilter={state.slotFilter}
              onSlotFilterChange={f => dispatch({ type: 'SET_SLOT_FILTER', slotFilter: f })}
              shipTypeId={state.shipTypeId}
              onSelectShip={handleShipSelect}
              onSelectModule={handleSelectModule}
              onAutoFitModule={handleAutoFitModule}
              onSelectCharge={handleSelectCharge}
            />
          </div>

          {/* Center: Ship + Slots + Module Details */}
          <div style={{ overflow: 'auto' }}>
            <ShipDisplay
              shipDetail={state.shipDetail}
              items={state.items}
              charges={state.charges}
              drones={state.drones}
              stats={stats}
              activeSlot={state.pickerMode?.kind === 'module' ? { type: state.pickerMode.slotType, flag: state.pickerMode.flag } : null}
              onSlotClick={handleSlotClick}
              onRemoveModule={flag => dispatch({ type: 'REMOVE_MODULE', flag })}
              onChargeClick={handleChargeClick}
              isWeapon={isWeapon}
              moduleStates={state.moduleStates}
              onModuleStateChange={(flag, ms) => dispatch({ type: 'SET_MODULE_STATE', flag, state: ms })}
              activatableFlags={activatableFlags}
            />
            {isCarrier && <FighterSection fighters={fighters} onFightersChange={setFighters} />}
            <FleetBoostSection boosts={fleetBoosts} onBoostsChange={setFleetBoosts} />
            <ProjectedEffectsSection effects={projectedEffects} onEffectsChange={setProjectedEffects} label="Projected (Self)" color="#ff8800" />
            <ProjectedEffectsSection effects={targetProjected} onEffectsChange={setTargetProjected} label="Projected (Target)" color="#f85149" />
            {stats && stats.module_details && stats.module_details.length > 0 && (
              <div style={{ marginTop: '0.75rem' }}>
                <EnrichedModuleList stats={stats} />
              </div>
            )}
          </div>

          {/* Right: Stats */}
          <div style={{ overflow: 'auto' }}>
            <CollapsibleStats stats={stats} loading={statsLoading} hasShip={!!state.shipDetail} />
          </div>
        </div>

        {/* Save Dialog */}
        <FittingNameDialog
          open={state.showSaveDialog}
          onClose={() => dispatch({ type: 'TOGGLE_SAVE_DIALOG' })}
          onSave={handleSave}
          initialName={state.name}
          saving={saving}
          editingFittingId={editingFittingId}
        />

        {/* Import Dialog */}
        <ImportDialog open={showImport} onClose={() => setShowImport(false)} />
      </ModuleGate>
    </div>
  );
}
