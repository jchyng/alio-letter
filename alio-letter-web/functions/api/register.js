/**
 * POST /api/register
 * 입력 검증 → Gemini API 스펙 파싱 → D1 INSERT users
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
  const GEMINI_API_KEY = env.GEMINI_API_KEY;

  try {
    const body = await context.request.json();
    const { name, email, spec_text, filter_prefs } = body;

    // 1. 서버 사이드 검증
    if (!name || name.trim().length < 2) return jsonResponse({ success: false, error: '이름을 입력해주세요.' }, 400);
    if (!email || !email.includes('@')) return jsonResponse({ success: false, error: '올바른 이메일을 입력해주세요.' }, 400);
    if (!spec_text || !spec_text.trim()) return jsonResponse({ success: false, error: '스펙 정보를 입력해주세요.' }, 400);

    // 2. Gemini API — 스펙 파싱 (UserProfile JSON)
    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: `다음 사용자 스펙을 JSON으로 파싱해줘. 스펙: ${spec_text}` }] }],
          generationConfig: { responseMimeType: 'application/json' },
        }),
      }
    );
    const geminiData = await geminiRes.json();
    let parsedSpec = null;
    try {
      parsedSpec = JSON.parse(geminiData.candidates[0].content.parts[0].text);
    } catch (_) {}

    // 3. edit_token 생성 (crypto.randomUUID)
    const editToken = crypto.randomUUID();

    // 4. D1 INSERT users (중복 이메일은 REPLACE)
    await env.DB.prepare(
      `INSERT OR REPLACE INTO users (email, name, raw_spec_text, parsed_spec, filter_prefs, edit_token)
       VALUES (?, ?, ?, ?, ?, ?)`
    ).bind(
      email.trim().toLowerCase(),
      name.trim(),
      spec_text.trim(),
      parsedSpec ? JSON.stringify(parsedSpec) : null,
      filter_prefs ? JSON.stringify(filter_prefs) : null,
      editToken
    ).run();

    return jsonResponse({ success: true, message: '등록되었습니다.' });

  } catch (err) {
    console.error('Register error:', err);
    return jsonResponse({ success: false, error: '처리 중 오류가 발생했습니다.' }, 500);
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
