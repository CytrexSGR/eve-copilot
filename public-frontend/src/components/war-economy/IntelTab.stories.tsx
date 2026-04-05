import type { Meta, StoryObj } from '@storybook/react';
import { IntelTab } from './IntelTab';
import { mockWarEconomyAnalysis } from '../../../.storybook/mocks/data/war-economy';

const meta: Meta<typeof IntelTab> = {
  title: 'Economy & Market/War Economy/IntelTab',
  component: IntelTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof IntelTab>;

/**
 * Default: AI-generated market intelligence briefing with
 * summary, doctrine alert, key insights, trading recommendations,
 * and risk warnings sections.
 */
export const Default: Story = {
  args: {
    analysis: mockWarEconomyAnalysis,
    loading: false,
  },
};

/** Loading state: shows skeleton placeholder. */
export const Loading: Story = {
  args: {
    analysis: null,
    loading: true,
  },
};

/** Error state: analysis returned with error flag. */
export const Error: Story = {
  args: {
    analysis: {
      summary: '',
      insights: [],
      recommendations: [],
      risk_warnings: [],
      generated_at: '2026-02-20T12:00:00Z',
      error: 'Analysis service temporarily unavailable',
    },
    loading: false,
  },
};

/** No data: null analysis without loading. */
export const NoData: Story = {
  args: {
    analysis: null,
    loading: false,
  },
};
