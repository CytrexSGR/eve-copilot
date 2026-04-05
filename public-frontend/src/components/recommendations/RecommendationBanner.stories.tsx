import type { Meta, StoryObj } from '@storybook/react';
import { RecommendationBanner } from './RecommendationBanner';

const meta: Meta<typeof RecommendationBanner> = {
  title: 'Recommendations/RecommendationBanner',
  component: RecommendationBanner,
  parameters: { layout: 'padded' },
  decorators: [(Story) => (
    <div style={{ maxWidth: 600 }}><Story /></div>
  )],
};
export default meta;
type Story = StoryObj<typeof RecommendationBanner>;

export const CanAfford: Story = {
  args: {
    ps: {
      score: 85,
      canAfford: true,
      hasSkills: true,
      affordPercent: 100,
      missingSkillCount: 0,
      iskPerHour: 125_000_000,
      riskLevel: 'low',
      recommendation: 'Highly recommended for your profile',
    },
  },
};

export const NeedISK: Story = {
  args: {
    ps: {
      score: 45,
      canAfford: false,
      hasSkills: true,
      affordPercent: 45,
      missingSkillCount: 0,
      iskPerHour: 80_000_000,
      riskLevel: 'medium',
      recommendation: 'Consider saving up before purchasing',
    },
  },
};

export const MissingSkills: Story = {
  args: {
    ps: {
      score: 60,
      canAfford: true,
      hasSkills: false,
      affordPercent: 100,
      missingSkillCount: 3,
      iskPerHour: 0,
      riskLevel: 'medium',
      recommendation: 'Train required skills first',
    },
  },
};

export const Compact: Story = {
  args: {
    ps: {
      score: 92,
      canAfford: true,
      hasSkills: true,
      affordPercent: 100,
      missingSkillCount: 0,
      iskPerHour: 250_000_000,
      riskLevel: 'low',
      recommendation: 'Great choice',
    },
    compact: true,
  },
};

export const CompactNeedISK: Story = {
  args: {
    ps: {
      score: 15,
      canAfford: false,
      hasSkills: false,
      affordPercent: 22,
      missingSkillCount: 5,
      iskPerHour: 0,
      riskLevel: 'high',
      recommendation: 'Not recommended',
    },
    compact: true,
  },
};
