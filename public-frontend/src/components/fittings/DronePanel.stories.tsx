import type { Meta, StoryObj } from '@storybook/react';
import { DronePanel } from './DronePanel';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof DronePanel> = {
  title: 'Fittings & Navigation/Fittings/DronePanel',
  component: DronePanel,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onAddDrone: fn(),
    onRemoveDrone: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof DronePanel>;

export const WithDrones: Story = {
  args: {
    drones: [
      { type_id: 2488, count: 3 },
      { type_id: 2456, count: 2 },
    ],
    droneBayTotal: 25,
    droneBandwidthTotal: 25,
  },
};

export const EmptyDroneBay: Story = {
  args: {
    drones: [],
    droneBayTotal: 50,
    droneBandwidthTotal: 50,
  },
};

export const NoDroneBay: Story = {
  args: {
    drones: [],
    droneBayTotal: 0,
    droneBandwidthTotal: 0,
  },
};

export const FullDroneBay: Story = {
  args: {
    drones: [
      { type_id: 2488, count: 5 },
      { type_id: 2456, count: 5 },
    ],
    droneBayTotal: 125,
    droneBandwidthTotal: 125,
  },
};
