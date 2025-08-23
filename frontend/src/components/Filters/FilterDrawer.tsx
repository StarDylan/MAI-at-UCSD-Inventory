import React from 'react';
import { Button, Drawer, Stack } from '@mantine/core';
import type { FiltersState } from '../../types';
import { Filters } from './Filters';

type Props = {
  opened: boolean;
  onClose: () => void;
  value: FiltersState;
  onChange: (next: FiltersState) => void;
  onReset?: () => void;
};

export function FilterDrawer({ opened, onClose, value, onChange, onReset }: Props) {
  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title="Filters"
      position="left"
      size="md"
      padding="md"
    >
      <Stack gap="md">
        <Filters value={value} onChange={onChange} />
        <Stack gap="xs">
          <Button fullWidth variant="light" onClick={onReset}>
            Reset
          </Button>
          <Button fullWidth onClick={onClose}>
            Apply
          </Button>
        </Stack>
      </Stack>
    </Drawer>
  );
}
