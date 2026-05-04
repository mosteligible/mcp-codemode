import { redirect } from "next/navigation";

import { ChatApp } from "@/components/chat-app";
import { getAuthSession } from "@/lib/auth";

export default async function Home() {
  const session = await getAuthSession();

  if (!session) {
    redirect("/auth/signin?callbackUrl=/");
  }

  return (
    <ChatApp
      userName={session.user?.name ?? session.user?.email ?? "Signed-in account"}
    />
  );
}
