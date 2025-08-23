import React from 'react';
import { SegmentedControl } from '@mantine/core';
import type { ExpiredFilterMode } from '../../types';
import { FilterSection } from './FilterSection';

type Props = { value: ExpiredFilterMode; onChange: (v: ExpiredFilterMode) => void };
export function ExpirationFilter({ value, onChange }: Props) {
  return (
    <FilterSection title="Status">
      <SegmentedControl
        fullWidth
        value={value}
        onChange={(v: string) => onChange(v as ExpiredFilterMode)}
        data={[
          { label: 'All', value: 'all' },
          { label: 'OK', value: 'ok' },
          { label: 'Expired', value: 'expired' },
        ]}
      />
    </FilterSection>
  );
}
