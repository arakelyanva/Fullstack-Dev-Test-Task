import { create } from "zustand";
import { UserCreate, UserOut, UserUpdate, UsersService } from "../client";

interface UsersStore {
    users: UserOut[];
    getUsers: () => Promise<void>;
    addUser: (user: UserCreate) => Promise<void>;
    editUser: (id: number, user: UserUpdate) => Promise<void>;
    deleteUser: (id: number) => Promise<void>;
    resetUsers: () => void;
}

export const useUsersStore = create<UsersStore>((set) => ({
    users: [],
    getUsers: async () => {
        const usersResponse = await UsersService.usersReadUsers({ skip: 0, limit: 10 });
        set({ users: usersResponse.data });
    },
    addUser: async (user: UserCreate) => {
        const userResponse = await UsersService.usersCreateUser({ requestBody: user });
        set((state) => ({ users: [...state.users, userResponse] }));
    },
    editUser: async (id: number, user: UserUpdate) => {
        const userResponse = await UsersService.usersUpdateUser({ userId: id, requestBody: user });
        set((state) => ({
            users: state.users.map((user) => (user.id === id ? userResponse : user))
        }));
    },
    deleteUser: async (id: number) => {
        await UsersService.usersDeleteUser({ userId: id });
        set((state) => ({ users: state.users.filter((user) => user.id !== id) }));
    },
    resetUsers: () => {
        set({ users: [] });
    }
}))
