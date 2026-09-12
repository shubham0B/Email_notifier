-- =====================================================================
-- JECRC PERSONAL WHATSAPP & DEAN'S DIGEST PORTAL
-- MYSQL 8.X DATABASE DDL SCHEMA
-- Target Database: personal_whatsapp_db
-- =====================================================================

CREATE DATABASE IF NOT EXISTS personal_whatsapp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE personal_whatsapp_db;

-- 1. Master Table for Daily Digests
CREATE TABLE IF NOT EXISTS digests (
    id VARCHAR(36) PRIMARY KEY,
    target_date VARCHAR(50) NOT NULL,
    mode VARCHAR(50) NOT NULL,
    total_emails INT DEFAULT 0,
    urgent_count INT DEFAULT 0,
    pdf_filename VARCHAR(255) NULL,
    pdf_path VARCHAR(500) NULL,
    status VARCHAR(50) DEFAULT 'GENERATED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Inbound Analyzed & Categorized Emails
CREATE TABLE IF NOT EXISTS digest_emails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    digest_id VARCHAR(36) NOT NULL,
    sender_name VARCHAR(255),
    sender_email VARCHAR(255),
    subject VARCHAR(500),
    category VARCHAR(100),
    urgency_level VARCHAR(50),
    summary TEXT,
    arrival_time VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (digest_id) REFERENCES digests(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. News Headlines & Executive Bulletins
CREATE TABLE IF NOT EXISTS digest_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    digest_id VARCHAR(36) NOT NULL,
    category VARCHAR(100),
    headline TEXT,
    source VARCHAR(255),
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (digest_id) REFERENCES digests(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. WhatsApp Dispatches Log
CREATE TABLE IF NOT EXISTS whatsapp_dispatches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    digest_id VARCHAR(36) NULL,
    recipient VARCHAR(50) NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message_id VARCHAR(100) NULL,
    error_message TEXT NULL,
    dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 5. Scheduler & System Config
CREATE TABLE IF NOT EXISTS scheduler_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO scheduler_config (config_key, config_value) VALUES
('morning_time', '09:00'),
('evening_time', '20:00'),
('recipient_number', '919876543210')
ON DUPLICATE KEY UPDATE config_key=config_key;
