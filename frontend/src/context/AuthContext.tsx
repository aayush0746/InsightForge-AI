import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AuthResponse } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  showAuthModal: boolean;
  authModalMode: 'signin' | 'signup';
  setShowAuthModal: (show: boolean) => void;
  setAuthModalMode: (mode: 'signin' | 'signup') => void;
  openAuthModal: (mode?: 'signin' | 'signup') => void;
  closeAuthModal: () => void;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  verifyOtp: (payload: { email: string; otp: string; name?: string; password?: string }) => Promise<void>;
  signInWithGoogle: (payload: {
    email: string;
    name: string;
    avatar_url?: string | null;
    google_id?: string;
    credential?: string;
    mode?: 'signin' | 'signup';
  }) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem('insightforge_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('insightforge_auth_token');
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<'signin' | 'signup'>('signin');

  useEffect(() => {
    const verifySession = async () => {
      const savedToken = localStorage.getItem('insightforge_auth_token');
      if (savedToken) {
        try {
          const verifiedUser = await api.getCurrentUser(savedToken);
          setUser(verifiedUser);
          localStorage.setItem('insightforge_user', JSON.stringify(verifiedUser));
        } catch (err) {
          console.warn('Session verification failed, logging out:', err);
          localStorage.removeItem('insightforge_auth_token');
          localStorage.removeItem('insightforge_user');
          setUser(null);
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    verifySession();
  }, []);

  const openAuthModal = (mode: 'signin' | 'signup' = 'signin') => {
    setAuthModalMode(mode);
    setShowAuthModal(true);
  };

  const closeAuthModal = () => {
    setShowAuthModal(false);
  };

  const handleAuthSuccess = (res: AuthResponse) => {
    setUser(res.user);
    setToken(res.access_token);
    localStorage.setItem('insightforge_auth_token', res.access_token);
    localStorage.setItem('insightforge_user', JSON.stringify(res.user));
    setShowAuthModal(false);
    window.dispatchEvent(new CustomEvent('insightforge-auth-change', { detail: { user: res.user } }));
  };

  const signIn = async (email: string, password: string) => {
    const res = await api.signIn({ email, password });
    handleAuthSuccess(res);
  };

  const signUp = async (name: string, email: string, password: string) => {
    const res = await api.signUp({ name, email, password });
    handleAuthSuccess(res);
  };

  const verifyOtp = async (payload: { email: string; otp: string; name?: string; password?: string }) => {
    const res = await api.verifyOtp(payload);
    handleAuthSuccess(res);
  };

  const signInWithGoogle = async (payload: {
    email: string;
    name: string;
    avatar_url?: string | null;
    google_id?: string;
    credential?: string;
    mode?: 'signin' | 'signup';
  }) => {
    const effectiveMode = payload.mode || authModalMode || 'signin';
    const res = await api.googleAuth({
      ...payload,
      mode: effectiveMode,
    });
    handleAuthSuccess(res);
  };

  const signOut = async () => {
    try {
      await api.logout();
      await api.clearGuestData();
    } catch {
      // ignore
    }
    setUser(null);
    setToken(null);
    localStorage.removeItem('insightforge_auth_token');
    localStorage.removeItem('insightforge_user');
    sessionStorage.clear();
    window.dispatchEvent(new CustomEvent('insightforge-auth-change', { detail: { user: null } }));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        showAuthModal,
        authModalMode,
        setShowAuthModal,
        setAuthModalMode,
        openAuthModal,
        closeAuthModal,
        signIn,
        signUp,
        verifyOtp,
        signInWithGoogle,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

