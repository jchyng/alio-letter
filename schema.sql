-- 1. institutions (기관)
CREATE TABLE IF NOT EXISTS institutions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  alio_id VARCHAR(50) UNIQUE,
  category VARCHAR(100),
  headquarters VARCHAR(100),
  website_url VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. salary_info (급여정보)
CREATE TABLE IF NOT EXISTS salary_info (
  id INT AUTO_INCREMENT PRIMARY KEY,
  institution_id INT,
  fiscal_year INT,
  employment_type VARCHAR(50),
  base_salary INT,
  fixed_allowance INT,
  performance_allowance INT,
  bonus INT,
  avg_annual_salary INT,
  avg_salary_male INT,
  avg_salary_female INT,
  headcount DECIMAL(10,1),
  avg_tenure_months INT,
  source_url VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_salary (institution_id, fiscal_year, employment_type),
  FOREIGN KEY (institution_id) REFERENCES institutions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. job_postings (채용공고)
CREATE TABLE IF NOT EXISTS job_postings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  institution_id INT,
  posting_number VARCHAR(100),
  title VARCHAR(500),
  posted_date DATE,
  application_start DATE,
  application_end DATE,
  total_headcount INT,
  source_url VARCHAR(500),
  pdf_url VARCHAR(500),
  ai_summary TEXT,
  status VARCHAR(20) DEFAULT 'active',
  raw_extracted_data JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (institution_id) REFERENCES institutions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. recruitment_sections (채용구분 섹션)
CREATE TABLE IF NOT EXISTS recruitment_sections (
  id INT AUTO_INCREMENT PRIMARY KEY,
  posting_id INT,
  section_name VARCHAR(200),
  recruitment_type VARCHAR(50),
  education_level VARCHAR(50),
  grade VARCHAR(50),
  probation_months INT,
  work_locations JSON,
  work_type VARCHAR(50),
  section_order INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. recruitment_units (직무별 채용인원)
CREATE TABLE IF NOT EXISTS recruitment_units (
  id INT AUTO_INCREMENT PRIMARY KEY,
  section_id INT,
  posting_id INT,
  job_field VARCHAR(100) NOT NULL,
  headcount INT NOT NULL,
  note TEXT,
  FOREIGN KEY (section_id) REFERENCES recruitment_sections(id),
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. qualification_requirements (지원자격)
CREATE TABLE IF NOT EXISTS qualification_requirements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  section_id INT,
  age_limit VARCHAR(100),
  education_req VARCHAR(100),
  certificate_req TEXT,
  language_req TEXT,
  military_req VARCHAR(200),
  disability_req VARCHAR(200),
  veteran_req VARCHAR(200),
  other_req TEXT,
  preferred_certs TEXT,
  FOREIGN KEY (section_id) REFERENCES recruitment_sections(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. selection_stages (전형 단계)
CREATE TABLE IF NOT EXISTS selection_stages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  section_id INT,
  stage_number INT,
  stage_name VARCHAR(100),
  details TEXT,
  pass_ratio VARCHAR(50),
  max_score INT,
  sub_items JSON,
  FOREIGN KEY (section_id) REFERENCES recruitment_sections(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. bonus_points (가점 항목)
CREATE TABLE IF NOT EXISTS bonus_points (
  id INT AUTO_INCREMENT PRIMARY KEY,
  posting_id INT,
  bonus_type VARCHAR(100),
  description TEXT,
  document_effect VARCHAR(100),
  written_effect VARCHAR(100),
  interview_effect VARCHAR(100),
  max_cumulative_pct INT,
  required_docs TEXT,
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. recruitment_targets (채용목표제)
CREATE TABLE IF NOT EXISTS recruitment_targets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  posting_id INT,
  target_type VARCHAR(100),
  description TEXT,
  target_rate_pct INT,
  applicable_fields TEXT,
  conditions TEXT,
  FOREIGN KEY (posting_id) REFERENCES job_postings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. users (사용자)
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(200) UNIQUE NOT NULL,
  name VARCHAR(100),
  is_active TINYINT DEFAULT 0,
  education_level VARCHAR(50),
  military_status VARCHAR(20),
  is_disabled TINYINT DEFAULT 0,
  is_veteran_family TINYINT DEFAULT 0,
  is_low_income TINYINT DEFAULT 0,
  is_north_defector TINYINT DEFAULT 0,
  is_multicultural TINYINT DEFAULT 0,
  is_self_reliance TINYINT DEFAULT 0,
  residence_region VARCHAR(20),
  toeic_score INT,
  toeic_speaking_level VARCHAR(10),
  opic_level VARCHAR(10),
  certificates JSON,
  preferred_fields JSON,
  preferred_regions JSON,
  preferred_types JSON,
  preferred_institutions JSON,
  synced_at DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;