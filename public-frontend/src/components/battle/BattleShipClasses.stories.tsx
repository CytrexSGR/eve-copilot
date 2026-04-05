import type { Meta, StoryObj } from '@storybook/react';
import { BattleShipClasses } from './BattleShipClasses';
import { mockShipClasses } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleShipClasses> = {
  title: 'Intel & Battle/Battle Report/BattleShipClasses',
  component: BattleShipClasses,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleShipClasses>;

export const Default: Story = {
  args: {
    shipClasses: mockShipClasses,
  },
};

export const NoData: Story = {
  args: {
    shipClasses: null,
  },
};

export const CapitalHeavy: Story = {
  args: {
    shipClasses: {
      total_kills: 28,
      group_by: 'ship_class',
      breakdown: {
        capital: 12,
        battleship: 8,
        logistics: 4,
        cruiser: 3,
        frigate: 1,
      },
    },
  },
};
