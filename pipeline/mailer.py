"""
이메일 발송 모듈 (Resend API).

# 왜 Resend인가?
# Cloudflare·커스텀 도메인 미준비 상태에서도 .env 키만으로 즉시 테스트 가능.
# RESEND_FROM 미설정 시 onboarding@resend.dev 폴백 (개발용 무인증 도메인).

환경 변수 (.env):
    RESEND_API_KEY — Resend API 키 (없으면 발송 skip)
    RESEND_FROM    — 발신 주소 (없으면 onboarding@resend.dev)
"""

import datetime
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

_DEFAULT_FROM = "onboarding@resend.dev"
_SITE_BASE = "https://alio-letter.pages.dev"

_ICON_CHECK = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block;"><path d="M20 6 9 17l-5-5"/></svg>'

_ELIG_LABELS = [
    ("education",   "학력"),
    ("career",      "경력"),
    ("age",         "연령"),
    ("language",    "어학"),
    ("certificate", "자격증"),
    ("etc",         "기타"),
]


def _req_rows(eligibility: dict) -> str:
    """자격요건 항목별 ✓ 행 생성 (eligible 트랙만 오므로 모두 충족)."""
    rows = []
    for key, label in _ELIG_LABELS:
        val = (eligibility or {}).get(key, "")
        if not val:
            continue
        rows.append(f"""
      <tr><td style="padding:12px 16px;border-bottom:1px solid #f1f5f9;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="width:30px;vertical-align:middle;">{_ICON_CHECK}</td>
          <td style="vertical-align:middle;">
            <span style="font-size:13px;font-weight:600;color:#1e293b;">{label}</span>
            <span style="display:block;font-size:11px;color:#94a3b8;margin-top:2px;">{val}</span>
          </td>
        </tr></table>
      </td></tr>""")
    return "".join(rows)


def _bonus_rows(bonus_reasons: list) -> str:
    """가산점 항목별 행 생성."""
    if not bonus_reasons:
        return ""
    rows = []
    for reason in bonus_reasons:
        rows.append(f"""
      <tr>
        <td style="width:46px;padding:10px 8px 10px 16px;vertical-align:middle;border-bottom:1px solid #f8fafc;">{_ICON_CHECK}</td>
        <td style="padding:10px 16px 10px 4px;vertical-align:middle;border-bottom:1px solid #f8fafc;">
          <span style="font-size:13px;font-weight:600;color:#334155;">{reason}</span>
        </td>
      </tr>""")
    return "".join(rows)


def _track_block(track: dict, judgment: dict, is_recommended: bool) -> str:
    """eligible 트랙 1개 HTML 블록. 목업 트랙 A/B 섹션 구조."""
    track_name    = track.get("track_name", "")
    total         = track.get("total_positions", "")
    eligibility   = track.get("eligibility") or {}
    bonus         = judgment.get("bonus_summary", "없음")
    bonus_reasons = judgment.get("bonus_reasons") or []

    count_str = f" · {total}명" if total else ""

    # 트랙 헤더 — 추천 트랙은 파란 강조
    if is_recommended:
        header_html = f"""
  <tr>
    <td style="background:#eff6ff;padding:12px 20px;border-top:2px solid #1d4ed8;border-bottom:1px solid #bfdbfe;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td><span style="font-size:14px;font-weight:800;color:#1e3a8a;">{track_name}</span><span style="font-size:12px;color:#94a3b8;margin-left:8px;">{count_str}</span></td>
        <td align="right"><span style="background:#1d4ed8;color:#ffffff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:4px;">추천</span></td>
      </tr></table>
    </td>
  </tr>"""
        req_border  = "border:1px solid #bfdbfe;"
        bonus_border = "border:1px solid #bfdbfe;"
        bonus_bg    = "background:#eff6ff;"
        bonus_color = "#1e3a8a"
        total_color = "#1e3a8a"
    else:
        header_html = f"""
  <tr>
    <td style="background:#f1f5f9;padding:12px 20px;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;">
      <span style="font-size:14px;font-weight:800;color:#0f172a;">{track_name}</span>
      <span style="font-size:12px;color:#94a3b8;margin-left:8px;">{count_str}</span>
    </td>
  </tr>"""
        req_border  = "border:1px solid #e2e8f0;"
        bonus_border = "border:1px solid #e2e8f0;"
        bonus_bg    = "background:#f8fafc;"
        bonus_color = "#334155"
        total_color = "#0f172a"

    # 자격요건 체크리스트
    req_rows = _req_rows(eligibility)
    req_section = f"""
  <tr><td style="padding:16px 20px 0;">
    <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:0.8px;">기본 자격요건</p>
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="{req_border}border-radius:8px;overflow:hidden;">
      {req_rows}
    </table>
  </td></tr>""" if req_rows else ""

    # 가산점 섹션
    bonus_row_html = _bonus_rows(bonus_reasons)
    if bonus_row_html:
        bonus_section = f"""
  <tr><td style="padding:16px 20px 0;">
    <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:0.8px;">가산점</p>
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="{bonus_border}border-radius:8px;overflow:hidden;">
      {bonus_row_html}
      <tr style="{bonus_bg}">
        <td colspan="2" style="padding:14px 16px;font-size:13px;font-weight:800;color:{bonus_color};">
          가산점 합계: <span style="font-size:16px;">{bonus}</span>
        </td>
      </tr>
    </table>
  </td></tr>"""
    elif bonus and bonus != "없음":
        bonus_section = f"""
  <tr><td style="padding:16px 20px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td style="border-left:3px solid #1d4ed8;padding:10px 14px;{bonus_bg}border-radius:0 6px 6px 0;">
        <span style="font-size:13px;font-weight:700;color:{bonus_color};">가산점 {bonus}</span>
      </td></tr>
    </table>
  </td></tr>"""
    else:
        bonus_section = ""

    return header_html + req_section + bonus_section


def build_email_html(user_name: str, items: list[dict], edit_token: str = "") -> str:
    """이메일 본문 HTML 생성. eligible=True 트랙만 포함.

    items 구조:
        [{"posting": Posting dict, "tracks": [{"track": PostingTrack, "judgment": TrackJudgment}]}]
    edit_token: 사용자 프로필 페이지 링크 생성용 (없으면 링크 미포함)
    """
    today = datetime.date.today().strftime("%Y-%m-%d")

    if edit_token:
        profile_url   = f"{_SITE_BASE}/profile?token={edit_token}"
        footer_manage = f'<a href="{profile_url}" style="font-size:12px;color:#64748b;text-decoration:underline;margin-right:16px;">내 정보 수정하기</a>'
        footer_unsub  = f'<a href="{profile_url}" style="font-size:12px;color:#94a3b8;text-decoration:underline;">알림 해지</a>'
    else:
        footer_manage = f'<a href="{_SITE_BASE}" style="font-size:12px;color:#64748b;text-decoration:underline;margin-right:16px;">alio-letter 바로가기</a>'
        footer_unsub  = ""

    posting_blocks = []
    for item in items:
        posting = item["posting"]
        org        = posting.get("org_name") or posting.get("org", "")
        title      = posting.get("title", "")
        deadline   = posting.get("deadline", "")
        url        = posting.get("posting_url") or posting.get("url", "")
        salary_url = posting.get("salary_url", "")

        # eligible 트랙만 추림
        eligible_tracks = [t for t in item.get("tracks", []) if t["judgment"].get("eligible")]
        if not eligible_tracks:
            continue

        # 가산점이 있는 트랙을 "추천"으로 강조 (없으면 첫 번째가 추천)
        has_bonus = [t for t in eligible_tracks if t["judgment"].get("bonus_summary", "없음") != "없음"]
        recommended_name = has_bonus[0]["track"]["track_name"] if has_bonus else eligible_tracks[0]["track"]["track_name"]

        track_sections = "\n".join(
            _track_block(t["track"], t["judgment"], is_recommended=(t["track"]["track_name"] == recommended_name))
            for t in eligible_tracks
        )

        salary_btn = ""
        if salary_url:
            salary_btn = f'<td style="padding-left:6px;width:50%;"><a href="{salary_url}" style="display:block;background:#ffffff;color:#1d4ed8;text-align:center;padding:12.5px;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;border:1.5px solid #1d4ed8;">연봉 정보 보기</a></td>'

        posting_blocks.append(f"""
<!-- 공고 카드: {org} -->
<tr><td style="height:12px;background:#ffffff;"></td></tr>
<table width="100%" cellpadding="0" cellspacing="0" border="0">

  <!-- ① 공고 히어로 -->
  <tr>
    <td style="background:#0f172a;padding:20px 20px 24px;border-bottom:3px solid #1d4ed8;">
      <p style="margin:0 0 4px;font-size:10px;color:#475569;letter-spacing:0.8px;">공공기관 채용공고</p>
      <p style="margin:0 0 4px;font-size:24px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;">{org}</p>
      <p style="margin:0 0 14px;font-size:12px;color:#64748b;line-height:1.5;">{title}</p>
      <span style="font-size:20px;font-weight:900;color:#ffffff;">마감 {deadline}</span>
    </td>
  </tr>

  {track_sections}

  <!-- CTA -->
  <tr><td style="height:4px;background:#ffffff;"></td></tr>
  <tr><td style="padding:16px 20px 20px;background:#ffffff;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="{'width:50%;padding-right:6px;' if salary_url else ''}">
        <a href="{url}" style="display:block;background:#1d4ed8;color:#ffffff;text-align:center;padding:14px;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;">잡알리오 원문 보기</a>
      </td>
      {salary_btn}
    </tr></table>
  </td></tr>

</table>""")

    body = "\n".join(posting_blocks)
    eligible_count = sum(
        1 for item in items
        for t in item.get("tracks", [])
        if t["judgment"].get("eligible")
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Alio·Letter — 채용 분석 레포트</title>
  <style>
    body{{margin:0;padding:0;background:#f1f5f9;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}
    table,td{{mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;}}
    img{{-ms-interpolation-mode:bicubic;border:0;outline:none;text-decoration:none;}}
    @media screen and (max-width:600px){{
      .main-wrapper{{width:100%!important;border-radius:0!important;}}
      .main-container{{padding:0!important;}}
      .stack-column{{display:block!important;width:100%!important;max-width:100%!important;padding-left:0!important;padding-right:0!important;margin-bottom:12px!important;box-sizing:border-box;}}
      .spacer{{display:none!important;}}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;-webkit-font-smoothing:antialiased;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;" class="main-container">
<tr><td align="center" style="padding:24px 16px;" class="main-container">

<table width="600" cellpadding="0" cellspacing="0" border="0" class="main-wrapper" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.10);">

  <!-- ━━━ 헤더 바 ━━━ -->
  <tr>
    <td style="background:#0f172a;padding:10px 20px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td><span style="font-size:13px;font-weight:800;color:#ffffff;">Alio·Letter</span><span style="font-size:11px;color:#475569;margin-left:8px;">채용 분석 레포트</span></td>
        <td align="right"><span style="font-size:10px;color:#475569;">{today}</span></td>
      </tr></table>
    </td>
  </tr>

  <!-- ━━━ 인트로 ━━━ -->
  <tr><td style="padding:20px 20px 8px;background:#ffffff;">
    <p style="margin:0 0 4px;font-size:15px;color:#0f172a;">안녕하세요, <strong>{user_name}</strong>님!</p>
    <p style="margin:0;font-size:13px;color:#64748b;">오늘 지원 가능한 트랙 <strong style="color:#1d4ed8;">{eligible_count}개</strong>를 분석했습니다.</p>
  </td></tr>

  <!-- ━━━ 공고 목록 ━━━ -->
  {body}

  <!-- ━━━ 푸터 ━━━ -->
  <tr><td style="height:16px;background:#ffffff;"></td></tr>
  <tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:16px 20px;border-radius:0 0 12px 12px;">
    <span style="font-size:11px;color:#94a3b8;line-height:1.8;display:block;">
      본 메일은 Alio·Letter 맞춤 채용 알림 서비스에서 발송되었습니다.<br/>
      자격·가산점 판단은 AI 추정치이며, 최종 기준은 공고 원문을 확인하세요.
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
