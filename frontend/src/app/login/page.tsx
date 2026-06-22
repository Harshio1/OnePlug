"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Lock, User, BatteryCharging, AlertCircle, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // If token already exists, redirect to dashboard
  useEffect(() => {
    const token = localStorage.getItem("oneplug_token");
    if (token) {
      router.push("/");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (!username || !password) {
      setError("Please fill in all fields.");
      setLoading(false);
      return;
    }

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8002`;
      const response = await fetch(`${apiBase}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed. Please check credentials.");
      }

      // Save token & redirect
      localStorage.setItem("oneplug_token", data.access_token);
      localStorage.setItem("oneplug_username", username);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Failed to connect to the backend server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-bg px-4 py-12 sm:px-6 lg:px-8">
      {/* Dynamic Background Elements */}
      <div className="absolute top-1/4 left-1/4 h-72 w-72 rounded-full bg-brand-green/5 blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 h-80 w-80 rounded-full bg-brand-green/5 blur-3xl" />

      <div className="w-full max-w-md space-y-8 relative z-10">
        {/* Brand Logo and Title */}
        <div className="flex flex-col items-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-card border border-brand-border pulse-green-glow">
            <BatteryCharging className="h-10 w-10 text-brand-green" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">
            OnePlug <span className="text-brand-green font-extrabold">EV</span>
          </h2>
          <p className="mt-2 text-center text-sm text-brand-text-muted">
            Internal AI Transcription & Call Analytics Platform
          </p>
        </div>

        {/* Login Form Card */}
        <div className="bg-brand-card border border-brand-border rounded-2xl p-8 shadow-2xl">
          <div className="mb-6 flex items-center justify-between border-b border-brand-border pb-4">
            <span className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Shield className="h-4 w-4 text-brand-green" /> Employee Portal
            </span>
            <span className="inline-flex items-center rounded-md bg-brand-green/10 px-2 py-1 text-xs font-medium text-brand-green ring-1 ring-inset ring-brand-green/20">
              v1.0.0
            </span>
          </div>

          {error && (
            <div className="mb-6 rounded-lg bg-red-900/20 border border-red-500/30 p-4 text-sm text-red-200 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Username field */}
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-brand-text-muted uppercase tracking-wider mb-2">
                Employee Username
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <User className="h-5 w-5 text-brand-text-muted" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. admin"
                  className="block w-full rounded-lg border border-brand-border bg-brand-bg/50 py-3 pl-10 pr-3 text-white placeholder-brand-text-muted/50 focus:border-brand-green focus:outline-none focus:ring-1 focus:ring-brand-green sm:text-sm transition"
                />
              </div>
            </div>

            {/* Password field */}
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-brand-text-muted uppercase tracking-wider mb-2">
                Access Password
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Lock className="h-5 w-5 text-brand-text-muted" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full rounded-lg border border-brand-border bg-brand-bg/50 py-3 pl-10 pr-10 text-white placeholder-brand-text-muted/50 focus:border-brand-green focus:outline-none focus:ring-1 focus:ring-brand-green sm:text-sm transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-brand-text-muted hover:text-white"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center rounded-lg bg-brand-green px-3 py-3 text-sm font-semibold text-brand-bg hover:bg-brand-green-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-green transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-bg border-t-transparent" />
              ) : (
                "Authenticate Account"
              )}
            </button>
          </form>

          {/* Seed User Helper Box */}
          <div className="mt-8 rounded-xl bg-brand-bg/50 border border-brand-border p-4">
            <h4 className="text-xs font-semibold text-brand-green uppercase tracking-wider mb-2 flex items-center gap-1.5">
              Demo Access Credentials
            </h4>
            <p className="text-xs text-brand-text-muted mb-3">
              This application has been pre-seeded with a default secure administrator account for immediate testing:
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-brand-card/80 p-2.5 rounded-lg border border-brand-border/60">
              <div>
                <span className="text-brand-text-muted">Username:</span>{" "}
                <code className="text-white bg-brand-bg px-1 py-0.5 rounded border border-brand-border">admin</code>
              </div>
              <div>
                <span className="text-brand-text-muted">Password:</span>{" "}
                <code className="text-white bg-brand-bg px-1 py-0.5 rounded border border-brand-border">oneplug2026</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
