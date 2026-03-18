"""
이메일 발송 모듈 (Resend API).

# 왜 Resend인가?
# Cloudflare·커스텀 도메인 미준비 상태에서도 .env 키만으로 즉시 테스트 가능.
# RESEND_FROM 미설정 시 onboarding@resend.dev 폴백 (개발용 무인증 도메인).

환경 변수 (.env):
    RESEND_API_KEY — Resend API 키 (없으면 발송 skip)
    RESEND_FROM    — 발신 주소 (없으면 onboarding@resend.dev)
"""

import os

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

_DEFAULT_FROM = "onboarding@resend.dev"


_SITE_BASE = "https://alio-letter.pages.dev"


def build_email_html(user_name: str, items: list[dict], edit_token: str = "") -> str:
    """이메일 본문 HTML 생성.

    items 구조:
        [{"posting": Posting dict, "tracks": [{"track": PostingTrack, "judgment": TrackJudgment}]}]
    edit_token: 사용자 프로필 페이지 링크 생성용 (없으면 링크 미포함)
    """
    sections = []
    for item in items:
        posting = item["posting"]
        title = posting.get("title", "")
        org = posting.get("org_name") or posting.get("org", "")
        deadline = posting.get("deadline", "")
        url = posting.get("posting_url") or posting.get("url", "")
        salary_url = posting.get("salary_url", "")

        track_rows = []
        for t in item.get("tracks", []):
            track = t["track"]
            judgment = t["judgment"]
            track_name = track.get("track_name", "")
            total = track.get("total_positions", "")
            eligible = judgment.get("eligible", False)
            bonus = judgment.get("bonus_summary", "없음")
            unmet = judgment.get("unmet", [])
            bonus_reasons = judgment.get("bonus_reasons", [])

            count_str = f" ({total}명)" if total else ""
            if eligible:
                bonus_detail = ""
                if bonus and bonus != "없음":
                    bonus_detail = f'<span style="color:#2563eb;font-size:13px">🎯 가산점 {bonus}</span>'
                    if bonus_reasons:
                        reasons_text = " / ".join(bonus_reasons)
                        bonus_detail += f'<br><span style="color:#6b7280;font-size:12px">{reasons_text}</span>'
                track_rows.append(f"""
        <tr style="border-top:1px solid #f3f4f6">
          <td style="padding:10px 8px;vertical-align:top">
            <span style="display:inline-block;background:#dcfce7;color:#166534;border-radius:4px;padding:1px 7px;font-size:12px;font-weight:600">지원 가능</span>
          </td>
          <td style="padding:10px 8px">
            <strong style="font-size:14px">{track_name}</strong>{count_str}
            {'<br>' + bonus_detail if bonus_detail else ''}
          </td>
        </tr>""")
            else:
                unmet_text = " / ".join(unmet) if unmet else "-"
                track_rows.append(f"""
        <tr style="border-top:1px solid #f3f4f6">
          <td style="padding:10px 8px;vertical-align:top">
            <span style="display:inline-block;background:#f3f4f6;color:#9ca3af;border-radius:4px;padding:1px 7px;font-size:12px;font-weight:600">미충족</span>
          </td>
          <td style="padding:10px 8px">
            <strong style="font-size:14px;color:#9ca3af">{track_name}</strong>{count_str}
            <br><span style="color:#ef4444;font-size:12px">{unmet_text}</span>
          </td>
        </tr>""")

        tracks_html = f'<table style="width:100%;border-collapse:collapse">{"".join(track_rows)}</table>' if track_rows else ""
        cta_html = f'<a href="{url}" style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;padding:8px 18px;border-radius:6px;font-size:14px;font-weight:600">공고 보기 →</a>'
        salary_html = f' &nbsp;<a href="{salary_url}" style="font-size:13px;color:#6b7280">연봉 정보</a>' if salary_url else ""

        sections.append(f"""
<div style="margin-bottom:20px;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden">
  <div style="background:#f8fafc;padding:14px 16px;border-bottom:1px solid #e5e7eb">
    <p style="margin:0 0 2px;font-size:12px;color:#6b7280">{org}</p>
    <h3 style="margin:0 0 4px;font-size:16px;color:#111827;line-height:1.4">{title}</h3>
    <p style="margin:0;font-size:12px;color:#9ca3af">마감 {deadline}</p>
  </div>
  <div style="padding:4px 0">
    {tracks_html}
  </div>
  <div style="padding:12px 16px;border-top:1px solid #f3f4f6">
    {cta_html}{salary_html}
  </div>
</div>""")

    body = "\n".join(sections)
    eligible_count = sum(
        1 for item in items
        for t in item.get("tracks", [])
        if t["judgment"].get("eligible")
    )

    if edit_token:
        profile_url = f"{_SITE_BASE}/profile?token={edit_token}"
        footer_links = (
            f'<a href="{profile_url}" style="color:#6b7280;text-decoration:none">내 정보 수정</a>'
            f' &nbsp;·&nbsp; '
            f'<a href="{profile_url}" style="color:#6b7280;text-decoration:none">알림 해지</a>'
        )
    else:
        footer_links = '내 정보 수정은 <a href="https://alio-letter.pages.dev" style="color:#6b7280">alio-letter</a>에서'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>alio-letter</title>
</head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 16px">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">

        <!-- 헤더 -->
        <tr><td style="background:#1d4ed8;border-radius:10px 10px 0 0;padding:24px 28px">
          <p style="margin:0;font-size:13px;color:#93c5fd;letter-spacing:1px">ALIO-LETTER</p>
          <h1 style="margin:6px 0 0;font-size:22px;color:#fff;font-weight:700">오늘의 맞춤 공고</h1>
        </td></tr>

        <!-- 본문 -->
        <tr><td style="background:#fff;padding:24px 28px">
          <p style="margin:0 0 6px;font-size:15px;color:#374151">안녕하세요, <strong>{user_name}</strong>님!</p>
          <p style="margin:0 0 20px;font-size:14px;color:#6b7280">오늘 매칭된 공고 <strong>{len(items)}건</strong> 중 지원 가능한 트랙 <strong style="color:#1d4ed8">{eligible_count}개</strong>가 있습니다.</p>
          {body}
        </td></tr>

        <!-- 푸터 -->
        <tr><td style="background:#f3f4f6;border-radius:0 0 10px 10px;padding:16px 28px;text-align:center">
          <p style="margin:0;font-size:12px;color:#9ca3af">
            {footer_links}
            <br><span style="margin-top:4px;display:inline-block">alio-letter · 공공기관 채용 알림 서비스</span>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(to_email: str, to_name: str, subject: str, html: str) -> bool:
    """Resend API로 이메일 발송. 실패 시 False 반환 (예외 미전파).
    RESEND_API_KEY 없으면 발송 skip하고 False 반환.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print(f"[mailer] RESEND_API_KEY 없음 — 발송 skip: {to_email}")
        return False

    from_addr = os.environ.get("RESEND_FROM", _DEFAULT_FROM)

    try:
        import resend  # type: ignore
        resend.api_key = api_key
        resend.Emails.send({
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        print(f"[mailer] 발송 완료: {to_email}")
        return True
    except Exception as e:
        print(f"[mailer] 발송 실패 ({to_email}): {e}")
        return False
