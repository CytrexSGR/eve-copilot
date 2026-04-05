import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useModules } from '../hooks/useModules';
import { authApi, tierApi, characterMgmtApi } from '../services/api/auth';
import { TIER_COLORS, TIER_LABELS, MODULE_NAMES, MODULE_COLORS } from '../types/auth';
import type { CorpInfo, TokenHealth } from '../types/auth';

export function Account() {
  const { isLoggedIn, isLoading: authLoading, account, tierInfo, login, refresh } = useAuth();
  const { activeModules, orgPlan } = useModules();
  const [corpInfo, setCorpInfo] = useState<CorpInfo | null>(null);
  const [corpLoading, setCorpLoading] = useState(false);
  const [addingChar, setAddingChar] = useState(false);
  const [tokenHealthMap, setTokenHealthMap] = useState<Record<number, TokenHealth>>({});
  const [removingChar, setRemovingChar] = useState<number | null>(null);
  const [settingPrimary, setSettingPrimary] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoggedIn || !account?.corporation_id) return;
    setCorpLoading(true);
    tierApi.getCorpInfo()
      .then(setCorpInfo)
      .catch(() => {})
      .finally(() => setCorpLoading(false));
  }, [isLoggedIn, account?.corporation_id]);

  useEffect(() => {
    if (!isLoggedIn || !account?.characters) return;
    account.characters.forEach(char => {
      characterMgmtApi.getTokenHealth(char.character_id)
        .then(health => setTokenHealthMap(prev => ({ ...prev, [char.character_id]: health })))
        .catch(() => {});
    });
  }, [isLoggedIn, account?.characters]);

  const handleSetPrimary = async (charId: number) => {
    setSettingPrimary(charId);
    try {
      await characterMgmtApi.setPrimary(charId);
      await refresh();
    } catch {
      // silently fail
    } finally {
      setSettingPrimary(null);
    }
  };

  const handleRemoveChar = async (charId: number, charName: string) => {
    if (!confirm(`Remove ${charName} from your account? This cannot be undone.`)) return;
    setRemovingChar(charId);
    try {
      await characterMgmtApi.removeCharacter(charId);
      await refresh();
    } catch {
      // silently fail
    } finally {
      setRemovingChar(null);
    }
  };

  if (authLoading) {
    return <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>Loading...</div>;
  }

  if (!isLoggedIn || !account) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>Account Settings</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Login to manage your account
        </p>
        <button
          onClick={login}
          style={{
            background: 'linear-gradient(135deg, #1a3a5c, #0d2137)',
            border: '1px solid rgba(0, 212, 255, 0.3)',
            color: '#00d4ff',
            padding: '10px 24px',
            borderRadius: '4px',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Login with EVE
        </button>
      </div>
    );
  }

  const tierColor = TIER_COLORS[tierInfo?.tier || 'free'];
  const tierLabel = TIER_LABELS[tierInfo?.tier || 'free'];

  const handleAddCharacter = async () => {
    setAddingChar(true);
    try {
      const { auth_url } = await authApi.addCharacter();
      window.location.href = auth_url;
    } catch {
      setAddingChar(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>Account</h1>

      {/* Section 1: Account Overview */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '2rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <img
            src={`https://images.evetech.net/characters/${account.primary_character_id}/portrait?size=64`}
            alt={account.primary_character_name}
            style={{ width: 56, height: 56, borderRadius: '50%', border: '2px solid var(--border-color)' }}
          />
          <div style={{ flex: 1 }}>
            <h3 style={{ margin: 0, marginBottom: '0.25rem' }}>{account.primary_character_name}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <span style={{
                padding: '2px 8px',
                background: `${tierColor}22`,
                border: `1px solid ${tierColor}55`,
                color: tierColor,
                borderRadius: '3px',
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase',
              }}>
                {tierLabel}
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                Account #{account.account_id}
              </span>
              {account.corporation_id && (
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Corp: {account.corporation_id}
                </span>
              )}
              {account.alliance_id && (
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Alliance: {account.alliance_id}
                </span>
              )}
            </div>
          </div>
          <Link to="/subscription" style={{
            color: tierColor,
            fontSize: '0.85rem',
            textDecoration: 'none',
            border: `1px solid ${tierColor}44`,
            padding: '6px 14px',
            borderRadius: '4px',
          }}>
            Subscription
          </Link>
        </div>
      </div>

      {/* Section 2: Linked Characters */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '2rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0 }}>Linked Characters</h3>
          <button
            onClick={handleAddCharacter}
            disabled={addingChar}
            style={{
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              color: '#00d4ff',
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '0.85rem',
              cursor: addingChar ? 'not-allowed' : 'pointer',
              opacity: addingChar ? 0.6 : 1,
            }}
          >
            {addingChar ? 'Redirecting...' : '+ Add Character'}
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {account.characters.map(char => {
            const health = tokenHealthMap[char.character_id];
            const dotColor = !health ? '#484f58' :
              health.status === 'valid' ? '#3fb950' :
              health.status === 'incomplete' || health.status === 'expiring' ? '#d29922' : '#f85149';
            const scopeGroups = health?.scope_groups || {};
            const activeGroups = Object.entries(scopeGroups).filter(([, v]) => v === 'full').map(([k]) => k);

            return (
              <div key={char.character_id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.5rem',
                background: 'var(--bg-tertiary)',
                borderRadius: '4px',
              }}>
                {/* Token health dot */}
                <span
                  title={health ? `Token: ${health.status}` : 'Loading...'}
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: dotColor,
                    flexShrink: 0,
                  }}
                />
                <img
                  src={`https://images.evetech.net/characters/${char.character_id}/portrait?size=32`}
                  alt={char.character_name}
                  style={{ width: 32, height: 32, borderRadius: '50%', border: '1px solid var(--border-color)' }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.9rem' }}>{char.character_name}</div>
                  {activeGroups.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.25rem' }}>
                      {activeGroups.map(group => (
                        <span key={group} style={{
                          padding: '1px 5px',
                          background: 'rgba(139, 148, 158, 0.15)',
                          border: '1px solid rgba(139, 148, 158, 0.25)',
                          color: '#8b949e',
                          borderRadius: '3px',
                          fontSize: '0.6rem',
                          fontWeight: 600,
                          textTransform: 'capitalize',
                        }}>
                          {group.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {char.is_primary && (
                  <span style={{
                    padding: '2px 6px',
                    background: 'rgba(0, 212, 255, 0.15)',
                    color: '#00d4ff',
                    borderRadius: '3px',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    flexShrink: 0,
                  }}>
                    PRIMARY
                  </span>
                )}
                {!char.is_primary && (
                  <button
                    onClick={() => handleSetPrimary(char.character_id)}
                    disabled={settingPrimary === char.character_id}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#8b949e',
                      fontSize: '0.75rem',
                      cursor: settingPrimary === char.character_id ? 'not-allowed' : 'pointer',
                      opacity: settingPrimary === char.character_id ? 0.5 : 1,
                      padding: '2px 6px',
                      flexShrink: 0,
                    }}
                  >
                    {settingPrimary === char.character_id ? 'Setting...' : 'Set Primary'}
                  </button>
                )}
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', fontFamily: 'monospace', flexShrink: 0 }}>
                  {char.character_id}
                </span>
                {!char.is_primary && (
                  <button
                    onClick={() => handleRemoveChar(char.character_id, char.character_name)}
                    disabled={removingChar === char.character_id}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#f85149',
                      fontSize: '0.75rem',
                      cursor: removingChar === char.character_id ? 'not-allowed' : 'pointer',
                      opacity: removingChar === char.character_id ? 0.5 : 1,
                      padding: '2px 6px',
                      flexShrink: 0,
                    }}
                  >
                    {removingChar === char.character_id ? 'Removing...' : 'Remove'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 3: Active Modules */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '2rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0 }}>Active Modules</h3>
          <Link to="/pricing" style={{
            color: '#00d4ff',
            fontSize: '0.85rem',
            textDecoration: 'none',
            border: '1px solid rgba(0,212,255,0.3)',
            padding: '4px 12px',
            borderRadius: '4px',
          }}>
            Browse Modules
          </Link>
        </div>
        {activeModules && activeModules.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {activeModules.map(mod => {
              const color = MODULE_COLORS[mod] || '#00d4ff';
              const name = MODULE_NAMES[mod] || mod;
              return (
                <span key={mod} style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                  padding: '4px 10px',
                  background: `${color}15`,
                  border: `1px solid ${color}44`,
                  borderRadius: '4px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color,
                }}>
                  <span style={{ color: '#3fb950' }}>&#10003;</span>
                  {name}
                </span>
              );
            })}
          </div>
        ) : (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
            No active modules. <Link to="/pricing" style={{ color: '#00d4ff' }}>Try a 24H free trial</Link>
          </p>
        )}
        {orgPlan && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem',
            background: 'var(--bg-tertiary)',
            borderRadius: '4px',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Organization Plan</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontWeight: 700, fontSize: '0.9rem', textTransform: 'capitalize' }}>{orgPlan.type} — {orgPlan.plan}</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {orgPlan.seats_used}/{orgPlan.heavy_seats} seats used
              </span>
              {orgPlan.has_seat && (
                <span style={{
                  padding: '2px 6px',
                  background: 'rgba(63,185,80,0.15)',
                  color: '#3fb950',
                  borderRadius: '3px',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                }}>SEATED</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Section 4: Corp Management */}
      {corpLoading && (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
          Loading corp info...
        </div>
      )}
      {corpInfo && corpInfo.has_management_access && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid rgba(255, 204, 0, 0.2)',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: '#ffcc00' }}>Corporation Management</h3>
            <span style={{
              padding: '2px 8px',
              background: 'rgba(255, 204, 0, 0.15)',
              color: '#ffcc00',
              borderRadius: '3px',
              fontSize: '0.75rem',
              fontWeight: 700,
              textTransform: 'uppercase',
            }}>
              {corpInfo.role}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{
              background: 'var(--bg-tertiary)',
              borderRadius: '4px',
              padding: '0.75rem',
            }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>Corporation ID</div>
              <div style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>{corpInfo.corporation_id}</div>
            </div>
            <div style={{
              background: 'var(--bg-tertiary)',
              borderRadius: '4px',
              padding: '0.75rem',
            }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>Members</div>
              <div style={{ fontSize: '0.9rem' }}>{corpInfo.members ?? 0}</div>
            </div>
          </div>

          {corpInfo.subscription ? (
            <div style={{
              background: 'rgba(0, 255, 136, 0.08)',
              border: '1px solid rgba(0, 255, 136, 0.2)',
              borderRadius: '4px',
              padding: '0.75rem',
              marginBottom: '1rem',
              fontSize: '0.85rem',
            }}>
              <span style={{ color: '#00ff88', fontWeight: 700 }}>
                {TIER_LABELS[corpInfo.subscription.tier]} Subscription Active
              </span>
              <span style={{ color: 'var(--text-secondary)', marginLeft: '1rem' }}>
                Expires: {new Date(corpInfo.subscription.expires_at).toLocaleDateString()}
              </span>
            </div>
          ) : (
            <div style={{
              background: 'rgba(255, 204, 0, 0.08)',
              border: '1px solid rgba(255, 204, 0, 0.2)',
              borderRadius: '4px',
              padding: '0.75rem',
              marginBottom: '1rem',
              fontSize: '0.85rem',
            }}>
              <span style={{ color: '#ffcc00' }}>No active corp subscription.</span>{' '}
              <Link to="/pricing" style={{ color: '#00d4ff' }}>View plans</Link>
            </div>
          )}

          {corpInfo.roles && corpInfo.roles.length > 0 && (
            <>
              <h4 style={{ margin: '1rem 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                Platform Roles ({corpInfo.roles.length})
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {corpInfo.roles.map(r => (
                  <div key={r.character_id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.4rem 0.5rem',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                  }}>
                    <span style={{ flex: 1 }}>{r.character_name || r.character_id}</span>
                    <span style={{
                      padding: '1px 6px',
                      borderRadius: '3px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      background: r.role === 'admin' ? 'rgba(255,68,68,0.15)' : r.role === 'officer' ? 'rgba(255,204,0,0.15)' : 'rgba(139,148,158,0.15)',
                      color: r.role === 'admin' ? '#ff4444' : r.role === 'officer' ? '#ffcc00' : '#8b949e',
                    }}>
                      {r.role}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}