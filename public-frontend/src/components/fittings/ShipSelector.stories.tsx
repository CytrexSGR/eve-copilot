import type { Meta, StoryObj } from '@storybook/react';
import { ShipSelector } from './ShipSelector';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { mockDrakeDetail } from '../../../.storybook/mocks/data/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof ShipSelector> = {
  title: 'Fittings & Navigation/Fittings/ShipSelector',
  component: ShipSelector,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onSelect: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof ShipSelector>;

export const NoShipSelected: Story = {
  args: {
    selectedShip: null,
  },
};

export const DrakeSelected: Story = {
  args: {
    selectedShip: mockDrakeDetail,
  },
};
