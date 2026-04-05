import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { tierApi } from '../services/api/auth';
import { TIER_COLORS, TIER_LABELS, TIER_HIERARCHY } from '../types/auth';
import type { SubscriptionDetail, SubscribeResponse } from '../types/auth';
import { formatISK } from '../utils/format';

export function Subscription() {
  const { isLoggedIn, isLoading: authLoading, tierInfo, login, refresh } = useAuth();
  const [subDetail, setSubDetail] = useState<SubscriptionDetail | null>(null);

  // Upgrade flow state
  const [selectedTier, setSelectedTier] = useState('');
  const [corpId, setCorpId] = useState('');
  const [allianceId, setAllianceId] = useState('');
  const [subscribeResult, setSubscribeResult] = useState<SubscribeResponse | null>(null);
  const [subscribing, setSubscribing] = useState(false);
  const [subscribeError, setSubscribeError] = useState('');
  const [paymentVerified, setPaymentVerified] = useState(false);
  const [copied, setCopied] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isLoggedIn) return;
    tierApi.getMySubscription()
      .then(setSubDetail)
      .catch(() => {});
  }, [isLoggedIn]);

  // Poll for payment verification
  useEffect(() => {
    if (!subscribeResult) return;
    pollRef.current = setInterval(async () => {
      try {
        const status = await tierApi.getPaymentStatus(subscribeResult.reference_code);
        if (status.status === 'verified') {
          setPaymentVerified(true);
          if (pollRef.current) clearInterval(pollRef.current);
          refresh();
        }
      } catch { /* ignore */ }
    }, 30_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [subscribeResult, refresh]);

  if (authLoading) {
    return <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>Loading...</div>;
  }

  if (!isLoggedIn) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>Subscription Management</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Login to manage your subscription
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

  const currentTier = tierInfo?.tier || 'free';
  const currentColor = TIER_COLORS[currentTier] || '#8b949e';
  const currentLabel = TIER_LABELS[currentTier] || 'Free';
  const currentRank = TIER_HIERARCHY[currentTier] ?? 0;

  const upgradeTiers = Object.entries(TIER_HIERARCHY)
    .filter(([, rank]) => rank > currentRank && rank < 4) // exclude coalition
    .map(([tier]) => tier);

  const handleSubscribe = async () => {
    if (!selectedTier) return;
    setSubscribing(true);
    setSubscribeError('');
    try {
      const result = await tierApi.subscribe(
        selectedTier,
        selectedTier === 'corporation' ? Number(corpId) || undefined : undefined,
        selectedTier === 'alliance' ? Number(allianceId) || undefined : undefined,
      );
      setSubscribeResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Subscription failed';
      setSubscribeError(msg);
    } finally {
      setSubscribing(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      // Fallback for HTTP
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const daysRemaining = tierInfo?.expires_at
    ? Math.max(0, Math.ceil((new Date(tierInfo.expires_at).getTime() - Date.now()) / 86_400_000))
    : null;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>Subscription</h1>

      {/* Section 1: Current Plan */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: `1px solid ${currentColor}44`,
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '2rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <span style={{
                padding: '4px 10px',
                background: `${currentColor}22`,
                border: `1px solid ${currentColor}55`,
                color: currentColor,
                borderRadius: '4px',
                fontSize: '0.85rem',
                fontWeight: 700,
                textTransform: 'uppercase',
              }}>
                {currentLabel}
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Current Plan</span>
            </div>
            {daysRemaining !== null && daysRemaining > 0 && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Expires in {daysRemaining} day{daysRemaining !== 1 ? 's' : ''}
                {tierInfo?.expires_at && (
                  <span> ({new Date(tierInfo.expires_at).toLocaleDateString()})</span>
                )}
              </p>
            )}
            {currentTier === 'free' && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Upgrade to unlock more features
              </p>
            )}
          </div>
          <Link to="/pricing" style={{
            color: 'var(--text-secondary)',
            fontSize: '0.85rem',
            textDecoration: 'none',
            border: '1px solid var(--border-color)',
            padding: '6px 14px',
            borderRadius: '4px',
          }}>
            View Plans
          </Link>
        </div>
      </div>

      {/* Section 2: Upgrade Flow */}
      {upgradeTiers.length > 0 && !subscribeResult && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.5rem',
          marginBottom: '2rem',
        }}>
          <h3 style={{ marginBottom: '1rem' }}>Upgrade</h3>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <select
              value={selectedTier}
              onChange={e => setSelectedTier(e.target.value)}
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                color: 'inherit',
                padding: '8px 12px',
                borderRadius: '4px',
                fontSize: '0.9rem',
                minWidth: 160,
              }}
            >
              <option value="">Select tier...</option>
              {upgradeTiers.map(tier => (
                <option key={tier} value={tier}>{TIER_LABELS[tier]}</option>
              ))}
            </select>

            {selectedTier === 'corporation' && (
              <input
                type="number"
                placeholder="Corporation ID"
                value={corpId}
                onChange={e => setCorpId(e.target.value)}
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  color: 'inherit',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  width: 160,
                }}
              />
            )}

            {selectedTier === 'alliance' && (
              <input
                type="number"
                placeholder="Alliance ID"
                value={allianceId}
                onChange={e => setAllianceId(e.target.value)}
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  color: 'inherit',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  fontSize: '0.9rem',
                  width: 160,
                }}
              />
            )}

            <button
              onClick={handleSubscribe}
              disabled={!selectedTier || subscribing}
              style={{
                background: selectedTier ? TIER_COLORS[selectedTier] : '#555',
                border: 'none',
                color: '#000',
                padding: '8px 20px',
                borderRadius: '4px',
                fontSize: '0.9rem',
                fontWeight: 700,
                cursor: selectedTier ? 'pointer' : 'not-allowed',
                opacity: subscribing ? 0.6 : 1,
              }}
            >
              {subscribing ? 'Processing...' : 'Generate Payment Code'}
            </button>
          </div>
          {subscribeError && (
            <p style={{ color: '#ff4444', fontSize: '0.85rem' }}>{subscribeError}</p>
          )}
        </div>
      )}

      {/* Payment Instructions */}
      {subscribeResult && !paymentVerified && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: `1px solid ${TIER_COLORS[subscribeResult.tier]}55`,
          borderRadius: '8px',
          padding: '1.5rem',
          marginBottom: '2rem',
        }}>
          <h3 style={{ marginBottom: '1rem', color: TIER_COLORS[subscribeResult.tier] }}>
            Payment Instructions
          </h3>
          <div style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            padding: '1rem',
            marginBottom: '1rem',
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Amount:</span>
              <span style={{ fontWeight: 700 }}>{formatISK(subscribeResult.amount_isk)}</span>
              <span style={{ color: 'var(--text-secondary)' }}>Send to:</span>
              <span style={{ fontWeight: 700 }}>{subscribeResult.billing_character}</span>
              <span style={{ color: 'var(--text-secondary)' }}>Reason:</span>
              <span style={{
                fontWeight: 700,
                fontFamily: 'monospace',
                fontSize: '1.1rem',
                color: TIER_COLORS[subscribeResult.tier],
              }}>
                {subscribeResult.reference_code}
              </span>
            </div>
          </div>
          <button
            onClick={() => handleCopy(subscribeResult.instructions)}
            style={{
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              color: copied ? '#00ff88' : 'var(--text-secondary)',
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {copied ? 'Copied!' : 'Copy Instructions'}
          </button>
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: '0.8rem',
            marginTop: '1rem',
          }}>
            Auto-checking for payment every 30 seconds...
          </p>
        </div>
      )}

      {/* Payment Verified */}
      {paymentVerified && (
        <div style={{
          background: 'rgba(0, 255, 136, 0.1)',
          border: '1px solid rgba(0, 255, 136, 0.3)',
          borderRadius: '8px',
          padding: '1.5rem',
          marginBottom: '2rem',
          textAlign: 'center',
        }}>
          <h3 style={{ color: '#00ff88', marginBottom: '0.5rem' }}>Subscription Active!</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Your {TIER_LABELS[subscribeResult?.tier || '']} subscription has been activated.
          </p>
        </div>
      )}

      {/* Section 3: Payment History */}
      {subDetail?.payments && subDetail.payments.length > 0 && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <h3 style={{ marginBottom: '1rem' }}>Payment History</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Date</th>
                <th style={{ textAlign: 'right', padding: '0.5rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Amount</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Code</th>
                <th style={{ textAlign: 'center', padding: '0.5rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {subDetail.payments.map(p => (
                <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '0.5rem' }}>
                    {new Date(p.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '0.5rem', textAlign: 'right', fontFamily: 'monospace' }}>
                    {formatISK(p.amount)}
                  </td>
                  <td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {p.reference_code}
                  </td>
                  <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '3px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      background: p.status === 'verified' ? 'rgba(0,255,136,0.15)' : 'rgba(255,204,0,0.15)',
                      color: p.status === 'verified' ? '#00ff88' : '#ffcc00',
                    }}>
                      {p.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
