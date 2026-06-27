import React from 'react';

import { Button, Container, Text } from '@chakra-ui/react';
import { Link } from 'react-router-dom';

const Forbidden: React.FC = () => (
    <Container h='100vh' alignItems='stretch' justifyContent='center' textAlign='center' maxW='xs' centerContent>
        <Text fontSize='8xl' color='ui.main' fontWeight='bold' lineHeight='1' mb={4}>403</Text>
        <Text fontSize='md'>Access Denied.</Text>
        <Text fontSize='md'>You don't have permission to view this page.</Text>
        <Button as={Link} to='/' color='ui.main' borderColor='ui.main' variant='outline' mt={4}>
            Go back to Home
        </Button>
    </Container>
);

export default Forbidden;
