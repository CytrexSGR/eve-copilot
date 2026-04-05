import { useState } from 'react'
import { X, Save } from 'lucide-react'

interface FittingNameDialogProps {
  open: boolean
  onClose: () => void
  onSave: (data: { name: string; description: string; tags: string[]; isPublic: boolean }) => void
  initialName?: string
  saving?: boolean
}

const AVAILABLE_TAGS = ['PvP', 'PvE', 'Fleet', 'Solo', 'Industry', 'Exploration', 'Abyssal']

export function FittingNameDialog({ open, onClose, onSave, initialName = '', saving }: FittingNameDialogProps) {
  const [name, setName] = useState(initialName)
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [isPublic, setIsPublic] = useState(false)

  if (!open) return null

  function toggleTag(tag: string) {
    setTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
  }

  function handleSave() {
    if (!name.trim()) return
    onSave({ name: name.trim(), description: description.trim(), tags, isPublic })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Save Fitting</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My awesome fitting..."
              className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              rows={2}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-2 block">Tags</label>
            <div className="flex gap-1.5 flex-wrap">
              {AVAILABLE_TAGS.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                    tags.includes(tag)
                      ? 'bg-primary/20 text-primary border border-primary/40'
                      : 'bg-background text-muted-foreground border border-border hover:border-primary/30'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Public toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Share publicly</p>
              <p className="text-xs text-muted-foreground">Other players can find and copy this fitting</p>
            </div>
            <button
              onClick={() => setIsPublic(!isPublic)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                isPublic ? 'bg-primary' : 'bg-border'
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                  isPublic ? 'translate-x-4.5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-6">
          <button
            onClick={onClose}
            className="flex-1 h-9 rounded-md border border-border text-sm font-medium hover:bg-accent transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saving}
            className="flex-1 h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
