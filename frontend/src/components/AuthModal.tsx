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
  Loader2,
  ArrowLeft,
  KeyRound,
  RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

// Google Multi-Color G Icon SVG
export const GoogleIcon: React.FC<{ className?: string }> = ({ className = 'w-5 h-5' }) => (
  <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
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

export const AuthModal: React.FC = () => {
  const {
    showAuthModal,
    closeAuthModal,
    authModalMode,
    setAuthModalMode,
    signIn,
    signUp,
    verifyOtp,
    resetPassword,
    signInWithGoogle
  } = useAuth();

  const [modalView, setModalView] = useState<'form' | 'otp_verify' | 'forgot_password'>('form');
  const [authMethod, setAuthMethod] = useState<'otp' | 'password'>('otp');

  // Forgot password state
  const [forgotStep, setForgotStep] = useState<'request' | 'reset'>('request');
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotOtp, setForgotOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Primary form fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // OTP Verification state
  const [otp, setOtp] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [otpCountdown, setOtpCountdown] = useState(0);
  const [otpSentToEmail, setOtpSentToEmail] = useState('');
  const [otpPendingData, setOtpPendingData] = useState<{ name: string; email: string; password?: string } | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [clientId, setClientId] = useState<string>(() => {
    return (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID || '';
  });
  const [isGisButtonRendered, setIsGisButtonRendered] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!clientId) {
      api.getAuthConfig().then((cfg) => {
        if (cfg.google_client_id) {
          setClientId(cfg.google_client_id);
        }
      }).catch(() => {
        // ignore config fetch error
      });
    }
  }, [clientId]);

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
        } catch {
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
      setDevOtp(null);
      setIsGisButtonRendered(false);
      setOtp('');
      setForgotOtp('');
      setName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
      setShowPassword(false);
      setShowNewPassword(false);
      setOtpPendingData(null);
    }
  }, [showAuthModal]);

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

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);
    setDevOtp(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    try {
      setIsLoading(true);
      const res = await api.sendOtp({
        email: cleanEmail,
        name: name.trim() || undefined,
        purpose: authModalMode === 'signup' ? 'signup' : 'login'
      });
      setOtpPendingData({
        name: name.trim() || cleanEmail.split('@')[0],
        email: cleanEmail,
      });
      setOtpSentToEmail(cleanEmail);
      setDevOtp(res.dev_otp || null);
      setInfoMessage(res.message || 'Verification code sent to your email.');
      setOtp('');
      setOtpCountdown(30);
      setModalView('otp_verify');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to send verification code.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
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
        await signUp(name.trim(), email.trim().toLowerCase(), password);
      } catch (err: any) {
        setErrorMessage(err.message || 'Account registration failed.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    try {
      setIsLoading(true);
      await signIn(email.trim().toLowerCase(), password);
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestPasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);
    setDevOtp(null);
    const cleanEmail = (forgotEmail || email).trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    try {
      setIsLoading(true);
      const res = await api.forgotPassword({ email: cleanEmail });
      setForgotEmail(cleanEmail);
      setDevOtp(res.dev_otp || null);
      setInfoMessage(res.message || 'Password reset code sent to your email.');
      setForgotStep('reset');
      setForgotOtp('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to send password reset code.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);

    const cleanOtp = forgotOtp.trim().replace(/\D/g, '');
    if (cleanOtp.length < 6) {
      setErrorMessage('Please enter the complete 6-digit verification code.');
      return;
    }

    if (newPassword.length < 6) {
      setErrorMessage('New password must be at least 6 characters.');
      return;
    }

    if (newPassword !== confirmNewPassword) {
      setErrorMessage('Passwords do not match. Please verify.');
      return;
    }

    try {
      setIsLoading(true);
      await resetPassword({
        email: forgotEmail.trim().toLowerCase(),
        otp: cleanOtp,
        new_password: newPassword
      });
      closeAuthModal();
    } catch (err: any) {
      setErrorMessage(err.message || 'Password reset failed. Please check the code.');
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
      setDevOtp(res.dev_otp || null);
      setInfoMessage(res.message || 'Verification code sent to your email.');
      setOtpCountdown(30);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to resend verification code.');
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
            <div className="p-6 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white relative">
              <button
                type="button"
                onClick={closeAuthModal}
                aria-label="Close authentication modal"
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

            <div className="p-6 space-y-5">
              {/* Official Google Identity Services Button (rendered only when GOOGLE_CLIENT_ID is configured) */}
              {clientId ? (
                <div className="space-y-2">
                  <div
                    ref={googleBtnRef}
                    className={`flex justify-center w-full overflow-hidden rounded-2xl ${isGisButtonRendered ? '' : 'hidden'}`}
                  />
                  {!isGisButtonRendered && (
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 text-xs text-slate-500 flex items-center justify-center gap-2">
                      <GoogleIcon className="w-4 h-4 shrink-0" />
                      <span>Loading Google Sign-In...</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2">
                  <GoogleIcon className="w-4 h-4 shrink-0 opacity-75" />
                  <span>Google OAuth activates once <code className="font-mono text-indigo-600 dark:text-indigo-400">GOOGLE_CLIENT_ID</code> is configured. Sign in via Email OTP or Password below.</span>
                </div>
              )}

              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex flex-col gap-2 animate-in fade-in" role="alert">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                      <span className="font-medium">{errorMessage}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setErrorMessage(null)}
                      aria-label="Dismiss error"
                      className="text-rose-400 hover:text-rose-600 dark:hover:text-rose-200 p-0.5"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {errorMessage.toLowerCase().includes('sign in') && authModalMode === 'signup' && (
                    <button
                      type="button"
                      onClick={() => {
                        setAuthModalMode('signin');
                        setErrorMessage(null);
                      }}
                      className="self-start text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                    >
                      <span>Switch to Sign In →</span>
                    </button>
                  )}
                </div>
              )}

              <div className="relative flex items-center justify-center my-2">
                <div className="border-t border-slate-200 dark:border-slate-800 w-full"></div>
                <span className="bg-white dark:bg-slate-900 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 whitespace-nowrap">
                  Continue with email
                </span>
                <div className="border-t border-slate-200 dark:border-slate-800 w-full"></div>
              </div>

              <div className="space-y-3">
                <div className="flex p-0.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-semibold">
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMethod('otp');
                      setErrorMessage(null);
                    }}
                    className={`flex-1 py-2 rounded-lg transition text-center flex items-center justify-center gap-1.5 ${authMethod === 'otp'
                      ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                      }`}
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>Instant Email OTP</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMethod('password');
                      setErrorMessage(null);
                    }}
                    className={`flex-1 py-2 rounded-lg transition text-center flex items-center justify-center gap-1.5 ${authMethod === 'password'
                      ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                      }`}
                  >
                    <Lock className="w-3.5 h-3.5" />
                    <span>Password</span>
                  </button>
                </div>

                {/* OTP Mode Form */}
                {authMethod === 'otp' && (
                  <form onSubmit={handleSendOtp} className="space-y-3 animate-in fade-in duration-150">
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      We&apos;ll issue a 6-digit verification code for passwordless sign-in.
                    </p>

                    {authModalMode === 'signup' && (
                      <div>
                        <label htmlFor="auth-otp-name" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Full Name
                        </label>
                        <div className="relative">
                          <UserIcon className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                          <input
                            id="auth-otp-name"
                            type="text"
                            autoComplete="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. Dr. Jane Watson"
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                      </div>
                    )}

                    <div>
                      <label htmlFor="auth-otp-email" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Email Address
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                        <input
                          id="auth-otp-email"
                          type="email"
                          autoComplete="email"
                          autoCorrect="off"
                          autoCapitalize="none"
                          spellCheck={false}
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="name@company.com"
                          required
                          className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isLoading || !email.trim()}
                      className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Dispatching 6-digit code...</span>
                        </>
                      ) : (
                        <>
                          <Mail className="w-3.5 h-3.5" />
                          <span>Send 6-Digit Login Code</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </form>
                )}

                {/* Password Mode Form */}
                {authMethod === 'password' && (
                  <form onSubmit={handlePasswordSubmit} className="space-y-3 animate-in fade-in duration-150">
                    {authModalMode === 'signup' && (
                      <div>
                        <label htmlFor="auth-pw-name" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Full Name
                        </label>
                        <div className="relative">
                          <UserIcon className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                          <input
                            id="auth-pw-name"
                            type="text"
                            autoComplete="name"
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
                      <label htmlFor="auth-pw-email" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                        Email Address
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                        <input
                          id="auth-pw-email"
                          type="email"
                          autoComplete="username"
                          autoCorrect="off"
                          autoCapitalize="none"
                          spellCheck={false}
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="name@company.com"
                          required
                          className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label htmlFor="auth-pw-password" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                          Password
                        </label>
                        {authModalMode === 'signin' && (
                          <button
                            type="button"
                            onClick={() => {
                              setErrorMessage(null);
                              setInfoMessage(null);
                              setDevOtp(null);
                              setForgotEmail(email);
                              setForgotStep('request');
                              setModalView('forgot_password');
                            }}
                            className="text-[11px] font-medium text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
                          >
                            Forgot Password?
                          </button>
                        )}
                      </div>
                      <div className="relative">
                        <Lock className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                        <input
                          id="auth-pw-password"
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
                          aria-pressed={showPassword}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                          className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {authModalMode === 'signup' && (
                      <div>
                        <label htmlFor="auth-pw-confirm" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Confirm Password
                        </label>
                        <div className="relative">
                          <Lock className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                          <input
                            id="auth-pw-confirm"
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
                          <span>{authModalMode === 'signin' ? 'Sign In with Password' : 'Create Account'}</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </>
        )}

        {/* VIEW 2: EMAIL OTP VERIFICATION */}
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
                type="button"
                onClick={closeAuthModal}
                aria-label="Close modal"
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
                We generated a 6-digit verification code for<br />
                <strong className="text-slate-800 dark:text-slate-200 font-semibold">{otpSentToEmail}</strong>
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2" role="alert">
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

            {devOtp && (
              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-center justify-between">
                <span className="font-semibold">Local Dev OTP (no SMTP):</span>
                <code className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900 font-mono text-sm font-bold tracking-widest">
                  {devOtp}
                </code>
              </div>
            )}

            <form onSubmit={handleVerifyOtp} className="space-y-5">
              <div>
                <label htmlFor="auth-otp-code" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 text-center">
                  Enter 6-Digit Verification Code
                </label>
                <input
                  id="auth-otp-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
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
                    <span>Verify &amp; Continue</span>
                  </>
                )}
              </button>

              <div className="flex items-center justify-between pt-2 text-xs text-slate-400">
                <span>Didn&apos;t receive the code?</span>
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

        {/* VIEW 3: FORGOT & RESET PASSWORD (SINGLE INSTANCE) */}
        {modalView === 'forgot_password' && (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setErrorMessage(null);
                  setInfoMessage(null);
                  setDevOtp(null);
                  setModalView('form');
                }}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Sign In</span>
              </button>

              <button
                type="button"
                onClick={closeAuthModal}
                aria-label="Close modal"
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 shadow-xs">
                <Lock className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100 font-sans">
                Reset Your Password
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed px-2">
                {forgotStep === 'request'
                  ? 'Enter your registered email to receive a 6-digit verification code.'
                  : `Enter the 6-digit code sent to ${forgotEmail} and choose a new password.`}
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2" role="alert">
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

            {devOtp && forgotStep === 'reset' && (
              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-center justify-between">
                <span className="font-semibold">Local Dev Reset OTP:</span>
                <code className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900 font-mono text-sm font-bold tracking-widest">
                  {devOtp}
                </code>
              </div>
            )}

            {forgotStep === 'request' ? (
              <form onSubmit={handleRequestPasswordReset} className="space-y-4">
                <div>
                  <label htmlFor="forgot-email-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Registered Email Address
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                    <input
                      id="forgot-email-input"
                      type="email"
                      autoComplete="email"
                      autoCorrect="off"
                      autoCapitalize="none"
                      spellCheck={false}
                      value={forgotEmail || email}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="name@company.com"
                      required
                      autoFocus
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !(forgotEmail || email).trim()}
                  className="w-full py-3 px-4 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-md shadow-indigo-600/25 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Sending reset code...</span>
                    </>
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      <span>Send 6-Digit Reset Code</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
                <div>
                  <label htmlFor="forgot-otp-code" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 text-center">
                    6-Digit Verification Code
                  </label>
                  <input
                    id="forgot-otp-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    autoCorrect="off"
                    autoCapitalize="none"
                    spellCheck={false}
                    maxLength={6}
                    value={forgotOtp}
                    onChange={(e) => setForgotOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                    autoFocus
                    required
                    className="w-full text-center text-2xl font-mono tracking-[0.3em] font-bold py-2.5 bg-slate-50 dark:bg-slate-800 border-2 border-indigo-200 dark:border-indigo-800 rounded-xl text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </div>

                <div>
                  <label htmlFor="forgot-new-pw" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                    <input
                      id="forgot-new-pw"
                      type={showNewPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 6 characters"
                      required
                      className="w-full pl-10 pr-10 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      aria-pressed={showNewPassword}
                      aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    >
                      {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="forgot-confirm-pw" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                    <input
                      id="forgot-confirm-pw"
                      type={showNewPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                      placeholder="Repeat new password"
                      required
                      className="w-full pl-10 pr-10 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs md:text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading || forgotOtp.length < 6 || newPassword.length < 6}
                  className="w-full py-3 px-4 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-md shadow-indigo-600/25 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Updating password...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Reset Password &amp; Log In</span>
                    </>
                  )}
                </button>

                <div className="text-center pt-1">
                  <button
                    type="button"
                    onClick={handleRequestPasswordReset}
                    disabled={isLoading}
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
                  >
                    Didn&apos;t receive code? Resend code
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

      </div>
    </div>
  );
};
