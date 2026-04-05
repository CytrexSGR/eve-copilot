/**
 * SovDefensePanel - Active sovereignty campaigns + ADM vulnerability
 *
 * Compact design showing systems under attack and their defense status.
 */

import type { SovDefenseData, SovCampaign, VulnerabilityLevel } from '../../../types/geography-dotlan';
import { getVulnerabilityColor } from '../../../types/geography-dotlan';

interface SovDefensePanelProps {
  data: SovDefenseData;
}

export function SovDefensePanel({ data }: SovDefensePanelProps) {
  if (!data.campaigns || data.campaigns.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        color: '#3fb950',
        padding: '0.5rem',
        background: 'rgba(63, 185, 80, 0.1)',
        borderRadius: '4px',
        border: '1px solid rgba(63, 185, 80, 0.3)',
        fontSize: '0.7rem',
      }}>
        ✓ No active sovereignty campaigns
      </div>
    );
  }

  const criticalCount = data.campaigns.filter(c => c.vulnerability === 'critical').length;
  const vulnerableCount = data.campaigns.filter(c => c.vulnerability === 'vulnerable').length;

  return (
    <div>
      {/* Summary Row */}
      {criticalCount > 0 && (
        <div style={{
          background: 'rgba(248, 81, 73, 0.15)',
          border: '1px solid #f85149',
          borderRadius: '3px',
          padding: '0.25rem 0.5rem',
          marginBottom: '0.4rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.7rem',
        }}>
          <span style={{ animation: 'pulse 1.5s ease-in-out infinite' }}>⚠️</span>
          <span style={{ color: '#f85149', fontWeight: 600 }}>
            {criticalCount} CRITICAL
          </span>
          {vulnerableCount > 0 && (
            <span style={{ color: '#d29922' }}>• {vulnerableCount} Vulnerable</span>
          )}
          <span style={{ marginLeft: 'auto', color: '#8b949e' }}>
            {data.campaigns.length} total
          </span>
        </div>
      )}

      {/* Compact Campaign Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.25rem', maxHeight: '250px', overflowY: 'auto' }}>
        {data.campaigns.map((campaign) => (
          <CampaignRow key={campaign.campaign_id} campaign={campaign} />
        ))}
      </div>
    </div>
  );
}

function CampaignRow({ campaign }: { campaign: SovCampaign }) {
  const vulnColor = getVulnerabilityColor(campaign.vulnerability);
  const isCritical = campaign.vulnerability === 'critical';
  const isUnknown = campaign.vulnerability === 'unknown';

  // Use score to estimate status when ADM unknown
  const scoreColor = campaign.score !== null
    ? campaign.score > 50 ? '#3fb950' : campaign.score > 30 ? '#d29922' : '#f85149'
    : '#ff8800'; // Orange for reinforced (no score)

  // Border color: use score-based color if ADM unknown, orange for RF
  const borderColor = isUnknown
    ? (campaign.score !== null ? scoreColor : '#ff8800')
    : vulnColor;

  return (
    <div
      style={{
        background: isCritical ? 'rgba(248,81,73,0.08)' : 'rgba(0,0,0,0.2)',
        borderRadius: '3px',
        padding: '0.3rem 0.4rem',
        borderLeft: `2px solid ${borderColor}`,
        fontSize: '0.65rem',
      }}
    >
      {/* System + Structure + Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.15rem' }}>
        <span style={{ fontWeight: 600, color: '#c9d1d9', fontSize: '0.7rem' }}>
          {campaign.system_name || `#${campaign.solar_system_id}`}
        </span>
        <span style={{ color: '#6e7681', fontSize: '0.55rem' }}>{campaign.structure_type}</span>
        <VulnBadge level={campaign.vulnerability} />
        {/* Show score-based status if ADM unknown */}
        {isUnknown && (
          <span style={{
            padding: '0.05rem 0.2rem',
            borderRadius: '2px',
            fontSize: '0.5rem',
            fontWeight: 700,
            background: campaign.score !== null ? `${scoreColor}25` : 'rgba(255,136,0,0.2)',
            color: campaign.score !== null ? scoreColor : '#ff8800',
            marginLeft: 'auto',
          }}>
            {campaign.score !== null
              ? (campaign.score > 50 ? 'WIN' : campaign.score > 30 ? 'CONT' : 'LOSE')
              : 'RF'}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#8b949e' }}>
        <span style={{ color: '#6e7681', fontSize: '0.55rem' }}>{campaign.region_name}</span>

        {campaign.score !== null && (
          <span style={{ marginLeft: 'auto' }}>
            <span style={{ opacity: 0.5 }}>Score </span>
            <span style={{ color: scoreColor, fontWeight: 600, fontFamily: 'monospace' }}>
              {campaign.score.toFixed(0)}%
            </span>
          </span>
        )}

        {campaign.adm_level !== null && (
          <span>
            <span style={{ opacity: 0.5 }}>ADM </span>
            <span style={{
              fontWeight: 600,
              fontFamily: 'monospace',
              color: campaign.adm_level < 2 ? '#f85149' : campaign.adm_level < 4 ? '#d29922' : '#3fb950',
            }}>
              {campaign.adm_level.toFixed(1)}
            </span>
          </span>
        )}

        {campaign.defender_name && (
          <span style={{ fontSize: '0.55rem', color: '#6e7681', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '80px' }}>
            {campaign.defender_name}
          </span>
        )}
      </div>

      {/* Progress bar for score */}
      {campaign.score !== null && (
        <div style={{ marginTop: '0.2rem', height: '3px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{
            width: `${campaign.score}%`,
            height: '100%',
            background: scoreColor,
            transition: 'width 0.3s',
          }} />
        </div>
      )}
    </div>
  );
}

function VulnBadge({ level }: { level: VulnerabilityLevel }) {
  const color = getVulnerabilityColor(level);
  const labels: Record<VulnerabilityLevel, string> = {
    critical: 'CRIT',
    vulnerable: 'VULN',
    defended: 'DEF',
    unknown: 'N/A',
  };

  // Don't show badge at all for unknown - just show score/ADM if available
  if (level === 'unknown') {
    return null;
  }

  return (
    <span
      style={{
        padding: '0.05rem 0.2rem',
        borderRadius: '2px',
        fontSize: '0.5rem',
        fontWeight: 700,
        background: `${color}25`,
        color: color,
        marginLeft: 'auto',
      }}
    >
      {labels[level]}
    </span>
  );
}

export default SovDefensePanel;
