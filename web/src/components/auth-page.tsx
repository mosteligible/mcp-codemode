"use client";

import { Chrome, Github, LogIn } from "lucide-react";
import { signIn } from "next-auth/react";
import { useState } from "react";

interface AuthPageProps {
  callbackUrl: string;
  error?: string;
  providers: {
    github: boolean;
    google: boolean;
  };
}

const errorMessages: Record<string, string> = {
  OAuthSignin: "The provider could not start the sign-in flow.",
  OAuthCallback: "The provider could not complete the sign-in flow.",
  OAuthCreateAccount: "The account could not be created.",
  EmailCreateAccount: "The account could not be created.",
  Callback: "The sign-in callback failed.",
  OAuthAccountNotLinked: "Use the same provider you originally used for this email.",
  AccessDenied: "Access was denied for this account.",
  Configuration: "The auth provider is not configured correctly.",
  Verification: "The sign-in link is no longer valid.",
  Default: "Sign-in failed. Try again.",
};

function authErrorMessage(error?: string): string | null {
  if (!error) return null;
  return errorMessages[error] ?? errorMessages.Default;
}

export function AuthPage({ callbackUrl, error, providers }: AuthPageProps) {
  const [pendingProvider, setPendingProvider] = useState<string | null>(null);
  const message = authErrorMessage(error);
  const hasConfiguredProvider = providers.github || providers.google;

  async function handleSignIn(provider: "github" | "google") {
    setPendingProvider(provider);
    await signIn(provider, { callbackUrl });
    setPendingProvider(null);
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="auth-title">
        <div>
          <p className="eyebrow">Private workspace</p>
          <h1 id="auth-title">Sign in to Codemode Chat</h1>
          <p className="auth-copy">
            Continue with a configured GitHub or Google account.
          </p>
        </div>

        <div className="auth-actions">
          <button
            type="button"
            className="auth-provider-button"
            disabled={!providers.github || pendingProvider !== null}
            onClick={() => handleSignIn("github")}
          >
            <Github size={18} aria-hidden="true" />
            <span>
              {pendingProvider === "github" ? "Opening GitHub..." : "Continue with GitHub"}
            </span>
          </button>

          <button
            type="button"
            className="auth-provider-button"
            disabled={!providers.google || pendingProvider !== null}
            onClick={() => handleSignIn("google")}
          >
            <Chrome size={18} aria-hidden="true" />
            <span>
              {pendingProvider === "google" ? "Opening Google..." : "Continue with Google"}
            </span>
          </button>
        </div>

        {message ? (
          <p className="auth-message warn" role="alert">
            {message}
          </p>
        ) : null}

        {!hasConfiguredProvider ? (
          <p className="auth-message">
            Add GitHub or Google OAuth credentials to enable sign-in.
          </p>
        ) : null}

        <div className="auth-footer">
          <LogIn size={16} aria-hidden="true" />
          <span>OAuth sign-in only</span>
        </div>
      </section>
    </main>
  );
}
