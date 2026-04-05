import { http, HttpResponse } from 'msw';
import { mockGeographyExtended } from '../data/alliances';

/**
 * MSW handlers for Alliance/Corporation/PowerBloc shared view endpoints.
 */
export const allianceHandlers = [
  // Geography Extended — all 3 entity types
  http.get('/api/intelligence/fast/:entityId/geography/extended', () => {
    return HttpResponse.json(mockGeographyExtended);
  }),

  http.get('/api/intelligence/fast/corporation/:entityId/geography/extended', () => {
    return HttpResponse.json(mockGeographyExtended);
  }),

  http.get('/api/powerbloc/:entityId/geography/extended', () => {
    return HttpResponse.json(mockGeographyExtended);
  }),

  // Offensive Stats — all 3 entity types
  http.get('/api/intelligence/fast/:entityId/offensive-stats', () => {
    return HttpResponse.json({
      summary: { total_kills: 1847, isk_destroyed: '142.5B', avg_kill_value: '77.1M', kd_ratio: 2.07, efficiency: 62.4, solo_kill_pct: 12.3, capital_kills: 18, max_kill_value: 3_200_000_000 },
      engagement_profile: { solo: { kills: 227, percentage: 12.3 }, small: { kills: 554, percentage: 30.0 }, medium: { kills: 738, percentage: 39.9 }, large: { kills: 258, percentage: 14.0 }, blob: { kills: 70, percentage: 3.8 } },
      timeline: [],
      solo_killers: [],
      doctrine_profile: [],
      geographic: { regions: [], systems: [] },
    });
  }),

  // Defensive Stats
  http.get('/api/intelligence/fast/:entityId/defensive-stats', () => {
    return HttpResponse.json({
      summary: { total_deaths: 892, isk_lost: '68.2B', avg_loss_value: '76.5M', max_loss_value: 2_100_000_000, total_kills: 1847, efficiency: 62.4, kd_ratio: 2.07, solo_death_pct: 8.4, capital_losses: 5 },
      threat_profile: { solo_ganked: { deaths: 75, percentage: 8.4 }, small: { deaths: 267, percentage: 29.9 }, medium: { deaths: 356, percentage: 39.9 }, large: { deaths: 142, percentage: 15.9 }, blob: { deaths: 52, percentage: 5.8 } },
      death_prone_pilots: [],
      ship_losses: [],
      geographic: { regions: [], systems: [] },
    });
  }),

  // Capitals Stats
  http.get('/api/intelligence/fast/:entityId/capitals', () => {
    return HttpResponse.json({
      summary: { capital_kills: 18, capital_losses: 5, isk_destroyed: '42.8B', isk_lost: '12.1B', unique_pilots: 34, kd_ratio: 3.6, efficiency: 78.0 },
      fleet_composition: [
        { capital_type: 'Dreadnought', kills: 8, losses: 2, kills_pct: 44.4, losses_pct: 40 },
        { capital_type: 'Carrier', kills: 5, losses: 1, kills_pct: 27.8, losses_pct: 20 },
        { capital_type: 'Force Auxiliary', kills: 3, losses: 2, kills_pct: 16.7, losses_pct: 40 },
      ],
      ship_details: [],
      capital_timeline: [],
      geographic: { hotspots: [], regions: [] },
      top_killers: [],
      top_losers: [],
    });
  }),
];
