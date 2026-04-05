import type { Meta, StoryObj } from '@storybook/react';
import { DefensiveView } from './DefensiveView';

/**
 * DefensiveView is a large data-fetching component (~1200+ lines) showing
 * comprehensive 11-panel loss analysis and defensive assessment including
 * death timeline, defensive performance, danger systems, damage taken profile,
 * e-war threats, threat profile, death-prone pilots, ship/doctrine analysis,
 * geographic intelligence, and top threats.
 *
 * It uses MSW handlers for API mocking (defensive-stats endpoint).
 */
const meta: Meta<typeof DefensiveView> = {
  title: 'Intel & Battle/Alliance Views/DefensiveView',
  component: DefensiveView,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof DefensiveView>;

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
