import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

# The settings class is responsible for loading all the keys and basic config info from .env file
class Settings:
    app_name: str = os.getenv("APP_NAME", "SaaS Chatbot API") # name of the chatbot
    environment: str = os.getenv("ENVIRONMENT", "development").strip().lower() # environment is used for /health api to show the stage of the chatbot project
    academy_name: str = os.getenv("ACADEMY_NAME", "Generic Organization") # fallback name
    website_url: str = os.getenv("WEBSITE_URL", "") # loading the website url for the crawler process
    debug: bool = os.getenv("DEBUG", "true").strip().lower() == "true" # Typically to control behavior between development and production.
    """
    When debug=True:
        Show detailed error traces
        Enable verbose logging
        Auto-reload server on code changes
        Display internal exception details
        Easier troubleshooting
    When debug=False:
        Hide internal errors from users
        Reduce logging noise
        Improve security
        Improve performance
    """

    ai_provider: str = os.getenv("AI_PROVIDER", "multi").strip().lower() # loading the quantity of ai to use, if it's grok it will directly use grok but multi means it will use all 3 api as fallback.

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "") # loading openai key
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini") # loading openai model name

    groq_api_key: str = os.getenv("GROQ_API_KEY", "") or os.getenv("GORQ_API_KEY", "") # loading gorq key
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") # loading gorq model name

    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "") # loading openrouter key
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openrouter/free") # loading openrouter name
    openrouter_models: list[str] = [
        item.strip()
        for item in os.getenv("OPENROUTER_MODELS", os.getenv("OPENROUTER_MODEL", "openrouter/free")).split(",")
        if item.strip() 
    ]

    vector_store_id: str = os.getenv("OPENAI_VECTOR_STORE_ID", "") 
    local_context_chars: int = int(os.getenv("LOCAL_CONTEXT_CHARS", "2500"))

    crm_api_url: str = os.getenv("CRM_API_URL", "") # loading crm api url,
    crm_api_token: str = os.getenv("CRM_API_TOKEN", "") # loading crm api access token if any
    crm_timeout_seconds: int = int(os.getenv("CRM_TIMEOUT_SECONDS", "10")) # setting up timeout rule, so if connection happened with in 10 seconds else show fail and try again

    database_path: str = os.getenv("DATABASE_PATH", "./data/chatbot_sessions.sqlite3") # connecting DB
    docs_dir: str = os.getenv("DOCS_DIR", "./data/docs") # directory for knowledge base documents
    retention_days: int = int(os.getenv("RETENTION_DAYS", "90")) # rules for data retention days

    cors_origins: list[str] = [
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "*").split(",")
        if item.strip()
    ] # Allowed websites/frontends that can make API requests to this server, like Controls which frontend websites are allowed to connect to this backend

    # Maximum number of recent messages/conversations to keep in memory for a session
    session_memory_limit: int = int(os.getenv("SESSION_MEMORY_LIMIT", "12"))

    # Maximum number of website pages to crawl while building the knowledge base
    crawl_max_pages: int = int(os.getenv("CRAWL_MAX_PAGES", "80"))

    # Maximum time (in milliseconds) allowed for website crawling before stopping
    crawl_timeout: int = int(os.getenv("CRAWL_TIMEOUT", "20000"))

    # Enable or disable automatic website crawling for knowledge base generation
    crawl_website: bool = os.getenv("CRAWL_WEBSITE", "false").strip().lower() == "true"

    # Secret token used to authorize knowledge base ingestion/rebuild requests
    ingestion_api_token: str = os.getenv("INGESTION_API_TOKEN", "")

    # Method used for lead analysis (e.g., rule-based, AI-based, or hybrid)
    lead_analysis_mode: str = os.getenv("LEAD_ANALYSIS_MODE", "hybrid").strip().lower()

# Load application settings, validate values, and cache them for reuse

# Cache settings so they are loaded only once
@lru_cache
def get_settings() -> Settings:

    # Load settings from environment variables
    settings = Settings()

    # Correct common typo: gorq -> groq
    if settings.ai_provider == "gorq":
        settings.ai_provider = "groq"

    # Use default provider if configured provider is invalid
    if settings.ai_provider not in {"multi", "groq", "openrouter", "openai"}:
        settings.ai_provider = "multi"

    # Automatically select AI provider if none was specified
    if not settings.ai_provider:

        # Use Groq if API key is available
        if settings.groq_api_key:
            settings.ai_provider = "groq"

        # Otherwise use OpenRouter
        elif settings.openrouter_api_key:
            settings.ai_provider = "openrouter"

        # Otherwise use OpenAI
        elif settings.openai_api_key:
            settings.ai_provider = "openai"

        # Final fallback
        else:
            settings.ai_provider = "multi"

    # Validate lead analysis mode, Use hybrid lead analysis if configured mode is invalid
    if settings.lead_analysis_mode not in {"rules", "hybrid"}:
        settings.lead_analysis_mode = "hybrid"

    # Return validated settings
    return settings
