"""
scripts/seed_db.py
Create the HRMS schema and populate it with sample data in PostgreSQL.
Run: python -m scripts.seed_db
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from src.core.config import get_settings


DDL = """
-- Drop in reverse FK order
DROP TABLE IF EXISTS payroll CASCADE;
DROP TABLE IF EXISTS leave_requests CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS departments CASCADE;

CREATE TABLE departments (
    department_id   SERIAL PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    location        VARCHAR(150)
);

CREATE TABLE employees (
    employee_id       SERIAL PRIMARY KEY,
    first_name        VARCHAR(50)  NOT NULL,
    last_name         VARCHAR(50)  NOT NULL,
    email             VARCHAR(150) UNIQUE NOT NULL,
    phone             VARCHAR(20),
    hire_date         DATE         NOT NULL,
    department_id     INT REFERENCES departments(department_id),
    job_title         VARCHAR(100),
    salary            NUMERIC(12,2),
    manager_id        INT REFERENCES employees(employee_id),
    employment_status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE attendance (
    attendance_id SERIAL PRIMARY KEY,
    employee_id   INT NOT NULL REFERENCES employees(employee_id),
    date          DATE NOT NULL,
    check_in      TIME,
    check_out     TIME,
    work_hours    NUMERIC(5,2)
);

CREATE TABLE leave_requests (
    leave_id     SERIAL PRIMARY KEY,
    employee_id  INT NOT NULL REFERENCES employees(employee_id),
    leave_type   VARCHAR(50),
    start_date   DATE NOT NULL,
    end_date     DATE NOT NULL,
    leave_status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE payroll (
    payroll_id  SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(employee_id),
    pay_month   DATE NOT NULL,
    base_salary NUMERIC(12,2),
    bonus       NUMERIC(12,2) DEFAULT 0,
    deductions  NUMERIC(12,2) DEFAULT 0,
    net_salary  NUMERIC(12,2)
);
"""

SEED = """
INSERT INTO departments (department_name, location) VALUES
    ('Engineering',  'Floor 3'),
    ('Human Resources', 'Floor 2'),
    ('Finance',      'Floor 1'),
    ('Sales',        'Floor 4'),
    ('Operations',   'Floor 5');

INSERT INTO employees (first_name, last_name, email, phone, hire_date, department_id, job_title, salary, employment_status) VALUES
    ('Alice',   'Smith',   'alice@hrms.com',   '555-0101', '2024-01-15', 1, 'Software Engineer',   85000, 'active'),
    ('Bob',     'Jones',   'bob@hrms.com',     '555-0102', '2023-05-01', 1, 'Senior Engineer',    110000, 'active'),
    ('Carol',   'White',   'carol@hrms.com',   '555-0103', '2022-03-10', 2, 'HR Manager',          72000, 'active'),
    ('David',   'Brown',   'david@hrms.com',   '555-0104', '2021-08-20', 3, 'Finance Analyst',     68000, 'active'),
    ('Eva',     'Davis',   'eva@hrms.com',     '555-0105', '2024-03-01', 4, 'Sales Executive',     60000, 'active'),
    ('Frank',   'Miller',  'frank@hrms.com',   '555-0106', '2020-11-15', 5, 'Operations Lead',     90000, 'active'),
    ('Grace',   'Wilson',  'grace@hrms.com',   '555-0107', '2019-06-01', 1, 'Engineering Manager',130000, 'active'),
    ('Henry',   'Moore',   'henry@hrms.com',   '555-0108', '2023-09-10', 2, 'HR Specialist',       58000, 'inactive');

-- Attendance (last 7 days for Alice and Bob)
INSERT INTO attendance (employee_id, date, check_in, check_out, work_hours) VALUES
    (1, CURRENT_DATE - 1, '09:00', '17:30', 8.5),
    (1, CURRENT_DATE - 2, '08:45', '17:00', 8.25),
    (2, CURRENT_DATE - 1, '09:15', '18:00', 8.75),
    (2, CURRENT_DATE - 2, '09:00', '17:30', 8.5);

-- Leave requests
INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, leave_status) VALUES
    (3, 'annual',   '2025-12-24', '2025-12-31', 'approved'),
    (5, 'sick',     CURRENT_DATE, CURRENT_DATE + 2, 'pending'),
    (8, 'maternity','2025-10-01', '2026-01-01', 'approved');

-- Payroll (last 2 months)
INSERT INTO payroll (employee_id, pay_month, base_salary, bonus, deductions, net_salary) VALUES
    (1, DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month'), 85000/12,  500,  200, 85000/12 +  500 -  200),
    (2, DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month'), 110000/12,1000,  400, 110000/12+1000 -  400),
    (3, DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month'), 72000/12,    0,  150, 72000/12        -  150),
    (1, DATE_TRUNC('month', CURRENT_DATE),                       85000/12,  750,  200, 85000/12 +  750 -  200),
    (2, DATE_TRUNC('month', CURRENT_DATE),                       110000/12,1500,  400, 110000/12+1500 -  400);
"""


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    print(f"Connecting to {settings.postgres_host}/{settings.postgres_db} ...")
    with engine.connect() as conn:
        print("Creating schema ...")
        conn.execute(text(DDL))
        print("Seeding data ...")
        conn.execute(text(SEED))
        conn.commit()
    print("✅  Database seeded successfully.")


if __name__ == "__main__":
    main()
