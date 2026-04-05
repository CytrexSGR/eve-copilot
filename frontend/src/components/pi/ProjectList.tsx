import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ProductionChainView } from './ProductionChainView';
import { SollSummaryCard } from './SollSummaryCard';
import {
  Eye,
  Pause,
  Play,
  Check,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Loader2,
  FolderOpen,
} from 'lucide-react';
import {
  getProjects,
  getProjectDetail,
  updateProjectStatus,
  deleteProject,
  syncProjectTracking,
} from '../../api/pi';
import type { PIProject, PIProjectDetail } from '../../api/pi';

interface ProjectListProps {
  characterId?: number;
  onProjectDeleted?: () => void;
}

const STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  planning: { bg: 'rgba(107, 114, 128, 0.2)', color: '#9ca3af', label: 'Planning' },
  active: { bg: 'rgba(63, 185, 80, 0.2)', color: '#3fb950', label: 'Active' },
  paused: { bg: 'rgba(210, 153, 34, 0.2)', color: '#d29922', label: 'Paused' },
  completed: { bg: 'rgba(88, 166, 255, 0.2)', color: '#58a6ff', label: 'Completed' },
};

function formatIsk(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

export function ProjectList({ characterId, onProjectDeleted }: ProjectListProps) {
  const queryClient = useQueryClient();
  const [expandedProjectId, setExpandedProjectId] = useState<number | null>(null);
  const [syncingProjectId, setSyncingProjectId] = useState<number | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<number | null>(null);

  // Fetch projects
  const {
    data: projects,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['pi-projects', characterId],
    queryFn: () => getProjects({ character_id: characterId }),
  });

  // Fetch project detail when expanded
  const { data: projectDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['pi-project-detail', expandedProjectId],
    queryFn: () => (expandedProjectId ? getProjectDetail(expandedProjectId) : null),
    enabled: expandedProjectId !== null,
  });

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ projectId, status }: { projectId: number; status: string }) =>
      updateProjectStatus(projectId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi-projects'] });
      queryClient.invalidateQueries({ queryKey: ['pi-project-detail'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi-projects'] });
      setDeletingProjectId(null);
      onProjectDeleted?.();
    },
    onError: () => {
      setDeletingProjectId(null);
    },
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: syncProjectTracking,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi-projects'] });
      queryClient.invalidateQueries({ queryKey: ['pi-project-detail'] });
      setSyncingProjectId(null);
    },
    onError: () => {
      setSyncingProjectId(null);
    },
  });

  const handleViewDetails = (projectId: number) => {
    setExpandedProjectId(expandedProjectId === projectId ? null : projectId);
  };

  const handleTogglePause = (project: PIProject) => {
    const newStatus = project.status === 'paused' ? 'active' : 'paused';
    updateStatusMutation.mutate({ projectId: project.project_id, status: newStatus });
  };

  const handleComplete = (projectId: number) => {
    updateStatusMutation.mutate({ projectId, status: 'completed' });
  };

  const handleSync = (projectId: number) => {
    setSyncingProjectId(projectId);
    syncMutation.mutate(projectId);
  };

  const handleDelete = (projectId: number) => {
    if (window.confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      setDeletingProjectId(projectId);
      deleteMutation.mutate(projectId);
    }
  };

  if (isLoading) {
    return (
      <div className="project-list">
        <div className="loading-inline">Loading projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="project-list">
        <div className="error-state">
          Failed to load projects. Please try again.
        </div>
      </div>
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <div className="project-list">
        <div className="empty-state">
          <FolderOpen size={48} />
          <h3>No Active Projects</h3>
          <p className="empty-hint">
            Create a new project from the Recommendations tab to start tracking your PI operations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="project-list">
      <div className="project-list-header">
        <h3>Active Projects</h3>
        <span className="project-count">{projects.length} project{projects.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="projects-container">
        {projects.map((project) => (
          <ProjectCard
            key={project.project_id}
            project={project}
            isExpanded={expandedProjectId === project.project_id}
            projectDetail={expandedProjectId === project.project_id ? projectDetail : undefined}
            detailLoading={expandedProjectId === project.project_id && detailLoading}
            isSyncing={syncingProjectId === project.project_id}
            isDeleting={deletingProjectId === project.project_id}
            isUpdating={updateStatusMutation.isPending}
            onViewDetails={() => handleViewDetails(project.project_id)}
            onTogglePause={() => handleTogglePause(project)}
            onComplete={() => handleComplete(project.project_id)}
            onSync={() => handleSync(project.project_id)}
            onDelete={() => handleDelete(project.project_id)}
          />
        ))}
      </div>
    </div>
  );
}

interface ProjectCardProps {
  project: PIProject;
  isExpanded: boolean;
  projectDetail?: PIProjectDetail | null;
  detailLoading: boolean;
  isSyncing: boolean;
  isDeleting: boolean;
  isUpdating: boolean;
  onViewDetails: () => void;
  onTogglePause: () => void;
  onComplete: () => void;
  onSync: () => void;
  onDelete: () => void;
}

function ProjectCard({
  project,
  isExpanded,
  projectDetail,
  detailLoading,
  isSyncing,
  isDeleting,
  isUpdating,
  onViewDetails,
  onTogglePause,
  onComplete,
  onSync,
  onDelete,
}: ProjectCardProps) {
  const statusConfig = STATUS_COLORS[project.status] || STATUS_COLORS.planning;

  // Calculate variance and progress from detail if available
  const variance = projectDetail?.variance_percent ?? 0;
  const progress = projectDetail
    ? projectDetail.total_actual_output > 0 && projectDetail.total_expected_output > 0
      ? Math.min((projectDetail.total_actual_output / projectDetail.total_expected_output) * 100, 100)
      : 0
    : 0;
  const expiringExtractors = projectDetail?.expiring_extractors ?? 0;

  return (
    <div className={`project-card ${isExpanded ? 'expanded' : ''}`}>
      <div className="project-card-header">
        <div className="project-title-row">
          <div className="project-name-section">
            <span className="project-name">{project.name}</span>
            <span
              className="status-badge"
              style={{
                backgroundColor: statusConfig.bg,
                color: statusConfig.color,
              }}
            >
              {statusConfig.label}
            </span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="project-progress-section">
          <div className="progress-label">
            <span>Progress</span>
            <span className="progress-percent">{progress.toFixed(0)}%</span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${progress}%`,
                backgroundColor: progress >= 90 ? '#3fb950' : progress >= 50 ? '#58a6ff' : '#d29922',
              }}
            />
          </div>
        </div>

        {/* Output & Variance */}
        {projectDetail && (
          <div className="project-metrics">
            <div className="metric">
              <span className="metric-label">Output</span>
              <span className="metric-value">
                {formatIsk(projectDetail.total_actual_output)}/day
              </span>
              <span className="metric-target">
                (target: {formatIsk(projectDetail.total_expected_output)})
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Variance</span>
              <span className={`metric-value ${variance >= 0 ? 'positive' : 'negative'}`}>
                {variance >= 0 ? '+' : ''}{variance.toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* Expiring Extractors Warning */}
        {expiringExtractors > 0 && (
          <div className="extractor-warning">
            <AlertTriangle size={16} />
            <span>{expiringExtractors} extractor{expiringExtractors !== 1 ? 's' : ''} expiring soon</span>
          </div>
        )}

        {/* Actions */}
        <div className="project-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={onViewDetails}
            title="View Details"
          >
            <Eye size={14} />
            View Details
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onTogglePause}
            disabled={isUpdating || project.status === 'completed'}
            title={project.status === 'paused' ? 'Resume' : 'Pause'}
          >
            {project.status === 'paused' ? <Play size={14} /> : <Pause size={14} />}
            {project.status === 'paused' ? 'Resume' : 'Pause'}
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onComplete}
            disabled={isUpdating || project.status === 'completed'}
            title="Complete"
          >
            <Check size={14} />
            Complete
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onSync}
            disabled={isSyncing}
            title="Sync with ESI"
          >
            {isSyncing ? (
              <Loader2 size={14} className="spin" />
            ) : (
              <RefreshCw size={14} />
            )}
            Sync
          </button>

          <button
            className="btn btn-danger btn-sm"
            onClick={onDelete}
            disabled={isDeleting}
            title="Delete"
          >
            {isDeleting ? (
              <Loader2 size={14} className="spin" />
            ) : (
              <Trash2 size={14} />
            )}
            Delete
          </button>
        </div>
      </div>

      {/* Expanded Detail */}
      {isExpanded && (
        <div className="project-detail">
          {detailLoading ? (
            <div className="loading-inline">Loading project details...</div>
          ) : projectDetail ? (
            <div className="detail-content">
              <div className="detail-section">
                <h4>Project Information</h4>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">Strategy</span>
                    <span className="detail-value">{project.strategy}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Created</span>
                    <span className="detail-value">
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Last Updated</span>
                    <span className="detail-value">
                      {new Date(project.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Colonies</span>
                    <span className="detail-value">
                      {projectDetail.colonies.length} assigned
                    </span>
                  </div>
                </div>
              </div>

              {/* SOLL Summary */}
              <SollSummaryCard projectId={project.project_id} />

              {projectDetail.colonies.length > 0 && (
                <div className="detail-section">
                  <h4>Assigned Colonies</h4>
                  <div className="colonies-list">
                    {projectDetail.colonies.map((colony) => (
                      <div key={colony.id} className="colony-item">
                        <div className="colony-item-header">
                          <span className="colony-role">{colony.role || 'Production'}</span>
                          {colony.actual_output_per_hour !== undefined &&
                            colony.expected_output_per_hour !== undefined && (
                              <span
                                className={`colony-variance ${
                                  colony.actual_output_per_hour >= colony.expected_output_per_hour
                                    ? 'positive'
                                    : 'negative'
                                }`}
                              >
                                {colony.actual_output_per_hour >= colony.expected_output_per_hour ? '+' : ''}
                                {(
                                  ((colony.actual_output_per_hour - colony.expected_output_per_hour) /
                                    colony.expected_output_per_hour) *
                                  100
                                ).toFixed(0)}
                                %
                              </span>
                            )}
                        </div>
                        <div className="colony-item-stats">
                          {colony.expected_output_per_hour !== undefined && (
                            <span>
                              Output: {formatIsk(colony.actual_output_per_hour ?? 0)}/hr
                              (target: {formatIsk(colony.expected_output_per_hour)}/hr)
                            </span>
                          )}
                        </div>
                        {colony.last_sync && (
                          <div className="colony-item-sync">
                            Last sync: {new Date(colony.last_sync).toLocaleString()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Production Chain View */}
              {project.target_product_type_id && (
                <div className="detail-section">
                  <ProductionChainView
                    typeId={project.target_product_type_id}
                    title={project.name.replace(' Production', '')}
                    projectId={project.project_id}
                    colonies={projectDetail?.colonies || []}
                  />
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">No details available</div>
          )}
        </div>
      )}
    </div>
  );
}
