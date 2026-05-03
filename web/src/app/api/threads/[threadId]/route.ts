import { NextResponse } from "next/server";
import { z } from "zod";

import { getThread, updateThreadTitle } from "@/lib/thread-store";

const updateSchema = z.object({
  title: z.string().min(1).max(120),
});

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

export async function PATCH(request: Request, context: Params) {
  const { threadId } = await context.params;

  const body = await request
    .json()
    .then((value) => updateSchema.safeParse(value))
    .catch(() => updateSchema.safeParse({}));

  if (!body.success) {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  const thread = updateThreadTitle(threadId, body.data.title);

  if (!thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  return NextResponse.json({ thread });
}
