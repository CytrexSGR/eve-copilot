import type { Meta, StoryObj } from '@storybook/react';
import { SlotEditor } from './SlotEditor';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { mockDrakeDetail, mockDrakePvEItems } from '../../../.storybook/mocks/data/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof SlotEditor> = {
  title: 'Fittings & Navigation/Fittings/SlotEditor',
  component: SlotEditor,
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
type Story = StoryObj<typeof SlotEditor>;

export const FullyFitted: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: mockDrakePvEItems,
    charges: { 27: 24517, 28: 24517, 29: 24517, 30: 24517, 31: 24517, 32: 24517, 33: 24517 },
    moduleStates: {},
    activeSlot: null,
  },
};

export const EmptyFitting: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: [],
    charges: {},
    moduleStates: {},
    activeSlot: null,
  },
};

export const ActiveSlotHighlighted: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: mockDrakePvEItems.slice(0, 7),
    charges: {},
    moduleStates: {},
    activeSlot: { type: 'mid' as const, flag: 19 },
  },
};

export const OverheatedModules: Story = {
  args: {
    shipDetail: mockDrakeDetail,
    items: mockDrakePvEItems,
    charges: {},
    moduleStates: { 27: 'overheated' as const, 28: 'overheated' as const, 29: 'active' as const, 14: 'offline' as const },
    activeSlot: null,
  },
};
