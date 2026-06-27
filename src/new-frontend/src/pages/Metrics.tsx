import React, { useEffect, useState } from 'react';

import { Container, Heading, SimpleGrid, Spinner, Stat, StatLabel, StatNumber, Flex } from '@chakra-ui/react';

import { ApiError, MetricsService } from '../client';
import Forbidden from '../components/Common/Forbidden';
import useAuth from '../hooks/useAuth';
import useCustomToast from '../hooks/useCustomToast';

interface MetricsData {
    total_users: number;
    active_users: number;
    total_items: number;
}

const Metrics: React.FC = () => {
    const showToast = useCustomToast();
    const [isLoading, setIsLoading] = useState(false);
    const [data, setData] = useState<MetricsData | null>(null);
    const { can } = useAuth();

    useEffect(() => {
        if (!can('metrics:view')) return;
        const fetchMetrics = async () => {
            setIsLoading(true);
            try {
                const result = await MetricsService.metricsReadMetrics();
                setData(result as unknown as MetricsData);
            } catch (err) {
                const errDetail = (err as ApiError).body?.detail ?? 'Unknown error';
                showToast('Something went wrong.', `${errDetail}`, 'error');
            } finally {
                setIsLoading(false);
            }
        };
        fetchMetrics();
    }, []);

    if (!can('metrics:view')) return <Forbidden />;

    return (
        <>
            {isLoading ? (
                <Flex justify='center' align='center' height='100vh' width='full'>
                    <Spinner size='xl' color='ui.main' />
                </Flex>
            ) : (
                <Container maxW='full'>
                    <Heading size='lg' textAlign={{ base: 'center', md: 'left' }} pt={12}>
                        Metrics & Insights
                    </Heading>
                    <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mt={8}>
                        <Stat p={6} borderWidth='1px' borderRadius='lg'>
                            <StatLabel>Total Users</StatLabel>
                            <StatNumber>{data?.total_users ?? '—'}</StatNumber>
                        </Stat>
                        <Stat p={6} borderWidth='1px' borderRadius='lg'>
                            <StatLabel>Active Users</StatLabel>
                            <StatNumber>{data?.active_users ?? '—'}</StatNumber>
                        </Stat>
                        <Stat p={6} borderWidth='1px' borderRadius='lg'>
                            <StatLabel>Total Items</StatLabel>
                            <StatNumber>{data?.total_items ?? '—'}</StatNumber>
                        </Stat>
                    </SimpleGrid>
                </Container>
            )}
        </>
    );
};

export default Metrics;
