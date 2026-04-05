import type { Meta, StoryObj } from '@storybook/react';
import { ApplicationsTab } from './ApplicationsTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof ApplicationsTab> = {
  title: 'Corporation Tools/HR/ApplicationsTab',
  component: ApplicationsTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof ApplicationsTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
