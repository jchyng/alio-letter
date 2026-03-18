/**
 * POST /api/register
 * 입력 검증 → Gemini API 스펙 파싱 → D1 INSERT users
 */

import { parseSpecWithGemini } from './_lib/gemini.js';

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
      parsedSpec = await parseSpecWithGemini(GEMINI_API_KEY, spec_text.trim());
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

async function sendWelcomeEmail(env, to, name, editToken) {
  const from = env.RESEND_FROM || 'onboarding@resend.dev';
  const profileUrl = `https://alio-letter.pages.dev/profile?token=${editToken}`;
  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Alio·Letter 등록 완료</title>
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
      <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td><span style="font-size:14px;font-weight:800;color:#fff;">Alio·Letter</span>
            <span style="font-size:11px;color:#475569;margin-left:8px;">공공기관 채용 알리미</span></td>
      </tr></table>
    </td>
  </tr>

  <!-- 히어로 -->
  <tr>
    <td style="background:#0f172a;padding:32px 24px 36px;border-bottom:3px solid #1d4ed8;" class="pad">
      <p style="margin:0 0 8px;font-size:12px;color:#64748b;letter-spacing:0.8px;">등록 완료</p>
      <p style="margin:0 0 12px;font-size:26px;font-weight:900;color:#fff;letter-spacing:-0.5px;">환영합니다, ${name}님!</p>
      <p style="margin:0;font-size:14px;color:#94a3b8;line-height:1.7;">
        Alio·Letter에 등록이 완료되었습니다.<br/>
        매일 아침 맞춤 공공기관 채용공고를 분석해 전달드립니다.
      </p>
    </td>
  </tr>

  <!-- 안내 카드 -->
  <tr>
    <td style="padding:28px 24px 8px;" class="pad">
      <p style="margin:0 0 16px;font-size:13px;font-weight:700;color:#0f172a;">이런 정보를 받아볼 수 있어요</p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f1f5f9;vertical-align:top;width:28px;font-size:16px;">✅</td>
          <td style="padding:12px 0 12px 10px;border-bottom:1px solid #f1f5f9;">
            <span style="font-size:13px;font-weight:600;color:#1e293b;">자격요건 충족 여부</span>
            <span style="display:block;font-size:12px;color:#64748b;margin-top:2px;">학력·경력·나이 등 기준을 자동으로 비교해드려요</span>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f1f5f9;vertical-align:top;font-size:16px;">⭐</td>
          <td style="padding:12px 0 12px 10px;border-bottom:1px solid #f1f5f9;">
            <span style="font-size:13px;font-weight:600;color:#1e293b;">가산점 분석</span>
            <span style="display:block;font-size:12px;color:#64748b;margin-top:2px;">내 스펙에 적용되는 가산점, 준비 가능한 항목까지 알려드려요</span>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 0;vertical-align:top;font-size:16px;">📋</td>
          <td style="padding:12px 0 12px 10px;">
            <span style="font-size:13px;font-weight:600;color:#1e293b;">맞춤 공고 선별</span>
            <span style="display:block;font-size:12px;color:#64748b;margin-top:2px;">희망 근무지·분야·고용형태에 맞는 공고만 골라서 보내드려요</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- CTA -->
  <tr>
    <td style="padding:24px 24px 28px;" class="pad">
      <p style="margin:0 0 12px;font-size:13px;color:#64748b;">
        스펙과 희망조건을 더 자세히 입력할수록 매칭 정확도가 높아집니다.
      </p>
      <a href="${profileUrl}"
         style="display:block;background:#1d4ed8;color:#fff;text-align:center;padding:14px;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;">
        내 정보 입력·수정하기
      </a>
    </td>
  </tr>

  <!-- 푸터 -->
  <tr>
    <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:16px 24px;border-radius:0 0 12px 12px;">
      <span style="font-size:11px;color:#94a3b8;line-height:1.8;display:block;">
        본 메일은 Alio·Letter 서비스 가입으로 발송되었습니다.<br/>
        공고 알림을 중단하려면 내 정보 페이지에서 탈퇴하실 수 있습니다.
      </span>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>`;
  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ from, to: [to], subject: '[Alio·Letter] 등록이 완료되었습니다 🎉', html }),
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
