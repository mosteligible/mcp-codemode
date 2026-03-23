import { NextResponse } from "next/server";

import { getThread } from "@/lib/thread-store";

export const runtime = "nodejs";

interface Params {
  params: Promise<{
    threadId: string;
  }>;
}

export async function GET(_request: Request, context: Params) {
  const { threadId } = await context.params;
  const thread = getThread(threadId);

  if (!thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  return NextResponse.json({ thread });
}
