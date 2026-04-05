import type { Meta, StoryObj } from '@storybook/react';
import { StatBox, StatRow, InlineStat } from './StatBox';
import { COLORS } from '../../constants';

// ---------------------------------------------------------------------------
// StatBox
// ---------------------------------------------------------------------------

const statBoxMeta: Meta<typeof StatBox> = {
  title: 'Shared UI/StatBox',
  component: StatBox,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    size: {
      control: 'select',
      options: ['sm', 'md'],
    },
    color: { control: 'color' },
  },
};

export default statBoxMeta;
type StatBoxStory = StoryObj<typeof StatBox>;

export const Default: StatBoxStory = {
  args: {
    label: 'Kills (7d)',
    value: '3,604',
  },
};

export const WithColor: StatBoxStory = {
  args: {
    label: 'ISK Destroyed',
    value: '127.4B',
    color: COLORS.positive,
  },
};

export const Danger: StatBoxStory = {
  args: {
    label: 'ISK Lost',
    value: '84.2B',
    color: COLORS.negative,
  },
};

export const Warning: StatBoxStory = {
  args: {
    label: 'Fuel Remaining',
    value: '3 days',
    color: COLORS.warning,
  },
};

export const SmallSize: StatBoxStory = {
  args: {
    label: 'Active Pilots',
    value: '4,909',
    size: 'sm',
  },
};

export const NumericValue: StatBoxStory = {
  args: {
    label: 'Efficiency',
    value: 77.5,
    color: COLORS.positive,
  },
};

// ---------------------------------------------------------------------------
// StatRow
// ---------------------------------------------------------------------------

export const RowDefault: StoryObj<typeof StatRow> = {
  render: () => (
    <StatRow>
      <StatBox label="Kills" value="3,604" color={COLORS.positive} />
      <StatBox label="Deaths" value="1,048" color={COLORS.negative} />
      <StatBox label="Efficiency" value="77.5%" color={COLORS.positive} />
      <StatBox label="K/D Ratio" value="3.44" color={COLORS.accentBlue} />
    </StatRow>
  ),
};

export const RowSmall: StoryObj<typeof StatRow> = {
  render: () => (
    <StatRow gap="0.5rem">
      <StatBox label="DPS" value="847" size="sm" color={COLORS.negative} />
      <StatBox label="EHP" value="49,200" size="sm" color={COLORS.accentBlue} />
      <StatBox label="Cap" value="Stable" size="sm" color={COLORS.positive} />
      <StatBox label="Align" value="4.2s" size="sm" color={COLORS.warning} />
    </StatRow>
  ),
};

export const RowWrapping: StoryObj<typeof StatRow> = {
  render: () => (
    <div style={{ maxWidth: 400 }}>
      <StatRow>
        <StatBox label="Shield HP" value="5,500" color={COLORS.accentBlue} />
        <StatBox label="Armor HP" value="3,250" color={COLORS.warning} />
        <StatBox label="Hull HP" value="3,750" />
        <StatBox label="Total EHP" value="49,200" color={COLORS.positive} />
        <StatBox label="Signature" value="175m" />
        <StatBox label="Velocity" value="1,089 m/s" />
      </StatRow>
    </div>
  ),
};

// ---------------------------------------------------------------------------
// InlineStat
// ---------------------------------------------------------------------------

export const InlineDefault: StoryObj<typeof InlineStat> = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <InlineStat icon="⚔️" value="3,604" label="kills" color={COLORS.positive} />
      <InlineStat icon="💀" value="1,048" label="deaths" color={COLORS.negative} />
      <InlineStat icon="💰" value="127.4B" label="ISK destroyed" color={COLORS.accentBlue} />
      <InlineStat icon="📊" value="77.5%" label="efficiency" color={COLORS.positive} />
    </div>
  ),
};

export const InlineNoIcon: StoryObj<typeof InlineStat> = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <InlineStat value="1,089" label="m/s" />
      <InlineStat value="4.2s" label="align" color={COLORS.warning} />
      <InlineStat value="175m" label="sig" />
    </div>
  ),
};
