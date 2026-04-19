// PrenceYours Proxy Worker v2
// 反向代理到 Railway 后端
export default {
  async fetch(request) {
    const url = new URL(request.url);
    
    // 目标：Railway 后端
    const targetUrl = `https://web-production-36c87.up.railway.app${url.pathname}${url.search}`;
    
    // 转发请求，保留原始方法/头
    const newHeaders = new Headers(request.headers);
    newHeaders.set('Host', 'web-production-36c87.up.railway.app');
    newHeaders.delete('cf-connecting-ip');
    newHeaders.delete('cf-ipcountry');
    newHeaders.delete('cf-ray');
    newHeaders.delete('cf-visitor');
    
    try {
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: newHeaders,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
      });
      
      // 复制响应并添加CORS头
      const newResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
      });
      
      // 复制原始响应头
      response.headers.forEach((value, key) => {
        newResponse.headers.set(key, value);
      });
      
      // 添加CORS和缓存控制
      newResponse.headers.set('Access-Control-Allow-Origin', '*');
      newResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      newResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type');
      newResponse.headers.set('Cache-Control', 'public, max-age=30');
      
      return newResponse;
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
