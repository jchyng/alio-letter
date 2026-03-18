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


_ICON_CHECK = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M20 6 9 17l-5-5"/></svg>'
_ICON_X = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><circle cx="12" cy="12" r="10"/><path d="M4.929 4.929 19.07 19.071"/></svg>'

_ELIG_LABELS = [
    ("education", "학력"),
    ("career",    "경력"),
    ("age",       "연령"),
    ("language",  "어학"),
    ("certificate", "자격증"),
    ("etc",       "기타"),
]


def _eligibility_rows(eligibility: dict, unmet: list[str]) -> str:
    """자격요건 항목별 충족/미충족 행 생성."""
    rows = []
    for key, label in _ELIG_LABELS:
        val = (eligibility or {}).get(key, "")
        if not val:
            continue
        is_unmet = any(label in u or key in u.lower() for u in unmet)
        icon = _ICON_X if is_unmet else _ICON_CHECK
        text_color = "#dc2626" if is_unmet else "#334155"
        sub_color = "#dc2626" if is_unmet else "#94a3b8"
        rows.append(f"""
      <tr>
        <td style="width:28px;padding:10px 6px 10px 16px;vertical-align:middle;border-bottom:1px solid #f1f5f9;">{icon}</td>
        <td style="padding:10px 16px 10px 4px;vertical-align:middle;border-bottom:1px solid #f1f5f9;">
          <span style="font-size:13px;font-weight:600;color:{text_color};">{label}</span>
          <span style="display:block;font-size:11px;color:{sub_color};margin-top:2px;">{val}</span>
        </td>
      </tr>""")
    return "".join(rows)


def _track_section(track: dict, judgment: dict, is_last: bool = False) -> str:
    """트랙 1개 HTML 블록 생성."""
    track_name   = track.get("track_name", "")
    total        = track.get("total_positions", "")
    eligibility  = track.get("eligibility") or {}
    eligible     = judgment.get("eligible", False)
    unmet        = judgment.get("unmet") or []
    bonus        = judgment.get("bonus_summary", "없음")
    bonus_reasons = judgment.get("bonus_reasons") or []

    count_str = f" · {total}명" if total else ""
    border_bottom = "" if is_last else "border-bottom:2px solid #e2e8f0;"

    if eligible:
        badge = '<span style="background:#1d4ed8;color:#fff;font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;">지원 가능</span>'
        header_bg = "#eff6ff"
        header_border = "border-top:2px solid #1d4ed8;"
    else:
        badge = '<span style="background:#f1f5f9;color:#94a3b8;font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;">미충족</span>'
        header_bg = "#f8fafc"
        header_border = "border-top:1px solid #e2e8f0;"

    # 자격요건 테이블
    elig_rows = _eligibility_rows(eligibility, unmet)
    elig_table = f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-top:12px;">
      {elig_rows}
    </table>""" if elig_rows else ""

    # 가산점 / 미충족 블록
    extra_block = ""
    if eligible and bonus and bonus != "없음":
        reasons_html = "".join(
            f'<li style="margin-bottom:3px;">{r}</li>' for r in bonus_reasons
        ) if bonus_reasons else ""
        extra_block = f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">
      <tr><td style="border-left:3px solid #1d4ed8;padding:10px 14px;background:#eff6ff;border-radius:0 6px 6px 0;">
        <span style="font-size:12px;font-weight:700;color:#1e3a8a;">가산점 {bonus}</span>
        {'<ul style="margin:6px 0 0;padding-left:16px;font-size:11px;color:#3b5998;line-height:1.7;">' + reasons_html + '</ul>' if reasons_html else ''}
      </td></tr>
    </table>"""
    elif not eligible and unmet:
        unmet_items = "".join(
            f'<li style="margin-bottom:3px;">{u}</li>' for u in unmet
        )
        extra_block = f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">
      <tr><td style="border-left:3px solid #dc2626;padding:10px 14px;background:#fef2f2;border-radius:0 6px 6px 0;">
        <span style="font-size:12px;font-weight:700;color:#991b1b;">미충족 항목</span>
        <ul style="margin:6px 0 0;padding-left:16px;font-size:11px;color:#b91c1c;line-height:1.7;">{unmet_items}</ul>
      </td></tr>
    </table>"""

    return f"""
  <!-- 트랙: {track_name} -->
  <tr><td style="{header_bg and f'background:{header_bg};'}{header_border}padding:12px 20px;{border_bottom}">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td><span style="font-size:14px;font-weight:800;color:#0f172a;">{track_name}</span><span style="font-size:12px;color:#94a3b8;margin-left:6px;">{count_str}</span></td>
      <td align="right">{badge}</td>
    </tr></table>
    {elig_table}
    {extra_block}
  </td></tr>"""


def build_email_html(user_name: str, items: list[dict], edit_token: str = "") -> str:
    """이메일 본문 HTML 생성.

    items 구조:
        [{"posting": Posting dict, "tracks": [{"track": PostingTrack, "judgment": TrackJudgment}]}]
    edit_token: 사용자 프로필 페이지 링크 생성용 (없으면 링크 미포함)
    """
    import datetime
    today = datetime.date.today().strftime("%Y-%m-%d")

    eligible_count = sum(
        1 for item in items
        for t in item.get("tracks", [])
        if t["judgment"].get("eligible")
    )

    if edit_token:
        profile_url = f"{_SITE_BASE}/profile?token={edit_token}"
        footer_manage = f'<a href="{profile_url}" style="font-size:12px;color:#64748b;text-decoration:underline;margin-right:16px;">내 정보 수정하기</a>'
        footer_unsub  = f'<a href="{profile_url}" style="font-size:12px;color:#94a3b8;text-decoration:underline;">알림 해지</a>'
    else:
        footer_manage = f'<a href="{_SITE_BASE}" style="font-size:12px;color:#64748b;text-decoration:underline;margin-right:16px;">alio-letter 바로가기</a>'
        footer_unsub  = ""

    posting_blocks = []
    for item in items:
        posting = item["posting"]
        title    = posting.get("title", "")
        org      = posting.get("org_name") or posting.get("org", "")
        deadline = posting.get("deadline", "")
        url      = posting.get("posting_url") or posting.get("url", "")
        salary_url = posting.get("salary_url", "")
        tracks   = item.get("tracks", [])

        track_sections = "".join(
            _track_section(t["track"], t["judgment"], is_last=(i == len(tracks) - 1))
            for i, t in enumerate(tracks)
        )

        salary_btn = ""
        if salary_url:
            salary_btn = f'<td style="padding-left:8px;width:50%;"><a href="{salary_url}" style="display:block;background:#ffffff;color:#1d4ed8;text-align:center;padding:12.5px;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;border:1.5px solid #1d4ed8;">연봉 정보 보기</a></td>'

        posting_blocks.append(f"""
<!-- ━━━ 공고: {org} ━━━ -->
<tr><td style="height:16px;background:#ffffff;"></td></tr>
<tr>
  <td style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-radius:12px;overflow:hidden;">

      <!-- 공고 히어로 -->
      <tr><td style="background:#0f172a;padding:20px 20px 22px;border-bottom:3px solid #1d4ed8;">
        <p style="margin:0 0 4px;font-size:10px;color:#475569;letter-spacing:0.8px;">공공기관 채용공고</p>
        <p style="margin:0 0 6px;font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;">{org}</p>
        <p style="margin:0 0 14px;font-size:12px;color:#94a3b8;line-height:1.5;">{title}</p>
        <span style="font-size:18px;font-weight:900;color:#ffffff;">마감 {deadline}</span>
      </td></tr>

      <!-- 트랙 목록 -->
      {track_sections}

      <!-- CTA -->
      <tr><td style="padding:16px 20px 12px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="{'width:50%;padding-right:8px;' if salary_url else ''}">
            <a href="{url}" style="display:block;background:#1d4ed8;color:#ffffff;text-align:center;padding:14px;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;">잡알리오 원문 보기</a>
          </td>
          {salary_btn}
        </tr></table>
      </td></tr>

    </table>
  </td>
</tr>""")

    body = "\n".join(posting_blocks)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Alio·Letter — 채용 분석 레포트</title>
  <style>
    body{{margin:0;padding:0;background:#f1f5f9;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}
    table,td{{mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;}}
    @media screen and (max-width:600px){{
      .main-wrapper{{width:100%!important;border-radius:0!important;}}
      .main-container{{padding:0!important;}}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;-webkit-font-smoothing:antialiased;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;" class="main-container">
<tr><td align="center" style="padding:24px 16px;" class="main-container">

<table width="600" cellpadding="0" cellspacing="0" border="0" class="main-wrapper" style="max-width:600px;width:100%;background:#f1f5f9;">

  <!-- ━━━ 헤더 바 ━━━ -->
  <tr><td style="background:#0f172a;border-radius:12px 12px 0 0;padding:10px 20px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td><span style="font-size:13px;font-weight:800;color:#ffffff;">Alio·Letter</span><span style="font-size:11px;color:#475569;margin-left:8px;">채용 분석 레포트</span></td>
      <td align="right"><span style="font-size:10px;color:#475569;">{today}</span></td>
    </tr></table>
  </td></tr>

  <!-- ━━━ 인트로 ━━━ -->
  <tr><td style="background:#ffffff;padding:20px 20px 4px;">
    <p style="margin:0 0 4px;font-size:15px;color:#0f172a;">안녕하세요, <strong>{user_name}</strong>님!</p>
    <p style="margin:0;font-size:13px;color:#64748b;">오늘 매칭된 공고 <strong>{len(items)}건</strong> · 지원 가능 트랙 <strong style="color:#1d4ed8;">{eligible_count}개</strong></p>
  </td></tr>

  <!-- ━━━ 공고 목록 ━━━ -->
  {body}

  <!-- ━━━ 푸터 ━━━ -->
  <tr><td style="height:16px;"></td></tr>
  <tr><td style="background:#f8fafc;border-radius:0 0 12px 12px;border-top:1px solid #e2e8f0;padding:16px 20px;">
    <span style="font-size:11px;color:#94a3b8;line-height:1.8;display:block;">
      본 메일은 Alio·Letter 맞춤 채용 알림 서비스에서 발송되었습니다.<br/>
      점수·자격 판단은 AI 추정치이며, 최종 기준은 공고 원문을 확인하세요.
    </span>
    <span style="display:block;margin-top:12px;">{footer_manage}{footer_unsub}</span>
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
