-- Database Schema for MyMediFile (MySQL)
-- Run this script to initialize the MySQL tables manually.

CREATE DATABASE IF NOT EXISTS mymedifile;
USE mymedifile;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone_number VARCHAR(20) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Family Members Table
CREATE TABLE IF NOT EXISTS family_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50) NOT NULL,
    age INT NOT NULL,
    blood_group VARCHAR(10) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Health Profiles Table
CREATE TABLE IF NOT EXISTS health_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    family_member_id INT NULL,
    blood_group VARCHAR(10) NOT NULL,
    height FLOAT NOT NULL,
    weight FLOAT NOT NULL,
    allergies TEXT NULL,
    chronic_diseases TEXT NULL,
    current_medications TEXT NULL,
    emergency_contact_name VARCHAR(100) NULL,
    emergency_contact_phone VARCHAR(20) NULL,
    family_doctor_name VARCHAR(100) NULL,
    family_doctor_phone VARCHAR(20) NULL,
    insurance_provider VARCHAR(100) NULL,
    insurance_policy_number VARCHAR(50) NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Medical Records Table
CREATE TABLE IF NOT EXISTS medical_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    family_member_id INT NULL,
    title VARCHAR(150) NOT NULL,
    doctor_name VARCHAR(100) NULL,
    hospital_name VARCHAR(100) NULL,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    file_path VARCHAR(256) NOT NULL,
    description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    family_member_id INT NULL,
    doctor_name VARCHAR(100) NOT NULL,
    hospital_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    purpose VARCHAR(200) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Menstrual Cycles Table
CREATE TABLE IF NOT EXISTS menstrual_cycles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    last_period_date DATE NOT NULL,
    average_cycle_length INT NOT NULL DEFAULT 28,
    period_duration INT NOT NULL DEFAULT 5,
    cramps BOOLEAN DEFAULT FALSE,
    headache BOOLEAN DEFAULT FALSE,
    mood_swings BOOLEAN DEFAULT FALSE,
    fatigue BOOLEAN DEFAULT FALSE,
    back_pain BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Vaccinations Table
CREATE TABLE IF NOT EXISTS vaccinations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    family_member_id INT NULL,
    vaccine_name VARCHAR(100) NOT NULL,
    date_taken DATE NOT NULL,
    next_due_date DATE NULL,
    hospital_clinic_name VARCHAR(100) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Health Metrics Table
CREATE TABLE IF NOT EXISTS health_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    family_member_id INT NULL,
    systolic INT NULL,
    diastolic INT NULL,
    blood_sugar FLOAT NULL,
    heart_rate INT NULL,
    oxygen_level INT NULL,
    body_temperature FLOAT NULL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
