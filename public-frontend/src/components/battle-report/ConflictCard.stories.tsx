import type { Meta, StoryObj } from '@storybook/react';
import { ConflictCard } from './ConflictCard';

const meta: Meta<typeof ConflictCard> = {
  title: 'BattleReport/ConflictCard',
  component: ConflictCard,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof ConflictCard>;

export const Default: Story = {
  args: {
    conflict: {
      alliance_1_id: 99003581,
      alliance_1_name: 'Fraternity.',
      alliance_1_kills: 2450,
      alliance_1_losses: 1820,
      alliance_1_efficiency: 62.4,
      alliance_2_id: 1354830081,
      alliance_2_name: 'Goonswarm Federation',
      alliance_2_kills: 1820,
      alliance_2_losses: 2450,
      alliance_2_efficiency: 42.6,
      primary_regions: ['Tribute', 'Vale of the Silent'],
      duration_days: 45,
      total_isk_destroyed: 850_000_000_000,
      active_systems: [
        { system_name: 'M-OEE8' },
        { system_name: 'SH1-6P' },
      ],
    },
  },
};

export const EvenFight: Story = {
  args: {
    conflict: {
      alliance_1_id: 99010079,
      alliance_1_name: 'Brave Collective',
      alliance_1_kills: 500,
      alliance_1_losses: 480,
      alliance_1_efficiency: 51.2,
      alliance_2_id: 99009163,
      alliance_2_name: 'Pandemic Horde',
      alliance_2_kills: 480,
      alliance_2_losses: 500,
      alliance_2_efficiency: 48.9,
      primary_regions: ['Catch'],
      duration_days: 7,
    },
  },
};
