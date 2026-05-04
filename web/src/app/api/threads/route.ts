import { NextResponse } from "next/server";
import { z } from "zod";

import { getAuthUserId } from "@/lib/auth";
import { createThread, listThreads } from "@/lib/thread-store";

const createSchema = z.object({
  title: z.string().min(1).max(120).optional(),
});

export const runtime = "nodejs";

function unauthorized() {
  return NextResponse.json({ error: "Authentication required." }, { status: 401 });
}

export async function GET() {
  const userId = await getAuthUserId();
  if (!userId) return unauthorized();

  return NextResponse.json({ threads: listThreads(userId) });
}

export async function POST(request: Request) {
  const userId = await getAuthUserId();
  if (!userId) return unauthorized();

  const body = await request
    .json()
    .then((value) => createSchema.safeParse(value))
    .catch(() => createSchema.safeParse({}));

  if (!body.success) {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  const thread = createThread(userId, body.data.title);

  return NextResponse.json({ thread }, { status: 201 });
}
