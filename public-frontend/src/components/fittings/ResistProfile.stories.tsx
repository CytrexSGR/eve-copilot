import type { Meta, StoryObj } from '@storybook/react';
import { ResistProfile } from './ResistProfile';
import { mockDrakeStats } from '../../../.storybook/mocks/data/fittings';

const meta: Meta<typeof ResistProfile> = {
  title: 'Fittings & Navigation/Fittings/ResistProfile',
  component: ResistProfile,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof ResistProfile>;

export const DrakeShieldTank: Story = {
  args: {
    defense: mockDrakeStats.defense,
  },
};

export const ArmorTanked: Story = {
  args: {
    defense: {
      total_ehp: 52000,
      shield_ehp: 8000,
      armor_ehp: 38000,
      hull_ehp: 6000,
      shield_hp: 2500,
      armor_hp: 8500,
      hull_hp: 2800,
      shield_resists: { em: 0, thermal: 20, kinetic: 40, explosive: 50 },
      armor_resists: { em: 73.5, thermal: 67.2, kinetic: 56.8, explosive: 72.4 },
      hull_resists: { em: 0, thermal: 0, kinetic: 0, explosive: 0 },
      tank_type: 'armor',
    },
  },
};

export const MinimalResists: Story = {
  args: {
    defense: {
      total_ehp: 5000,
      shield_ehp: 2000,
      armor_ehp: 2000,
      hull_ehp: 1000,
      shield_hp: 1000,
      armor_hp: 1000,
      hull_hp: 800,
      shield_resists: { em: 0, thermal: 20, kinetic: 40, explosive: 50 },
      armor_resists: { em: 50, thermal: 45, kinetic: 25, explosive: 10 },
      hull_resists: { em: 0, thermal: 0, kinetic: 0, explosive: 0 },
      tank_type: 'shield',
    },
  },
};

export const HighResists: Story = {
  args: {
    defense: {
      total_ehp: 250000,
      shield_ehp: 180000,
      armor_ehp: 50000,
      hull_ehp: 20000,
      shield_hp: 25000,
      armor_hp: 5000,
      hull_hp: 4000,
      shield_resists: { em: 86.2, thermal: 88.5, kinetic: 84.1, explosive: 82.8 },
      armor_resists: { em: 50, thermal: 45, kinetic: 25, explosive: 10 },
      hull_resists: { em: 0, thermal: 0, kinetic: 0, explosive: 0 },
      tank_type: 'shield',
    },
  },
};
