import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.INTERNAL_BACKEND_URL || 'http://backend:8000';

async function handleProxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = (params?.path || []).join('/');
  const url = new URL(req.url);
  const targetUrl = `${BACKEND_URL}/api/${path}${url.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (k !== 'host' && k !== 'connection' && k !== 'content-length') {
      headers.set(key, value);
    }
  });

  const fetchOptions: RequestInit = {
    method: req.method,
    headers,
  };

  if (!['GET', 'HEAD'].includes(req.method)) {
    try {
      const body = await req.arrayBuffer();
      if (body && body.byteLength > 0) {
        fetchOptions.body = body;
      }
    } catch {
      // Body may be empty
    }
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 3-minute timeout for LLM inference
    fetchOptions.signal = controller.signal;

    const res = await fetch(targetUrl, fetchOptions);
    clearTimeout(timeoutId);

    const responseHeaders = new Headers();
    res.headers.forEach((val, key) => {
      const k = key.toLowerCase();
      if (k !== 'transfer-encoding' && k !== 'content-encoding') {
        responseHeaders.set(key, val);
      }
    });

    const responseBody = await res.arrayBuffer();

    return new NextResponse(responseBody, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (err: any) {
    console.error(`Proxy error for ${targetUrl}:`, err);
    return NextResponse.json(
      { detail: `Backend proxy error: ${err.message}` },
      { status: 504 }
    );
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const DELETE = handleProxy;
export const PATCH = handleProxy;
