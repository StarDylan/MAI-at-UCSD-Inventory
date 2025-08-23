import React from 'react';
import { IconX } from '@tabler/icons-react';
import { Button, Divider, Group, Stack, Title } from '@mantine/core';

type Props = { title: string; children: React.ReactNode; onClear?: () => void };
export function FilterSection({ title, children, onClear }: Props) {
  return (
    <Stack gap={8}>
      <Group justify="space-between" align="center">
        <Title order={6}>{title}</Title>
        {onClear && (
          <Button
            size="compact-xs"
            variant="subtle"
            leftSection={<IconX size={14} />}
            onClick={onClear}
          >
            Clear
          </Button>
        )}
      </Group>
      {children}
      <Divider my={4} />
    </Stack>
  );
}
