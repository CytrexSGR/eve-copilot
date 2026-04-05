import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, X, ChevronRight, Plus, Loader2 } from 'lucide-react';
import {
  getOptimizationRecommendations,
  getProductionChain,
  createProject,
} from '../../api/pi';
import type { PICharacterSlots, PIRecommendation, PIChainNode } from '../../api/pi';
import { PlanetTypeChip } from './PlanetTypeChip';

interface RecommendationListProps {
  characterSlots: PICharacterSlots[];
  systemId: number;
  mode: 'market_driven' | 'vertical';
  onProjectCreated?: () => void;
}

const TIER_COLORS: Record<number, string> = {
  1: '#22c55e',
  2: '#3b82f6',
  3: '#a855f7',
  4: '#f97316',
};

function formatIsk(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

export function RecommendationList({
  characterSlots,
  systemId,
  mode,
  onProjectCreated,
}: RecommendationListProps) {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [creatingProjectId, setCreatingProjectId] = useState<number | null>(null);

  // Get character IDs from slots
  const characterIds = characterSlots.map((slot) => slot.character_id);

  // Fetch recommendations
  const {
    data: recommendations,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['pi-recommendations', characterIds, systemId, mode],
    queryFn: () =>
      getOptimizationRecommendations({
        character_ids: characterIds,
        system_id: systemId,
        mode: mode,
      }),
    enabled: characterIds.length > 0,
  });

  // Fetch production chain for expanded item
  const { data: chainData, isLoading: chainLoading } = useQuery({
    queryKey: ['pi-chain', expandedId],
    queryFn: () => (expandedId ? getProductionChain(expandedId) : null),
    enabled: expandedId !== null,
  });

  const [mutationError, setMutationError] = useState<string | null>(null);

  // Create project mutation
  const createProjectMutation = useMutation({
    mutationFn: (recommendation: PIRecommendation) => {
      // Use the first character with free slots
      const availableChar = characterSlots.find((slot) => slot.free_planets > 0);
      if (!availableChar) {
        throw new Error('No character with free planet slots available');
      }

      return createProject({
        character_id: availableChar.character_id,
        name: `${recommendation.type_name} Production`,
        strategy: mode,
        target_product_type_id: recommendation.type_id,
        target_profit_per_hour: recommendation.profit_per_hour,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi-projects'] });
      queryClient.invalidateQueries({ queryKey: ['pi-recommendations'] });
      setCreatingProjectId(null);
      setMutationError(null);
      onProjectCreated?.();
    },
    onError: (err: Error) => {
      setCreatingProjectId(null);
      setMutationError(err.message || 'Failed to create project');
      setTimeout(() => setMutationError(null), 5000);
    },
  });

  const handleViewChain = (typeId: number) => {
    setExpandedId(expandedId === typeId ? null : typeId);
  };

  const handleCreateProject = (recommendation: PIRecommendation) => {
    if (!characterSlots || characterSlots.length === 0) {
      setMutationError('Character slots not loaded yet. Please wait and try again.');
      return;
    }

    setCreatingProjectId(recommendation.type_id);
    createProjectMutation.mutate(recommendation);
  };

  if (isLoading) {
    return (
      <div className="recommendation-list">
        <div className="loading-inline">Loading recommendations...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendation-list">
        <div className="error-state">
          Failed to load recommendations. Please try again.
        </div>
      </div>
    );
  }

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="recommendation-list">
        <div className="empty-state">
          <p>No recommendations available</p>
          <span className="empty-hint">
            Try adjusting your filters or adding more characters
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="recommendation-list">
      {mutationError && (
        <div className="error-banner">
          <X size={16} onClick={() => setMutationError(null)} style={{ cursor: 'pointer' }} />
          <span>{mutationError}</span>
        </div>
      )}
      {recommendations.map((rec, index) => (
        <div key={rec.type_id} className="recommendation-item">
          <div className="recommendation-header">
            <div className="recommendation-rank">{index + 1}.</div>
            <div className="recommendation-main">
              <div className="recommendation-title">
                <span className="recommendation-name">{rec.type_name}</span>
                <span
                  className="tier-badge"
                  style={{ backgroundColor: TIER_COLORS[rec.tier] || '#6b7280' }}
                >
                  P{rec.tier}
                </span>
              </div>
              <div className="recommendation-stats">
                <span className="stat-roi">ROI: {rec.roi_percent.toFixed(0)}%</span>
                <span className="stat-profit positive">
                  +{formatIsk(rec.profit_per_hour * 24)}/day
                </span>
              </div>
            </div>
          </div>

          <div className="recommendation-planets">
            <span className="planets-label">Needs:</span>
            <div className="planet-chips">
              {rec.required_planet_types.map((type, i) => (
                <PlanetTypeChip key={`${type}-${i}`} type={type} />
              ))}
            </div>
          </div>

          <div className="recommendation-feasibility">
            {rec.feasible ? (
              <div className="feasibility-status feasible">
                <Check size={16} />
                <span>Feasible</span>
              </div>
            ) : (
              <div className="feasibility-status not-feasible">
                <X size={16} />
                <span>{rec.reason || 'Not feasible with current slots'}</span>
              </div>
            )}
          </div>

          <div className="recommendation-actions">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => handleViewChain(rec.type_id)}
            >
              <ChevronRight
                size={14}
                className={expandedId === rec.type_id ? 'rotated' : ''}
              />
              View Chain
            </button>
            <button
              className={`btn btn-sm ${rec.feasible ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => handleCreateProject(rec)}
              disabled={creatingProjectId === rec.type_id}
              title={!rec.feasible ? 'Create project for planning (missing planet types)' : 'Create project'}
            >
              {creatingProjectId === rec.type_id ? (
                <Loader2 size={14} className="spin" />
              ) : (
                <Plus size={14} />
              )}
              {rec.feasible ? 'Create Project' : 'Plan Project'}
            </button>
          </div>

          {expandedId === rec.type_id && (
            <div className="recommendation-chain">
              {chainLoading ? (
                <div className="chain-loading">Loading production chain...</div>
              ) : chainData ? (
                <div className="production-chain">
                  <h4>Production Chain</h4>
                  <ChainTree node={chainData} />
                </div>
              ) : null}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

interface ChainTreeProps {
  node: PIChainNode;
  depth?: number;
}

function ChainTree({ node, depth = 0 }: ChainTreeProps) {
  return (
    <div className="chain-node" style={{ marginLeft: depth * 24 }}>
      <div className="chain-item">
        <span
          className="tier-badge"
          style={{ backgroundColor: TIER_COLORS[node.tier] || '#6b7280' }}
        >
          P{node.tier}
        </span>
        <span className="chain-name">{node.type_name}</span>
        <span className="chain-qty">x{node.quantity_needed.toFixed(1)}</span>
      </div>
      {node.children?.map((child, i) => (
        <ChainTree key={`${child.type_id}-${i}`} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}
