import type { Meta, StoryObj } from '@storybook/react';
import { ShipDisplay } from './ShipDisplay';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { mockDrakeDetail, mockDrakePvEItems, mockDrakeStats } from '../../../.storybook/mocks/data/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof ShipDisplay> = {
  title: 'Fittings & Navigation/Fittings/ShipDisplay',
  component: ShipDisplay,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onSlotClick: fn(),
    onRemoveModule: fn(),
    onChargeClick: fn(),
    onModuleStateChange: fn(),
    isWeapon: (typeId: number) => typeId === 3170 || typeId === 25715,
  },
};
export default meta;
type Story = StoryObj<typeof ShipDisplay>;

export const FullyFittedDrake: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: mockDrakePvEItems,
    charges: { 27: 24517, 28: 24517, 29: 24517, 30: 24517, 31: 24517, 32: 24517, 33: 24517 },
    drones: [{ type_id: 2488, count: 3 }, { type_id: 2456, count: 2 }],
    stats: mockDrakeStats,
    activeSlot: null,
    moduleStates: {},
  },
};

export const EmptyFitting: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: [],
    charges: {},
    drones: [],
    stats: null,
    activeSlot: null,
    moduleStates: {},
  },
};

export const NoShipSelected: Story = {
  args: {
    shipDetail: null,
    items: [],
    charges: {},
    drones: [],
    stats: null,
    activeSlot: null,
    moduleStates: {},
  },
};

export const WithActiveSlot: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: mockDrakePvEItems.slice(0, 7),
    charges: {},
    drones: [],
    stats: null,
    activeSlot: { type: 'mid' as const, flag: 19 },
    moduleStates: {},
  },
};

export const WithOverheatedModules: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: mockDrakePvEItems,
    charges: {},
    drones: [],
    stats: mockDrakeStats,
    activeSlot: null,
    moduleStates: { 27: 'overheated' as const, 28: 'overheated' as const, 14: 'offline' as const },
  },
};
