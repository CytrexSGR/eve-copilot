import type { Meta, StoryObj } from '@storybook/react';
import { RouteCard } from './RouteCard';

const meta: Meta<typeof RouteCard> = {
  title: 'Home/RouteCard',
  component: RouteCard,
  parameters: { layout: 'padded' },
  decorators: [(Story) => (
    <div style={{ maxWidth: 400 }}><Story /></div>
  )],
};
export default meta;
type Story = StoryObj<typeof RouteCard>;

export const Dangerous: Story = {
  args: {
    route: {
      origin_system: 'Jita',
      destination_system: '1DQ1-A',
      jumps: 42,
      danger_score: 75,
      total_kills: 78,
      total_isk_destroyed: 12_500_000_000,
      systems: [
        { system_name: 'HED-GP', is_gate_camp: true },
      ],
    },
  },
};

export const Safe: Story = {
  args: {
    route: {
      origin_system: 'Dodixie',
      destination_system: 'Amarr',
      jumps: 12,
      danger_score: 5,
      total_kills: 2,
      total_isk_destroyed: 50_000_000,
    },
  },
};

export const MediumDanger: Story = {
  args: {
    route: {
      origin_system: 'Amarr',
      destination_system: 'GE-8JV',
      jumps: 28,
      danger_score: 35,
      total_kills: 22,
      total_isk_destroyed: 3_200_000_000,
    },
  },
};
