import type { Meta, StoryObj } from '@storybook/react';
import { FreightCalculator } from './FreightCalculator';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';

const meta: Meta<typeof FreightCalculator> = {
  title: 'Fittings & Navigation/Shopping/FreightCalculator',
  component: FreightCalculator,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof FreightCalculator>;

export const Default: Story = {};
