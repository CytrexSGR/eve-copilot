import { http, HttpResponse } from 'msw';
import {
  mockBattleInfo,
  mockCommanderIntel,
  mockBattleSides,
  mockKills,
  mockShipClasses,
  mockDamageAnalysis,
  mockVictimTankAnalysis,
  mockStrategicContext,
  mockAttackerLoadouts,
  mockParticipants,
  mockSystemDanger,
  mockWarSummary,
} from '../data/battles';

/**
 * MSW handlers for battle-related API endpoints.
 */
export const battleHandlers = [
  // GET /api/war/battle/:id
  http.get('/api/war/battle/:id', () => {
    return HttpResponse.json(mockBattleInfo);
  }),

  // GET /api/war/battle/:id/sides
  http.get('/api/war/battle/:id/sides', () => {
    return HttpResponse.json(mockBattleSides);
  }),

  // GET /api/war/battle/:id/commander-intel
  http.get('/api/war/battle/:id/commander-intel', () => {
    return HttpResponse.json(mockCommanderIntel);
  }),

  // GET /api/war/battle/:id/kills
  http.get('/api/war/battle/:id/kills', () => {
    return HttpResponse.json(mockKills);
  }),

  // GET /api/war/battle/:id/ship-classes
  http.get('/api/war/battle/:id/ship-classes', () => {
    return HttpResponse.json(mockShipClasses);
  }),

  // GET /api/war/battle/:id/damage-analysis
  http.get('/api/war/battle/:id/damage-analysis', () => {
    return HttpResponse.json(mockDamageAnalysis);
  }),

  // GET /api/war/battle/:id/victim-tank-analysis
  http.get('/api/war/battle/:id/victim-tank-analysis', () => {
    return HttpResponse.json(mockVictimTankAnalysis);
  }),

  // GET /api/war/battle/:id/strategic-context
  http.get('/api/war/battle/:id/strategic-context', () => {
    return HttpResponse.json(mockStrategicContext);
  }),

  // GET /api/war/battle/:id/attacker-loadouts
  http.get('/api/war/battle/:id/attacker-loadouts', () => {
    return HttpResponse.json(mockAttackerLoadouts);
  }),

  // GET /api/war/battle/:id/participants
  http.get('/api/war/battle/:id/participants', () => {
    return HttpResponse.json(mockParticipants);
  }),

  // GET /api/war/system/:id/danger
  http.get('/api/war/system/:id/danger', () => {
    return HttpResponse.json(mockSystemDanger);
  }),

  // GET /api/war/summary
  http.get('/api/war/summary', () => {
    return HttpResponse.json(mockWarSummary);
  }),

  // GET /api/intelligence/fast/alliance/:id/offensive-stats (for alliance card expand)
  http.get('/api/intelligence/fast/alliance/:id/offensive-stats', () => {
    return HttpResponse.json({
      summary: { isk_efficiency: 62.4, kd_ratio: 2.1, kills: 1247, deaths: 594 },
      fleet_profile: { avg_fleet_size: 27.3, median_fleet_size: 18, max_fleet_size: 142 },
    });
  }),

  // GET /api/war/power-blocs/live (for BattleSidesPanel power bloc cache)
  http.get('/api/war/power-blocs/live', () => {
    return HttpResponse.json({
      coalitions: [
        {
          name: 'Fraternity. Coalition',
          members: [
            { alliance_id: 99003581, alliance_name: 'Fraternity.' },
            { alliance_id: 99009163, alliance_name: 'Ranger Regiment' },
          ],
        },
        {
          name: 'Imperium',
          members: [
            { alliance_id: 1354830081, alliance_name: 'Goonswarm Federation' },
            { alliance_id: 99003214, alliance_name: 'The Initiative.' },
          ],
        },
      ],
    });
  }),
];
