import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { parseEft, blocksToFittingItems } from '../../lib/eft-parser';
import { sdeApi } from '../../services/api/fittings';
import { getTypeIconUrl } from '../../types/fittings';

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
}

interface ParsedModule {
  name: string;
  quantity: number;
  ammo?: string;
}

interface ResolvedData {
  shipName: string;
  shipTypeId: number;
  fittingName: string;
  blocks: ParsedModule[][];
  nameToTypeId: Map<string, number>;
  unresolvedNames: string[];
}

export function ImportDialog({ open, onClose }: ImportDialogProps) {
  const navigate = useNavigate();
  const [step, setStep] = useState<'paste' | 'preview' | 'error'>('paste');
  const [eftText, setEftText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resolved, setResolved] = useState<ResolvedData | null>(null);

  if (!open) return null;

  const handleParse = async () => {
    setLoading(true);
    setError('');

    try {
      const parsed = parseEft(eftText);
      if (!parsed) {
        setError('Invalid EFT format. Please check your input.');
        setStep('error');
        setLoading(false);
        return;
      }

      // Collect all unique names
      const allNames = new Set<string>([parsed.shipName]);
      for (const block of parsed.blocks) {
        for (const mod of block) {
          allNames.add(mod.name);
          if (mod.ammo) allNames.add(mod.ammo);
        }
      }

      // Resolve type names
      const resolveResponse = await sdeApi.resolveTypeNames(Array.from(allNames));

      // Build name-to-typeId map (case-insensitive)
      const nameToTypeId = new Map<string, number>();
      for (const item of resolveResponse) {
        nameToTypeId.set(item.type_name, item.type_id);
        nameToTypeId.set(item.type_name.toLowerCase(), item.type_id);
      }

      // Check ship resolves
      const shipTypeId = nameToTypeId.get(parsed.shipName) || nameToTypeId.get(parsed.shipName.toLowerCase());
      if (!shipTypeId) {
        setError(`Ship "${parsed.shipName}" not found in database.`);
        setStep('error');
        setLoading(false);
        return;
      }

      // Identify unresolved module names
      const unresolvedNames: string[] = [];
      for (const block of parsed.blocks) {
        for (const mod of block) {
          const resolvedMod = nameToTypeId.get(mod.name) || nameToTypeId.get(mod.name.toLowerCase());
          if (!resolvedMod) {
            unresolvedNames.push(mod.name);
          }
        }
      }

      setResolved({
        shipName: parsed.shipName,
        shipTypeId,
        fittingName: parsed.fittingName,
        blocks: parsed.blocks,
        nameToTypeId,
        unresolvedNames,
      });
      setStep('preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse fitting');
      setStep('error');
    } finally {
      setLoading(false);
    }
  };

  const handleImport = () => {
    if (!resolved) return;

    const { items, charges, cargo: _cargo } = blocksToFittingItems(resolved.blocks, resolved.nameToTypeId);

    navigate('/fittings/new', {
      state: {
        shipTypeId: resolved.shipTypeId,
        items,
        charges,
        name: resolved.fittingName,
      },
    });

    onClose();
  };

  const handleBack = () => {
    setStep('paste');
    setError('');
    setResolved(null);
  };

  const handleClose = () => {
    setStep('paste');
    setError('');
    setResolved(null);
    setEftText('');
    onClose();
  };

  const placeholderText = `[Raven, PvE Mission Runner]
Cruise Missile Launcher II, Scourge Fury Cruise Missile
Cruise Missile Launcher II, Scourge Fury Cruise Missile

Large Shield Extender II
Pith X-Type Shield Boost Amplifier

Ballistic Control System II
Ballistic Control System II`;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={handleClose}
    >
      <div
        style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '1.5rem',
          maxWidth: 560,
          width: '90%',
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Import EFT Fitting</h2>
          <button
            onClick={handleClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '1.5rem',
              padding: 0,
            }}
          >
            x
          </button>
        </div>

        {step === 'paste' && (
          <>
            <textarea
              value={eftText}
              onChange={e => setEftText(e.target.value)}
              placeholder={placeholderText}
              style={{
                width: '100%',
                height: '300px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '0.75rem',
                color: 'var(--text-primary)',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                resize: 'vertical',
                marginBottom: '1rem',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={handleClose}
                style={{
                  padding: '0.5rem 1rem',
                  background: 'transparent',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleParse}
                disabled={loading || !eftText.trim()}
                style={{
                  padding: '0.5rem 1rem',
                  background: loading || !eftText.trim() ? 'var(--bg-secondary)' : '#00d4ff',
                  border: 'none',
                  borderRadius: '6px',
                  color: loading || !eftText.trim() ? 'var(--text-tertiary)' : '#000',
                  cursor: loading || !eftText.trim() ? 'not-allowed' : 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              >
                {loading ? 'Parsing...' : 'Parse & Preview'}
              </button>
            </div>
          </>
        )}

        {step === 'preview' && resolved && (
          <>
            {/* Ship Card */}
            <div
              style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
              }}
            >
              <img
                src={getTypeIconUrl(resolved.shipTypeId, 64)}
                alt={resolved.shipName}
                style={{ width: 64, height: 64, borderRadius: '4px' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                  {resolved.fittingName}
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {resolved.shipName}
                </div>
              </div>
            </div>

            {/* Unresolved Warning */}
            {resolved.unresolvedNames.length > 0 && (
              <div
                style={{
                  background: 'rgba(248, 81, 73, 0.1)',
                  border: '1px solid rgba(248, 81, 73, 0.3)',
                  borderRadius: '8px',
                  padding: '0.75rem',
                  marginBottom: '1rem',
                  fontSize: '0.85rem',
                  color: '#f85149',
                }}
              >
                Warning: {resolved.unresolvedNames.length} module(s) could not be resolved and will be skipped.
              </div>
            )}

            {/* Module List */}
            <div
              style={{
                maxHeight: 280,
                overflowY: 'auto',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '0.75rem',
                marginBottom: '1rem',
              }}
            >
              {resolved.blocks.map((block, blockIdx) => {
                const slotLabels = ['Low Slots', 'Mid Slots', 'High Slots', 'Rig Slots', 'Drones', 'Cargo'];
                const slotLabel = slotLabels[blockIdx] || 'Items';

                return (
                  <div key={blockIdx} style={{ marginBottom: blockIdx < resolved.blocks.length - 1 ? '1rem' : 0 }}>
                    <div
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        color: 'var(--text-secondary)',
                        marginBottom: '0.5rem',
                        letterSpacing: '0.05em',
                      }}
                    >
                      {slotLabel}
                    </div>
                    {block.map((mod, modIdx) => {
                      const typeId = resolved.nameToTypeId.get(mod.name) || resolved.nameToTypeId.get(mod.name.toLowerCase());
                      const isResolved = !!typeId;

                      return (
                        <div
                          key={modIdx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.35rem 0',
                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                          }}
                        >
                          {isResolved && typeId ? (
                            <img
                              src={getTypeIconUrl(typeId, 32)}
                              alt={mod.name}
                              style={{ width: 32, height: 32, borderRadius: '2px' }}
                            />
                          ) : (
                            <div
                              style={{
                                width: 32,
                                height: 32,
                                background: 'var(--bg-elevated)',
                                borderRadius: '2px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.75rem',
                                color: 'var(--text-tertiary)',
                              }}
                            >
                              ?
                            </div>
                          )}
                          <div style={{ flex: 1, fontSize: '0.85rem' }}>
                            {mod.name}
                            {mod.quantity > 1 && (
                              <span style={{ color: 'var(--text-secondary)', marginLeft: '0.25rem' }}>
                                x{mod.quantity}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={handleBack}
                style={{
                  padding: '0.5rem 1rem',
                  background: 'transparent',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                }}
              >
                Back
              </button>
              <button
                onClick={handleImport}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#00d4ff',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#000',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              >
                Import to Editor
              </button>
            </div>
          </>
        )}

        {step === 'error' && (
          <>
            <div
              style={{
                background: 'rgba(248, 81, 73, 0.1)',
                border: '1px solid rgba(248, 81, 73, 0.3)',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1rem',
              }}
            >
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f85149', marginBottom: '0.5rem' }}>
                Parse Error
              </div>
              <div style={{ fontSize: '0.85rem', color: '#f85149' }}>{error}</div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={handleBack}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#00d4ff',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#000',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              >
                Back
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
