/**
 * Alliance CombinedTimelineCard Component - Modern Design
 *
 * Displays combined kill/death timeline with integrated statistics overlay.
 */

import { useState, useEffect } from 'react';
import { getOffensiveStats, getDefensiveStats } from '../../services/allianceApi';
import type { AllianceOffensiveStats, AllianceDefensiveStats } from '../../types/alliance';

interface TimelineDay {
  day: string;
  kills?: number;
  deaths?: number;
  active_pilots?: number;
}

interface CombinedTimelineCardProps {
  allianceId: number;
  days: number;
}

export function CombinedTimelineCard({ allianceId, days }: CombinedTimelineCardProps) {
  const [offensiveData, setOffensiveData] = useState<AllianceOffensiveStats | null>(null);
  const [defensiveData, setDefensiveData] = useState<AllianceDefensiveStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getOffensiveStats(allianceId, days),
      getDefensiveStats(allianceId, days),
    ])
      .then(([offensive, defensive]) => {
        setOffensiveData(offensive);
        setDefensiveData(defensive);
      })
      .catch((err: Error) => console.error('Timeline error:', err))
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.4)',
        borderRadius: '8px',
        padding: '0.75rem',
        border: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div className="skeleton" style={{ height: '200px', borderRadius: '6px' }} />
      </div>
    );
  }

  if (!offensiveData || !defensiveData) return null;

  const killTimeline = offensiveData.kill_timeline || [];
  const deathTimeline = defensiveData.death_timeline || [];

  // Merge timelines by day
  const mergedTimeline: TimelineDay[] = [];
  const dayMap = new Map<string, TimelineDay>();

  killTimeline.forEach(kt => {
    dayMap.set(kt.day, { day: kt.day, kills: kt.kills || 0, deaths: 0, active_pilots: kt.active_pilots || 0 });
  });

  deathTimeline.forEach(dt => {
    if (dayMap.has(dt.day)) {
      const existing = dayMap.get(dt.day)!;
      existing.deaths = dt.deaths || 0;
      existing.active_pilots = Math.max(existing.active_pilots || 0, dt.active_pilots || 0);
    } else {
      dayMap.set(dt.day, { day: dt.day, kills: 0, deaths: dt.deaths || 0, active_pilots: dt.active_pilots || 0 });
    }
  });

  mergedTimeline.push(...Array.from(dayMap.values()).sort((a, b) => a.day.localeCompare(b.day)));

  if (mergedTimeline.length === 0) return null;

  const kills = mergedTimeline.map(t => t.kills || 0);
  const deaths = mergedTimeline.map(t => t.deaths || 0);
  const pilots = mergedTimeline.map(t => t.active_pilots || 0);

  const maxKills = Math.max(...kills, 1);
  const maxDeaths = Math.max(...deaths, 1);
  const maxPilots = Math.max(...pilots, 1);
  const maxActivity = Math.max(maxKills, maxDeaths);

  // Statistics
  const totalKills = kills.reduce((a, b) => a + b, 0);
  const totalDeaths = deaths.reduce((a, b) => a + b, 0);
  const avgKillsPerDay = kills.length > 0 ? totalKills / kills.length : 0;
  const avgDeathsPerDay = deaths.length > 0 ? totalDeaths / deaths.length : 0;
  const last3DaysKills = kills.length >= 3 ? kills.slice(-3).reduce((a, b) => a + b, 0) / 3 : 0;
  const last3DaysDeaths = deaths.length >= 3 ? deaths.slice(-3).reduce((a, b) => a + b, 0) / 3 : 0;
  const peakKills = Math.max(...kills, 0);
  const peakDeaths = Math.max(...deaths, 0);
  const avgPilots = pilots.length > 0 ? pilots.reduce((a, b) => a + b, 0) / pilots.length : 0;

  const huntingHours = offensiveData.hunting_hours;
  const safeDangerHours = defensiveData.safe_danger_hours;

  // Trend calculation
  const calculateTrend = (values: number[]): string => {
    if (values.length < 7) return '→';
    const last3 = values.slice(-3).reduce((a, b) => a + b, 0) / 3;
    const prev4 = values.slice(-7, -3).reduce((a, b) => a + b, 0) / 4;
    const change = ((last3 - prev4) / Math.max(prev4, 1)) * 100;
    if (change > 15) return '⬆️';
    if (change < -15) return '⬇️';
    return '→';
  };

  const killTrend = calculateTrend(kills);
  const deathTrend = calculateTrend(deaths);
  const pilotTrend = calculateTrend(pilots);

  // SVG Chart
  const width = 1200;
  const height = 225;
  const padding = { top: 40, right: 50, bottom: 35, left: 50 };
  const dataWidth = width - padding.left - padding.right;
  const dataHeight = height - padding.top - padding.bottom;

  // Generate points
  const killPoints = kills.map((k, i) => ({
    x: padding.left + (i / Math.max(kills.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (k / maxActivity) * dataHeight,
  }));

  const deathPoints = deaths.map((d, i) => ({
    x: padding.left + (i / Math.max(deaths.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (d / maxActivity) * dataHeight,
  }));

  const pilotPoints = pilots.map((p, i) => ({
    x: padding.left + (i / Math.max(pilots.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (p / maxPilots) * dataHeight,
  }));

  const killPath = killPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const deathPath = deathPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const pilotPath = pilotPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // Fill area paths
  const killFillPath = `${killPath} L ${killPoints[killPoints.length - 1].x},${padding.top + dataHeight} L ${killPoints[0].x},${padding.top + dataHeight} Z`;
  const deathFillPath = `${deathPath} L ${deathPoints[deathPoints.length - 1].x},${padding.top + dataHeight} L ${deathPoints[0].x},${padding.top + dataHeight} Z`;

  // X-axis labels
  const maxXLabels = 12;
  const step = Math.ceil(mergedTimeline.length / maxXLabels);

  const formatHour = (h: number) => `${h.toString().padStart(2, '0')}:00`;

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.3) 100%)',
      borderRadius: '8px',
      padding: '0',
      border: '1px solid rgba(255,255,255,0.1)',
      overflow: 'hidden',
      position: 'relative',
    }}>
      {/* SVG Chart with Integrated Stats */}
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
        {/* Background gradient areas */}
        <defs>
          <linearGradient id="killGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#3fb950" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#3fb950" stopOpacity={0.05} />
          </linearGradient>
          <linearGradient id="deathGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ff4444" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#ff4444" stopOpacity={0.05} />
          </linearGradient>
        </defs>

        {/* Grid lines + Left Y-Axis Labels (Kills/Deaths) */}
        {[0, 0.25, 0.5, 0.75, 1].map(level => {
          const y = padding.top + dataHeight - level * dataHeight;
          const value = Math.round(level * maxActivity);
          return (
            <g key={level}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="rgba(255,255,255,0.05)"
                strokeWidth={1}
                strokeDasharray={level === 0 ? '0' : '2,4'}
              />
              {/* Left Y-Axis Labels */}
              <text
                x={padding.left - 5}
                y={y + 3}
                fill="#8b949e"
                fontSize="10"
                textAnchor="end"
                fontFamily="monospace"
              >
                {value}
              </text>
            </g>
          );
        })}

        {/* Right Y-Axis Labels (Active Pilots) */}
        {[0, 0.25, 0.5, 0.75, 1].map(level => {
          const y = padding.top + dataHeight - level * dataHeight;
          const value = Math.round(level * maxPilots);
          return (
            <text
              key={`right-${level}`}
              x={width - padding.right + 5}
              y={y + 3}
              fill="#a855f7"
              fontSize="10"
              textAnchor="start"
              fontFamily="monospace"
            >
              {value}
            </text>
          );
        })}

        {/* X-axis date labels */}
        {mergedTimeline.filter((_, i) => i % step === 0).map((t, idx) => {
          const i = mergedTimeline.indexOf(t);
          const x = padding.left + (i / Math.max(mergedTimeline.length - 1, 1)) * dataWidth;
          return (
            <text
              key={idx}
              x={x}
              y={height - 15}
              fill="rgba(255,255,255,0.4)"
              fontSize="10"
              textAnchor="middle"
              fontFamily="monospace"
            >
              {t.day.slice(5)}
            </text>
          );
        })}

        {/* Fill areas */}
        <path d={killFillPath} fill="url(#killGradient)" />
        <path d={deathFillPath} fill="url(#deathGradient)" />

        {/* Lines */}
        <path d={killPath} fill="none" stroke="#3fb950" strokeWidth={2.5} opacity={0.9} />
        <path d={deathPath} fill="none" stroke="#ff4444" strokeWidth={2.5} opacity={0.9} />
        <path d={pilotPath} fill="none" stroke="#a855f7" strokeWidth={1.5} opacity={0.5} strokeDasharray="3,3" />

        {/* Header - Integrated into SVG */}
        <text x={15} y={18} fill="#58a6ff" fontSize="11" fontWeight="700" letterSpacing="0.5">COMBAT TIMELINE</text>
        <text x={140} y={18} fill="rgba(255,255,255,0.3)" fontSize="9">{days} days</text>

        {/* Top Stats Row - Kills */}
        <g>
          {/* Kills Total */}
          <rect x={250} y={5} width={90} height={24} rx={4} fill="rgba(63,185,80,0.15)" stroke="#3fb950" strokeWidth={1} />
          <text x={258} y={16} fill="rgba(255,255,255,0.5)" fontSize="8">● Kills</text>
          <text x={258} y={25} fill="#3fb950" fontSize="11" fontWeight="700" fontFamily="monospace">{totalKills}</text>
          <text x={330} y={17} fill="#3fb950" fontSize="14">{killTrend}</text>

          {/* Avg Kills/Day */}
          <rect x={350} y={5} width={70} height={24} rx={4} fill="rgba(63,185,80,0.1)" />
          <text x={358} y={16} fill="rgba(255,255,255,0.4)" fontSize="8">Avg/Day</text>
          <text x={358} y={25} fill="#3fb950" fontSize="10" fontWeight="700" fontFamily="monospace">{avgKillsPerDay.toFixed(1)}</text>

          {/* Last 3 Days */}
          <rect x={430} y={5} width={70} height={24} rx={4} fill="rgba(63,185,80,0.1)" />
          <text x={438} y={16} fill="rgba(255,255,255,0.4)" fontSize="8">Last 3 Days</text>
          <text x={438} y={25} fill="#3fb950" fontSize="10" fontWeight="700" fontFamily="monospace">{last3DaysKills.toFixed(1)}</text>

          {/* Peak */}
          <rect x={510} y={5} width={55} height={24} rx={4} fill="rgba(63,185,80,0.1)" />
          <text x={518} y={16} fill="rgba(255,255,255,0.4)" fontSize="8">Peak</text>
          <text x={518} y={25} fill="#3fb950" fontSize="10" fontWeight="700" fontFamily="monospace">{peakKills}</text>

          {/* Peak Hours */}
          <text x={575} y={16} fill="rgba(255,255,255,0.35)" fontSize="8">Peak Hours:</text>
          <text x={575} y={25} fill="#ffcc00" fontSize="9" fontWeight="600" fontFamily="monospace">
            {formatHour(huntingHours.peak_start)}-{formatHour(huntingHours.peak_end)}
          </text>

          {/* Low Activity */}
          <text x={675} y={16} fill="rgba(255,255,255,0.35)" fontSize="8">Low Activity:</text>
          <text x={675} y={25} fill="rgba(255,255,255,0.4)" fontSize="9" fontWeight="600" fontFamily="monospace">
            {formatHour(huntingHours.safe_start)}-{formatHour(huntingHours.safe_end)}
          </text>
        </g>

        {/* Top Stats Row - Deaths */}
        <g>
          {/* Deaths Total */}
          <rect x={820} y={5} width={90} height={24} rx={4} fill="rgba(255,68,68,0.15)" stroke="#ff4444" strokeWidth={1} />
          <text x={828} y={16} fill="rgba(255,255,255,0.5)" fontSize="8">● Deaths</text>
          <text x={828} y={25} fill="#ff4444" fontSize="11" fontWeight="700" fontFamily="monospace">{totalDeaths}</text>
          <text x={900} y={17} fill="#ff4444" fontSize="14">{deathTrend}</text>

          {/* Avg Deaths/Day */}
          <rect x={920} y={5} width={70} height={24} rx={4} fill="rgba(255,68,68,0.1)" />
          <text x={928} y={16} fill="rgba(255,255,255,0.4)" fontSize="8">Avg/Day</text>
          <text x={928} y={25} fill="#ff4444" fontSize="10" fontWeight="700" fontFamily="monospace">{avgDeathsPerDay.toFixed(1)}</text>

          {/* Last 3 Days */}
          <rect x={1000} y={5} width={70} height={24} rx={4} fill="rgba(255,68,68,0.1)" />
          <text x={1008} y={16} fill="rgba(255,255,255,0.4)" fontSize="8">Last 3 Days</text>
          <text x={1008} y={25} fill="#ff4444" fontSize="10" fontWeight="700" fontFamily="monospace">{last3DaysDeaths.toFixed(1)}</text>

          {/* Peak */}
          <rect x={1080} y={5} width={55} height={24} rx={4} fill="rgba(255,68,68,0.1)" />
          <text x={1088} y={16} fill="rgba(255,255,255,0.4)" fontSize="8">Peak</text>
          <text x={1088} y={25} fill="#ff4444" fontSize="10" fontWeight="700" fontFamily="monospace">{peakDeaths}</text>

          {/* Safe Hours */}
          <text x={1145} y={12} fill="rgba(255,255,255,0.35)" fontSize="7">Safe:</text>
          <text x={1145} y={20} fill="#3fb950" fontSize="8" fontWeight="600" fontFamily="monospace">
            {formatHour(safeDangerHours.safe_start)}-{formatHour(safeDangerHours.safe_end)}
          </text>

          {/* Danger Hours */}
          <text x={1145} y={27} fill="rgba(255,255,255,0.35)" fontSize="7">Danger:</text>
          <text x={1145} y={35} fill="#ff4444" fontSize="8" fontWeight="600" fontFamily="monospace">
            {formatHour(safeDangerHours.danger_start)}-{formatHour(safeDangerHours.danger_end)}
          </text>
        </g>

        {/* Y-Axis Titles */}
        <text
          x={padding.left - 5}
          y={padding.top - 10}
          fill="#8b949e"
          fontSize="9"
          textAnchor="end"
          fontWeight="600"
        >
          Kills/Deaths
        </text>
        <text
          x={width - padding.right + 5}
          y={padding.top - 10}
          fill="#a855f7"
          fontSize="9"
          textAnchor="start"
          fontWeight="600"
        >
          Active Pilots
        </text>

        {/* Bottom Legend */}
        <g>
          {/* Background */}
          <rect x={width / 2 - 180} y={height - 28} width={360} height={20} rx={4} fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)" strokeWidth={1} />

          {/* Kills Legend */}
          <line x1={width / 2 - 160} y1={height - 18} x2={width / 2 - 130} y2={height - 18} stroke="#3fb950" strokeWidth={2.5} />
          <text x={width / 2 - 125} y={height - 14} fill="rgba(255,255,255,0.7)" fontSize="9">Kills</text>

          {/* Deaths Legend */}
          <line x1={width / 2 - 70} y1={height - 18} x2={width / 2 - 40} y2={height - 18} stroke="#ff4444" strokeWidth={2.5} />
          <text x={width / 2 - 35} y={height - 14} fill="rgba(255,255,255,0.7)" fontSize="9">Deaths</text>

          {/* Active Pilots Legend */}
          <line x1={width / 2 + 30} y1={height - 18} x2={width / 2 + 60} y2={height - 18} stroke="#a855f7" strokeWidth={1.5} strokeDasharray="3,3" opacity={0.7} />
          <text x={width / 2 + 65} y={height - 14} fill="rgba(255,255,255,0.7)" fontSize="9">Active Pilots</text>
          <text x={width / 2 + 140} y={height - 14} fill="#a855f7" fontSize="9" fontWeight="700" fontFamily="monospace">(avg: {avgPilots.toFixed(0)} {pilotTrend})</text>
        </g>
      </svg>
    </div>
  );
}
