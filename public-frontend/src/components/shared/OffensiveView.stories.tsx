import type { Meta, StoryObj } from '@storybook/react';
import { OffensiveView } from './OffensiveView';

/**
 * OffensiveView is a large data-fetching component (~1500+ lines) showing
 * comprehensive 12-panel offensive capability assessment including kill timeline,
 * combat performance, hot systems, damage profile, e-war usage, engagement profile,
 * solo killers, geographic analysis, ship/doctrine profile, kill velocity trends,
 * top victims, and victim tank profile (PowerBloc only).
 *
 * It uses MSW handlers for API mocking (offensive-stats endpoint).
 */
const meta: Meta<typeof OffensiveView> = {
  title: 'Intel & Battle/Alliance Views/OffensiveView',
  component: OffensiveView,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof OffensiveView>;

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
