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

    // 1. 서버 사이드 검증 (이름·이메일만 필수, 스펙·조건은 선택)
    if (!name || name.trim().length < 2) return jsonResponse({ success: false, error: '이름을 입력해주세요.' }, 400);
    if (!email || !email.includes('@')) return jsonResponse({ success: false, error: '올바른 이메일을 입력해주세요.' }, 400);

    const normalizedEmail = email.trim().toLowerCase();

    // 2. 기존 사용자 여부 확인 (edit_token 재사용을 위해)
    const existing = await env.DB.prepare(
      'SELECT id, edit_token FROM users WHERE email = ?'
    ).bind(normalizedEmail).first();
    const editToken = existing ? existing.edit_token : crypto.randomUUID();

    // 3. Gemini API — 스펙 파싱 (스펙 텍스트가 있을 때만 호출)
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

    // 4. D1 UPSERT — 기존 사용자면 UPDATE, 신규면 INSERT (edit_token 보존)
    // spec_text가 있을 때만 parsed_spec 갱신 (없으면 기존 값 유지)
    if (existing) {
      const specProvided = spec_text && spec_text.trim();
      await env.DB.prepare(
        specProvided
          ? `UPDATE users SET name=?, raw_spec_text=?, parsed_spec=?, filter_prefs=? WHERE email=?`
          : `UPDATE users SET name=?, filter_prefs=? WHERE email=?`
      ).bind(
        ...(specProvided
          ? [name.trim(), spec_text.trim(), parsedSpec ? JSON.stringify(parsedSpec) : null,
             filter_prefs ? JSON.stringify(filter_prefs) : null, normalizedEmail]
          : [name.trim(), filter_prefs ? JSON.stringify(filter_prefs) : null, normalizedEmail])
      ).run();
    } else {
      await env.DB.prepare(
        `INSERT INTO users (email, name, raw_spec_text, parsed_spec, filter_prefs, edit_token)
         VALUES (?, ?, ?, ?, ?, ?)`
      ).bind(
        normalizedEmail,
        name.trim(),
        spec_text ? spec_text.trim() : null,
        parsedSpec ? JSON.stringify(parsedSpec) : null,
        filter_prefs ? JSON.stringify(filter_prefs) : null,
        editToken
      ).run();
    }

    // 5. 신규 가입 시 환영 이메일 발송 (실패해도 응답에 영향 없음)
    if (!existing && env.RESEND_API_KEY) {
      await sendWelcomeEmail(env, normalizedEmail, name.trim(), editToken);
    }

    return jsonResponse({ success: true, message: existing ? '정보가 업데이트되었습니다.' : '등록되었습니다.' });

  } catch (err) {
    console.error('Register error:', err);
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

async function sendWelcomeEmail(env, to, name, editToken) {
  const from = env.RESEND_FROM || 'onboarding@resend.dev';
  const profileUrl = `https://alio-letter.pages.dev/profile/${editToken}`;
  const html = `
    <p>안녕하세요, ${name}님!</p>
    <p>alio-letter에 등록이 완료되었습니다.</p>
    <p>스펙과 관심 조건을 입력하고 구독을 시작해보세요.</p>
    <p><a href="${profileUrl}">내 정보 관리 바로가기</a></p>
    <hr>
    <p style="color:#aaa;font-size:12px">alio-letter · 본 메일은 발신 전용입니다.</p>
  `;
  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ from, to: [to], subject: '[alio-letter] 등록이 완료되었습니다', html }),
    });
  } catch (e) {
    console.error('Welcome email failed:', e);
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
