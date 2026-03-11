/**
 * GET  /api/profile/:token  — MySQL에서 데이터 조회 (via Cloudflare Tunnel)
 * POST /api/profile/:token  — Gemini 재파싱 + MySQL UPDATE
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response(null, { headers: CORS_HEADERS });
}

// GET /api/profile/:token
export async function onRequestGet(context) {
  const { env, params } = context;
  const token = params.token;

  if (!token || token.length < 10) {
    return jsonResponse({ error: 'invalid_token' }, 400);
  }

  try {
    // TODO: MySQL에서 token으로 사용자 정보 조회
    // const userData = await query('SELECT * FROM users WHERE token = ?', [token]);
    
    // 임시 더미 데이터 응답
    return jsonResponse({
      name: '홍길동',
      email: 'test@example.com',
      raw_spec_text: '나의 기존 스펙 텍스트',
      raw_pref_text: '나의 기존 희망 조건 텍스트',
      subscription: { status: 'active', plan_type: 'premium' }
    });

  } catch (err) {
    console.error('Profile GET error:', err);
    return jsonResponse({ error: 'server_error' }, 500);
  }
}

// POST /api/profile/:token
export async function onRequestPost(context) {
  const { env, params } = context;
  const token = params.token;
  const GEMINI_API_KEY = env.GEMINI_API_KEY;

  if (!token || token.length < 10) {
    return jsonResponse({ success: false, error: 'invalid_token' }, 400);
  }

  try {
    const body = await context.request.json();
    const { name, spec_text, pref_text } = body;

    // 1. 검증
    if (!name || name.trim().length < 2) return jsonResponse({ success: false, error: '이름을 입력해주세요.' }, 400);

    // 2. Gemini API 재파싱
    const geminiRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{
          parts: [{ text: `사용자 정보를 업데이트해줘. 이름: ${name}, 스펙: ${spec_text}, 희망조건: ${pref_text}` }]
        }],
        generationConfig: { responseMimeType: "application/json" }
      })
    });

    const geminiData = await geminiRes.json();
    const parsedData = JSON.parse(geminiData.candidates[0].content.parts[0].text);

    // 3. MySQL UPDATE (Cloudflare Tunnel 도메인 이용)
    // TODO: DB 업데이트 로직 구현
    console.log('Parsed Data to update:', parsedData);

    return jsonResponse({ success: true, message: '수정되었습니다.' });

  } catch (err) {
    console.error('Profile POST error:', err);
    return jsonResponse({ success: false, error: '처리 중 오류가 발생했습니다.' }, 500);
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
