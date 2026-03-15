/**
 * POST /api/send-magic-link
 * 사용자가 이메일을 입력하면, 해당 이메일에 맞는 프로필 관리 토큰(edit_token)을 조회하여
 * 이메일로 전송(로그인 링크 발송)하는 API입니다.
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
  try {
    const body = await context.request.json();
    const { email } = body;

    if (!email || !email.includes('@')) {
      return jsonResponse({ success: false, error: '올바른 이메일 주소를 입력해주세요.' }, 400);
    }

    // D1에서 email로 edit_token 조회
    const user = await context.env.DB.prepare(
      'SELECT edit_token FROM users WHERE email = ?'
    ).bind(email).first();

    // 보안: 가입 여부와 무관하게 동일 응답 (계정 존재 여부 유추 방지)
    if (user) {
      const profileUrl = `https://alio-letter.pages.dev/profile/${user.edit_token}`;
      // TODO: Resend API로 매직링크 이메일 발송
      // await sendMagicLinkEmail(email, profileUrl);
      console.log(`Magic link for ${email}: ${profileUrl}`);
    }

    // 보안상 이메일이 실제 가입되었는지 여부와 상관없이 항상 성공 응답을 보냅니다.
    // (계정 존재 여부를 유추하는 해킹 방지)
    return jsonResponse({ success: true, message: '이메일 발송 요청 성공' });

  } catch (err) {
    console.error('Magic link send error:', err);
    return jsonResponse({ success: false, error: '처리 중 오류가 발생했습니다.' }, 500);
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
