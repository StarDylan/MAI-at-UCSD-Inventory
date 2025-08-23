import React from 'react';
import { IconBox, IconPackage, IconRulerMeasure, IconSum } from '@tabler/icons-react';
import {
  Badge,
  Box,
  Card,
  Divider,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from '@mantine/core';

export type Unit = 'in' | 'cm';

export interface BoxDimensions {
  length: number;
  width: number;
  height: number;
}

export interface BoxInventoryCardProps {
  /** Number of items that fit in a single box */
  itemsPerBox: number;
  /** Number of boxes you currently have */
  boxCount: number;
  /** Physical dimensions of one box */
  boxDimensions: BoxDimensions;
  /** Unit for dimensions */
  unit: Unit;
  /** Optional title shown at the top */
  title: string;
  /** Optional accent color (Mantine color token) */
  color: string;
}

const Stat: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  hint?: string;
}> = ({ icon, label, value, hint }) => (
  <Group align="flex-start" gap="sm" wrap="nowrap">
    <ThemeIcon size={40} radius="md" variant="light">
      {icon}
    </ThemeIcon>
    <Stack gap={0} style={{ minWidth: 0 }}>
      <Text size="xs" c="dimmed" fw={600} tt="uppercase" truncate>
        {label}
      </Text>
      <Group gap={6} wrap="nowrap">
        <Text size="xl" fw={800} style={{ lineHeight: 1.2 }}>
          {value}
        </Text>
        {hint && (
          <Tooltip label={hint} withArrow>
            <Badge variant="light" size="sm">
              info
            </Badge>
          </Tooltip>
        )}
      </Group>
    </Stack>
  </Group>
);

function formatNumber(n: number) {
  return new Intl.NumberFormat().format(n);
}

function superscript(unit: Unit) {
  // Return e.g. cm³ or in³ with proper superscript 3
  return `${unit}³`;
}

function prettyDims(d: BoxDimensions, unit: Unit) {
  const { length, width, height } = d;
  return `${length} × ${width} × ${height} ${unit}`;
}

function volume(d: BoxDimensions) {
  return d.length * d.width * d.height;
}

function miniatureBoxes(count: number, color?: string) {
  // Render a compact visual of up to 12 boxes (3x4 grid)
  const cells = Math.min(12, Math.max(0, count));
  const items = Array.from({ length: cells });
  return (
    <Box aria-hidden>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: 6,
        }}
      >
        {items.map((_, i) => (
          <div
            key={i}
            style={{
              aspectRatio: '1 / 1',
              borderRadius: 8,
              boxShadow: 'inset 0 0 0 1px var(--mantine-color-gray-4)',
              background:
                'linear-gradient(135deg, var(--mantine-color-gray-0), var(--mantine-color-gray-2))',
              position: 'relative',
            }}
          >
            <div
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: 8,
                boxShadow: `0 2px 0 0 var(--mantine-color-${color || 'blue'}-2) inset`,
              }}
            />
          </div>
        ))}
      </div>
      {count > 12 && (
        <Text size="xs" c="dimmed" mt={6} ta="center">
          +{formatNumber(count - 12)} more
        </Text>
      )}
    </Box>
  );
}
export default function BoxInventoryCard({
  itemsPerBox,
  boxCount,
  boxDimensions,
  title,
  color,
  unit,
}: BoxInventoryCardProps) {
  const totalItems = Math.max(0, Math.floor(itemsPerBox * boxCount));
  const vol = volume(boxDimensions);

  return (
    <Card withBorder padding="lg" radius="xl" shadow="sm">
      <Group justify="space-between" align="center" mb="sm">
        <Text fw={800} size="lg">
          {title}
        </Text>
        <Badge color={color} variant="light" radius="sm">
          {boxCount === 1 ? '1 box' : `${formatNumber(boxCount)} boxes`}
        </Badge>
      </Group>

      <Divider mb="md" />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
        <Stat
          icon={<IconPackage size={20} />}
          label="Items per box"
          value={formatNumber(itemsPerBox)}
        />
        <Stat
          icon={<IconBox size={20} />}
          label="Boxes"
          value={formatNumber(boxCount)}
          hint="Total number of boxes currently in stock"
        />
        <Stat
          icon={<IconSum size={20} />}
          label="Total items"
          value={formatNumber(totalItems)}
          hint="Calculated as items per box × number of boxes"
        />
        <Stat
          icon={<IconRulerMeasure size={20} />}
          label="Box dimensions"
          value={prettyDims(boxDimensions, unit)}
          hint="Length × Width × Height"
        />
        <Stat
          icon={<IconRulerMeasure size={20} />}
          label="Box volume"
          value={`${formatNumber(vol)} ${superscript(unit)}`}
          hint="Length × Width × Height"
        />
        <Group align="flex-start" gap="sm">
          <ThemeIcon size={40} radius="md" variant="light" color={color}>
            <IconBox size={20} />
          </ThemeIcon>
          <Stack gap={6} style={{ flex: 1 }}>
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Visual
            </Text>
            {miniatureBoxes(boxCount, color)}
          </Stack>
        </Group>
      </SimpleGrid>

      <Divider my="md" />
      <Text size="xs" c="dimmed">
        Tip: pass a custom <code>title</code>, change <code>unit</code> to <code>cm</code>, or set{' '}
        <code>color</code> to match your brand.
      </Text>
    </Card>
  );
}
