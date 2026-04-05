import type { Meta, StoryObj } from '@storybook/react';
import { CoalitionCard } from './CoalitionCard';

const meta: Meta<typeof CoalitionCard> = {
  title: 'BattleReport/CoalitionCard',
  component: CoalitionCard,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof CoalitionCard>;

export const Default: Story = {
  args: {
    coalition: {
      name: 'Fraternity. Coalition',
      leader_alliance_id: 99003581,
      leader_name: 'Fraternity.',
      member_count: 8,
      members: [
        { alliance_id: 99003581, name: 'Fraternity.', activity: 8500 },
        { alliance_id: 99008425, name: 'Ranger Regiment', activity: 2100 },
        { alliance_id: 99009163, name: 'Pandemic Horde', activity: 6200 },
      ],
      total_kills: 17941,
      total_losses: 15262,
      isk_destroyed: 2_500_000_000_000,
      isk_lost: 1_650_000_000_000,
      efficiency: 60.1,
      total_activity: 32000,
      kills_series: [120, 150, 180, 200, 165, 210, 195],
      deaths_series: [100, 110, 130, 140, 120, 150, 135],
      esi_members: 53522,
      active_pilots: 7377,
    },
  },
};

export const SmallCoalition: Story = {
  args: {
    coalition: {
      name: 'Brave Coalition',
      leader_alliance_id: 99010079,
      leader_name: 'Brave Collective',
      member_count: 3,
      members: [
        { alliance_id: 99010079, name: 'Brave Collective', activity: 1200 },
      ],
      total_kills: 2500,
      total_losses: 3100,
      isk_destroyed: 180_000_000_000,
      isk_lost: 250_000_000_000,
      efficiency: 41.8,
      total_activity: 5600,
    },
  },
};
