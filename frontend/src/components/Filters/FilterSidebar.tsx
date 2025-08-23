import React from 'react';
import { IconFilter } from '@tabler/icons-react';
import { Button, Divider, Group, Paper, ScrollArea, Stack, Text } from '@mantine/core';
import type { FiltersState } from '../../types';
import { Filters } from './Filters';

type Props = {
  value: FiltersState;
  onChange: (next: FiltersState) => void;
  onReset?: () => void;
  stickyOffset?: number; // px
};

export function FilterSidebar({ value, onChange, onReset, stickyOffset = 16 }: Props) {
  return (
    <Paper
      withBorder
      p={{ base: 'sm', sm: 'md' }}
      radius="md"
      style={{ position: 'sticky', top: '1rem' }}
    >
      <Group mb="sm" justify="space-between" align="center">
        <Group gap={6} align="center">
          <IconFilter size={16} />
          <Text fw={600}>Filters</Text>
        </Group>
        <Button variant="light" size="xs" onClick={onReset}>
          Reset
        </Button>
      </Group>
      <Divider my="xs" />
      <ScrollArea h={'70vh'} type="hover">
        <Stack gap="md" pt="xs">
          <Filters value={value} onChange={onChange} />
        </Stack>
      </ScrollArea>
    </Paper>
  );
}
