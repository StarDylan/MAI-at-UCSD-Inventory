import React from 'react';
import {
  AspectRatio,
  Badge,
  Card,
  CardSection,
  Container,
  Group,
  Image,
  MantineProvider,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';

export type MedicalItem = {
  id: string;
  name: string;
  image: string;
  quantity: number; // units available
  expired: boolean; // true if expired
};

export type MedicalItemCardProps = {
  item: MedicalItem;
  onClick?: (item: MedicalItem) => void; // optional row/card click
};

/**
 * Ultra-light, repeatable card for a medical surplus catalog.
 * Shows only image, name, quantity, and expired status. Designed for massive grids.
 */
export function MedicalItemCard({ item, onClick }: MedicalItemCardProps) {
  return (
    <Card
      withBorder
      radius="md"
      p={{ base: 'xs', sm: 'sm' }}
      style={{
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 100ms ease, box-shadow 100ms ease',
      }}
      onClick={() => onClick?.(item)}
      onMouseEnter={(e) => {
        if (matchMedia('(hover: hover) and (pointer: fine)').matches) {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--mantine-shadow-sm)';
        }
      }}
      onMouseLeave={(e) => {
        if (matchMedia('(hover: hover) and (pointer: fine)').matches) {
          (e.currentTarget as HTMLDivElement).style.transform = 'none';
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--mantine-shadow-xs)';
        }
      }}
    >
      <CardSection inheritPadding py={0}>
        <AspectRatio ratio={1 / 1}>
          <Image
            src={item.image}
            alt={item.name}
            fit="cover"
            radius="sm"
            loading="lazy"
            fallbackSrc="https://placehold.co/600x400/png"
          />
        </AspectRatio>
      </CardSection>

      <Stack gap={6} mt="xs">
        <Group justify="space-between" wrap="nowrap" align="start">
          <Text fw={600} fz={{ base: 'sm', sm: 'sm' }} lineClamp={10} style={{ flex: 1 }}>
            {item.name}
          </Text>
          <Badge
            variant={item.expired ? 'filled' : 'light'}
            color={item.expired ? 'red' : 'green'}
            size="sm"
          >
            {item.expired ? 'Expired' : 'OK'}
          </Badge>
        </Group>
        <Text c="dimmed" fz={{ base: 'xs', sm: 'sm' }}>
          Qty: {item.quantity}
        </Text>
      </Stack>
    </Card>
  );
}
