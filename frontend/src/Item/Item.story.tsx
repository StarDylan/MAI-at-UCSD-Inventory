import { Container, MantineProvider, SimpleGrid, Text } from '@mantine/core';
import { MedicalItem, MedicalItemCard } from './Item';

export default {
  title: 'Item',
};

const demoItems: MedicalItem[] = [
  {
    id: 'a1',
    name: 'Sterile Gauze Pads 4x4, 100 pack',
    image: 'https://i.imgur.com/FjDsWDZ.jpg',
    quantity: 56,
    expired: false,
  },
  {
    id: 'b2',
    name: 'Syringes 5ml — Bulk lot',
    image: 'https://i.imgur.com/S3FznBu.jpg',
    quantity: 240,
    expired: false,
  },
  {
    id: 'c3',
    name: '21G BD SafetyGlide Needle',
    image: 'https://i.imgur.com/Bp0TTp7.jpsg',
    quantity: 18,
    expired: true,
  },
];

export function Usage() {
  const handleClick = (item: MedicalItem) => alert(`Clicked: ${item.name}`);

  return (
    <MantineProvider defaultColorScheme="light">
      <Container size="lg" py="xl">
        <Text fz={24} fw={800} mb="sm">
          Medical surplus
        </Text>
        <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 6 }} spacing="md">
          {demoItems.map((it) => (
            <MedicalItemCard key={it.id} item={it} onClick={handleClick} />
          ))}
        </SimpleGrid>
      </Container>
    </MantineProvider>
  );
}
