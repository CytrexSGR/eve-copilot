/**
 * OverviewView Component
 *
 * Main Overview tab displaying 7 intelligence summary cards + 3 activity insights.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CombinedTimelineCard,
  OffensiveCard,
  DefensiveCard,
  CapitalCard,
  PilotCard,
  GeographyCard,
  ActivityCard,
  HuntingCard,
} from './overview';
import { corpApi } from '../../services/corporationApi';
import type {
  ParticipationTrendsResponse,
  BurnoutIndexResponse,
  AttritionTrackerResponse,
} from '../../types/corporation';

interface OverviewViewProps {
  corpId: number;
  days: number;
}

export function OverviewView({ corpId, days }: OverviewViewProps) {
  const [trends, setTrends] = useState<ParticipationTrendsResponse | null>(null);
  const [burnout, setBurnout] = useState<BurnoutIndexResponse | null>(null);
  const [attrition, setAttrition] = useState<AttritionTrackerResponse | null>(null);

  useEffect(() => {
    corpApi.getParticipationTrends(corpId, Math.max(days, 14)).then(setTrends).catch(() => {});
    corpApi.getBurnoutIndex(corpId, Math.max(days, 14)).then(setBurnout).catch(() => {});
    corpApi.getAttritionTracker(corpId, Math.max(days, 30)).then(setAttrition).catch(() => {});
  }, [corpId, days]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '0.75rem' }}>
      {/* COMBINED TIMELINE */}
      <CombinedTimelineCard corpId={corpId} days={days} />

      {/* SUMMARY CARDS GRID */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '0.75rem',
        }}
      >
        {/* Row 1: Offensive + Defensive + Capital */}
        <OffensiveCard corpId={corpId} days={days} />
        <DefensiveCard corpId={corpId} days={days} />
        <CapitalCard corpId={corpId} days={days} />

        {/* Row 2: Pilot + Geography + Activity */}
        <PilotCard corpId={corpId} days={days} />
        <GeographyCard corpId={corpId} days={days} />
        <ActivityCard corpId={corpId} days={days} />

        {/* Row 3: Hunting */}
        <HuntingCard corpId={corpId} days={days} />
      </div>

      {/* PARTICIPATION TRENDS */}
      {trends && trends.daily.length > 0 && (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          padding: '0.5rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#58a6ff', textTransform: 'uppercase' }}>
                📈 Participation Trends
              </span>
              {trends.trend.direction !== 'insufficient_data' && (
                <span style={{
                  fontSize: '0.55rem',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: trends.trend.direction === 'rising' ? 'rgba(63,185,80,0.2)' : trends.trend.direction === 'falling' ? 'rgba(248,81,73,0.2)' : 'rgba(255,204,0,0.2)',
                  color: trends.trend.direction === 'rising' ? '#3fb950' : trends.trend.direction === 'falling' ? '#f85149' : '#ffcc00',
                }}>
                  {trends.trend.direction === 'rising' ? '↑' : trends.trend.direction === 'falling' ? '↓' : '→'} {trends.trend.direction.toUpperCase()}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.6rem' }}>
              <span>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Kills Trend: </span>
                <span style={{ color: trends.trend.kills_change_pct >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                  {trends.trend.kills_change_pct >= 0 ? '+' : ''}{trends.trend.kills_change_pct}%
                </span>
              </span>
              <span>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Pilots Trend: </span>
                <span style={{ color: trends.trend.pilots_change_pct >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                  {trends.trend.pilots_change_pct >= 0 ? '+' : ''}{trends.trend.pilots_change_pct}%
                </span>
              </span>
            </div>
          </div>

          {/* Trend Chart - Kills + Deaths bars */}
          <div style={{ display: 'flex', gap: '2px', height: '60px', alignItems: 'flex-end' }}>
            {(() => {
              const maxVal = Math.max(...trends.daily.map(d => Math.max(d.kills, d.deaths)), 1);
              return trends.daily.map((d, i) => (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1px', height: '100%', justifyContent: 'flex-end' }}>
                  <div
                    style={{
                      height: `${(d.kills / maxVal) * 100}%`,
                      minHeight: d.kills > 0 ? '2px' : 0,
                      background: '#3fb950',
                      borderRadius: '1px 1px 0 0',
                      opacity: 0.8,
                    }}
                    title={`${d.day}: ${d.kills} kills`}
                  />
                  <div
                    style={{
                      height: `${(d.deaths / maxVal) * 100}%`,
                      minHeight: d.deaths > 0 ? '2px' : 0,
                      background: '#f85149',
                      borderRadius: '0 0 1px 1px',
                      opacity: 0.8,
                    }}
                    title={`${d.day}: ${d.deaths} deaths`}
                  />
                </div>
              ));
            })()}
          </div>

          {/* Pilot Activity Line */}
          <div style={{ marginTop: '0.3rem', display: 'flex', gap: '2px', height: '20px', alignItems: 'flex-end' }}>
            {(() => {
              const maxPilots = Math.max(...trends.daily.map(d => d.active_pilots), 1);
              return trends.daily.map((d, i) => (
                <div key={i} style={{
                  flex: 1,
                  height: `${(d.active_pilots / maxPilots) * 100}%`,
                  minHeight: d.active_pilots > 0 ? '2px' : 0,
                  background: '#a855f7',
                  borderRadius: '1px',
                  opacity: 0.7,
                }} title={`${d.day}: ${d.active_pilots} active pilots`} />
              ));
            })()}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
            <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
              {trends.daily[0]?.day?.slice(5) || ''}
            </span>
            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.5rem' }}>
              <span><span style={{ color: '#3fb950' }}>■</span> Kills</span>
              <span><span style={{ color: '#f85149' }}>■</span> Deaths</span>
              <span><span style={{ color: '#a855f7' }}>■</span> Active Pilots</span>
            </div>
            <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
              {trends.daily[trends.daily.length - 1]?.day?.slice(5) || ''}
            </span>
          </div>
        </div>
      )}

      {/* BURNOUT INDEX + ATTRITION TRACKER */}
      {(burnout || attrition) && (
        <div style={{ display: 'grid', gridTemplateColumns: burnout && attrition ? '1fr 1fr' : '1fr', gap: '0.75rem' }}>

          {/* BURNOUT INDEX */}
          {burnout && burnout.daily.length > 0 && (
            <div style={{
              background: 'rgba(0,0,0,0.3)',
              borderRadius: '6px',
              border: '1px solid rgba(255,255,255,0.08)',
              borderLeft: `3px solid ${
                burnout.summary.burnout_risk === 'critical' ? '#ff0000'
                : burnout.summary.burnout_risk === 'high' ? '#ff6600'
                : burnout.summary.burnout_risk === 'moderate' ? '#ffcc00'
                : '#3fb950'
              }`,
              padding: '0.5rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff6600', textTransform: 'uppercase' }}>
                    🔥 Burnout Index
                  </span>
                  <span style={{
                    fontSize: '0.5rem',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: burnout.summary.burnout_risk === 'critical' ? 'rgba(255,0,0,0.2)'
                      : burnout.summary.burnout_risk === 'high' ? 'rgba(255,102,0,0.2)'
                      : burnout.summary.burnout_risk === 'moderate' ? 'rgba(255,204,0,0.2)'
                      : 'rgba(63,185,80,0.2)',
                    color: burnout.summary.burnout_risk === 'critical' ? '#ff0000'
                      : burnout.summary.burnout_risk === 'high' ? '#ff6600'
                      : burnout.summary.burnout_risk === 'moderate' ? '#ffcc00'
                      : '#3fb950',
                  }}>
                    {burnout.summary.burnout_risk.toUpperCase()}
                  </span>
                </div>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
                  {burnout.summary.avg_kills_per_pilot} kills/pilot
                </span>
              </div>

              {/* Stats Row */}
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.4rem', fontSize: '0.6rem' }}>
                <span>
                  <span style={{ color: 'rgba(255,255,255,0.4)' }}>Workload: </span>
                  <span style={{ color: burnout.summary.kpp_trend_pct > 5 ? '#f85149' : burnout.summary.kpp_trend_pct < -5 ? '#3fb950' : '#ffcc00', fontWeight: 600 }}>
                    {burnout.summary.kpp_trend_pct > 0 ? '+' : ''}{burnout.summary.kpp_trend_pct}%
                  </span>
                </span>
                <span>
                  <span style={{ color: 'rgba(255,255,255,0.4)' }}>Pilots: </span>
                  <span style={{ color: burnout.summary.pilot_trend_pct >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                    {burnout.summary.pilot_trend_pct > 0 ? '+' : ''}{burnout.summary.pilot_trend_pct}%
                  </span>
                </span>
              </div>

              {/* Dual Chart: Kills/Pilot (orange) + Active Pilots (blue) */}
              <div style={{ display: 'flex', gap: '2px', height: '50px', alignItems: 'flex-end' }}>
                {(() => {
                  const maxKpp = Math.max(...burnout.daily.map(d => d.kills_per_pilot), 0.1);
                  return burnout.daily.map((d, i) => (
                    <div key={i} style={{
                      flex: 1,
                      height: `${(d.kills_per_pilot / maxKpp) * 100}%`,
                      minHeight: d.kills_per_pilot > 0 ? '2px' : 0,
                      background: d.kills_per_pilot > maxKpp * 0.7 ? '#f85149' : d.kills_per_pilot > maxKpp * 0.4 ? '#ff6600' : '#ffcc00',
                      borderRadius: '1px',
                      opacity: 0.8,
                    }} title={`${d.day}: ${d.kills_per_pilot} kills/pilot, ${d.active_pilots} pilots`} />
                  ));
                })()}
              </div>
              <div style={{ display: 'flex', gap: '2px', height: '20px', alignItems: 'flex-end', marginTop: '2px' }}>
                {(() => {
                  const maxP = Math.max(...burnout.daily.map(d => d.active_pilots), 1);
                  return burnout.daily.map((d, i) => (
                    <div key={i} style={{
                      flex: 1,
                      height: `${(d.active_pilots / maxP) * 100}%`,
                      minHeight: d.active_pilots > 0 ? '2px' : 0,
                      background: '#58a6ff',
                      borderRadius: '1px',
                      opacity: 0.6,
                    }} title={`${d.day}: ${d.active_pilots} active pilots`} />
                  ));
                })()}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.2rem', fontSize: '0.5rem' }}>
                <span style={{ color: 'rgba(255,255,255,0.3)' }}>{burnout.daily[0]?.day?.slice(5)}</span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <span><span style={{ color: '#ff6600' }}>■</span> Kills/Pilot</span>
                  <span><span style={{ color: '#58a6ff' }}>■</span> Active Pilots</span>
                </div>
                <span style={{ color: 'rgba(255,255,255,0.3)' }}>{burnout.daily[burnout.daily.length - 1]?.day?.slice(5)}</span>
              </div>
            </div>
          )}

          {/* ATTRITION TRACKER */}
          {attrition && attrition.summary.departed_pilots > 0 && (
            <div style={{
              background: 'rgba(0,0,0,0.3)',
              borderRadius: '6px',
              border: '1px solid rgba(255,255,255,0.08)',
              borderLeft: `3px solid ${attrition.summary.retention_rate >= 80 ? '#3fb950' : attrition.summary.retention_rate >= 60 ? '#ffcc00' : '#f85149'}`,
              overflow: 'hidden',
            }}>
              <div style={{
                padding: '0.4rem 0.5rem',
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#f85149', textTransform: 'uppercase' }}>
                  🚪 Attrition Tracker
                </span>
                <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>{attrition.period_days}d</span>
              </div>

              {/* Summary Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.3rem', padding: '0.4rem 0.5rem' }}>
                <div style={{ textAlign: 'center', padding: '0.3rem', background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
                    {attrition.summary.retention_rate}%
                  </div>
                  <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>RETENTION</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.3rem', background: 'rgba(248,81,73,0.1)', borderRadius: '3px' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f85149', fontFamily: 'monospace' }}>
                    {attrition.summary.departed_pilots}
                  </div>
                  <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>DEPARTED</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.3rem', background: 'rgba(88,166,255,0.1)', borderRadius: '3px' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#58a6ff', fontFamily: 'monospace' }}>
                    {attrition.summary.tracked_destinations}
                  </div>
                  <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>TRACKED</div>
                </div>
              </div>

              {/* Destinations */}
              {attrition.destinations.length > 0 && (
                <div style={{ padding: '0 0.5rem 0.4rem' }}>
                  <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.25rem' }}>
                    Where they went:
                  </div>
                  {attrition.destinations.slice(0, 5).map((dest, i) => (
                    <Link key={dest.corporation_id} to={`/corporation/${dest.corporation_id}`} style={{ textDecoration: 'none' }}>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        padding: '0.25rem 0.3rem',
                        marginBottom: '0.1rem',
                        background: i === 0 ? 'rgba(248,81,73,0.1)' : 'rgba(255,255,255,0.02)',
                        borderRadius: '3px',
                        borderLeft: `2px solid ${i === 0 ? '#f85149' : 'rgba(255,255,255,0.1)'}`,
                      }}>
                        <img
                          src={`https://images.evetech.net/corporations/${dest.corporation_id}/logo?size=32`}
                          alt=""
                          style={{ width: 16, height: 16, borderRadius: 2 }}
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                        <span style={{ fontSize: '0.65rem', color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {dest.corporation_name}
                        </span>
                        <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>[{dest.ticker}]</span>
                        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#f85149', fontFamily: 'monospace' }}>
                          {dest.pilot_count}
                        </span>
                        <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>pilots</span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
