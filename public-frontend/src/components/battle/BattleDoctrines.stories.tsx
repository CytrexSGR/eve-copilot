import type { Meta, StoryObj } from '@storybook/react';
import { BattleDoctrines } from './BattleDoctrines';
import { mockCommanderIntel } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleDoctrines> = {
  title: 'Intel & Battle/Battle Report/BattleDoctrines',
  component: BattleDoctrines,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleDoctrines>;

export const Default: Story = {
  args: {
    doctrines: mockCommanderIntel.doctrines,
  },
};

export const NoDoctrines: Story = {
  args: {
    doctrines: {},
  },
};

export const MixedDoctrines: Story = {
  args: {
    doctrines: {
      'Fraternity.': {
        losses: [
          { ship_class: 'Heavy Assault Cruiser', ship_name: 'Muninn', count: 8, value: 1_200_000_000 },
          { ship_class: 'Logistics Cruiser', ship_name: 'Scimitar', count: 3, value: 450_000_000 },
        ],
        fielding: [
          { ship_class: 'Heavy Assault Cruiser', ship_name: 'Muninn', engagements: 12 },
          { ship_class: 'Logistics Cruiser', ship_name: 'Scimitar', engagements: 6 },
          { ship_class: 'Interdictor', ship_name: 'Sabre', engagements: 4 },
        ],
      },
      'Goonswarm Federation': {
        losses: [
          { ship_class: 'Battleship', ship_name: 'Nightmare', count: 5, value: 3_500_000_000 },
        ],
        fielding: [
          { ship_class: 'Battleship', ship_name: 'Nightmare', engagements: 18 },
          { ship_class: 'Logistics Cruiser', ship_name: 'Guardian', engagements: 8 },
        ],
      },
    },
  },
};
