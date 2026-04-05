import type { Meta, StoryObj } from '@storybook/react';
import { ChargePicker } from './ChargePicker';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof ChargePicker> = {
  title: 'Fittings & Navigation/Fittings/ChargePicker',
  component: ChargePicker,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onSelectCharge: fn(),
    onClose: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof ChargePicker>;

export const HeavyMissileLauncher: Story = {
  args: {
    weaponTypeId: 3170,
  },
};
