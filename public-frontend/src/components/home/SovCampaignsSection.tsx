/**
 * Sovereignty Campaigns Ticker - Horizontal scrolling ticker showing active sov campaigns
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSovCampaigns } from '../../hooks/useSovCampaigns';
import { COLORS } from '../../constants';
import type { SovCampaign } from '../../types/dotlan';

// Get status badge info
function getStatusBadge(campaign: SovCampaign): { label: string; color: string; bg: string } {
  if (campaign.score === null) {
    return { label: 'RF', color: '#ff8800', bg: 'rgba(255,136,0,0.2)' }; // Reinforced
  }
  if (campaign.score < 0.3) {
    return { label: 'CRIT', color: COLORS.negative, bg: 'rgba(248,81,73,0.2)' }; // Critical
  }
  if (campaign.score < 0.7) {
    return { label: 'CONT', color: '#ffcc00', bg: 'rgba(255,204,0,0.2)' }; // Contested
  }
  return { label: 'DEF', color: COLORS.positive, bg: 'rgba(63,185,80,0.2)' }; // Defended
}

// Format score as percentage
function formatScore(score: number | null): string {
  if (score === null) return 'RF';
  return `${Math.round(score * 100)}%`;
}

export function SovCampaignsSection() {
  const { data: campaigns, isLoading, isError } = useSovCampaigns();
  const [isPaused, setIsPaused] = useState(false);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div style={{
        height: '36px',
        background: 'var(--bg-elevated)',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1rem',
        color: 'var(--text-tertiary)',
        fontSize: '0.75rem',
        marginBottom: '1rem',
      }}>
        Loading sovereignty campaigns...
      </div>
    );
  }

  if (isError || !campaigns) {
    return null; // Silently fail
  }

  if (campaigns.length === 0) {
    return (
      <div style={{
        height: '36px',
        background: 'var(--bg-elevated)',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1rem',
        gap: '0.5rem',
        marginBottom: '1rem',
      }}>
        <span style={{ color: COLORS.positive }}>✓</span>
        <span style={{ fontSize: '0.75rem', color: COLORS.positive }}>
          No active sovereignty campaigns
        </span>
      </div>
    );
  }

  const handleClick = (systemId: number) => {
    navigate(`/system/${systemId}`);
  };

  // Duplicate campaigns for seamless loop
  const duplicatedCampaigns = [...campaigns, ...campaigns];

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'var(--bg-elevated)',
          borderRadius: '4px',
          height: '36px',
        }}
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Gradient overlays for fade effect */}
        <div style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '40px',
          background: 'linear-gradient(to right, var(--bg-elevated), transparent)',
          zIndex: 2,
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute',
          right: 0,
          top: 0,
          bottom: 0,
          width: '40px',
          background: 'linear-gradient(to left, var(--bg-elevated), transparent)',
          zIndex: 2,
          pointerEvents: 'none',
        }} />

        {/* Ticker content */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            height: '100%',
            animation: isPaused ? 'none' : `sovTicker ${campaigns.length * 3}s linear infinite`,
            whiteSpace: 'nowrap',
          }}
        >
          {duplicatedCampaigns.map((campaign, index) => {
            const badge = getStatusBadge(campaign);

            return (
              <div
                key={`${campaign.campaign_id}-${index}`}
                onClick={() => handleClick(campaign.solar_system_id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0 1.5rem',
                  borderRight: '1px solid var(--border-color)',
                  height: '100%',
                  transition: 'background 0.2s',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                {/* Icon */}
                <span style={{ fontSize: '0.9rem' }}>🔥</span>

                {/* Status Badge */}
                <span style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.3rem',
                  borderRadius: '3px',
                  background: badge.bg,
                  color: badge.color,
                }}>
                  {badge.label}
                </span>

                {/* Defender (Faction) */}
                <span style={{
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  maxWidth: '140px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {campaign.defender_name || 'Unknown'}
                </span>

                {/* System Name */}
                <span style={{ fontWeight: 500, fontSize: '0.75rem', color: 'var(--accent-blue)' }}>
                  {campaign.solar_system_name || `#${campaign.solar_system_id}`}
                </span>

                {/* Structure Type */}
                <span style={{
                  fontSize: '0.6rem',
                  padding: '0.1rem 0.25rem',
                  borderRadius: '2px',
                  background: 'rgba(255,255,255,0.1)',
                  color: 'var(--text-secondary)',
                }}>
                  {campaign.structure_type}
                </span>

                {/* Region */}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
                  {campaign.region_name || 'Unknown'}
                </span>

                {/* Score */}
                {campaign.score !== null && (
                  <span style={{
                    fontSize: '0.75rem',
                    color: badge.color,
                    fontFamily: 'monospace',
                    fontWeight: 600,
                  }}>
                    {formatScore(campaign.score)}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* CSS Animation */}
        <style>{`
          @keyframes sovTicker {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
        `}</style>
      </div>
    </div>
  );
}
