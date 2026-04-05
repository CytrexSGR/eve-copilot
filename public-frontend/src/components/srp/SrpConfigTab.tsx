import { useState, useEffect } from 'react';
import { srpApi } from '../../services/api/srp';
import type { SrpConfig } from '../../types/srp';
import { formatIsk } from '../../types/srp';

const PRICING_LABELS: Record<string, string> = {
  jita_buy: 'Jita Buy', jita_sell: 'Jita Sell', jita_split: 'Jita Split',
};

const INSURANCE_LABELS: Record<string, string> = {
  none: 'None', basic: 'Basic', standard: 'Standard', bronze: 'Bronze',
  silver: 'Silver', gold: 'Gold', platinum: 'Platinum',
};

export function SrpConfigTab({ corpId }: { corpId: number }) {
  const [config, setConfig] = useState<SrpConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{ synced: number; total_types: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Editable fields
  const [pricingMode, setPricingMode] = useState('jita_sell');
  const [insuranceLevel, setInsuranceLevel] = useState('platinum');
  const [autoApproveThreshold, setAutoApproveThreshold] = useState('90');
  const [maxPayout, setMaxPayout] = useState('');

  useEffect(() => {
    setLoading(true);
    srpApi.getConfig(corpId)
      .then(cfg => {
        setConfig(cfg);
        setPricingMode(cfg.pricing_mode);
        setInsuranceLevel(cfg.default_insurance_level);
        setAutoApproveThreshold(String(cfg.auto_approve_threshold * 100));
        setMaxPayout(cfg.max_payout != null ? String(cfg.max_payout) : '');
      })
      .catch(err => {
        console.error('Failed to load SRP config:', err);
        setError('Failed to load configuration');
      })
      .finally(() => setLoading(false));
  }, [corpId]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updates: Partial<SrpConfig> = {
        pricing_mode: pricingMode as SrpConfig['pricing_mode'],
        default_insurance_level: insuranceLevel,
        auto_approve_threshold: Number(autoApproveThreshold) / 100,
        max_payout: maxPayout ? Number(maxPayout) : null,
      };
      const updated = await srpApi.updateConfig(corpId, updates);
      setConfig(updated);
    } catch (err) {
      console.error('Failed to save config:', err);
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleSyncPrices = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await srpApi.syncPrices(corpId);
      setSyncResult(result);
    } catch (err) {
      console.error('Failed to sync prices:', err);
      setError('Failed to sync prices');
    } finally {
      setSyncing(false);
    }
  };

  const inputStyle = {
    background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
    borderRadius: '4px', color: '#fff', padding: '0.5rem 0.75rem', fontSize: '0.85rem', outline: 'none',
    width: '100%',
  };

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '600px' }}>
      {error && (
        <div style={{
          background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
          borderRadius: '6px', padding: '0.75rem 1rem', color: '#f85149', fontSize: '0.85rem',
        }}>
          {error}
        </div>
      )}

      {/* Config form */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', padding: '1.25rem',
        display: 'flex', flexDirection: 'column', gap: '1rem',
      }}>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.25rem' }}>SRP Configuration</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Pricing Mode</label>
          <select value={pricingMode} onChange={e => setPricingMode(e.target.value)}
            style={{ ...inputStyle, cursor: 'pointer' }}>
            {Object.entries(PRICING_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)' }}>
            How fitting values are calculated from market prices
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Default Insurance Level</label>
          <select value={insuranceLevel} onChange={e => setInsuranceLevel(e.target.value)}
            style={{ ...inputStyle, cursor: 'pointer' }}>
            {Object.entries(INSURANCE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)' }}>
            Insurance payout deducted from SRP reimbursement
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Auto-Approve Threshold (%)</label>
          <input type="number" value={autoApproveThreshold} onChange={e => setAutoApproveThreshold(e.target.value)}
            min="0" max="100" style={inputStyle} />
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)' }}>
            Requests with match score above this threshold are auto-approved
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Max Payout (ISK)</label>
          <input type="number" value={maxPayout} onChange={e => setMaxPayout(e.target.value)}
            placeholder="No limit" style={{ ...inputStyle, fontFamily: 'monospace' }} />
          <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)' }}>
            Maximum ISK payout per request. Leave empty for no limit.
          </span>
        </div>

        {/* Current config display */}
        {config && (
          <div style={{
            marginTop: '0.5rem', padding: '0.75rem', background: 'rgba(0,0,0,0.2)',
            borderRadius: '4px', fontSize: '0.78rem',
          }}>
            <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: '0.5rem', fontSize: '0.7rem', textTransform: 'uppercase' }}>Current Settings</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.3rem' }}>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Pricing:</span>
              <span>{PRICING_LABELS[config.pricing_mode] || config.pricing_mode}</span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Insurance:</span>
              <span>{INSURANCE_LABELS[config.default_insurance_level] || config.default_insurance_level}</span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Auto-Approve:</span>
              <span>{(config.auto_approve_threshold * 100).toFixed(0)}%</span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Max Payout:</span>
              <span>{config.max_payout != null ? formatIsk(config.max_payout) : 'No limit'}</span>
            </div>
          </div>
        )}

        <button onClick={handleSave} disabled={saving} style={{
          background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
          borderRadius: '6px', color: '#3fb950', padding: '0.5rem 1.25rem',
          fontSize: '0.85rem', fontWeight: 600, alignSelf: 'flex-start',
          cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.5 : 1,
        }}>
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>

      {/* Price sync */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', padding: '1.25rem',
      }}>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Price Sync</div>
        <p style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.75rem' }}>
          Sync current market prices for all doctrine items. This updates fitting values and payout calculations.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button onClick={handleSyncPrices} disabled={syncing} style={{
            background: 'rgba(0,212,255,0.15)', border: '1px solid rgba(0,212,255,0.3)',
            borderRadius: '6px', color: '#00d4ff', padding: '0.5rem 1.25rem',
            fontSize: '0.85rem', fontWeight: 600,
            cursor: syncing ? 'not-allowed' : 'pointer', opacity: syncing ? 0.5 : 1,
          }}>
            {syncing ? 'Syncing...' : 'Sync Prices'}
          </button>
          {syncResult && (
            <span style={{ fontSize: '0.8rem', color: '#3fb950' }}>
              Synced {syncResult.synced} / {syncResult.total_types} types
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
