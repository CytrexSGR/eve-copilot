import type { Meta, StoryObj } from '@storybook/react';
import ProjectedEffectsSection from './ProjectedEffectsSection';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof ProjectedEffectsSection> = {
  title: 'Fittings & Navigation/Fittings/ProjectedEffectsSection',
  component: ProjectedEffectsSection,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onEffectsChange: fn(),
    label: 'Projected Effects',
    color: '#d29922',
  },
};
export default meta;
type Story = StoryObj<typeof ProjectedEffectsSection>;

export const NoEffects: Story = {
  args: {
    effects: [],
  },
};

export const WebAndPaint: Story = {
  args: {
    effects: [
      { effect_type: 'web' as const, strength: 60, count: 1 },
      { effect_type: 'paint' as const, strength: 30, count: 1 },
    ],
  },
};

export const HeavyNeut: Story = {
  args: {
    effects: [
      { effect_type: 'neut' as const, strength: 600, count: 1 },
    ],
  },
};

export const LogiShield: Story = {
  args: {
    effects: [
      { effect_type: 'remote_shield' as const, strength: 350, count: 2 },
    ],
    label: 'Incoming Reps',
    color: '#3fb950',
  },
};
