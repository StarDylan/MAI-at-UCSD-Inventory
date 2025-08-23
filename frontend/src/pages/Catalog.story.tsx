import React, { useMemo, useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import {
  Box,
  Button,
  Container,
  Drawer,
  Group,
  MantineProvider,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
import { MedicalItemCard } from '@/Item/Item';
import { defaultFilters, FiltersState, MedicalItem } from '@/types';
import { ExpirationFilter } from '../components/Filters/ExpirationFilter';
import { FilterDrawer } from '../components/Filters/FilterDrawer';
import { FilterSidebar } from '../components/Filters/FilterSidebar';
import { QuantityRangeFilter } from '../components/Filters/QuantityRangeFilter';
import { SearchFilter } from '../components/Filters/SearchFilter';
import { CatalogPage } from './Catalog';

const withMantine = (Story: React.ComponentType) => (
  <MantineProvider defaultColorScheme="light">
    {' '}
    <Story />{' '}
  </MantineProvider>
);
const meta: Meta = {
  title: 'Demo/MedicalSurplusPage',
  decorators: [withMantine],
};
export default meta;
export type Story = StoryObj;

const demoItems: MedicalItem[] = [
  {
    id: 'a1',
    name: 'Sterile Gauze Pads 4x4, 100 pack',
    image:
      'https://images.unsplash.com/photo-1583941700141-2f3dfc83f9b1?q=80&w=1200&auto=format&fit=crop',
    quantity: 56,
    expired: false,
  },
  {
    id: 'b2',
    name: 'Syringes 5ml — Bulk lot',
    image:
      'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?q=80&w=1200&auto=format&fit=crop',
    quantity: 240,
    expired: false,
  },
  {
    id: 'c3',
    name: 'N95 Respirators — Mixed sizes',
    image:
      'https://images.unsplash.com/photo-1588771930297-8d4cb07a8d0f?q=80&w=1200&auto=format&fit=crop',
    quantity: 18,
    expired: true,
  },
  {
    id: 'd4',
    name: 'Alcohol Prep Pads',
    image:
      'https://images.unsplash.com/photo-1586943328530-5f9a2b0d4f23?q=80&w=1200&auto=format&fit=crop',
    quantity: 400,
    expired: false,
  },
];

export function Usage() {
  return <CatalogPage items={demoItems} />;
}
