import type { Meta, StoryObj } from '@storybook/react';
import FleetBoostSection from './FleetBoostSection';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof FleetBoostSection> = {
  title: 'Fittings & Navigation/Fittings/FleetBoostSection',
  component: FleetBoostSection,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onBoostsChange: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof FleetBoostSection>;

export const NoBoosts: Story = {
  args: {
    boosts: [],
  },
};

export const ShieldBoostActive: Story = {
  args: {
    boosts: [
      { buff_id: 1, value: 25.0 },
      { buff_id: 2, value: 25.0 },
      { buff_id: 3, value: 20.0 },
      { buff_id: 4, value: -15.0 },
    ],
  },
};

export const SkirmishBoostActive: Story = {
  args: {
    boosts: [
      { buff_id: 9, value: 20.0 },
      { buff_id: 10, value: 18.0 },
      { buff_id: 11, value: 15.0 },
    ],
  },
};
