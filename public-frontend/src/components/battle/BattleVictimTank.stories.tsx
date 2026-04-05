import type { Meta, StoryObj } from '@storybook/react';
import { BattleVictimTank } from './BattleVictimTank';
import { mockVictimTankAnalysis } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleVictimTank> = {
  title: 'Intel & Battle/Battle Report/BattleVictimTank',
  component: BattleVictimTank,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleVictimTank>;

export const Default: Story = {
  args: {
    data: mockVictimTankAnalysis,
  },
};

export const NoData: Story = {
  args: {
    data: null,
  },
};

export const ShieldHeavy: Story = {
  args: {
    data: {
      ...mockVictimTankAnalysis,
      tank_distribution: { shield: 78.5, armor: 15.2, hull: 6.3 },
      resist_profile: {
        em: { avg: 28.4, weakness: 'EXPLOIT' as const },
        thermal: { avg: 42.1, weakness: 'SOFT' as const },
        kinetic: { avg: 55.8, weakness: 'NORMAL' as const },
        explosive: { avg: 62.3, weakness: 'NORMAL' as const },
      },
    },
  },
};
