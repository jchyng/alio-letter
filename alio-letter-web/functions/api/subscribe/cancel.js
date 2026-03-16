/**
 * POST /api/subscribe/cancel
 * edit_token으로 사용자 is_active = 0 처리 (알림 수신 중단)
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { headers: CORS_HEADERS });
}

export async function onRequestPost(context) {
  const { env } = context;

  try {
    const body = await context.request.json();
    const { token } = body;

    if (!token || token.length < 10) {
      return jsonResponse({ success: false, error: 'invalid_token' }, 400);
    }

    const result = await env.DB.prepare(
      'UPDATE users SET is_active = 0 WHERE edit_token = ?'
    ).bind(token).run();

    if (result.meta.changes === 0) {
      return jsonResponse({ success: false, error: 'not_found' }, 404);
    }

    return jsonResponse({ success: true, message: '알림 수신이 중단되었습니다.' });

  } catch (err) {
    console.error('Subscribe cancel error:', err);
    return jsonResponse({ success: false, error: '처리 중 오류가 발생했습니다.' }, 500);
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
