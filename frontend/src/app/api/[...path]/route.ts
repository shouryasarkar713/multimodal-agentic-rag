import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.INTERNAL_BACKEND_URL || 'http://backend:8000';

async function handleProxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = (params?.path || []).join('/');
  const url = new URL(req.url);
  const targetUrl = `${BACKEND_URL}/api/${path}${url.search}`;

  console.log(`[Proxy] ${req.method} -> ${targetUrl}`);

  const headers: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (k !== 'host' && k !== 'connection' && k !== 'content-length') {
      headers[k] = value;
    }
  });

  const fetchOptions: RequestInit = {
    method: req.method,
    headers,
  };

  if (!['GET', 'HEAD'].includes(req.method)) {
    try {
      const contentType = req.headers.get('content-type') || '';
      if (contentType.includes('application/json') || contentType.includes('text/')) {
        const text = await req.text();
        if (text) {
          fetchOptions.body = text;
        }
      } else {
        const arrayBuf = await req.arrayBuffer();
        if (arrayBuf && arrayBuf.byteLength > 0) {
          fetchOptions.body = Buffer.from(arrayBuf);
        }
      }
    } catch (err) {
      console.error(`[Proxy] Error reading body for ${targetUrl}:`, err);
    }
  }

  try {
    const res = await fetch(targetUrl, fetchOptions);

    console.log(`[Proxy] ${targetUrl} responded with ${res.status}`);

    const responseHeaders = new Headers();
    res.headers.forEach((val, key) => {
      const k = key.toLowerCase();
      if (k !== 'transfer-encoding' && k !== 'content-encoding') {
        responseHeaders.set(key, val);
      }
    });

    const responseData = await res.arrayBuffer();

    return new NextResponse(responseData, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (err: any) {
    console.error(`[Proxy] Error forwarding to ${targetUrl}:`, err);
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
