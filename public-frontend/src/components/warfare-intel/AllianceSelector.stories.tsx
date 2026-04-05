import type { Meta, StoryObj } from '@storybook/react';
import { AllianceSelector } from './AllianceSelector';
import { fn } from '@storybook/test';

const meta: Meta<typeof AllianceSelector> = {
  title: 'WarfareIntel/AllianceSelector',
  component: AllianceSelector,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof AllianceSelector>;

const mockCoalitions = [
  {
    coalition_id: 99003581,
    leader_name: 'Fraternity.',
    member_count: 8,
    total_ship_uses: 45000,
    primary_doctrines: ['Muninn Fleet', 'Eagle Fleet'],
    members: [
      { alliance_id: 99003581, alliance_name: 'Fraternity.', primary_doctrine: 'Muninn Fleet', total_uses: 25000 },
      { alliance_id: 99008425, alliance_name: 'Ranger Regiment', primary_doctrine: 'Eagle Fleet', total_uses: 8000 },
    ],
  },
];

const mockAlliances = [
  {
    alliance_id: 99003581,
    alliance_name: 'Fraternity.',
    ticker: 'FRT',
    kills: 8552,
    deaths: 10300,
    isk_destroyed: 1_200_000_000_000,
    isk_lost: 850_000_000_000,
    efficiency: 58.5,
  },
  {
    alliance_id: 1354830081,
    alliance_name: 'Goonswarm Federation',
    ticker: 'CONDI',
    kills: 6200,
    deaths: 4800,
    isk_destroyed: 1_800_000_000_000,
    isk_lost: 950_000_000_000,
    efficiency: 65.4,
  },
];

export const Default: Story = {
  args: {
    coalitions: mockCoalitions,
    alliances: mockAlliances,
    selectedCoalitionId: null,
    selectedAllianceId: 99003581,
    onCoalitionChange: fn(),
    onAllianceChange: fn(),
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    coalitions: [],
    alliances: [],
    selectedCoalitionId: null,
    selectedAllianceId: null,
    onCoalitionChange: fn(),
    onAllianceChange: fn(),
    loading: true,
  },
};

export const CoalitionSelected: Story = {
  args: {
    coalitions: mockCoalitions,
    alliances: mockAlliances,
    selectedCoalitionId: 99003581,
    selectedAllianceId: null,
    onCoalitionChange: fn(),
    onAllianceChange: fn(),
    loading: false,
  },
};
