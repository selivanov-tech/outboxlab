import { NextResponse, type NextRequest } from 'next/server';

import { clearCredentials, CONNECT_PATH } from '@/shared/session/session';

async function disconnect(request: NextRequest): Promise<NextResponse> {
  await clearCredentials();
  const target = new URL(CONNECT_PATH, request.url);
  if (request.nextUrl.searchParams.get('reason') === 'rejected') {
    target.searchParams.set('reason', 'rejected');
  }
  return NextResponse.redirect(target, 303);
}

export const GET = disconnect;
export const POST = disconnect;
