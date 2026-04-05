import type { Meta, StoryObj } from '@storybook/react';
import { CorpSummary } from './CorpSummary';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof CorpSummary> = {
  title: 'Characters & Account/Dashboard/CorpSummary',
  component: CorpSummary,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof CorpSummary>;

export const Default: Story = {};
