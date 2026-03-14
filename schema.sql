-- =============================================================
-- Alio Letter — DB Schema
-- =============================================================
-- 단계별 적용:
--   Phase 1 (크롤링):         postings
--   Phase 2 (Gemini 파싱):    posting_tracks
--   Phase 3 (매칭·분석):      users, user_preferences, user_specs,
--                              user_certificates, user_posting_analyses
-- =============================================================


-- ─────────────────────────────────────────
-- Phase 1: 크롤링
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS postings (
  posting_id        INT           AUTO_INCREMENT PRIMARY KEY,
  alio_id           VARCHAR(20)   NOT NULL UNIQUE,
  title             VARCHAR(200)  NOT NULL,
  org_name          VARCHAR(100)  NOT NULL,
  org_type          VARCHAR(50)   NULL,     -- 잡알리오 페이지에서 직접 노출 안 됨, 추후 보완
  regions           JSON          NOT NULL,
  job_fields        JSON          NOT NULL,
  employment_types  JSON          NOT NULL,
  recruit_types     JSON          NOT NULL,
  education_levels  JSON          NOT NULL,
  positions_summary JSON,
  total_positions   INT,
  posting_url       VARCHAR(500)  NOT NULL,
  file_urls         JSON,
  posted_date       DATE          NOT NULL,
  deadline          DATETIME      NOT NULL,
  schedule          JSON,
  parse_status      ENUM('pending','done','partial','failed','no_file') NOT NULL DEFAULT 'pending',
  status            ENUM('진행중','마감') NOT NULL DEFAULT '진행중',
  created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─────────────────────────────────────────
-- Phase 2: Gemini PDF 파싱
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS posting_tracks (
  track_id                  INT         AUTO_INCREMENT PRIMARY KEY,
  posting_id                INT         NOT NULL,
  track_name                VARCHAR(50) NOT NULL,
  grade                     VARCHAR(30),
  positions                 JSON        NOT NULL,
  total_positions           INT         NOT NULL,
  work_locations            JSON,
  work_type                 VARCHAR(50),
  eligibility               JSON        NOT NULL,
  selection_process         JSON        NOT NULL,
  scoring_criteria          JSON,
  bonus_points              JSON,
  certificate_bonus_table   JSON,
  language_conversion_table JSON,
  quota_policies            JSON,
  bonus_points_rule         VARCHAR(500),
  FOREIGN KEY (posting_id) REFERENCES postings(posting_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ─────────────────────────────────────────
-- Phase 3: 사용자 · 매칭 · 분석
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
  user_id                 INT          AUTO_INCREMENT PRIMARY KEY,
  name                    VARCHAR(50)  NOT NULL,
  email                   VARCHAR(100) NOT NULL UNIQUE,
  edit_token              VARCHAR(36)  UNIQUE,
  raw_spec_text           TEXT,
  raw_pref_text           TEXT,
  notification_enabled    TINYINT(1)   NOT NULL DEFAULT 1,
  is_active               TINYINT(1)   NOT NULL DEFAULT 1,
  subscription_status     ENUM('free','paid','expired') NOT NULL DEFAULT 'free',
  subscription_expires_at DATE,
  created_at              DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at              DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id               INT PRIMARY KEY,
  pref_regions          JSON,
  pref_job_fields       JSON,
  pref_employment_types JSON,
  pref_recruit_types    JSON,
  pref_education_levels JSON,
  pref_org_types        JSON,
  pref_org_names        JSON,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_specs (
  user_id                  INT         PRIMARY KEY,
  birth_date               DATE        NOT NULL,
  gender                   ENUM('남','여') NOT NULL,
  education_level          VARCHAR(30) NOT NULL,
  education_status         VARCHAR(20) NOT NULL,
  major_category           VARCHAR(30),
  school_name              VARCHAR(100),
  school_region            VARCHAR(30),
  military_status          VARCHAR(20) NOT NULL,
  military_discharge_date  DATE,
  is_disabled              TINYINT(1)  NOT NULL DEFAULT 0,
  disability_type          VARCHAR(100),
  is_veteran               TINYINT(1)  NOT NULL DEFAULT 0,
  veteran_type             VARCHAR(100),
  residence_region         VARCHAR(30),
  residence_detail         VARCHAR(200),
  toeic_score              INT,
  toeic_expiry             DATE,
  toeic_speaking_score     INT,
  toeic_speaking_expiry    DATE,
  opic_grade               VARCHAR(10),
  opic_expiry              DATE,
  is_low_income            TINYINT(1)  NOT NULL DEFAULT 0,
  is_north_korean_defector TINYINT(1)  NOT NULL DEFAULT 0,
  is_multicultural_family  TINYINT(1)  NOT NULL DEFAULT 0,
  is_independent_youth     TINYINT(1)  NOT NULL DEFAULT 0,
  is_career_break_woman    TINYINT(1)  NOT NULL DEFAULT 0,
  is_part_time_worker      TINYINT(1)  NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_certificates (
  cert_id    INT          AUTO_INCREMENT PRIMARY KEY,
  user_id    INT          NOT NULL,
  cert_name  VARCHAR(100) NOT NULL,
  issue_date DATE         NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_posting_analyses (
  analysis_id              INT  AUTO_INCREMENT PRIMARY KEY,
  user_id                  INT  NOT NULL,
  posting_id               INT  NOT NULL,
  track_id                 INT  NOT NULL,
  is_eligible              TINYINT(1)    NOT NULL,
  ineligible_reasons       JSON,
  language_score           DECIMAL(5,2),
  certificate_score        DECIMAL(5,2),
  total_document_score     DECIMAL(5,2),
  certificate_score_detail JSON,
  applicable_bonus_points  JSON,
  unchecked_bonus_points   JSON,
  quota_policy_matches     JSON,
  analyzed_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  email_sent_at            DATETIME,
  FOREIGN KEY (user_id)    REFERENCES users(user_id),
  FOREIGN KEY (posting_id) REFERENCES postings(posting_id),
  FOREIGN KEY (track_id)   REFERENCES posting_tracks(track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
