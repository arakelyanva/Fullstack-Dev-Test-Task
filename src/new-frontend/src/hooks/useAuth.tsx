import { useUserStore } from '../store/user-store';
import { Body_login_login_access_token as AccessToken, LoginService } from '../client';
import { useUsersStore } from '../store/users-store';
import { useItemsStore } from '../store/items-store';
import { useNavigate } from 'react-router-dom';
import { can as canDo, roleOf, type Permission } from '../lib/permissions';

const isLoggedIn = () => {
    return localStorage.getItem('access_token') !== null;
};

const useAuth = () => {
    const { user, getUser, resetUser } = useUserStore();
    const { resetUsers } = useUsersStore();
    const { resetItems } = useItemsStore();
    const navigate = useNavigate();

    const login = async (data: AccessToken) => {
        const response = await LoginService.loginLoginAccessToken({
            formData: data,
        });
        localStorage.setItem('access_token', response.access_token);
        await getUser();
        navigate('/');
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        resetUser();
        resetUsers();
        resetItems();
        navigate('/login');
    };

    return {
        login,
        logout,
        user,
        role: roleOf(user),
        can: (permission: Permission) => canDo(user, permission),
    };
}

export { isLoggedIn };
export default useAuth;