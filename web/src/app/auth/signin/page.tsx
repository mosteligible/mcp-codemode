import { redirect } from "next/navigation";

import { AuthPage } from "@/components/auth-page";
import { getAuthProviderStatus, getAuthSession } from "@/lib/auth";

type SignInSearchParams = Promise<{
  callbackUrl?: string | string[];
  error?: string | string[];
}>;

function firstParam(value?: string | string[]): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function normalizeCallbackUrl(value?: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }

  return value;
}

export default async function SignInPage({
  searchParams,
}: {
  searchParams: SignInSearchParams;
}) {
  const session = await getAuthSession();
  const params = await searchParams;
  const callbackUrl = normalizeCallbackUrl(firstParam(params.callbackUrl));

  if (session) {
    redirect(callbackUrl);
  }

  return (
    <AuthPage
      callbackUrl={callbackUrl}
      error={firstParam(params.error)}
      providers={getAuthProviderStatus()}
    />
  );
}
