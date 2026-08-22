import re
import os
import datetime
from io import BytesIO

# Standard Job Roles
TECH_ROLES = [
    "Python Full Stack Developer",
    "Full Stack Developer",
    "Fullstack Engineer",
    "Python Developer",
    "Django Developer",
    "Flutter Developer",
    "Frontend Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Backend Engineer",
    "Software Engineer",
    "Software Developer",
    "Digital Marketing Specialist",
    "Performance Marketing Executive",
    "Digital Marketing Executive",
    "Digital Marketing Intern",
    "Marketing Specialist",
    "Marketing Manager",
    "SEO Specialist",
    "Content Strategist",
    "UI/UX Designer",
    "UX/UI Designer",
    "Product Designer",
    "Data Analyst",
    "Data Scientist",
    "DevOps Engineer",
    "Mobile Developer",
    "iOS Developer",
    "Android Developer",
    "React Developer",
    "Java Developer",
    "Cloud Engineer",
    "Machine Learning Engineer",
    "QA Engineer",
    "Product Manager",
    "Project Manager",
    "Business Analyst",
]

ROLE_KEYWORDS = [
    "developer", "engineer", "specialist", "designer", "analyst",
    "executive", "manager", "architect", "consultant", "strategist",
    "lead", "coordinator", "intern", "officer", "administrator",
    "programmer", "director", "associate"
]

SKILL_NOISE_WORDS = [
    "python", "java", "javascript", "typescript", "flutter", "react",
    "angular", "vue", "django", "flask", "node", "express", "html",
    "css", "sql", "mysql", "postgresql", "mongodb", "aws", "cloud",
    "azure", "docker", "kubernetes", "git", "fullstack", "full",
    "stack", "frontend", "backend", "devops", "mobile", "android",
    "ios", "ui/ux", "ux/ui", "data", "machine", "learning", "ai",
    "software", "web", "testing", "qa", "agile", "scrum"
]

HEADER_NOISE_WORDS = [
    "resume", "curriculum", "vitae", "cv", "page", "contact",
    "email", "phone", "mobile", "address", "linkedin", "github",
    "profile", "summary", "objective", "experience", "education",
    "skills", "projects", "certifications", "http", "https", "www",
    "tools", "results", "declaration", "hobbies", "languages",
    "location", "about", "personal", "details", "portfolio"
]

DEGREE_NOISE_PATTERNS = r',?\s*(?:B\.E\.?\s*(?:CS&E|CSE|ECE|EEE|IT)?|B\.Tech|M\.Tech|B\.S\.|M\.S\.|B\.Sc|M\.Sc|BCA|MCA|MBA|BBA|Ph\.D|Diploma).*$'

def extract_text_from_pdf(pdf_source):
    """
    Extract raw text from PDF source safely converting to raw_bytes first.
    Tries pdfplumber (with layout mode), pypdf, and PyPDF2 in order with fresh BytesIO streams.
    """
    if isinstance(pdf_source, str) and not os.path.exists(pdf_source):
        return pdf_source

    raw_bytes = b""
    try:
        if hasattr(pdf_source, 'read'):
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
            raw_bytes = pdf_source.read()
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
        elif isinstance(pdf_source, bytes):
            raw_bytes = pdf_source
        elif isinstance(pdf_source, str) and os.path.exists(pdf_source):
            with open(pdf_source, 'rb') as f:
                raw_bytes = f.read()
    except Exception as e:
        print(f"Error extracting bytes from pdf_source: {e}")

    if not raw_bytes:
        return ""

    # Attempt 1: pdfplumber (best for layout and multi-column PDFs)
    try:
        import pdfplumber
        with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                t = page.extract_text(layout=True) or page.extract_text()
                if t:
                    text += t + "\n"
            if text.strip():
                return text
    except Exception as e:
        print(f"pdfplumber extraction error: {e}")

    # Attempt 2: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(raw_bytes))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"pypdf extraction error: {e}")

    # Attempt 3: PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(BytesIO(raw_bytes))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"PyPDF2 extraction error: {e}")

    return ""

def parse_email(text):
    """Extract email address using standard regex pattern."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0).strip() if match else ""

def parse_phone(text):
    """Extract phone number matching country code, hyphenated, or 10-digit formats and format into +91 XXXXX XXXXX."""
    phone_patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # +91 9037971873 or 789-208-4765
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',                         # (123) 456-7890
        r'\b\d{10}\b',                                                    # 7676083350
    ]
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            digits_only = re.sub(r'\D', '', m)
            if 10 <= len(digits_only) <= 13:
                last10 = digits_only[-10:]
                return f"+91 {last10[:5]} {last10[5:]}"
    return ""

def parse_date(text):
    """Extract submission date or date from resume text, fallback to current date."""
    m1 = re.search(r'\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b', text)
    if m1:
        try:
            return datetime.date(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
        except ValueError:
            pass

    m2 = re.search(r'\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/](20\d{2})\b', text)
    if m2:
        try:
            return datetime.date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
        except ValueError:
            pass

    month_names = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    m3 = re.search(rf'\b({month_names})\s+([0-2]?\d|3[01]),?\s+(20\d{{2}})\b', text, re.IGNORECASE)
    if m3:
        try:
            date_str = f"{m3.group(1)} {m3.group(2)} {m3.group(3)}"
            for fmt in ("%B %d %Y", "%b %d %Y"):
                try:
                    return datetime.datetime.strptime(date_str, fmt).date()
                except ValueError:
                    pass
        except Exception:
            pass

    return datetime.date.today()

def clean_candidate_name_line(line):
    """Strip degree suffixes (e.g. ', B.E CS&E') and clean line for candidate name evaluation."""
    line_clean = re.sub(DEGREE_NOISE_PATTERNS, '', line, flags=re.IGNORECASE).strip()
    # Strip any trailing punctuation
    line_clean = re.sub(r'[,\|\-\–\•]+$', '', line_clean).strip()
    # Collapse multiple spaces (e.g. "KASTHURI   K" -> "KASTHURI K")
    line_clean = re.sub(r'\s+', ' ', line_clean).strip()
    return line_clean

def format_clean_name(name):
    """Normalize whitespace and format candidate name into clean Title Case."""
    if not name:
        return "Candidate Name"
    name = re.sub(r'\s+', ' ', name).strip()
    words = name.split(' ')
    clean_words = []
    for w in words:
        if len(w) == 1:
            clean_words.append(w.upper())
        elif w.isupper():
            clean_words.append(w.capitalize())
        else:
            clean_words.append(w)
    return ' '.join(clean_words)

def is_valid_name_line(line):
    """Check if a text line qualifies as a Candidate Name."""
    line_clean = clean_candidate_name_line(line)
    if not line_clean or len(line_clean) < 2 or len(line_clean) > 50:
        return False

    lower = line_clean.lower()

    if any(w in lower for w in HEADER_NOISE_WORDS):
        return False
    if any(w in lower for w in ROLE_KEYWORDS):
        return False
    if any(w in lower for w in SKILL_NOISE_WORDS):
        return False

    if '@' in line_clean or 'http' in lower or any(c.isdigit() for c in line_clean):
        return False

    words = line_clean.split()
    if 1 <= len(words) <= 4:
        if all(w.isupper() or w[0].isupper() for w in words if w.isalpha()):
            return True

    return False

def parse_name(text, file_name=None):
    """
    Extract candidate name using PDF Filename Matching, Email Prefix Matching,
    degree stripping, and layout proximity heuristics.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return "Candidate Name"

    # 0. PDF FILENAME MATCHING ALGORITHM (e.g., "ResumeKIRANB.pdf" -> "KIRANB" -> "KIRAN B")
    if file_name:
        clean_file_base = os.path.splitext(os.path.basename(file_name))[0]
        # Remove common noise words from filename (e.g. resume, cv, bio, pdf)
        clean_file = re.sub(r'\b(resume|cv|bio|data|profile|document|file)\b', '', clean_file_base, flags=re.IGNORECASE).strip()
        file_letters = re.sub(r'[^a-zA-Z]', '', clean_file).lower() # "kiranb"

        if len(file_letters) >= 3:
            for line in lines[:15]:
                if '@' in line or 'http' in line.lower() or 'github' in line.lower():
                    continue

                cleaned_name = clean_candidate_name_line(line)
                if not cleaned_name:
                    continue

                lower_cand = cleaned_name.lower()
                if any(w in lower_cand for w in HEADER_NOISE_WORDS) or any(w in lower_cand for w in ROLE_KEYWORDS):
                    continue

                if not is_valid_name_line(cleaned_name):
                    continue

                line_letters = re.sub(r'[^a-zA-Z]', '', lower_cand).lower() # "kiranb"
                if not line_letters:
                    continue

                # Exact letter match (e.g. "kiranb" == "kiranb" for line "KIRAN B")
                if file_letters == line_letters or line_letters == file_letters:
                    return cleaned_name

                # Substring match (e.g. "kiranb" in "kiranbag" or vice versa)
                if file_letters in line_letters or line_letters in file_letters:
                    return cleaned_name

    email = parse_email(text)

    # 1. EMAIL PREFIX MATCHING ALGORITHM (e.g., "durgaprasadag@gmail.com" -> "durgaprasadag")
    if email:
        email_prefix = email.split('@')[0].lower()
        clean_prefix = re.sub(r'[^a-zA-Z]', '', email_prefix) # "durgaprasadag"

        if len(clean_prefix) >= 3:
            best_match = None
            best_score = 0.0

            for line in lines[:15]:
                if email in line or '@' in line or 'http' in line.lower() or 'github' in line.lower():
                    continue

                cleaned_name = clean_candidate_name_line(line)
                if not cleaned_name:
                    continue

                lower_cand = cleaned_name.lower()
                if any(w in lower_cand for w in HEADER_NOISE_WORDS) or any(w in lower_cand for w in ROLE_KEYWORDS):
                    continue

                if not is_valid_name_line(cleaned_name):
                    continue

                line_letters = re.sub(r'[^a-zA-Z]', '', lower_cand) # "durgaprasadag"
                if not line_letters:
                    continue

                if clean_prefix == line_letters or line_letters == clean_prefix:
                    return cleaned_name

                if clean_prefix in line_letters or line_letters in clean_prefix:
                    return cleaned_name

                common_chars = sum(1 for c in set(clean_prefix) if c in set(line_letters))
                score = common_chars / max(len(set(clean_prefix)), 1)
                if score > best_score and score >= 0.7:
                    best_score = score
                    best_match = cleaned_name

            if best_match:
                return best_match

    # 2. Contact Proximity Check
    phone = parse_phone(text)
    contact_index = -1
    for i, line in enumerate(lines):
        if (email and email in line) or (phone and phone in line):
            contact_index = i
            break

    if contact_index != -1:
        start_check = max(0, contact_index - 4)
        for i in range(contact_index - 1, start_check - 1, -1):
            cand = clean_candidate_name_line(lines[i])
            if is_valid_name_line(cand):
                return cand

        end_check = min(len(lines), contact_index + 3)
        for i in range(contact_index + 1, end_check):
            cand = clean_candidate_name_line(lines[i])
            if is_valid_name_line(cand):
                return cand

    # 3. Top-down line search in first 10 non-empty lines
    for line in lines[:10]:
        cand = clean_candidate_name_line(line)
        if is_valid_name_line(cand):
            return cand

    # 4. Explicit label fallback: Name: ...
    match = re.search(r'(?:Name|Candidate Name)\s*:\s*([A-Za-z\s]{2,40})', text, re.IGNORECASE)
    if match:
        val = clean_candidate_name_line(match.group(1).strip())
        if is_valid_name_line(val):
            return val

    return "Candidate Name"

def parse_applied_role(text):
    """Extract applied role using header subtitle anchors, keyword matching, and role suffix heuristics."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 1. Check top 15 lines for exact job role subtitle lines
    for line in lines[:15]:
        lower_line = line.lower()
        if '"' in line or "'" in line or 'architectures' in lower_line or 'overview' in lower_line or 'summary' in lower_line or 'clean' in lower_line:
            continue

        if any(keyword in lower_line for keyword in ROLE_KEYWORDS) or any(role.lower() in lower_line for role in TECH_ROLES):
            if not any(w in lower_line for w in ['experience', 'education', 'certifications', 'summary', 'skills', 'email', 'phone', 'portfolio', '@', 'http', 'mvc', 'mvvm']):
                line_clean = clean_candidate_name_line(line)
                words = line_clean.split()
                if 1 <= len(words) <= 6 and not any(c.isdigit() for c in line_clean):
                    email = parse_email(text)
                    if email and email.split('@')[0].lower() in line_clean.lower().replace(' ', ''):
                        continue
                    return line_clean

    # 2. Check known tech/business roles keywords anywhere in text
    for role in TECH_ROLES:
        pattern = rf'\b{re.escape(role)}\b'
        if re.search(pattern, text, re.IGNORECASE):
            return role

    # 3. Explicit label match: Role: ...
    label_pattern = r'(?:Role|Position|Applied Role|Applying for|Title|Objective)\s*:\s*([^\n\r]{2,60})'
    match = re.search(label_pattern, text, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        for role in TECH_ROLES:
            if role.lower() in val.lower():
                return role
        if 3 <= len(val) <= 40:
            return val

    return "Software Engineer"

def clean_degree_title(val):
    if not val:
        return "Not Specified"
    
    val = val.split('\n')[0].strip()
    val = re.sub(r'\s+', ' ', val).strip()

    # 1. B.E in [Subject]
    m_be = re.search(r'(?i)\b(B\.E\.?\s*(?:in\s+[A-Za-z\s]+|CS&E|CSE|ECE|EEE|IT|Civil|Mechanical)?)\b', val)
    if m_be:
        deg = m_be.group(1).strip()
        deg = re.sub(r'(?i)\s+(?:from|at|@|Apex|IPCS|Oxford|College|Institute|University|Research|Global|Pvt|Ltd|Bangalore|Chennai|Mumbai|Delhi).*$', '', deg).strip()
        if deg.lower().endswith(' in'): deg = deg[:-3].strip()
        return deg

    # 2. Bachelor of [Subject]
    m_bach = re.search(r'(?i)\b(Bachelor[’\']?s?\s+(?:of\s+[A-Za-z\s]+|Degree|in\s+[A-Za-z\s]+)?)\b', val)
    if m_bach:
        deg = m_bach.group(1).strip()
        deg = re.sub(r'(?i)\s+(?:from|at|@|Apex|IPCS|Oxford|College|Institute|University|Research|Global|Pvt|Ltd|Bangalore|Chennai|Mumbai|Delhi).*$', '', deg).strip()
        if deg.lower().endswith(' of'): deg = deg[:-3].strip()
        if deg.lower().endswith(' in'): deg = deg[:-3].strip()
        return deg

    # 3. Master of [Subject]
    m_mast = re.search(r'(?i)\b(Master[’\']?s?\s+(?:of\s+[A-Za-z\s]+|Degree|in\s+[A-Za-z\s]+)?)\b', val)
    if m_mast:
        deg = m_mast.group(1).strip()
        deg = re.sub(r'(?i)\s+(?:from|at|@|Apex|IPCS|Oxford|College|Institute|University|Research|Global|Pvt|Ltd|Bangalore|Chennai|Mumbai|Delhi).*$', '', deg).strip()
        if deg.lower().endswith(' of'): deg = deg[:-3].strip()
        if deg.lower().endswith(' in'): deg = deg[:-3].strip()
        return deg

    # 4. Diploma in [Subject]
    m_dip = re.search(r'(?i)\b(Diploma(?:\s+in\s+[A-Za-z\s]+)?)\b', val)
    if m_dip:
        deg = m_dip.group(1).strip()
        deg = re.sub(r'(?i)\s+(?:from|at|@|Apex|IPCS|Oxford|College|Institute|University|Research|Global|Pvt|Ltd|VALUE|LEAD|Bangalore|Chennai|Mumbai|Delhi).*$', '', deg).strip()
        if deg.lower().endswith(' in'): deg = deg[:-3].strip()
        return deg

    # 5. Standard acronyms (MBA, BCA, MCA, B.Tech, M.Tech, BBA, Ph.D, B.Sc, M.Sc, B.Com)
    m_acr = re.search(r'\b(MBA|BCA|MCA|B\.Tech|M\.Tech|BBA|Ph\.D|B\.Sc|M\.Sc|B\.Com)\b', val, re.IGNORECASE)
    if m_acr:
        return m_acr.group(1).strip()

    return val

def parse_qualifications(text):
    """Extract ONLY main academic degree qualification title (e.g. B.E in Computer Science, Bachelor of Business Administration, MBA, Diploma)."""
    degree_patterns = [
        r'\b(B\.E\.?\s*(?:CS&E|CSE|ECE|EEE|IT|Civil|Mechanical|in\s+[A-Za-z\s]+)?)\b',
        r'\b(B\.Tech(?:\s+in\s+[A-Za-z\s]+)?)\b',
        r'\b(M\.Tech(?:\s+in\s+[A-Za-z\s]+)?)\b',
        r'\b(B\.S\.|M\.S\.|B\.Sc|M\.Sc|BCA|MCA|MBA|BBA|Ph\.D)\b',
        r'\b(Diploma(?:\s+in\s+[A-Za-z\s]+){1,4})\b',
        r'\b(Bachelor[’\']?s?\s+(?:Degree|of\s+[A-Za-z\s]+)?)\b',
        r'\b(Master[’\']?s?\s+(?:Degree|of\s+[A-Za-z\s]+)?)\b',
    ]

    for pattern in degree_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = val.split('\n')[0].strip()
            cleaned = clean_degree_title(val)
            if cleaned and len(cleaned) >= 2 and cleaned != "Not Specified":
                return cleaned

    m_top = re.search(r',\s*(B\.E\.?\s*[A-Z&]*|B\.Tech|M\.Tech|MBA|BSc|MSc|Ph\.D|Diploma)', text, re.IGNORECASE)
    if m_top:
        cleaned = clean_degree_title(m_top.group(1).strip())
        if cleaned:
            return cleaned

    return "Not Specified"

def parse_experience(text):
    """Extract recent years of experience or recent experience date ranges."""
    # 1. Direct explicit years of experience (e.g., "5+ years of experience" or "3 yrs")
    m_years = re.search(r'\b(\d+(?:\.\d+)?\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?)\b', text, re.IGNORECASE)
    if m_years:
        return m_years.group(1).strip()

    # 2. Recent year ranges with Present (e.g., "2024 - Present" or "Aug 2026 - Present")
    m_present = re.search(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*202[0-9]\s*[\u2013\-]\s*Present)\b', text, re.IGNORECASE)
    if m_present:
        return m_present.group(1).strip()

    # 3. Standard date range (e.g., "Jan 2024 - Dec 2025" or "2022 - 2024")
    m_range = re.search(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*20\d{2}\s*[\u2013\-]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*20\d{2})\b', text, re.IGNORECASE)
    if m_range:
        return m_range.group(1).strip()

    return "Not Specified"

def parse_previous_company(text):
    """Extract previous company/organization name if present in resume."""
    label_match = re.search(r'(?:Previous\s+Company|Previous\s+Organization|Company|Organization|Employer)\s*:\s*([A-Za-z0-9\s&.,-]{2,40})', text, re.IGNORECASE)
    if label_match:
        val = label_match.group(1).strip()
        first_line = val.split('\n')[0].strip()
        if len(first_line) >= 2:
            return first_line

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines:
        lower = line.lower()
        if any(w in lower for w in ['experience', 'education', 'certifications', 'skills', 'summary', 'projects']):
            continue

        if any(sep in line for sep in ['—', '–', ' - ', ' at ', ' @ ']):
            parts = re.split(r'[\u2014\u2013]|\s+-\s+|\s+at\s+|\s+@\s+', line)
            if len(parts) >= 2:
                comp_cand = parts[1].strip()
                comp_cand = re.sub(r'[\.,].*$', '', comp_cand).strip()
                if 2 <= len(comp_cand) <= 40 and not any(w in comp_cand.lower() for w in ['remote', 'present', '2024', '2025', '2026', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                    return comp_cand

    return ""

def parse_resume_data(file_path_or_bytes, file_name=None):
    """Main parsing entrypoint."""
    if not file_name and isinstance(file_path_or_bytes, str) and os.path.exists(file_path_or_bytes):
        file_name = os.path.basename(file_path_or_bytes)

    raw_text = extract_text_from_pdf(file_path_or_bytes)
    
    email = parse_email(raw_text)
    phone = parse_phone(raw_text)
    sub_date = parse_date(raw_text)
    name = format_clean_name(parse_name(raw_text, file_name=file_name))
    applied_role = parse_applied_role(raw_text)
    qualifications = parse_qualifications(raw_text)
    experience = parse_experience(raw_text)
    previous_company = parse_previous_company(raw_text)

    return {
        'name': name,
        'email': email,
        'phone': phone,
        'applied_role': applied_role,
        'submission_date': sub_date,
        'qualifications': qualifications,
        'experience': experience,
        'previous_company': previous_company,
    }
