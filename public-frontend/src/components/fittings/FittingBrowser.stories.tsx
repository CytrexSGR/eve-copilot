import type { Meta, StoryObj } from '@storybook/react';
import FittingBrowser from './FittingBrowser';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { DRAKE_TYPE_ID } from '../../../.storybook/mocks/data/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof FittingBrowser> = {
  title: 'Fittings & Navigation/Fittings/FittingBrowser',
  component: FittingBrowser,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onTabChange: fn(),
    onSlotFilterChange: fn(),
    onSelectShip: fn(),
    onSelectModule: fn(),
    onAutoFitModule: fn(),
    onSelectCharge: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof FittingBrowser>;

export const HullsTab: Story = {
  args: {
    activeTab: 'hulls',
    slotFilter: null,
    shipTypeId: null,
  },
};

export const ModulesTab: Story = {
  args: {
    activeTab: 'modules',
    slotFilter: null,
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const ModulesWithHighSlotFilter: Story = {
  args: {
    activeTab: 'modules',
    slotFilter: 'high',
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const ChargesTab: Story = {
  args: {
    activeTab: 'charges',
    slotFilter: null,
    shipTypeId: DRAKE_TYPE_ID,
  },
};

export const DronesTab: Story = {
  args: {
    activeTab: 'drones',
    slotFilter: null,
    shipTypeId: null,
  },
};
