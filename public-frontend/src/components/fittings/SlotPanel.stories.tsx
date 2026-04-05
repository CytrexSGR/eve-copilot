import type { Meta, StoryObj } from '@storybook/react';
import { SlotPanel } from './SlotPanel';
import { mockDrakePvEItems } from '../../../.storybook/mocks/data/fittings';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';

const meta: Meta<typeof SlotPanel> = {
  title: 'Fittings & Navigation/Fittings/SlotPanel',
  component: SlotPanel,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof SlotPanel>;

const highSlotItems = mockDrakePvEItems.filter(i => i.flag >= 27 && i.flag <= 34);
const midSlotItems = mockDrakePvEItems.filter(i => i.flag >= 19 && i.flag <= 26);
const lowSlotItems = mockDrakePvEItems.filter(i => i.flag >= 11 && i.flag <= 18);
const rigSlotItems = mockDrakePvEItems.filter(i => i.flag >= 92 && i.flag <= 99);

export const HighSlots: Story = {
  args: {
    label: 'High Slots',
    items: highSlotItems,
    total: 7,
    color: '#f85149',
  },
};

export const MidSlots: Story = {
  args: {
    label: 'Mid Slots',
    items: midSlotItems,
    total: 6,
    color: '#00d4ff',
  },
};

export const LowSlots: Story = {
  args: {
    label: 'Low Slots',
    items: lowSlotItems,
    total: 4,
    color: '#3fb950',
  },
};

export const RigSlots: Story = {
  args: {
    label: 'Rig Slots',
    items: rigSlotItems,
    total: 3,
    color: '#d29922',
  },
};

export const EmptySlots: Story = {
  args: {
    label: 'High Slots',
    items: [],
    total: 8,
    color: '#f85149',
  },
};

export const PartiallyFilled: Story = {
  args: {
    label: 'Mid Slots',
    items: midSlotItems.slice(0, 2),
    total: 6,
    color: '#00d4ff',
  },
};
