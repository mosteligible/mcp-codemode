import { getServerSession, type NextAuthOptions } from "next-auth";
import GitHubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";

export const authOptions: NextAuthOptions = {
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID ?? "",
      clientSecret: process.env.GITHUB_SECRET ?? "",
    }),
    GoogleProvider({
      clientId: process.env.GOOGLE_ID ?? "",
      clientSecret: process.env.GOOGLE_SECRET ?? "",
    }),
  ],
  pages: {
    signIn: "/auth/signin",
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET ?? process.env.AUTH_SECRET,
  callbacks: {
    async jwt({ token, account }) {
      if (account?.provider && account.providerAccountId) {
        token.authUserId = `${account.provider}:${account.providerAccountId}`;
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.authUserId ?? token.sub;
      }

      return session;
    },
  },
};

export function getAuthSession() {
  return getServerSession(authOptions);
}

export async function getAuthUserId(): Promise<string | null> {
  const session = await getAuthSession();
  return session?.user?.id ?? session?.user?.email ?? null;
}

export function getAuthProviderStatus() {
  return {
    github: Boolean(process.env.GITHUB_ID && process.env.GITHUB_SECRET),
    google: Boolean(process.env.GOOGLE_ID && process.env.GOOGLE_SECRET),
  };
}
