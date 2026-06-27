/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ItemCreate } from '../models/ItemCreate';
import type { ItemOut } from '../models/ItemOut';
import type { ItemsOut } from '../models/ItemsOut';
import type { ItemUpdate } from '../models/ItemUpdate';
import type { Message } from '../models/Message';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class ItemsService {

    /**
     * Read Items
     * Retrieve items. Admins see all items; all other roles see only their own.
     * @returns ItemsOut Successful Response
     * @throws ApiError
     */
    public static itemsReadItems({
        skip,
        limit = 100,
    }: {
        skip?: number,
        limit?: number,
    }): CancelablePromise<ItemsOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/items/',
            query: {
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Create Item
     * Create new item.
     * @returns ItemOut Successful Response
     * @throws ApiError
     */
    public static itemsCreateItem({
        requestBody,
    }: {
        requestBody: ItemCreate,
    }): CancelablePromise<ItemOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/items/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Read Item
     * Get item by ID.
     * @returns ItemOut Successful Response
     * @throws ApiError
     */
    public static itemsReadItem({
        id,
    }: {
        id: number,
    }): CancelablePromise<ItemOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/items/{id}',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Update Item
     * Update an item.
     * @returns ItemOut Successful Response
     * @throws ApiError
     */
    public static itemsUpdateItem({
        id,
        requestBody,
    }: {
        id: number,
        requestBody: ItemUpdate,
    }): CancelablePromise<ItemOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/items/{id}',
            path: {
                'id': id,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Delete Item
     * Delete an item.
     * @returns Message Successful Response
     * @throws ApiError
     */
    public static itemsDeleteItem({
        id,
    }: {
        id: number,
    }): CancelablePromise<Message> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/items/{id}',
            path: {
                'id': id,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

}
