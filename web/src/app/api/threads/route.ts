import { NextResponse } from "next/server";
import { z } from "zod";

import { createThread, listThreads } from "@/lib/thread-store";

const createSchema = z.object({
  title: z.string().min(1).max(120).optional(),
});

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({ threads: listThreads() });
}

export async function POST(request: Request) {
  const body = await request
    .json()
    .then((value) => createSchema.safeParse(value))
    .catch(() => createSchema.safeParse({}));

  if (!body.success) {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  const thread = createThread(body.data.title);

  return NextResponse.json({ thread }, { status: 201 });
}
