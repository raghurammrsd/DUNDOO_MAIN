export async function onRequest(context) {
  const url = new URL(context.request.url);
  // Forward all requests from Cloudflare Pages directly to the live Render backend
  const targetUrl = `https://dundoo-main.onrender.com${url.pathname}${url.search}`;
  
  // Clone request headers and body for seamless proxying
  const newRequest = new Request(targetUrl, {
    method: context.request.method,
    headers: context.request.headers,
    body: ["GET", "HEAD"].includes(context.request.method) ? null : context.request.body,
    redirect: "manual"
  });
  
  return fetch(newRequest);
}
