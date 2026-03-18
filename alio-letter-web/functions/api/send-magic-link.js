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

    // register.js와 동일하게 정규화 (대소문자 불일치 방지)
    const normalizedEmail = email.trim().toLowerCase();

    // D1에서 email로 edit_token 조회
    const user = await context.env.DB.prepare(
      'SELECT edit_token FROM users WHERE email = ?'
    ).bind(normalizedEmail).first();

    // 보안: 가입 여부와 무관하게 동일 응답 (계정 존재 여부 유추 방지)
    if (user) {
      const profileUrl = `https://alio-letter.pages.dev/profile?token=${user.edit_token}`;
      await sendMagicLinkEmail(context.env, email, profileUrl);
    }

    // 보안상 이메일이 실제 가입되었는지 여부와 상관없이 항상 성공 응답을 보냅니다.
    // (계정 존재 여부를 유추하는 해킹 방지)
    return jsonResponse({ success: true, message: '이메일 발송 요청 성공' });

  } catch (err) {
    console.error('Magic link send error:', err);
    return jsonResponse({ success: false, error: '처리 중 오류가 발생했습니다.' }, 500);
  }
}

async function sendMagicLinkEmail(env, to, profileUrl) {
  const from = env.RESEND_FROM || 'onboarding@resend.dev';
  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Alio·Letter 로그인 링크</title>
  <style>
    body{margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
    table,td{border-collapse:collapse;}
    @media screen and (max-width:600px){
      .wrap{width:100%!important;border-radius:0!important;}
      .pad{padding:20px 16px!important;}
    }
  </style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;">
<tr><td align="center" style="padding:32px 16px;">

<table width="560" cellpadding="0" cellspacing="0" border="0" class="wrap"
       style="max-width:560px;width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.10);">

  <!-- 헤더 -->
  <tr>
    <td style="background:#0f172a;padding:12px 24px;">
      <span style="font-size:14px;font-weight:800;color:#fff;">Alio·Letter</span>
      <span style="font-size:11px;color:#475569;margin-left:8px;">공공기관 채용 알리미</span>
    </td>
  </tr>

  <!-- 히어로 -->
  <tr>
    <td style="background:#0f172a;padding:32px 24px 36px;border-bottom:3px solid #1d4ed8;" class="pad">
      <p style="margin:0 0 8px;font-size:12px;color:#64748b;letter-spacing:0.8px;">로그인 요청</p>
      <p style="margin:0 0 12px;font-size:26px;font-weight:900;color:#fff;letter-spacing:-0.5px;">내 정보 관리 링크</p>
      <p style="margin:0;font-size:14px;color:#94a3b8;line-height:1.7;">
        아래 버튼을 클릭하면 별도 비밀번호 없이<br/>내 정보 관리 페이지로 이동합니다.
      </p>
    </td>
  </tr>

  <!-- CTA -->
  <tr>
    <td style="padding:32px 24px 24px;" class="pad">
      <a href="${profileUrl}"
         style="display:block;background:#1d4ed8;color:#fff;text-align:center;padding:16px;border-radius:8px;font-size:15px;font-weight:700;text-decoration:none;">
        내 정보 관리 페이지로 이동
      </a>
    </td>
  </tr>

  <!-- 보안 안내 -->
  <tr>
    <td style="padding:0 24px 28px;" class="pad">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#fffbeb;border:1px solid #fef3c7;border-radius:8px;padding:14px;">
        <tr>
          <td style="padding:14px;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#92400e;">보안 안내</p>
            <p style="margin:0;font-size:12px;color:#b45309;line-height:1.7;">
              • 이 링크는 본인만 사용해주세요.<br/>
              • 요청하지 않은 링크라면 이 이메일을 무시하셔도 됩니다.<br/>
              • 링크를 타인에게 공유하지 마세요.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- 푸터 -->
  <tr>
    <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:16px 24px;border-radius:0 0 12px 12px;">
      <span style="font-size:11px;color:#94a3b8;line-height:1.8;display:block;">
        본 메일은 로그인 요청에 의해 자동 발송되었습니다.<br/>
        요청하지 않으셨다면 안전하게 무시하셔도 됩니다.
      </span>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>`;
  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ from, to: [to], subject: '[Alio·Letter] 로그인 링크가 도착했습니다', html }),
  });
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
