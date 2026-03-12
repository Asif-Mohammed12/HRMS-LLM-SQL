"""
src/core/schema.py
Single source of truth for the HRMS database schema.
Used by the prompt builder and the /schema API endpoint.
"""
from dataclasses import dataclass, field

HRMS_SCHEMA_SQL = """
-- HRMS Database Schema (PostgreSQL)

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
    department_id     INT          REFERENCES departments(department_id),
    job_title         VARCHAR(100),
    salary            NUMERIC(12,2),
    manager_id        INT          REFERENCES employees(employee_id),
    employment_status VARCHAR(20)  DEFAULT 'active'  -- active | inactive | terminated
);

CREATE TABLE attendance (
    attendance_id SERIAL PRIMARY KEY,
    employee_id   INT  NOT NULL REFERENCES employees(employee_id),
    date          DATE NOT NULL,
    check_in      TIME,
    check_out     TIME,
    work_hours    NUMERIC(5,2)
);

CREATE TABLE leave_requests (
    leave_id     SERIAL PRIMARY KEY,
    employee_id  INT          NOT NULL REFERENCES employees(employee_id),
    leave_type   VARCHAR(50),                        -- annual | sick | maternity | unpaid
    start_date   DATE         NOT NULL,
    end_date     DATE         NOT NULL,
    leave_status VARCHAR(20)  DEFAULT 'pending'      -- pending | approved | rejected
);

CREATE TABLE payroll (
    payroll_id   SERIAL PRIMARY KEY,
    employee_id  INT          NOT NULL REFERENCES employees(employee_id),
    pay_month    DATE         NOT NULL,              -- first day of the month
    base_salary  NUMERIC(12,2),
    bonus        NUMERIC(12,2) DEFAULT 0,
    deductions   NUMERIC(12,2) DEFAULT 0,
    net_salary   NUMERIC(12,2) GENERATED ALWAYS AS (base_salary + bonus - deductions) STORED
);
"""

# Lightweight dict representation returned by /schema
SCHEMA_DICT = {
    "tables": [
        {
            "name": "employees",
            "description": "Core employee records",
            "columns": [
                {"name": "employee_id",       "type": "integer", "pk": True},
                {"name": "first_name",        "type": "varchar"},
                {"name": "last_name",         "type": "varchar"},
                {"name": "email",             "type": "varchar"},
                {"name": "phone",             "type": "varchar"},
                {"name": "hire_date",         "type": "date"},
                {"name": "department_id",     "type": "integer", "fk": "departments.department_id"},
                {"name": "job_title",         "type": "varchar"},
                {"name": "salary",            "type": "numeric"},
                {"name": "manager_id",        "type": "integer", "fk": "employees.employee_id"},
                {"name": "employment_status", "type": "varchar"},
            ],
        },
        {
            "name": "departments",
            "description": "Business departments",
            "columns": [
                {"name": "department_id",   "type": "integer", "pk": True},
                {"name": "department_name", "type": "varchar"},
                {"name": "location",        "type": "varchar"},
            ],
        },
        {
            "name": "attendance",
            "description": "Daily check-in / check-out records",
            "columns": [
                {"name": "attendance_id", "type": "integer", "pk": True},
                {"name": "employee_id",   "type": "integer", "fk": "employees.employee_id"},
                {"name": "date",          "type": "date"},
                {"name": "check_in",      "type": "time"},
                {"name": "check_out",     "type": "time"},
                {"name": "work_hours",    "type": "numeric"},
            ],
        },
        {
            "name": "leave_requests",
            "description": "Employee leave requests",
            "columns": [
                {"name": "leave_id",     "type": "integer", "pk": True},
                {"name": "employee_id",  "type": "integer", "fk": "employees.employee_id"},
                {"name": "leave_type",   "type": "varchar"},
                {"name": "start_date",   "type": "date"},
                {"name": "end_date",     "type": "date"},
                {"name": "leave_status", "type": "varchar"},
            ],
        },
        {
            "name": "payroll",
            "description": "Monthly payroll entries",
            "columns": [
                {"name": "payroll_id",  "type": "integer", "pk": True},
                {"name": "employee_id", "type": "integer", "fk": "employees.employee_id"},
                {"name": "pay_month",   "type": "date"},
                {"name": "base_salary", "type": "numeric"},
                {"name": "bonus",       "type": "numeric"},
                {"name": "deductions",  "type": "numeric"},
                {"name": "net_salary",  "type": "numeric"},
            ],
        },
    ]
}
