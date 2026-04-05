import type { Meta, StoryObj } from '@storybook/react';
import { HuntersTab } from './HuntersTab';
import type { WormholeOpportunity } from '../../types/wormhole';

/**
 * HuntersTab is a large component (~900 lines) showing wormhole hunting
 * opportunities with score breakdowns, resident intel, and structure data.
 * It receives opportunities data via props and filters by wormhole class.
 */
const meta: Meta<typeof HuntersTab> = {
  title: 'Intel & Battle/Wormhole/HuntersTab',
  component: HuntersTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    onClassChange: { action: 'classChanged' },
  },
};

export default meta;
type Story = StoryObj<typeof HuntersTab>;

const mockOpportunities: WormholeOpportunity[] = [
  {
    system_id: 31001234,
    system_name: 'J123456',
    wormhole_class: 5,
    statics: [{ code: 'H296', destination: 'C5' }, { code: 'K162', destination: 'null' }],
    opportunity_score: 82,
    score_breakdown: { activity: 32, recency: 28, weakness: 22 },
    difficulty: 'HARD',
    kills_7d: 89,
    kills_24h: 12,
    isk_destroyed_7d: 42_000_000_000,
    isk_destroyed_24h: 4_800_000_000,
    last_activity: '2026-02-20T21:30:00Z',
    is_hot: true,
    resident_corps: 2,
    residents: [
      {
        corporation_id: 98000001,
        name: 'Lazerhawks',
        ticker: 'HAWKS',
        kills: 89,
        losses: 12,
        last_seen: '2026-02-20T19:00:00Z',
      },
    ],
    ships: {
      capital: ['Naglfar'],
      battleship: ['Rattlesnake', 'Leshak'],
      cruiser: ['Tengu', 'Loki'],
      destroyer: [],
      frigate: [],
      other: [],
      threats: ['Sabre'],
    },
    recent_ships: ['Rattlesnake', 'Tengu', 'Sabre'],
    effect: { name: 'Magnetar', icon: 'M', bonus: '+44% Damage', color: '#ff4444' },
    prime_time: { dominant: 'EU', eu_pct: 65, us_pct: 25, au_pct: 10 },
    recent_kills: [
      {
        killmail_id: 133100001,
        time: '2026-02-20T18:30:00Z',
        value: 1_200_000_000,
        ship: 'Rattlesnake',
        ship_class: 'Battleship',
        victim: 'SomePlayer',
        corp: 'Lazerhawks',
      },
    ],
    structures: {
      total_lost: 1,
      total_value: 2_000_000_000,
      citadels: 2,
      engineering: 0,
      refineries: 1,
      recent: [{ type: 'Raitaru', time: '2026-02-18T12:00:00Z', value: 800_000_000 }],
    },
    hunters: [{ alliance_id: 99005065, name: 'Hard Knocks Inc.', kills: 45 }],
    resident_alliances: [{ alliance_id: 99007235, name: 'Lazerhawks', corps: 3, kills: 89 }],
  },
  {
    system_id: 31002345,
    system_name: 'J234567',
    wormhole_class: 3,
    statics: [{ code: 'D382', destination: 'HS' }],
    opportunity_score: 64,
    score_breakdown: { activity: 24, recency: 22, weakness: 18 },
    difficulty: 'EASY',
    kills_7d: 12,
    kills_24h: 2,
    isk_destroyed_7d: 1_200_000_000,
    isk_destroyed_24h: 200_000_000,
    last_activity: '2026-02-20T15:00:00Z',
    is_hot: false,
    resident_corps: 0,
    residents: [],
    ships: { capital: [], battleship: [], cruiser: [], destroyer: [], frigate: [], other: [], threats: [] },
    recent_ships: [],
    effect: null,
    prime_time: null,
    recent_kills: [],
    structures: null,
    hunters: [],
    resident_alliances: [],
  },
];

export const Default: Story = {
  args: {
    opportunities: mockOpportunities,
    selectedClass: null,
    onClassChange: () => {},
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    opportunities: [],
    selectedClass: null,
    onClassChange: () => {},
    loading: true,
  },
};

export const Empty: Story = {
  args: {
    opportunities: [],
    selectedClass: null,
    onClassChange: () => {},
    loading: false,
  },
};

export const Class5Filtered: Story = {
  args: {
    opportunities: mockOpportunities,
    selectedClass: 5,
    onClassChange: () => {},
    loading: false,
  },
};
