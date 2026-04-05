import type { Meta, StoryObj } from '@storybook/react';
import { GeographyView } from './GeographyView';

/**
 * GeographyView is a large data-fetching component (~1000+ lines) that
 * shows DOTLAN-powered live activity, sovereignty defense, territorial changes,
 * alliance power metrics, plus regional distribution, top systems, and home systems.
 *
 * It uses MSW handlers for API mocking (geography/extended endpoint).
 */
const meta: Meta<typeof GeographyView> = {
  title: 'Intel & Battle/Alliance Views/GeographyView',
  component: GeographyView,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof GeographyView>;

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
