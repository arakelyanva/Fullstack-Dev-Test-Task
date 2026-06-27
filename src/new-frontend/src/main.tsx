import React from 'react';
import ReactDOM from 'react-dom/client';

import axios from 'axios';
import { ChakraProvider } from '@chakra-ui/provider';
import { createStandaloneToast } from '@chakra-ui/toast';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import { OpenAPI } from './client';
import { isLoggedIn } from './hooks/useAuth';
import privateRoutes from './routes/private_route';
import publicRoutes from './routes/public_route';
import theme from './theme';


OpenAPI.BASE = import.meta.env.VITE_API_URL;
OpenAPI.TOKEN = async () => {
  return localStorage.getItem('access_token') || '';
}

// Logout on 401 (expired/invalid token) only.
// 403 is a legitimate authorization failure for an authenticated user
// and must NOT destroy the session.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

const router = createBrowserRouter([
  isLoggedIn() ? privateRoutes() : {},
  ...publicRoutes(),
]);

const { ToastContainer } = createStandaloneToast();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <RouterProvider router={router} />
      <ToastContainer />
    </ChakraProvider>
  </React.StrictMode>,
)

