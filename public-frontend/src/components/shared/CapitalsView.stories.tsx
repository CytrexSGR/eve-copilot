import type { Meta, StoryObj } from '@storybook/react';
import { CapitalsView } from './CapitalsView';

/**
 * CapitalsView is a large data-fetching component that shows capital fleet
 * intelligence across 9 categories: summary, fleet composition, ship details,
 * timeline, geographic hotspots, top killers, top losers, engagements, and
 * recent activity.
 *
 * It uses MSW handlers for API mocking (capitals endpoint).
 */
const meta: Meta<typeof CapitalsView> = {
  title: 'Intel & Battle/Alliance Views/CapitalsView',
  component: CapitalsView,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof CapitalsView>;

export const Alliance: Story = {
  args: {
    entityType: 'alliance',
    entityId: 99003581,
    days: 7,
  },
};

export const Corporation: Story = {
  args: {
    entityType: 'corporation',
    entityId: 98378388,
    days: 7,
  },
};

export const PowerBloc: Story = {
  args: {
    entityType: 'powerbloc',
    entityId: 99003581,
    days: 30,
  },
};
