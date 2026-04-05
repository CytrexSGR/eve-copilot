import type { Meta, StoryObj } from '@storybook/react';
import { BattleDamageAnalysis } from './BattleDamageAnalysis';
import { mockDamageAnalysis } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleDamageAnalysis> = {
  title: 'Intel & Battle/Battle Report/BattleDamageAnalysis',
  component: BattleDamageAnalysis,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleDamageAnalysis>;

export const Default: Story = {
  args: {
    damageAnalysis: mockDamageAnalysis,
  },
};

export const NoData: Story = {
  args: {
    damageAnalysis: null,
  },
};

export const EMHeavy: Story = {
  args: {
    damageAnalysis: {
      ...mockDamageAnalysis,
      damage_profile: { em: 55.2, thermal: 22.1, kinetic: 12.8, explosive: 9.9 },
      primary_damage_type: 'em',
      secondary_damage_type: 'thermal',
      tank_recommendation: 'EM Hardeners + Thermal Resistance — Amarr weapon profile detected',
    },
  },
};
