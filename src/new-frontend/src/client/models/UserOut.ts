/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { Role } from './Role';

export type UserOut = {
    email: string;
    is_active?: boolean;
    role?: Role;
    full_name?: (string | null);
    id: number;
    /**
     * Backward-compatible derived field for existing API consumers and tests.
     */
    readonly is_superuser: boolean;
};

