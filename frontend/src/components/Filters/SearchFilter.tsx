import React from 'react';
import { TextInput } from '@mantine/core';
import { FilterSection } from './FilterSection';

type Props = { value: string; onChange: (v: string) => void };
export function SearchFilter({ value, onChange }: Props) {
  return (
    <FilterSection title="Search name" onClear={() => onChange('')}>
      <TextInput
        size="sm"
        radius="md"
        placeholder="e.g. Gauze, Syringe"
        value={value}
        onChange={(e) => onChange(e.currentTarget.value)}
      />
    </FilterSection>
  );
}
