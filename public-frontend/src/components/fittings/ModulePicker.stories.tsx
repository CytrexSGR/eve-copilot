import type { Meta, StoryObj } from '@storybook/react';
import { ModulePicker } from './ModulePicker';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';
import { DRAKE_TYPE_ID } from '../../../.storybook/mocks/data/fittings';

const meta: Meta<typeof ModulePicker> = {
  title: 'Fittings & Navigation/Fittings/ModulePicker',
  component: ModulePicker,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onSelectModule: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof ModulePicker>;

export const HighSlotModules: Story = {
  args: {
    slotType: 'high',
    droneMode: false,
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const MidSlotModules: Story = {
  args: {
    slotType: 'mid',
    droneMode: false,
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const LowSlotModules: Story = {
  args: {
    slotType: 'low',
    droneMode: false,
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const RigSlotModules: Story = {
  args: {
    slotType: 'rig',
    droneMode: false,
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const DroneMode: Story = {
  args: {
    slotType: null,
    droneMode: true,
  },
};

export const NoSlotSelected: Story = {
  args: {
    slotType: null,
    droneMode: false,
  },
};
