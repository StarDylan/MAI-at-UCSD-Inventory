import React, { useState } from 'react';
import { Box, Group, NumberInput, RangeSlider } from '@mantine/core';
import { FilterSection } from './FilterSection';

type Props = {
  min: number | null | undefined;
  max: number | null | undefined;
  onChange: (next: { min: number | null; max: number | null }) => void;
};

export function QuantityRangeFilter({ min, max, onChange }: Props) {
  const [localMin, setLocalMin] = useState<number | ''>(typeof min === 'number' ? min : '');
  const [localMax, setLocalMax] = useState<number | ''>(typeof max === 'number' ? max : '');

  const sliderMin = 0;
  const sliderMax = 1000;
  const sliderValue: [number, number] = [
    typeof localMin === 'number' ? localMin : sliderMin,
    typeof localMax === 'number' ? localMax : sliderMax,
  ];

  const commit = (nm: number | null, nx: number | null) => onChange({ min: nm, max: nx });

  return (
    <FilterSection
      title="Quantity range"
      onClear={() => {
        setLocalMin('');
        setLocalMax('');
        commit(null, null);
      }}
    >
      <Group grow>
        <NumberInput
          size="sm"
          radius="md"
          label="Min"
          placeholder="0"
          value={localMin}
          min={0}
          onChange={(v) => {
            const val = typeof v === 'number' ? v : null;
            setLocalMin(typeof v === 'number' ? v : '');
            commit(val, typeof localMax === 'number' ? localMax : null);
          }}
        />
        <NumberInput
          label="Max"
          placeholder="∞"
          value={localMax}
          min={0}
          onChange={(v) => {
            const val = typeof v === 'number' ? v : null;
            setLocalMax(typeof v === 'number' ? v : '');
            commit(typeof localMin === 'number' ? localMin : null, val);
          }}
        />
      </Group>
      <Box pt={4}>
        <RangeSlider
          size="sm"
          min={sliderMin}
          max={sliderMax}
          value={sliderValue}
          onChange={([a, b]) => {
            setLocalMin(a);
            setLocalMax(b);
          }}
          onChangeEnd={([a, b]) => commit(a, b)}
        />
      </Box>
    </FilterSection>
  );
}
