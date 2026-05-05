import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

interface AuthContextType {
  token: string | null;
  login: (token: string) => Promise<boolean>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('dashboard_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch('/admin/api/verify', {
          headers: {
            'X-Dashboard-Token': token,
          },
        });

        if (!response.ok) {
          throw new Error('Invalid token');
        }
        
        const data = await response.json();
        if (!data.valid) {
          throw new Error('Invalid token');
        }
      } catch (error) {
        console.error('Token verification failed:', error);
        setToken(null);
        localStorage.removeItem('dashboard_token');
      } finally {
        setIsLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  const login = async (newToken: string): Promise<boolean> => {
    try {
      const response = await fetch('/admin/api/verify', {
        headers: {
          'X-Dashboard-Token': newToken,
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.valid) {
          setToken(newToken);
          localStorage.setItem('dashboard_token', newToken);
          return true;
        }
      }
      return false;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('dashboard_token');
  };

  return (
    <AuthContext.Provider value={{ token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
