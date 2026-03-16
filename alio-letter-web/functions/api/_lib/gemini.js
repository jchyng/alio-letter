/**
 * Gemini API 공통 유틸리티
 * register.js / profile/[token].js 양쪽에서 공유
 */

/**
 * 사용자 스펙 텍스트 → UserProfile JSON 파싱 프롬프트 생성
 * @param {string} specText
 * @returns {string}
 */
export function buildSpecPrompt(specText) {
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
  "military": "병역필 또는 면제 또는 미필 또는 해당없음(여성)",
  "disability_grade": "해당없음 또는 경증 또는 중증",
  "veteran_type": "해당없음 또는 해당 유형명",
  "is_low_income": false,
  "is_north_korean_defector": false,
  "is_independent_youth": false,
  "is_multicultural_child": false
}`;
}

/**
 * Gemini로 스펙 텍스트를 파싱하여 UserProfile 객체 반환.
 * 파싱 실패 시 null 반환 (호출부에서 기존 값 유지).
 * @param {string} apiKey
 * @param {string} specText
 * @returns {Promise<object|null>}
 */
export async function parseSpecWithGemini(apiKey, specText) {
  const geminiRes = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: buildSpecPrompt(specText) }] }],
        generationConfig: { responseMimeType: 'application/json' },
      }),
    }
  );
  const geminiData = await geminiRes.json();
  try {
    return JSON.parse(geminiData.candidates[0].content.parts[0].text);
  } catch (_) {
    return null;
  }
}
