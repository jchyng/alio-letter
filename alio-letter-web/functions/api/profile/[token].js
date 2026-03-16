/**
 * GET  /api/profile/:token  — D1에서 사용자 조회
 * POST /api/profile/:token  — Gemini 재파싱 + D1 UPDATE
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
    const user = await env.DB.prepare(
      'SELECT email, name, raw_spec_text, filter_prefs, is_active FROM users WHERE edit_token = ?'
    ).bind(token).first();

    if (!user) return jsonResponse({ error: 'not_found' }, 404);

    return jsonResponse({
      name: user.name,
      email: user.email,
      raw_spec_text: user.raw_spec_text,
      filter_prefs: user.filter_prefs ? JSON.parse(user.filter_prefs) : {},
      is_active: user.is_active === 1,
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
    const { name, spec_text, filter_prefs } = body;

    if (!name || name.trim().length < 2) return jsonResponse({ success: false, error: '이름을 입력해주세요.' }, 400);

    // 토큰 유효성 확인
    const user = await env.DB.prepare(
      'SELECT id FROM users WHERE edit_token = ?'
    ).bind(token).first();
    if (!user) return jsonResponse({ success: false, error: 'not_found' }, 404);

    // Gemini API 재파싱
    let parsedSpec = null;
    if (spec_text && spec_text.trim()) {
      const geminiRes = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: buildSpecPrompt(spec_text) }] }],
            generationConfig: { responseMimeType: 'application/json' },
          }),
        }
      );
      const geminiData = await geminiRes.json();
      try {
        parsedSpec = JSON.parse(geminiData.candidates[0].content.parts[0].text);
      } catch (_) {}
    }

    // D1 UPDATE — spec_text를 보냈을 때만 parsed_spec 갱신 (없으면 기존 값 유지)
    const specProvided = spec_text && spec_text.trim();
    await env.DB.prepare(
      specProvided
        ? `UPDATE users SET name=?, raw_spec_text=?, parsed_spec=?, filter_prefs=? WHERE edit_token=?`
        : `UPDATE users SET name=?, filter_prefs=? WHERE edit_token=?`
    ).bind(
      ...(specProvided
        ? [name.trim(), spec_text.trim(), parsedSpec ? JSON.stringify(parsedSpec) : null,
           filter_prefs ? JSON.stringify(filter_prefs) : null, token]
        : [name.trim(), filter_prefs ? JSON.stringify(filter_prefs) : null, token])
    ).run();

    return jsonResponse({ success: true, message: '수정되었습니다.' });

  } catch (err) {
    console.error('Profile POST error:', err);
    return jsonResponse({ success: false, error: '처리 중 오류가 발생했습니다.' }, 500);
  }
}

function buildSpecPrompt(specText) {
  return `다음 사용자 스펙 텍스트를 아래 JSON 스키마에 맞게 파싱하라. JSON만 출력할 것.

스펙:
${specText}

스키마:
{
  "education": "최종학력 (예: 4년제 대졸, 고졸, 석사)",
  "career_years": 총경력연수(정수, 신입=0),
  "career_fields": [{"field": "분야명", "years": 연수(정수)}],
  "birth_year": 출생연도(정수 또는 null),
  "languages": [{"name": "어학명", "score": 점수(정수)}],
  "certificates": ["자격증명"],
  "military": "필필 또는 면제 또는 미필 또는 해당없음(여성)",
  "disability_grade": "해당없음 또는 경증 또는 중증",
  "veteran_type": "해당없음 또는 해당 유형명",
  "is_low_income": false,
  "is_north_korean_defector": false,
  "is_independent_youth": false,
  "is_multicultural_child": false
}`;
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
