/**
 * POST /api/register
 * 입력 검증 → Gemini API 파싱 → MySQL 직접 저장 (via Cloudflare Tunnel)
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
    const { name, email, spec_text, pref_text } = body;

    // 1. 서버 사이드 검증
    if (!name || name.trim().length < 2) return jsonResponse({ success: false, error: '이름을 입력해주세요.' }, 400);
    if (!email || !email.includes('@')) return jsonResponse({ success: false, error: '올바른 이메일을 입력해주세요.' }, 400);

    // 2. Gemini API를 이용한 스펙 파싱
    // (여기서는 예시로 fetch 호출 구조만 작성하며, 실제 프롬프트는 별도 관리 권장)
    const geminiRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{
          parts: [{ text: `다음 사용자 스펙과 희망조건을 JSON 구조로 파싱해줘. 스펙: ${spec_text}, 희망조건: ${pref_text}` }]
        }],
        generationConfig: { responseMimeType: "application/json" }
      })
    });

    const geminiData = await geminiRes.json();
    const parsedData = JSON.parse(geminiData.candidates[0].content.parts[0].text);

    // 3. MySQL DB 저장 (Cloudflare Tunnel 도메인 이용)
    // TODO: mysql2 라이브러리 또는 HTTP Proxy를 사용하여 db.yourdomain.com에 접속 및 저장 로직 구현
    console.log('Parsed Data to save:', parsedData);
    
    // 임시 성공 응답
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
