import type { Meta, StoryObj } from '@storybook/react';
import { ListManager } from './ListManager';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';

const meta: Meta<typeof ListManager> = {
  title: 'Fittings & Navigation/Shopping/ListManager',
  component: ListManager,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof ListManager>;

export const Default: Story = {};
