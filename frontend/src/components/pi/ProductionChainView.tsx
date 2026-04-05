// frontend/src/components/pi/ProductionChainView.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Wand2 } from 'lucide-react';
import {
  getProductionChain,
  getProjectAssignments,
  updateMaterialAssignment,
  autoAssignMaterials,
} from '../../api/pi';
import type { PIProjectColony, PIMaterialAssignment } from '../../api/pi';
import { flattenChainByTier, getRequiredPlanetTypes } from '../../utils/pi';
import { TIER_COLORS, TIER_LABELS } from '../../constants/pi';
import { PlanetTypeChip } from './PlanetTypeChip';
import { ColonyAssignmentChip } from './ColonyAssignmentChip';

interface ProductionChainViewProps {
  typeId: number;
  title?: string;
  projectId?: number;
  colonies?: PIProjectColony[];
}

export function ProductionChainView({
  typeId,
  title,
  projectId,
  colonies = []
}: ProductionChainViewProps) {
  const queryClient = useQueryClient();

  // Fetch chain data
  const {
    data: chainData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['pi-chain', typeId],
    queryFn: () => getProductionChain(typeId),
    enabled: typeId > 0,
  });

  // Fetch assignments if projectId provided
  const { data: assignments } = useQuery({
    queryKey: ['pi-assignments', projectId],
    queryFn: () => getProjectAssignments(projectId!),
    enabled: !!projectId,
  });

  // Mutation for updating assignment
  const updateAssignment = useMutation({
    mutationFn: ({ materialTypeId, colonyId }: { materialTypeId: number; colonyId: number | null }) =>
      updateMaterialAssignment(projectId!, materialTypeId, colonyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi-assignments', projectId] });
    },
  });

  // Mutation for auto-assign
  const autoAssign = useMutation({
    mutationFn: () => autoAssignMaterials(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi-assignments', projectId] });
    },
  });

  if (isLoading) {
    return (
      <div className="production-chain-view">
        <div className="chain-loading">
          <Loader2 size={20} className="spin" />
          <span>Loading production chain...</span>
        </div>
      </div>
    );
  }

  if (error || !chainData) {
    return (
      <div className="production-chain-view">
        <div className="chain-error">Failed to load production chain</div>
      </div>
    );
  }

  const tierMap = flattenChainByTier(chainData);
  const requiredPlanets = getRequiredPlanetTypes(tierMap);

  // Create assignment lookup by material_type_id
  const assignmentMap = new Map<number, PIMaterialAssignment>();
  assignments?.forEach(a => assignmentMap.set(a.material_type_id, a));

  const handleAssign = (materialTypeId: number, colonyId: number | null) => {
    updateAssignment.mutate({ materialTypeId, colonyId });
  };

  // Only show tiers that have materials
  const activeTiers = [0, 1, 2, 3, 4].filter(
    (tier) => tierMap[tier] && tierMap[tier].length > 0
  );

  return (
    <div className="production-chain-view">
      {/* Header with planet requirements */}
      <div className="chain-summary">
        <div className="chain-title">
          <span className="chain-title-label">Production Chain:</span>
          <span className="chain-title-name">{title || chainData.type_name}</span>
        </div>
        <div className="chain-header-actions">
          <div className="chain-planets">
            <span className="planets-label">Required Planets:</span>
            <div className="planet-chips">
              {requiredPlanets.map((planet) => (
                <PlanetTypeChip key={planet} type={planet} />
              ))}
            </div>
          </div>
          {projectId && (
            <button
              className="auto-assign-btn"
              onClick={() => autoAssign.mutate()}
              disabled={autoAssign.isPending}
            >
              {autoAssign.isPending ? (
                <Loader2 size={14} className="spin" />
              ) : (
                <Wand2 size={14} />
              )}
              <span>Auto-Assign</span>
            </button>
          )}
        </div>
      </div>

      {/* Tier columns */}
      <div className="chain-columns">
        {activeTiers.map((tier) => (
          <div key={tier} className="tier-column">
            <div
              className="tier-header"
              style={{ borderBottomColor: TIER_COLORS[tier] }}
            >
              <span
                className="tier-badge"
                style={{ backgroundColor: TIER_COLORS[tier] }}
              >
                P{tier}
              </span>
              <span className="tier-label">{TIER_LABELS[tier]}</span>
            </div>
            <div className="tier-materials">
              {tierMap[tier].map((material) => (
                <div
                  key={material.type_id}
                  className="chain-material"
                  style={{ borderLeftColor: TIER_COLORS[tier] }}
                >
                  <div className="material-name">{material.type_name}</div>
                  <div className="material-quantity">
                    x{material.quantity_needed.toFixed(1)}/run
                  </div>
                  {material.planet_types && material.planet_types.length > 0 && (
                    <div className="material-planets">
                      {material.planet_types.slice(0, 2).map((planet) => (
                        <PlanetTypeChip key={planet} type={planet} size="small" />
                      ))}
                      {material.planet_types.length > 2 && (
                        <span className="more-planets">
                          +{material.planet_types.length - 2}
                        </span>
                      )}
                    </div>
                  )}
                  {projectId && (
                    <ColonyAssignmentChip
                      assignment={assignmentMap.get(material.type_id) || null}
                      availableColonies={colonies}
                      materialTypeId={material.type_id}
                      materialName={material.type_name}
                      tier={tier}
                      validPlanetTypes={tier === 0 ? material.planet_types : undefined}
                      onAssign={(colonyId) => handleAssign(material.type_id, colonyId)}
                      disabled={updateAssignment.isPending}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
