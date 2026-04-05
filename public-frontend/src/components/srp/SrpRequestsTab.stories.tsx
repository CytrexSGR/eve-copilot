import type { Meta, StoryObj } from '@storybook/react';
import { SrpRequestsTab } from './SrpRequestsTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof SrpRequestsTab> = {
  title: 'Corporation Tools/SRP/SrpRequestsTab',
  component: SrpRequestsTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof SrpRequestsTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
