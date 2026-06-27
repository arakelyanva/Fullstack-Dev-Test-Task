/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Role } from './Role';

export type UserCreate = {
    email: string;
    is_active?: boolean;
    role?: Role;
    full_name?: (string | null);
    password: string;
};

