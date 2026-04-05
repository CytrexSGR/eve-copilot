import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { piApi, type PIProjectListItem, type PIProjectStatus, type PIProjectCreate } from '@/api/pi'
import { useCharacters } from '@/hooks/useCharacters'
import { cn } from '@/lib/utils'
import {
  ArrowLeft,
  Plus,
  Trash2,
  Factory,
  Search,
  X,
  Loader2,
} from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Status badge colors
 */
const STATUS_CONFIG: Record<PIProjectStatus, { label: string; color: string; bg: string }> = {
  active: { label: 'Active', color: 'text-green-400', bg: 'bg-green-500/20' },
  planning: { label: 'Planning', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  paused: { label: 'Paused', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  completed: { label: 'Completed', color: 'text-gray-400', bg: 'bg-gray-500/20' },
}

/**
 * Tier badge colors
 */
const TIER_CONFIG: Record<number, { label: string; color: string; bg: string }> = {
  0: { label: 'P0', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  1: { label: 'P1', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  2: { label: 'P2', color: 'text-green-400', bg: 'bg-green-500/20' },
  3: { label: 'P3', color: 'text-purple-400', bg: 'bg-purple-500/20' },
  4: { label: 'P4', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
}

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Create Project Modal
 */
function CreateProjectModal({
  isOpen,
  onClose,
  onCreated,
}: {
  isOpen: boolean
  onClose: () => void
  onCreated: () => void
}) {
  const queryClient = useQueryClient()
  const { data: charactersData } = useCharacters()
  const characters = charactersData?.characters ?? []

  const [selectedCharacterId, setSelectedCharacterId] = useState<number | null>(
    characters[0]?.character_id ?? null
  )
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProduct, setSelectedProduct] = useState<{
    type_id: number
    name: string
    tier: number
  } | null>(null)
  const [projectName, setProjectName] = useState('')

  // Search schematics
  const { data: searchResults } = useQuery({
    queryKey: ['pi', 'search', searchQuery],
    queryFn: () => piApi.searchSchematics(searchQuery),
    enabled: searchQuery.length >= 2,
    staleTime: 60 * 1000,
  })

  // Get make-or-buy for selected product
  const { data: makeOrBuy } = useQuery({
    queryKey: ['pi', 'make-or-buy', selectedProduct?.type_id],
    queryFn: () => piApi.analyzeMakeOrBuy(selectedProduct!.type_id),
    enabled: !!selectedProduct,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: PIProjectCreate) => piApi.createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'projects'] })
      onCreated()
      onClose()
      resetForm()
    },
  })

  const resetForm = () => {
    setSearchQuery('')
    setSelectedProduct(null)
    setProjectName('')
  }

  const handleSelectProduct = (item: { output_type_id: number; schematic_name: string; tier: number }) => {
    setSelectedProduct({
      type_id: item.output_type_id,
      name: item.schematic_name,
      tier: item.tier,
    })
    setProjectName(`${item.schematic_name} Production`)
    setSearchQuery('')
  }

  const handleCreate = () => {
    if (!selectedCharacterId || !selectedProduct) return

    createMutation.mutate({
      character_id: selectedCharacterId,
      name: projectName || `${selectedProduct.name} Production`,
      target_product_type_id: selectedProduct.type_id,
    })
  }

  if (!isOpen) return null

  // Update character selection when characters load
  if (characters.length > 0 && !selectedCharacterId) {
    setSelectedCharacterId(characters[0].character_id)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Create PI Project</CardTitle>
          <button onClick={onClose} className="p-1 hover:bg-secondary rounded">
            <X className="h-5 w-5" />
          </button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Character Select */}
          <div>
            <label className="text-sm text-muted-foreground">Character</label>
            <select
              value={selectedCharacterId ?? ''}
              onChange={(e) => setSelectedCharacterId(Number(e.target.value))}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-secondary/50 border border-border"
            >
              {characters.map((char) => (
                <option key={char.character_id} value={char.character_id}>
                  {char.character_name}
                </option>
              ))}
            </select>
          </div>

          {/* Product Search */}
          <div>
            <label className="text-sm text-muted-foreground">Target Product</label>
            {!selectedProduct ? (
              <div className="relative mt-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search PI products..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
                {searchResults && searchResults.length > 0 && searchQuery.length >= 2 && (
                  <div className="absolute z-10 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    {searchResults.map((item) => {
                      const tierConfig = TIER_CONFIG[item.tier] || TIER_CONFIG[1]
                      return (
                        <button
                          key={item.schematic_id}
                          onClick={() => handleSelectProduct(item)}
                          className="w-full flex items-center gap-2 px-3 py-2 hover:bg-secondary/50 text-left"
                        >
                          <img
                            src={getItemIconUrl(item.output_type_id)}
                            alt=""
                            className="w-6 h-6 rounded"
                            onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                          <span className="flex-1 truncate">{item.schematic_name}</span>
                          <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
                            {tierConfig.label}
                          </Badge>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-1 p-3 rounded-lg bg-secondary/30 border border-border">
                <div className="flex items-center gap-3">
                  <img
                    src={getItemIconUrl(selectedProduct.type_id)}
                    alt=""
                    className="w-10 h-10 rounded"
                    onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{selectedProduct.name}</span>
                      <Badge className={cn('text-xs', TIER_CONFIG[selectedProduct.tier]?.bg, TIER_CONFIG[selectedProduct.tier]?.color)}>
                        {TIER_CONFIG[selectedProduct.tier]?.label}
                      </Badge>
                      {makeOrBuy && (
                        <Badge className={cn('text-xs', makeOrBuy.recommendation === 'MAKE' ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400')}>
                          {makeOrBuy.recommendation}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedProduct(null)}
                    className="p-1 hover:bg-secondary rounded"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Project Name */}
          {selectedProduct && (
            <div>
              <label className="text-sm text-muted-foreground">Project Name</label>
              <Input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder={`${selectedProduct.name} Production`}
                className="mt-1"
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={!selectedCharacterId || !selectedProduct || createMutation.isPending}
              className="px-4 py-2 rounded-lg text-sm bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Create Project'
              )}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Main PI Projects Page
 */
export function PIProjects() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState<PIProjectStatus | ''>('')

  // Fetch projects
  const { data: projects, isLoading } = useQuery({
    queryKey: ['pi', 'projects', statusFilter],
    queryFn: () => piApi.getProjects(undefined, statusFilter || undefined),
    staleTime: 30 * 1000,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (projectId: number) => piApi.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'projects'] })
    },
  })

  const handleDelete = (project: PIProjectListItem) => {
    if (confirm(`Delete project "${project.name}"?`)) {
      deleteMutation.mutate(project.project_id)
    }
  }

  return (
    <div>
      <Header title="PI Projects" subtitle="Manage production projects" />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Planetary Industry
        </Link>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
          >
            <Plus className="h-4 w-4" />
            New Project
          </button>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as PIProjectStatus | '')}
            className="px-3 py-2 rounded-lg bg-secondary/50 border border-border text-sm"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="planning">Planning</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        {/* Projects Table */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-6 space-y-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : !projects || projects.length === 0 ? (
              <div className="py-12 text-center">
                <Factory className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No Projects</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first PI project to get started.
                </p>
                <button
                  onClick={() => setIsCreateModalOpen(true)}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
                >
                  Create Project
                </button>
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">Name</th>
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">Product</th>
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">Status</th>
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">Assigned</th>
                    <th className="text-right p-4 text-sm font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => {
                    const statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.planning
                    const tierConfig = project.target_tier !== null
                      ? TIER_CONFIG[project.target_tier]
                      : null

                    return (
                      <tr
                        key={project.project_id}
                        className="border-b border-border hover:bg-secondary/30 transition-colors"
                      >
                        <td className="p-4">
                          <div className="font-medium">{project.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {project.character_name}
                          </div>
                        </td>
                        <td className="p-4">
                          {project.target_product_name ? (
                            <div className="flex items-center gap-2">
                              {project.target_product_type_id && (
                                <img
                                  src={getItemIconUrl(project.target_product_type_id)}
                                  alt=""
                                  className="w-6 h-6 rounded"
                                  onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                                    e.currentTarget.style.display = 'none'
                                  }}
                                />
                              )}
                              <span className="truncate">{project.target_product_name}</span>
                              {tierConfig && (
                                <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
                                  {tierConfig.label}
                                </Badge>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="p-4">
                          <Badge className={cn('text-xs', statusConfig.bg, statusConfig.color)}>
                            {statusConfig.label}
                          </Badge>
                        </td>
                        <td className="p-4">
                          <span className={cn(
                            'font-mono text-sm',
                            project.assigned_count === project.total_materials && project.total_materials > 0
                              ? 'text-green-400'
                              : project.assigned_count > 0
                              ? 'text-yellow-400'
                              : 'text-muted-foreground'
                          )}>
                            {project.assigned_count}/{project.total_materials}
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => navigate(`/pi/projects/${project.project_id}`)}
                              className="px-3 py-1 rounded text-sm bg-secondary hover:bg-secondary/80"
                            >
                              View
                            </button>
                            <button
                              onClick={() => handleDelete(project)}
                              disabled={deleteMutation.isPending}
                              className="p-2 rounded text-red-400 hover:bg-red-500/20"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Modal */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={() => {}}
      />
    </div>
  )
}
