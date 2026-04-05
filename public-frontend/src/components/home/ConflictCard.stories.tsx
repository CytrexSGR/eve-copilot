import type { Meta, StoryObj } from '@storybook/react';
import { ConflictCard } from './ConflictCard';

const meta: Meta<typeof ConflictCard> = {
  title: 'Home/ConflictCard',
  component: ConflictCard,
  parameters: { layout: 'padded' },
  decorators: [(Story) => (
    <div style={{ maxWidth: 400 }}><Story /></div>
  )],
};
export default meta;
type Story = StoryObj<typeof ConflictCard>;

export const Default: Story = {
  args: {
    conflict: {
      alliance_1_id: 99003581,
      alliance_1_name: 'Fraternity.',
      alliance_1_kills: 2450,
      alliance_1_isk_destroyed: 850_000_000_000,
      alliance_1_efficiency: 62.4,
      alliance_2_id: 1354830081,
      alliance_2_name: 'Goonswarm Federation',
      alliance_2_kills: 1820,
      alliance_2_isk_destroyed: 520_000_000_000,
      alliance_2_efficiency: 42.6,
      kills_series_1: [120, 150, 180, 200, 165, 210, 195],
      kills_series_2: [100, 110, 130, 140, 120, 150, 135],
    },
  },
};

export const EvenFight: Story = {
  args: {
    conflict: {
      alliance_1_id: 99010079,
      alliance_1_name: 'Brave Collective',
      alliance_1_kills: 500,
      alliance_1_isk_destroyed: 80_000_000_000,
      alliance_1_efficiency: 51.2,
      alliance_2_id: 99009163,
      alliance_2_name: 'Pandemic Horde',
      alliance_2_kills: 480,
      alliance_2_isk_destroyed: 75_000_000_000,
      alliance_2_efficiency: 48.9,
    },
  },
};
