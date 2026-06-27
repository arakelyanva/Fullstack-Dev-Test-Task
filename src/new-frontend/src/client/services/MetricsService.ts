/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class MetricsService {

    /**
     * Read Metrics
     * Lightweight insights stub. Visible to admin and manager only.
     * @returns number Successful Response
     * @throws ApiError
     */
    public static metricsReadMetrics(): CancelablePromise<Record<string, number>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/metrics/',
        });
    }

}
