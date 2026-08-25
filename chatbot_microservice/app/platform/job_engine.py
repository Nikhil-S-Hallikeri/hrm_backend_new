from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote
import requests

_CACHE: dict[str, Any] = {"timestamp": 0, "jobs": []}
_DEP_CACHE: dict[str, Any] = {"timestamp": 0, "departments": []}
CACHE_TTL_SECONDS = 60


def fetch_active_departments() -> list[str]:
    """Fetches active departments from HR backend API sorted by ID descending."""
    now = time.time()
    if _DEP_CACHE["departments"] and (now - _DEP_CACHE["timestamp"]) < CACHE_TTL_SECONDS:
        return _DEP_CACHE["departments"]

    target_url = "https://hrmbackendapi.meridahr.com/root/ems/Departments/"
    try:
        response = requests.get(target_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                sorted_deps = sorted(data, key=lambda x: int(x.get("id", 0)), reverse=True)
                dep_names = [d["Dep_Name"] for d in sorted_deps if d.get("Dep_Name")]
                _DEP_CACHE["departments"] = dep_names
                _DEP_CACHE["timestamp"] = now
                return dep_names
    except Exception as err:
        print(f"[JobEngine] Error fetching departments: {err}")

    return _DEP_CACHE.get("departments", [])


def is_internal_company(company_intro: str | None, brand_keyword: str | None = None) -> bool:
    """Checks if the company belongs to the primary internal brand group (case-insensitive substring match)."""
    if not company_intro:
        return False
    c_lower = company_intro.lower()
    if brand_keyword and len(brand_keyword.strip()) > 2:
        bk_lower = brand_keyword.lower().strip()
        if bk_lower in c_lower or c_lower in bk_lower:
            return True
    return any(k in c_lower for k in ("merida", "internal", "company", "inc", "ltd", "corp"))


# Backward compatibility alias
is_merida_company = is_internal_company


def fetch_active_jobs(catalog_api_url: str | None = None) -> list[dict[str, Any]]:
    """Fetches active job openings / catalog items with in-memory caching."""
    now = time.time()
    if _CACHE["jobs"] and (now - _CACHE["timestamp"]) < CACHE_TTL_SECONDS:
        return _CACHE["jobs"]

    target_url = catalog_api_url or os.getenv("CATALOG_API_URL", "https://hrmbackendapi.meridahr.com/api/job_description/?active_only=true")

    try:
        response = requests.get(target_url, timeout=8)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                _CACHE["jobs"] = data
                _CACHE["timestamp"] = now
                return data
    except Exception as err:
        print(f"[JobEngine] Error fetching catalog items: {err}")

    return _CACHE.get("jobs", [])


def filter_jobs(
    jobs: list[dict[str, Any]],
    hiring_type: str | None = None,
    department: str | None = None,
    query: str | None = None,
    custom_domain_keywords: dict[str, list[str]] | None = None,
    brand_keyword: str | None = None,
) -> list[dict[str, Any]]:
    """Filters catalog items by category / hiring type, department, and query."""
    filtered = jobs

    if hiring_type:
        h_lower = hiring_type.lower()
        internal_keyword = (brand_keyword or "internal").lower()
        if internal_keyword in h_lower or "internal" in h_lower or "direct" in h_lower:
            filtered = [j for j in filtered if is_internal_company(j.get("company_inrto") or j.get("company"), brand_keyword)]
        elif "external" in h_lower or "partner" in h_lower or "consultancy" in h_lower:
            filtered = [j for j in filtered if not is_internal_company(j.get("company_inrto") or j.get("company"), brand_keyword)]

    if department:
        d_lower = department.lower()
        filtered = [j for j in filtered if (j.get("department_name") or j.get("department") or "").lower() == d_lower]

    if query:
        q_lower = query.lower().strip()

        # Dynamic or fallback taxonomy groupings
        keywords: tuple[str, ...] = (q_lower,)
        domain_dict = custom_domain_keywords or {
            "business development": ["bde", "business development", "biz dev", "sales"],
            "digital marketing": ["digital marketing", "marketing", "seo", "social media", "content"],
            "network engineer": ["network engineer", "network", "sysadmin", "system engineer"],
            "software": ["sde", "software", "developer", "software engineer", "fullstack", "backend", "frontend", "coding"],
            "ai": ["ai", "ml", "artificial intelligence", "data science", "machine learning"],
            "design": ["graphic", "designer", "design", "ui", "ux", "animator"],
            "healthcare": ["nurse", "nursing", "medical", "healthcare"],
            "hr": ["hr", "recruiter", "talent", "hiring manager", "human resource"],
            "management": ["manager", "management"],
        }

        for d_name, kw_list in domain_dict.items():
            if any(k in q_lower for k in kw_list):
                keywords = tuple(kw_list)
                break

        exact_matches = []
        keyword_matches = []

        for j in filtered:
            title = (j.get("Title") or j.get("title") or j.get("designation_name") or "").lower()
            dept = (j.get("department_name") or j.get("department") or "").lower()

            if q_lower in title or q_lower in dept:
                exact_matches.append(j)
            elif any(k in title or k in dept for k in keywords):
                keyword_matches.append(j)

        if exact_matches:
            return exact_matches
        if keyword_matches:
            return keyword_matches
        return []

    return filtered


def build_candidate_registration_url(job_title: str, job_id: int | str, template: str | None = None) -> str:
    """Generates the candidate application URL dynamically using tenant template or fallback."""
    encoded_title = quote(str(job_title or "Position"))
    if template and "{title}" in template:
        return template.format(title=encoded_title, id=job_id)
    return f"https://hrm.meridahr.com/Canditate_Registration_Form?source=meridahr&desig={encoded_title}&jobpk={job_id}"


def format_job_card(job: dict[str, Any], url_template: str | None = None, brand_keyword: str | None = None) -> dict[str, Any]:
    """Formats raw catalog item into canonical job card payload."""
    min_sal = job.get("min_salary") or ""
    max_sal = job.get("max_salary") or ""
    sal_type = job.get("salary_type") or "K"
    salary_range = f"₹{min_sal} - ₹{max_sal} {sal_type}" if min_sal and max_sal else "Best in Industry"

    job_id = job.get("id") or 1
    title = job.get("Title") or job.get("title") or job.get("designation_name") or "Position"
    apply_url = job.get("apply_url") or build_candidate_registration_url(title, job_id, template=url_template)

    return {
        "id": job_id,
        "title": title,
        "department": job.get("department_name") or job.get("department") or "General",
        "company": job.get("company_inrto") or job.get("company") or "Company",
        "location": job.get("job_location") or job.get("location") or "Flexible",
        "job_type": job.get("job_type") or "Full Time",
        "experience": f"{job.get('min_exp', '0')}+ Years" if job.get('min_exp') else job.get('Experience', 'Fresher'),
        "salary": salary_range,
        "description": job.get("Job_Discription") or job.get("description") or "",
        "slug": job.get("slug") or "",
        "is_merida": is_internal_company(job.get("company_inrto") or job.get("company"), brand_keyword),
        "apply_url": apply_url,
    }


def group_jobs_by_department(jobs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Groups formatted job cards by department."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for j in jobs:
        card = format_job_card(j)
        dept = card["department"]
        grouped.setdefault(dept, []).append(card)
    return grouped
    return grouped
