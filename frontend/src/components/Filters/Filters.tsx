import { FiltersState, MedicalItem } from '@/types';
import { ExpirationFilter } from './ExpirationFilter';
import { QuantityRangeFilter } from './QuantityRangeFilter';
import { SearchFilter } from './SearchFilter';

interface FilterProps {
  value: FiltersState;
  onChange: (value: FiltersState) => void;
}

export function applyFilters(items: MedicalItem[], f: FiltersState): MedicalItem[] {
  const q = f.query.trim().toLowerCase();
  return items.filter((it) => {
    if (q && !it.name.toLowerCase().includes(q)) return false;
    if (typeof f.quantityMin === 'number' && it.quantity < f.quantityMin) return false;
    if (typeof f.quantityMax === 'number' && it.quantity > f.quantityMax) return false;
    if (f.expired === 'ok' && it.expired) return false;
    if (f.expired === 'expired' && !it.expired) return false;
    return true;
  });
}

export function Filters(props: FilterProps) {
  const { value, onChange } = props;

  return (
    <>
      <SearchFilter value={value.query} onChange={(v) => onChange({ ...value, query: v })} />
      <QuantityRangeFilter
        min={value.quantityMin ?? null}
        max={value.quantityMax ?? null}
        onChange={({ min, max }) => onChange({ ...value, quantityMin: min, quantityMax: max })}
      />
      <ExpirationFilter
        value={value.expired}
        onChange={(v) => onChange({ ...value, expired: v })}
      />
    </>
  );
}
