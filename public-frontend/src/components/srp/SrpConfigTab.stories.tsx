import type { Meta, StoryObj } from '@storybook/react';
import { SrpConfigTab } from './SrpConfigTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof SrpConfigTab> = {
  title: 'Corporation Tools/SRP/SrpConfigTab',
  component: SrpConfigTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof SrpConfigTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
