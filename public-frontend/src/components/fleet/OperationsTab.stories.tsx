import type { Meta, StoryObj } from '@storybook/react';
import { OperationsTab } from './OperationsTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof OperationsTab> = {
  title: 'Corporation Tools/Fleet/OperationsTab',
  component: OperationsTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof OperationsTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
