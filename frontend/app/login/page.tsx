'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Lock, User, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const router = useRouter();
  
  // ═══════════════════════════════════════════════════════════
  // NEW FEATURE 1: Check if already logged in on page load
  // ═══════════════════════════════════════════════════════════
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      // User already logged in, redirect to upload page
      router.push('/upload');
    }
  }, [router]);
  
  async function handleSubmit(event: any) {
    event.preventDefault();
    
    setLoading(true);
    setError('');
    
    try {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        
        const response = await axios.post(
            'http://localhost:8000/api/auth/login',
            formData,
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            }
        );
        
        localStorage.setItem('token', response.data.access_token);
        router.push('/upload');
        
    } catch (err: any) {
        setError(err.response?.data?.detail || 'Login failed. Please try again.');
    }
    
    setLoading(false);
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome Back
          </h1>
          <p className="text-gray-600">
            Sign in to your account
          </p>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
                Username
            </label>
            <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter your username"
                />
            </div>
          </div>

          <div>
           <label className="block text-sm font-semibold text-gray-700 mb-2">
               Password
           </label>
           <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter your password"
                />
           </div>
          </div>
          
          {/* ═══════════════════════════════════════════════════════════
              NEW FEATURE 3: Forgot Password Link
              ═══════════════════════════════════════════════════════════ */}
          <div className="text-right">
            <a 
              href="/forgot-password" 
              className="text-sm text-blue-600 hover:text-blue-700 font-semibold"
            >
              Forgot password?
            </a>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className={`
              w-full py-3 rounded-lg font-bold text-white
              transition-all duration-300
              ${loading 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
              }
            `}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Signing in...
              </span>
            ) : (
              'Sign In'
            )}
          </button>
        </form>
        
        <p className="mt-6 text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <a href="/register" className="text-blue-600 font-semibold hover:text-blue-700">
            Create one
          </a>
        </p>
      </div>
    </div>
  );
}