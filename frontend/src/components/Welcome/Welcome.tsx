import { Anchor, List, Text, Title } from '@mantine/core';
import classes from './Welcome.module.css';

const sampleInventory = [
  {
    id: 1,
    name: 'Tubing',
    quantity: 5,
    categories: [],
    location: 'Box A',
    expiration_date: null,
    date_received: '2004-01-01',
    donating_organization: 'OR',
    created: '2025-08-21T03:55:21.395969Z',
  },
  {
    id: 2,
    name: 'Needles',
    quantity: 100,
    categories: [],
    location: 'Box B',
    expiration_date: null,
    date_received: '2004-01-01',
    donating_organization: 'OR',
    created: '2025-08-21T03:55:21.395969Z',
  },
  {
    id: 3,
    name: 'Scissors',
    quantity: 10,
    categories: [],
    location: 'Box C',
    expiration_date: null,
    date_received: '2004-01-01',
    donating_organization: 'OR',
    created: '2025-08-21T03:55:21.395969Z',
  },
];

export function Welcome() {
  return (
    <>
      <Title className={classes.title} ta="center" mt={100}>
        MAI Inventory
      </Title>
      <List>
        {sampleInventory.map((item) => (
          <Text key={item.id}>{item.name}</Text>
        ))}
      </List>
    </>
  );
}
