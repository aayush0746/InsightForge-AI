import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Mail,
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  Sparkles,
  CheckCircle2,
  ShieldCheck,
  Loader2,
  Plus,
  Trash2,
  ChevronRight,
  ArrowLeft,
  KeyRound,
  RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

// Authentic Google Multi-Color G Icon SVG
export const GoogleIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg className={className} viewBox="0 0 24 24">
    <path
      fill="#4285F4"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
    />
    <path
      fill="#34A853"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
    />
    <path
      fill="#EA4335"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
    />
  </svg>
);

interface SavedGoogleAccount {
  name: string;
  email: string;
  avatar_url?: string;
}

const DEFAULT_GOOGLE_ACCOUNTS: SavedGoogleAccount[] = [
  {
    name: 'Alex Rivera',
    email: 'alex.rivera@gmail.com',
    avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&auto=format&fit=crop&q=80'
  },
  {
    name: 'Student Researcher',
    email: 'researcher.student@gmail.com'
  }
];

export const AuthModal: React.FC = () => {
  const {
    showAuthModal,
    closeAuthModal,
    authModalMode,
    setAuthModalMode,
    signIn,
    signUp,
    verifyOtp,
    signInWithGoogle
  } = useAuth();

  // 'form' = Main Single "Continue with Google" view; 'google_chooser' = Choose Google Account; 'google_custom' = Enter custom Gmail; 'otp_verify' = Enter OTP
  const [modalView, setModalView] = useState<'form' | 'google_chooser' | 'google_custom' | 'otp_verify'>('form');
  const [showEmailForm, setShowEmailForm] = useState(false);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // OTP Verification state
  const [otp, setOtp] = useState('');
  const [otpCountdown, setOtpCountdown] = useState(0);
  const [otpSentToEmail, setOtpSentToEmail] = useState('');
  const [otpPendingData, setOtpPendingData] = useState<{ name: string; email: string; password?: string } | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  // Custom Google input state
  const [customGoogleEmail, setCustomGoogleEmail] = useState('');
  const [customGoogleName, setCustomGoogleName] = useState('');

  // Saved accounts state
  const [savedAccounts, setSavedAccounts] = useState<SavedGoogleAccount[]>(() => {
    try {
      const stored = localStorage.getItem('insightforge_saved_google_accounts');
      return stored ? JSON.parse(stored) : DEFAULT_GOOGLE_ACCOUNTS;
    } catch {
      return DEFAULT_GOOGLE_ACCOUNTS;
    }
  });

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [clientId, setClientId] = useState<string>(() => {
    return (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID || '';
  });
  const [isGisButtonRendered, setIsGisButtonRendered] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement>(null);

  // Fetch client ID from backend if not in env
  useEffect(() => {
    if (!clientId) {
      api.getAuthConfig().then((cfg) => {
        if (cfg.google_client_id) {
          setClientId(cfg.google_client_id);
        }
      }).catch((err) => {
        console.warn('Could not fetch auth config:', err);
      });
    }
  }, [clientId]);

  // Initialize and render Google Identity Services button
  useEffect(() => {
    if (!showAuthModal || modalView !== 'form' || !clientId) return;

    const timer = setTimeout(() => {
      if ((window as any).google?.accounts?.id && googleBtnRef.current) {
        try {
          (window as any).google.accounts.id.initialize({
            client_id: clientId,
            callback: async (response: any) => {
              if (response.credential) {
                try {
                  setIsLoading(true);
                  setErrorMessage(null);
                  await signInWithGoogle({
                    credential: response.credential,
                    email: '',
                    name: '',
                    mode: authModalMode,
                  });
                } catch (err: any) {
                  setErrorMessage(err.message || 'Google Sign-In failed.');
                } finally {
                  setIsLoading(false);
                }
              }
            },
          });

          // Render official button
          googleBtnRef.current.innerHTML = '';
          (window as any).google.accounts.id.renderButton(googleBtnRef.current, {
            theme: 'outline',
            size: 'large',
            width: 380,
            text: 'continue_with',
            shape: 'rectangular',
            logo_alignment: 'left',
          });
          setIsGisButtonRendered(true);
        } catch (err) {
          console.warn('Failed to render Google button:', err);
          setIsGisButtonRendered(false);
        }
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [showAuthModal, modalView, clientId, authModalMode]);

  useEffect(() => {
    if (!showAuthModal) {
      setModalView('form');
      setErrorMessage(null);
      setInfoMessage(null);
      setShowEmailForm(false);
      setIsGisButtonRendered(false);
      setOtp('');
      setName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      setOtpPendingData(null);
    }
  }, [showAuthModal]);

  // Clean sensitive fields whenever switching between Sign In and Sign Up
  useEffect(() => {
    setPassword('');
    setConfirmPassword('');
    setShowPassword(false);
    setErrorMessage(null);
  }, [authModalMode]);

  useEffect(() => {
    if (otpCountdown <= 0) return;
    const timer = setInterval(() => {
      setOtpCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [otpCountdown]);

  if (!showAuthModal) return null;

  const handleGoogleClick = () => {
    setErrorMessage(null);
    if (clientId && (window as any).google?.accounts?.id) {
      try {
        (window as any).google.accounts.id.prompt((notification: any) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            setModalView('google_chooser');
          }
        });
        return;
      } catch (err) {
        console.warn('Google prompt fallback:', err);
      }
    }
    setModalView('google_chooser');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);

    if (authModalMode === 'signup') {
      if (password !== confirmPassword) {
        setErrorMessage('Passwords do not match. Please verify.');
        return;
      }
      if (password.length < 6) {
        setErrorMessage('Password must be at least 6 characters.');
        return;
      }
      if (!name.trim()) {
        setErrorMessage('Please enter your full name.');
        return;
      }
      if (!email.trim()) {
        setErrorMessage('Please enter your email address.');
        return;
      }

      try {
        setIsLoading(true);
        const res = await api.sendOtp({
          email: email.trim().toLowerCase(),
          name: name.trim(),
          purpose: 'signup'
        });
        setOtpPendingData({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          password
        });
        setOtpSentToEmail(email.trim().toLowerCase());
        setInfoMessage(res.message);
        setOtp('');
        setOtpCountdown(30);
        setModalView('otp_verify');
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to send verification code.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    try {
      setIsLoading(true);
      await signIn(email, password);
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    const cleanCode = otp.trim().replace(/\D/g, '');
    if (cleanCode.length < 6) {
      setErrorMessage('Please enter the complete 6-digit verification code.');
      return;
    }
    if (!otpPendingData) {
      setErrorMessage('Verification session expired. Please start over.');
      setModalView('form');
      return;
    }

    try {
      setIsLoading(true);
      await verifyOtp({
        email: otpPendingData.email,
        otp: cleanCode,
        name: otpPendingData.name,
        password: otpPendingData.password
      });
      closeAuthModal();
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid verification code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (otpCountdown > 0 || !otpPendingData) return;
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const res = await api.resendOtp({
        email: otpPendingData.email,
        name: otpPendingData.name
      });
      setInfoMessage(res.message);
      setOtpCountdown(30);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to resend verification code.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectGoogleAccount = async (account: SavedGoogleAccount) => {
    try {
      setIsLoading(true);
      setErrorMessage(null);

      await signInWithGoogle({
        email: account.email.toLowerCase(),
        name: account.name,
        avatar_url: account.avatar_url || null,
        google_id: `g_${Date.now()}`,
        mode: authModalMode
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Google Sign-In failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomGoogleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customGoogleEmail.trim()) {
      setErrorMessage('Please enter your Google / Gmail address.');
      return;
    }

    const emailTrimmed = customGoogleEmail.trim().toLowerCase();
    const nameTrimmed = customGoogleName.trim() || emailTrimmed.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    const newAccount: SavedGoogleAccount = {
      name: nameTrimmed,
      email: emailTrimmed
    };

    // Save to list
    const updated = [newAccount, ...savedAccounts.filter((a) => a.email.toLowerCase() !== emailTrimmed)];
    setSavedAccounts(updated);
    try {
      localStorage.setItem('insightforge_saved_google_accounts', JSON.stringify(updated));
    } catch {
      // ignore
    }

    await handleSelectGoogleAccount(newAccount);
  };

  const handleRemoveSavedAccount = (e: React.MouseEvent, emailToRemove: string) => {
    e.stopPropagation();
    const updated = savedAccounts.filter((a) => a.email !== emailToRemove);
    setSavedAccounts(updated);
    try {
      localStorage.setItem('insightforge_saved_google_accounts', JSON.stringify(updated));
    } catch {
      // ignore
    }
  };

  const handleDemoSignIn = async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      await signIn('admin@insightforge.ai', 'admin123');
    } catch (err: any) {
      setErrorMessage(err.message || 'Demo sign in failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 backdrop-blur-md p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-md bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-in zoom-in-95 duration-150">

        {/* VIEW 1: MAIN SIGN IN / SIGN UP MODAL */}
        {modalView === 'form' && (
          <>
            {/* Header */}
            <div className="p-6 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white relative">
              <button
                onClick={closeAuthModal}
                className="absolute right-5 top-5 p-1.5 rounded-xl text-indigo-200 hover:text-white hover:bg-white/10 transition"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center text-white border border-white/20">
                  <Sparkles className="w-4 h-4 text-indigo-300" />
                </div>
                <span className="font-bold text-sm tracking-wide text-white">InsightForge AI</span>
              </div>

              <h3 className="text-xl font-bold text-white mt-1">
                {authModalMode === 'signin' ? 'Welcome Back' : 'Create an Account'}
              </h3>
              <p className="text-xs text-indigo-200/80 mt-1">
                {authModalMode === 'signin'
                  ? 'Sign in to access your research workspace, documents, and projects'
                  : 'Sign up to start collaborative agentic research and doc analysis'}
              </p>

              {/* Mode Switch Tabs */}
              <div className="flex p-1 rounded-xl bg-indigo-950/60 border border-indigo-700/50 mt-5 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalMode('signin');
                    setErrorMessage(null);
                  }}
                  className={`flex-1 py-1.5 rounded-lg transition text-center ${authModalMode === 'signin'
                    ? 'bg-white text-indigo-900 shadow-sm'
                    : 'text-indigo-200 hover:text-white'
                    }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthModalMode('signup');
                    setErrorMessage(null);
                  }}
                  className={`flex-1 py-1.5 rounded-lg transition text-center ${authModalMode === 'signup'
                    ? 'bg-white text-indigo-900 shadow-sm'
                    : 'text-indigo-200 hover:text-white'
                    }`}
                >
                  Sign Up
                </button>
              </div>
            </div>

            {/* Body Content */}
            <div className="p-6 space-y-5">
              {/* Single Primary "Continue with Google" Button (Requirement 3) */}
              <div className="space-y-3">
                {/* Official Google Identity Services One-Click Button */}
                <div
                  ref={googleBtnRef}
                  className={`flex justify-center w-full overflow-hidden rounded-2xl ${isGisButtonRendered ? '' : 'hidden'}`}
                />

                {/* Rendered only if Google Identity iframe is not available */}
                {!isGisButtonRendered && (
                  <button
                    type="button"
                    onClick={handleGoogleClick}
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-3 px-5 py-3.5 rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-750 hover:border-slate-400 dark:hover:border-slate-600 font-semibold text-sm shadow-xs transition duration-150 cursor-pointer disabled:opacity-50"
                  >
                    <GoogleIcon className="w-5 h-5 shrink-0" />
                    <span>Continue with Google</span>
                  </button>
                )}
              </div>

              {/* Error Banner */}
              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex flex-col gap-2 animate-in fade-in">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                      <span className="font-medium">{errorMessage}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setErrorMessage(null)}
                      className="text-rose-400 hover:text-rose-600 dark:hover:text-rose-200 p-0.5"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {errorMessage.toLowerCase().includes('sign up') && authModalMode === 'signin' && (
                    <button
                      type="button"
                      onClick={() => {
                        setAuthModalMode('signup');
                        setErrorMessage(null);
                      }}
                      className="self-start text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                    >
                      <span>Click here to switch to Sign Up →</span>
                    </button>
                  )}
                </div>
              )}

              {/* Optional Email Collapsible */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setShowEmailForm(!showEmailForm)}
                  className="w-full flex items-center justify-center gap-2 text-xs font-medium text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 transition"
                >
                  <span>{showEmailForm ? 'Hide email options' : 'Or continue with email address'}</span>
                  <ChevronRight className={`w-3.5 h-3.5 transition-transform duration-200 ${showEmailForm ? 'rotate-90' : ''}`} />
                </button>

                {showEmailForm && (
                  <form onSubmit={handleSubmit} className="mt-4 space-y-3.5 animate-in fade-in duration-150">
                    {authModalMode === 'signup' && (
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Full Name
                        </label>
                        <div className="relative">
                          <UserIcon className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                          <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. Dr. Jane Watson"
                            required
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Email Address
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="name@company.com"
                          required
                          className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Password
                      </label>
                      <div className="relative">
                        <Lock className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                        <input
                          type={showPassword ? 'text' : 'password'}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="••••••••"
                          required
                          autoComplete={authModalMode === 'signin' ? 'current-password' : 'new-password'}
                          className="w-full pl-10 pr-10 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {authModalMode === 'signup' && (
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Confirm Password
                        </label>
                        <div className="relative">
                          <Lock className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                          <input
                            type={showPassword ? 'text' : 'password'}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                            autoComplete="new-password"
                            className="w-full pl-10 pr-10 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <span>{authModalMode === 'signin' ? 'Sign In with Email' : 'Create Email Account'}</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </form>
                )}
              </div>

              {/* Quick Demo Sign In */}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-400">Quick Test?</span>
                <button
                  type="button"
                  onClick={handleDemoSignIn}
                  disabled={isLoading}
                  className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Instant Lead Researcher Login</span>
                </button>
              </div>
            </div>
          </>
        )}

        {/* VIEW 2: AUTHENTIC GOOGLE ACCOUNT CHOOSER */}
        {modalView === 'google_chooser' && (
          <div className="p-6 space-y-6">
            {/* Top Bar with Back Arrow */}
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setModalView('form')}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </button>

              <button
                onClick={closeAuthModal}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Google Brand Header */}
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center mx-auto shadow-xs">
                <GoogleIcon className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100 font-sans">
                Choose an account
              </h3>
              <p className="text-xs text-slate-500">
                to continue to <strong className="text-indigo-600 dark:text-indigo-400">InsightForge AI</strong>
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* List of Accounts */}
            <div className="divide-y divide-slate-100 dark:divide-slate-800 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              {savedAccounts.map((acc) => (
                <div
                  key={acc.email}
                  onClick={() => handleSelectGoogleAccount(acc)}
                  className="p-3.5 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/60 transition cursor-pointer group"
                >
                  <div className="flex items-center gap-3 truncate">
                    {acc.avatar_url ? (
                      <img
                        src={acc.avatar_url}
                        alt={acc.name}
                        className="w-9 h-9 rounded-full object-cover border border-slate-200 dark:border-slate-700 shrink-0"
                      />
                    ) : (
                      <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
                        {acc.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="truncate text-left">
                      <div className="font-semibold text-xs text-slate-900 dark:text-slate-100 truncate">
                        {acc.name}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate">{acc.email}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={(e) => handleRemoveSavedAccount(e, acc.email)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition opacity-0 group-hover:opacity-100"
                      title="Remove from list"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </div>
                </div>
              ))}

              {/* Option: Use Another Account */}
              <div
                onClick={() => {
                  setErrorMessage(null);
                  setModalView('google_custom');
                }}
                className="p-3.5 flex items-center gap-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition cursor-pointer"
              >
                <div className="w-9 h-9 rounded-full border border-dashed border-slate-300 dark:border-slate-700 flex items-center justify-center text-slate-500 shrink-0">
                  <Plus className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <div className="font-semibold text-xs text-slate-900 dark:text-slate-100">
                    Use another Google / Gmail account
                  </div>
                  <div className="text-[11px] text-slate-400">Sign in with your personal or school Gmail</div>
                </div>
              </div>
            </div>

            {/* Google Footer Disclaimer */}
            <p className="text-[11px] text-slate-400 text-center leading-relaxed px-4">
              To continue, Google will share your name, email address, and language preference with InsightForge AI.
            </p>
          </div>
        )}

        {/* VIEW 3: ENTER CUSTOM GMAIL / GOOGLE ACCOUNT */}
        {modalView === 'google_custom' && (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setModalView('google_chooser')}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Accounts</span>
              </button>

              <button
                onClick={closeAuthModal}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-center space-y-1.5">
              <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center mx-auto">
                <GoogleIcon className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-sans">
                Sign in with your Google Account
              </h3>
              <p className="text-xs text-slate-500">
                Enter your Gmail or Google Workspace address
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleCustomGoogleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Google Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                  <input
                    type="email"
                    value={customGoogleEmail}
                    onChange={(e) => setCustomGoogleEmail(e.target.value)}
                    placeholder="you@gmail.com"
                    required
                    autoFocus
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Display Name (Optional)
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                  <input
                    type="text"
                    value={customGoogleName}
                    onChange={(e) => setCustomGoogleName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading || !customGoogleEmail.trim()}
                className="w-full py-3 px-4 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-md shadow-indigo-600/25 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in with Google...</span>
                  </>
                ) : (
                  <>
                    <span>Continue with this Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* VIEW 4: EMAIL OTP VERIFICATION (Routing after entering details) */}
        {modalView === 'otp_verify' && (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setErrorMessage(null);
                  setModalView('form');
                }}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Edit Details / Back</span>
              </button>

              <button
                onClick={closeAuthModal}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 shadow-xs">
                <KeyRound className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100 font-sans">
                Verify Your Email
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed px-2">
                We sent a 6-digit verification code to<br />
                <strong className="text-slate-800 dark:text-slate-200 font-semibold">{otpSentToEmail}</strong>
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                <span>{errorMessage}</span>
              </div>
            )}

            {infoMessage && !errorMessage && (
              <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-200 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-indigo-600" />
                <span>{infoMessage}</span>
              </div>
            )}

            <form onSubmit={handleVerifyOtp} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 text-center">
                  Enter 6-Digit Verification Code
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                  autoFocus
                  required
                  className="w-full text-center text-3xl font-mono tracking-[0.4em] font-bold py-3.5 bg-slate-50 dark:bg-slate-800 border-2 border-indigo-200 dark:border-indigo-800 rounded-2xl text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-4 focus:ring-indigo-500/10 transition"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || otp.length < 6}
                className="w-full py-3 px-4 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-md shadow-indigo-600/25 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Verifying Code...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Verify & Complete Registration</span>
                  </>
                )}
              </button>

              <div className="flex items-center justify-between pt-2 text-xs text-slate-400">
                <span>Didn't receive the email?</span>
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={isLoading || otpCountdown > 0}
                  className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50 disabled:no-underline flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
                  <span>{otpCountdown > 0 ? `Resend in ${otpCountdown}s` : 'Resend Code'}</span>
                </button>
              </div>
            </form>
          </div>
        )}

      </div>
    </div>
  );
};
