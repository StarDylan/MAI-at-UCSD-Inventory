import { useMemo, useState } from 'react';
import { Box, Button, Container, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import { FilterDrawer } from '@/components/Filters/FilterDrawer';
import { applyFilters } from '@/components/Filters/Filters';
import { FilterSidebar } from '@/components/Filters/FilterSidebar';
import { MedicalItem, MedicalItemCard } from '@/Item/Item';
import { defaultFilters, FiltersState } from '@/types';

interface CatalogPageProps {
  items: MedicalItem[];
}

export function CatalogPage(props: CatalogPageProps) {
  const [filters, setFilters] = useState<FiltersState>(defaultFilters);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const filtered = useMemo(() => applyFilters(props.items, filters), [filters]);
  const reset = () => setFilters(defaultFilters);

  return (
    <Container size="lg" py="xl">
      {/* Top bar with title and mobile-only filter button */}
      <Group justify="space-between" mb="sm">
        <Stack gap={0}>
          <Text fz={{ base: 20, sm: 24 }} fw={800}>
            Medical surplus
          </Text>
          <Text c="dimmed" fz="sm">
            Showing {filtered.length} of {props.items.length}
          </Text>
        </Stack>
        <Button
          hiddenFrom="sm"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open filters"
          aria-controls="filters-drawer"
          aria-expanded={drawerOpen}
        >
          Filters
        </Button>
      </Group>

      <Group align="flex-start" wrap="nowrap" gap="lg">
        {/* Desktop sidebar only */}
        <Box visibleFrom="sm" style={{ width: 300, flex: '0 0 300px' }}>
          <FilterSidebar value={filters} onChange={setFilters} onReset={reset} />
        </Box>

        <Box style={{ flex: 1 }}>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing={{ base: 'sm', sm: 'md' }}>
            {filtered.map((it) => (
              <MedicalItemCard key={it.id} item={it} />
            ))}
          </SimpleGrid>
        </Box>
      </Group>

      {/* Mobile drawer */}
      <FilterDrawer
        opened={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        value={filters}
        onChange={setFilters}
        onReset={reset}
      />
    </Container>
  );
}
