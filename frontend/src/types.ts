export type MedicalItem = {
  id: string;
  name: string;
  image: string;
  quantity: number; // units available
  expired: boolean; // true if expired
};

export type ExpiredFilterMode = 'all' | 'ok' | 'expired';

export type FiltersState = {
  query: string;
  quantityMin?: number | null;
  quantityMax?: number | null;
  expired: ExpiredFilterMode;
};

export const defaultFilters: FiltersState = {
  query: '',
  quantityMin: null,
  quantityMax: null,
  expired: 'all',
};
