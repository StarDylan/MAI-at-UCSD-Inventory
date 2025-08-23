// File: BoxInventoryCard.story.tsx
import React from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { Container, MantineProvider } from '@mantine/core';
import BoxInventoryCard, { BoxInventoryCardProps } from './InventoryInfographic';

const meta: Meta<typeof BoxInventoryCard> = {
  title: 'Inventory/BoxInventoryCard',
  component: BoxInventoryCard,
  argTypes: {
    itemsPerBox: { control: { type: 'number', min: 0 } },
    boxCount: { control: { type: 'number', min: 0 } },
    unit: { control: { type: 'radio' }, options: ['in', 'cm'] },
    color: { control: 'text' },
    title: { control: 'text' },
    boxDimensions: {
      control: 'object',
      description: 'Length × Width × Height',
    },
  },
};
export default meta;

type Story = StoryObj<typeof BoxInventoryCard>;

const Template = (args: BoxInventoryCardProps) => (
  <MantineProvider>
    <Container size="sm" my="lg">
      <BoxInventoryCard {...args} />
    </Container>
  </MantineProvider>
);

export const Default: Story = {
  render: Template,
  args: {
    title: 'Widget Boxes',
    itemsPerBox: 24,
    boxCount: 86,
    unit: 'in',
    color: 'indigo',
    boxDimensions: { length: 12, width: 9, height: 6 },
  },
};

export const MetricUnits: Story = {
  render: Template,
  args: {
    title: 'Gadget Crates',
    itemsPerBox: 48,
    boxCount: 12,
    unit: 'cm',
    color: 'teal',
    boxDimensions: { length: 30, width: 20, height: 15 },
  },
};

export const LotsOfBoxes: Story = {
  render: Template,
  args: {
    title: 'Bulk Shipment',
    itemsPerBox: 8,
    boxCount: 240,
    unit: 'in',
    color: 'orange',
    boxDimensions: { length: 10, width: 10, height: 10 },
  },
};
