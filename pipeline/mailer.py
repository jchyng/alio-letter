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


def build_email_html(user_name: str, items: list[dict]) -> str:
    """이메일 본문 HTML 생성.

    items 구조:
        [{"posting": Posting dict, "tracks": [{"track": PostingTrack, "judgment": TrackJudgment}]}]
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
            icon = "✅" if eligible else "❌"
            bonus = judgment.get("bonus_summary", "없음")
            unmet = judgment.get("unmet", [])

            detail = f"가산점: {bonus}" if eligible else f"미충족: {', '.join(unmet) if unmet else '-'}"
            count_str = f" ({total}명)" if total else ""
            track_rows.append(
                f"<li>{icon} <strong>{track_name}</strong>{count_str} — {detail}</li>"
            )

        tracks_html = "<ul>" + "".join(track_rows) + "</ul>" if track_rows else ""
        link_html = f'<a href="{url}">잡알리오 보기</a>'
        salary_html = f' | <a href="{salary_url}">연봉 보기</a>' if salary_url else ""

        sections.append(f"""
<div style="margin-bottom:24px;padding:16px;border:1px solid #ddd;border-radius:8px;">
  <h3 style="margin:0 0 4px">{title}</h3>
  <p style="margin:0 0 8px;color:#555">{org} | 마감 {deadline}</p>
  {tracks_html}
  <p style="margin:8px 0 0">{link_html}{salary_html}</p>
</div>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><title>alio-letter</title></head>
<body style="font-family:sans-serif;max-width:640px;margin:auto;padding:16px">
  <h2>안녕하세요, {user_name}님!</h2>
  <p>오늘 새로 매칭된 공고입니다.</p>
  {body}
  <hr>
  <p style="font-size:12px;color:#aaa">alio-letter · 수신거부는 회원 페이지에서</p>
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
