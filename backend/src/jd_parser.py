"""
Intelligent Query Understanding Engine
LLM-level natural language understanding through layered rule-based intelligence.
"""

import re
import json
import logging
from typing import Dict, List, Any, Tuple, Set
from rapidfuzz import fuzz, process
from src.utils import normalize_text

logger = logging.getLogger(__name__)


class JDParser:
    """
    Multi-layered query understanding engine.
    Handles formal JDs, casual queries, abbreviations, typos, and implicit intent.
    """

    # ════════════════════════════════════════════════════════════════════
    # LAYER 1: ROLE ONTOLOGY (300+ mappings)
    # ════════════════════════════════════════════════════════════════════

    ROLE_ONTOLOGY = {
        # Engineering roles
        "sde":           ["software engineer", "software developer", "developer"],
        "sde1":          ["software engineer", "junior developer"],
        "sde2":          ["software engineer", "mid level developer"],
        "sde3":          ["senior software engineer"],
        "swe":           ["software engineer", "software developer"],
        "swe1":          ["software engineer i", "junior software engineer"],
        "swe2":          ["software engineer ii", "mid software engineer"],
        "swe3":          ["senior software engineer"],
        "se":            ["software engineer"],
        "sse":           ["senior software engineer"],
        "dev":           ["developer", "software developer"],
        "developer":     ["software developer", "software engineer"],
        "engineer":      ["software engineer", "engineer"],
        "programmer":    ["software developer", "programmer"],
        "coder":         ["developer", "programmer"],
        "ic":            ["individual contributor", "engineer"],

        # Specialized engineering
        "fe":            ["frontend engineer", "frontend developer", "ui developer"],
        "frontend":      ["frontend engineer", "frontend developer", "ui developer"],
        "be":            ["backend engineer", "backend developer", "server engineer"],
        "backend":       ["backend engineer", "backend developer", "server engineer"],
        "fs":            ["full stack developer", "fullstack engineer"],
        "fullstack":     ["full stack developer", "fullstack engineer"],
        "full-stack":    ["full stack developer", "fullstack engineer"],
        "mobile":        ["mobile developer", "ios developer", "android developer"],
        "ios":           ["ios developer", "swift developer", "mobile developer"],
        "android":       ["android developer", "kotlin developer", "mobile developer"],
        "web":           ["web developer", "web engineer"],
        "embedded":      ["embedded engineer", "firmware engineer"],
        "firmware":      ["firmware engineer", "embedded engineer"],
        "game":          ["game developer", "unity developer", "unreal developer"],

        # DevOps and infra
        "devops":        ["devops engineer", "site reliability engineer", "infrastructure engineer"],
        "sre":           ["site reliability engineer", "devops engineer"],
        "platform":      ["platform engineer", "infrastructure engineer"],
        "infra":         ["infrastructure engineer", "platform engineer"],
        "cloud":         ["cloud engineer", "cloud architect"],
        "network":       ["network engineer"],
        "security":      ["security engineer", "cybersecurity engineer", "infosec"],
        "secops":        ["security engineer", "security operations"],
        "appsec":        ["application security engineer"],

        # Data and ML
        "ds":            ["data scientist"],
        "de":            ["data engineer"],
        "da":            ["data analyst"],
        "ml":            ["machine learning engineer", "ml engineer"],
        "mle":           ["machine learning engineer", "ml engineer"],
        "ai":            ["ai engineer", "artificial intelligence engineer"],
        "aie":           ["ai engineer", "applied ai engineer"],
        "nlp":           ["nlp engineer", "natural language processing engineer"],
        "cv":            ["computer vision engineer"],
        "llm":           ["llm engineer", "large language model engineer", "generative ai engineer"],
        "mlops":         ["mlops engineer", "machine learning operations"],
        "dataops":       ["data operations engineer"],
        "analytics":     ["data analyst", "analytics engineer"],
        "researcher":    ["research scientist", "applied scientist"],
        "scientist":     ["data scientist", "applied scientist"],

        # QA and testing
        "qa":            ["quality assurance engineer", "test engineer", "qa engineer"],
        "sdet":          ["software development engineer in test"],
        "tester":        ["test engineer", "qa engineer"],
        "automation":    ["automation engineer", "qa automation"],

        # Management and leadership
        "em":            ["engineering manager", "team lead"],
        "tl":            ["tech lead", "technical lead", "team lead"],
        "lead":          ["tech lead", "team lead", "engineering lead"],
        "principal":     ["principal engineer", "principal software engineer"],
        "staff":         ["staff engineer", "staff software engineer"],
        "architect":     ["software architect", "solutions architect"],
        "sa":            ["solutions architect", "system architect"],
        "ea":            ["enterprise architect"],
        "director":      ["engineering director", "director"],
        "vp":            ["vice president", "vp engineering"],
        "cto":           ["chief technology officer"],
        "ceo":           ["chief executive officer"],
        "cfo":           ["chief financial officer"],
        "cio":           ["chief information officer"],
        "cdo":           ["chief data officer"],
        "cmo":           ["chief marketing officer"],
        "coo":           ["chief operating officer"],
        "founder":       ["founder", "co-founder", "entrepreneur"],

        # Product
        "pm":            ["product manager"],
        "spm":           ["senior product manager"],
        "gpm":           ["group product manager"],
        "tpm":           ["technical program manager"],
        "po":            ["product owner"],
        "product":       ["product manager"],
        "designer":      ["product designer", "ui designer", "ux designer"],
        "ux":            ["ux designer", "user experience designer"],
        "ui":            ["ui designer", "user interface designer"],
        "uxr":           ["ux researcher", "user research"],

        # Business
        "hr":            ["human resources", "hr manager", "recruiter",
                          "talent acquisition", "people operations", "hrbp"],
        "hrbp":          ["hr business partner"],
        "ta":            ["talent acquisition specialist", "recruiter"],
        "recruiter":     ["recruiter", "talent acquisition"],
        "ba":            ["business analyst"],
        "sales":         ["sales executive", "account executive", "sdr"],
        "sdr":           ["sales development representative"],
        "bdr":           ["business development representative"],
        "ae":            ["account executive"],
        "csm":           ["customer success manager"],
        "marketing":     ["marketing manager", "digital marketing"],
        "smm":           ["social media manager"],
        "seo":           ["seo specialist", "search engine optimization"],
        "content":       ["content writer", "content strategist"],
        "writer":        ["content writer", "copywriter"],

        # Finance
        "ca":            ["chartered accountant"],
        "cpa":           ["certified public accountant"],
        "cfp":           ["certified financial planner"],
        "fpa":           ["financial planning analyst"],
        "accountant":    ["accountant", "financial analyst"],
        "finance":       ["finance manager", "financial analyst"],

        # Operations
        "ops":           ["operations manager", "business operations"],
        "supply":        ["supply chain manager"],
        "logistics":     ["logistics manager"],

        # Civil/Mechanical
        "civil":         ["civil engineer"],
        "mech":          ["mechanical engineer"],
        "elec":          ["electrical engineer"],
        "ec":            ["electronics engineer"],
        "che":           ["chemical engineer"],
    }

    # ════════════════════════════════════════════════════════════════════
    # LAYER 2: SKILL ONTOLOGY (500+ technical terms)
    # ════════════════════════════════════════════════════════════════════

    SKILL_ABBREVIATIONS = {
        # Languages
        "js": "javascript", "ts": "typescript", "py": "python", "rb": "ruby",
        "go": "golang", "cpp": "c++", "cs": "c#", "kt": "kotlin",
        "rs": "rust", "sc": "scala", "ph": "php", "pl": "perl",

        # Frameworks
        "node": "node.js", "nodejs": "node.js",
        "ng": "angular", "vue": "vue.js",
        "rxjs": "rxjs", "redux": "redux",
        "next": "next.js", "nuxt": "nuxt.js",
        "tf": "tensorflow", "pt": "pytorch",
        "sklearn": "scikit-learn", "sk": "scikit-learn",
        "np": "numpy", "pd": "pandas",
        "ds": "data structures", "algo": "algorithms",
        "oop": "object oriented programming", "fp": "functional programming",

        # Cloud
        "aws": "amazon web services", "gcp": "google cloud platform",
        "az": "azure", "do": "digitalocean",
        "ec2": "ec2", "s3": "s3", "rds": "rds", "lambda": "aws lambda",
        "gke": "google kubernetes engine", "eks": "elastic kubernetes service",
        "aks": "azure kubernetes service",

        # DevOps
        "k8s": "kubernetes", "tf": "terraform",
        "ci": "continuous integration", "cd": "continuous deployment",
        "ci/cd": "ci/cd", "gh": "github", "gl": "gitlab",
        "iac": "infrastructure as code",

        # Databases
        "psql": "postgresql", "pg": "postgresql", "pgsql": "postgresql",
        "mongo": "mongodb", "es": "elasticsearch", "ms": "mssql",
        "db": "database", "rdbms": "relational database",
        "nosql": "nosql database",

        # ML/AI
        "ml": "machine learning", "dl": "deep learning",
        "ai": "artificial intelligence", "agi": "artificial general intelligence",
        "nlp": "natural language processing", "cv": "computer vision",
        "rl": "reinforcement learning", "gan": "generative adversarial network",
        "cnn": "convolutional neural network", "rnn": "recurrent neural network",
        "lstm": "long short term memory", "gru": "gated recurrent unit",
        "bert": "bert", "gpt": "gpt", "llm": "large language models",
        "rag": "retrieval augmented generation",
        "vector db": "vector database",
        "embed": "embeddings", "embeds": "embeddings",
        "transformer": "transformer", "attention": "attention mechanism",
        "fine tune": "fine tuning", "finetune": "fine tuning",
        "prompt eng": "prompt engineering",

        # Data
        "etl": "extract transform load", "elt": "extract load transform",
        "dwh": "data warehouse", "dl": "data lake",
        "olap": "online analytical processing",
        "oltp": "online transaction processing",
        "bi": "business intelligence",
        "kpi": "key performance indicator",
        "ab test": "a/b testing", "abtest": "a/b testing",

        # Web/API
        "rest": "rest api", "restful": "rest api",
        "gql": "graphql", "ws": "websockets",
        "soap": "soap api", "grpc": "grpc",
        "jwt": "json web token", "oauth": "oauth",
        "spa": "single page application", "ssr": "server side rendering",
        "ssg": "static site generation", "csr": "client side rendering",
        "pwa": "progressive web app", "seo": "search engine optimization",

        # Tools/Misc
        "vs": "visual studio", "vscode": "vs code",
        "ide": "integrated development environment",
        "tdd": "test driven development", "bdd": "behavior driven development",
        "ddd": "domain driven design",
        "solid": "solid principles", "kiss": "keep it simple",
        "dry": "dont repeat yourself",
        "mvc": "model view controller", "mvp": "model view presenter",
        "mvvm": "model view viewmodel",
        "soa": "service oriented architecture",
        "saas": "software as a service", "paas": "platform as a service",
        "iaas": "infrastructure as a service",
        "b2b": "business to business", "b2c": "business to consumer",
        "crm": "customer relationship management",
        "erp": "enterprise resource planning",
    }

    # ════════════════════════════════════════════════════════════════════
    # LAYER 3: DOMAIN CONCEPT MAP
    # ════════════════════════════════════════════════════════════════════

    DOMAIN_KEYWORDS = {
        "backend": [
            "backend", "back-end", "back end", "server-side", "server side",
            "api", "rest api", "graphql", "microservices", "monolith",
            "database design", "server", "api development",
        ],
        "frontend": [
            "frontend", "front-end", "front end", "client-side", "client side",
            "ui development", "browser", "responsive design", "spa",
        ],
        "fullstack": [
            "fullstack", "full-stack", "full stack", "end to end",
            "end-to-end", "frontend and backend",
        ],
        "mobile": [
            "mobile", "ios", "android", "react native", "flutter",
            "mobile app", "app development",
        ],
        "web": [
            "web", "web development", "website", "web app", "web application",
        ],
        "devops": [
            "devops", "dev ops", "infrastructure", "deployment", "ci/cd",
            "automation", "platform engineering", "site reliability",
        ],
        "cloud": [
            "cloud", "cloud computing", "cloud architecture", "cloud native",
            "aws", "azure", "gcp", "serverless",
        ],
        "data": [
            "data", "data engineering", "data pipeline", "etl", "data warehouse",
            "big data", "data lake", "streaming", "batch processing",
        ],
        "analytics": [
            "analytics", "data analytics", "business analytics", "reporting",
            "dashboards", "kpis", "metrics", "insights",
        ],
        "ml": [
            "machine learning", "ml", "deep learning", "ai/ml", "model training",
            "neural networks", "supervised learning", "unsupervised learning",
        ],
        "ai": [
            "artificial intelligence", "ai", "generative ai", "llm",
            "large language models", "chatbots", "rag",
        ],
        "nlp": [
            "natural language processing", "nlp", "text analysis",
            "sentiment analysis", "text classification",
        ],
        "computer_vision": [
            "computer vision", "cv", "image recognition", "object detection",
            "image segmentation", "ocr",
        ],
        "security": [
            "security", "cybersecurity", "infosec", "appsec", "penetration testing",
            "vulnerability", "encryption", "authentication", "authorization",
        ],
        "qa": [
            "qa", "testing", "quality assurance", "test automation",
            "manual testing", "regression testing", "unit testing",
        ],
        "design": [
            "design", "ux", "ui", "user experience", "user interface",
            "wireframing", "prototyping", "figma", "design systems",
        ],
        "product": [
            "product management", "product strategy", "roadmap",
            "product owner", "agile", "scrum",
        ],
        "hr": [
            "hr", "human resources", "recruitment", "talent acquisition",
            "people operations", "employee relations", "hiring", "interviewing",
            "onboarding", "training", "performance management",
            "compensation", "benefits", "hrbp",
        ],
        "sales": [
            "sales", "business development", "account management",
            "sales pipeline", "lead generation", "client acquisition",
        ],
        "marketing": [
            "marketing", "digital marketing", "content marketing",
            "seo", "sem", "social media marketing", "email marketing",
            "growth", "brand", "campaigns",
        ],
        "finance": [
            "finance", "accounting", "financial analysis", "budgeting",
            "forecasting", "audit", "tax", "treasury",
        ],
        "operations": [
            "operations", "ops", "business operations", "supply chain",
            "logistics", "procurement",
        ],
        "consulting": [
            "consulting", "consultant", "advisory", "strategy",
        ],
        "research": [
            "research", "r&d", "innovation", "lab", "scientific",
        ],
        "education": [
            "teaching", "training", "education", "instructor", "tutor",
            "professor", "academic",
        ],
        "healthcare": [
            "healthcare", "medical", "clinical", "patient care", "nursing",
        ],
        "legal": [
            "legal", "law", "attorney", "lawyer", "compliance", "contracts",
        ],
    }

    # ════════════════════════════════════════════════════════════════════
    # LAYER 4: SEMANTIC CONCEPT EXPANSION
    # When user says X, also consider Y, Z (related concepts)
    # ════════════════════════════════════════════════════════════════════

    CONCEPT_EXPANSIONS = {
        "communication": [
            "interpersonal skills", "verbal communication", "written communication",
            "presentation skills", "stakeholder management", "active listening",
        ],
        "leadership": [
            "team management", "mentoring", "coaching", "people management",
            "strategic thinking", "decision making", "delegation",
        ],
        "problem solving": [
            "analytical thinking", "critical thinking", "troubleshooting",
            "debugging", "root cause analysis",
        ],
        "teamwork": [
            "collaboration", "cross-functional", "team player",
            "interpersonal skills",
        ],
        "creativity": [
            "innovation", "creative thinking", "design thinking",
            "out of the box",
        ],
        "scalability": [
            "high scale", "distributed systems", "performance optimization",
            "load balancing", "horizontal scaling",
        ],
        "performance": [
            "optimization", "profiling", "benchmarking", "low latency",
            "high throughput",
        ],
        "architecture": [
            "system design", "design patterns", "microservices",
            "distributed systems", "scalable architecture",
        ],
        "agile": [
            "scrum", "kanban", "sprint planning", "agile methodologies",
            "iterative development",
        ],
        "startup": [
            "early stage", "fast-paced", "ambiguity", "wear many hats",
            "founder mentality", "scrappy", "build from scratch",
        ],
        "enterprise": [
            "large scale", "complex systems", "compliance", "governance",
            "enterprise architecture",
        ],
        "remote": [
            "work from home", "wfh", "distributed team", "remote first",
            "async communication",
        ],
        "growth": [
            "growth hacking", "user acquisition", "metrics-driven",
            "experimentation", "a/b testing",
        ],
    }

    # ════════════════════════════════════════════════════════════════════
    # LAYER 5: INTENSITY AND EXPERIENCE QUALIFIERS
    # ════════════════════════════════════════════════════════════════════

    INTENSITY_MODIFIERS = {
        "expert":     ["expert", "expertise", "master", "guru", "wizard",
                       "deep knowledge", "deep expertise", "ninja", "rockstar"],
        "advanced":   ["advanced", "highly skilled", "proficient",
                       "very experienced", "extensive experience"],
        "strong":     ["strong", "solid", "robust", "excellent", "exceptional",
                       "outstanding", "great", "very good"],
        "good":       ["good", "competent", "capable", "decent", "skilled"],
        "moderate":   ["some", "moderate", "working knowledge", "familiar with",
                       "exposure to"],
        "basic":      ["basic", "fundamental", "entry-level", "beginner",
                       "novice", "limited"],
    }

    EXPERIENCE_QUALIFIERS = {
        "extensive":  (8, 20),
        "veteran":    (10, 20),
        "seasoned":   (7, 15),
        "very good":  (5, 15),
        "deep":       (5, 15),
        "expert":     (5, 20),
        "experienced": (3, 12),
        "good":       (3, 10),
        "solid":      (3, 10),
        "strong":     (4, 12),
        "decent":     (2, 8),
        "some":       (1, 5),
        "moderate":   (2, 7),
        "basic":      (0, 3),
        "entry":      (0, 2),
        "junior":     (0, 3),
        "fresher":    (0, 1),
        "graduate":   (0, 2),
        "senior":     (5, 15),
        "lead":       (7, 20),
        "principal":  (10, 25),
        "staff":      (8, 20),
    }

    # ════════════════════════════════════════════════════════════════════
    # LAYER 6: SKILL TAXONOMY (kept from original)
    # ════════════════════════════════════════════════════════════════════

    TECH_SKILLS_TAXONOMY = {
        "languages": [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
            "rust", "ruby", "php", "scala", "kotlin", "swift", "r", "matlab", "perl",
            "sql", "nosql", "html", "css", "sass", "less", "shell", "bash", "powershell",
            "dart", "elixir", "clojure", "haskell", "f#", "lua", "groovy",
        ],
        "frameworks": [
            "react", "angular", "vue", "vue.js", "node.js", "nodejs", "express",
            "django", "flask", "fastapi", "spring", "spring boot", "springboot",
            ".net", "dotnet", "rails", "ruby on rails", "laravel", "nextjs", "next.js",
            "nuxt", "nuxt.js", "svelte", "ember", "backbone", "jquery",
            "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
            "spark", "pyspark", "hadoop", "kafka", "airflow", "dbt",
            "fastify", "koa", "hapi", "phoenix", "gin", "echo", "fiber",
            "react native", "flutter", "ionic", "xamarin",
        ],
        "cloud_platforms": [
            "aws", "amazon web services", "azure", "microsoft azure", "gcp",
            "google cloud", "google cloud platform", "heroku", "digitalocean",
            "cloudflare", "vercel", "netlify", "render", "fly.io", "railway",
        ],
        "databases": [
            "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
            "cassandra", "dynamodb", "oracle", "sql server", "sqlite", "neo4j",
            "couchdb", "firestore", "bigquery", "snowflake", "redshift",
            "clickhouse", "timescaledb", "influxdb", "cockroachdb", "supabase",
        ],
        "tools": [
            "docker", "kubernetes", "k8s", "jenkins", "github actions", "gitlab ci",
            "terraform", "ansible", "puppet", "chef", "grafana", "prometheus",
            "datadog", "splunk", "jira", "confluence", "git", "svn",
            "ci/cd", "devops", "mlops", "argocd", "helm", "vault", "consul",
            "circleci", "travis", "bamboo", "teamcity",
        ],
        "ai_ml": [
            "machine learning", "deep learning", "natural language processing", "nlp",
            "computer vision", "reinforcement learning", "neural networks",
            "transformers", "bert", "gpt", "llm", "large language models",
            "generative ai", "gen ai", "rag", "retrieval augmented generation",
            "embeddings", "vector databases", "langchain", "llamaindex",
            "feature engineering", "model deployment", "mlflow",
            "huggingface", "transformers library", "diffusion models",
            "stable diffusion", "openai api", "anthropic", "llama",
        ],
        "data": [
            "data engineering", "data pipeline", "etl", "elt", "data warehouse",
            "data lake", "data modeling", "data governance", "data quality",
            "business intelligence", "bi", "tableau", "power bi", "looker",
            "analytics", "statistical analysis", "a/b testing",
            "snowflake", "databricks", "fivetran", "stitch",
        ],
        "web_concepts": [
            "rest api", "graphql", "websockets", "microservices", "monolith",
            "soap", "grpc", "oauth", "jwt", "api design", "swagger", "openapi",
            "webhooks", "server sent events",
        ],
        "cs_fundamentals": [
            "data structures", "algorithms", "system design", "object oriented programming",
            "design patterns", "concurrency", "multithreading", "asynchronous programming",
            "memory management", "garbage collection",
        ],
        "testing": [
            "unit testing", "integration testing", "e2e testing", "selenium",
            "cypress", "playwright", "jest", "pytest", "junit", "mocha",
            "tdd", "bdd", "test automation",
        ],
        "soft_business": [
            "product management", "project management", "agile", "scrum",
            "kanban", "stakeholder management", "roadmapping",
        ],
    }

    SOFT_SKILLS = [
        "leadership", "communication", "teamwork", "collaboration",
        "problem solving", "problem-solving", "critical thinking",
        "project management", "time management", "adaptability",
        "mentoring", "coaching", "stakeholder management",
        "cross-functional", "agile", "scrum", "presentation",
        "strategic thinking", "decision making", "initiative",
        "attention to detail", "analytical", "creative",
        "negotiation", "conflict resolution", "empathy",
        "interpersonal", "verbal communication", "written communication",
        "active listening", "emotional intelligence", "ownership",
        "accountability", "self-motivated", "proactive",
        "customer focus", "data-driven", "results-oriented",
    ]

    EDUCATION_PATTERNS = {
        "phd": r"\b(ph\.?d|doctorate|doctoral)\b",
        "masters": r"\b(master'?s?|m\.?s\.?|m\.?a\.?|mba|m\.?eng|msc|m\.?tech)\b",
        "bachelors": r"\b(bachelor'?s?|b\.?s\.?|b\.?a\.?|b\.?eng|bsc|b\.?tech|undergraduate|degree)\b",
        "diploma": r"\b(diploma|associate)\b",
    }

    SENIORITY_PATTERNS = {
        "intern":    r"\b(intern|internship|trainee|apprentice)\b",
        "junior":    r"\b(junior|jr\.?|entry[\s-]level|associate|graduate|fresher|fresh)\b",
        "mid":       r"\b(mid[\s-]?level|intermediate|mid\s+career)\b",
        "senior":    r"\b(senior|sr\.?|experienced|seasoned)\b",
        "lead":      r"\b(lead|team\s*lead|tech\s*lead|principal|staff)\b",
        "manager":   r"\b(manager|management|director|head\s+of|vp|vice\s+president)\b",
        "executive": r"\b(chief|c-level|cto|ceo|cio|cdo|executive|founder)\b",
    }

    # Common typos and their corrections
    TYPO_CORRECTIONS = {
        "javscript": "javascript",
        "javasript": "javascript",
        "javasctipt": "javascript",
        "pyhton": "python",
        "pythn": "python",
        "phyton": "python",
        "reactjs": "react",
        "ractjs": "react",
        "nodjs": "node.js",
        "noejs": "node.js",
        "kuberneties": "kubernetes",
        "kubernetis": "kubernetes",
        "dokcer": "docker",
        "docekr": "docker",
        "tensoflow": "tensorflow",
        "tensorlfow": "tensorflow",
        "tesnorflow": "tensorflow",
        "machne learning": "machine learning",
        "machie learning": "machine learning",
        "machne lerning": "machine learning",
        "deeep learning": "deep learning",
        "comunication": "communication",
        "communcation": "communication",
        "communicaton": "communication",
        "expereince": "experience",
        "experiance": "experience",
        "expirience": "experience",
        "managment": "management",
        "develpment": "development",
        "develoment": "development",
        "engineerig": "engineering",
        "enginering": "engineering",
    }

    # ════════════════════════════════════════════════════════════════════
    # INDUSTRY/DOMAIN MAPPING
    # ════════════════════════════════════════════════════════════════════

    INDUSTRY_DOMAINS = {
        "fintech":      r"\b(fintech|financial|banking|payments|trading|insurance|insurtech|lending|wealth)\b",
        "healthcare":   r"\b(health|medical|clinical|pharma|biotech|hospital|telemedicine|diagnostics)\b",
        "ecommerce":    r"\b(e-?commerce|retail|marketplace|shopping|d2c|consumer goods)\b",
        "saas":         r"\b(saas|b2b|enterprise\s+software|cloud\s+software)\b",
        "adtech":       r"\b(advertising|adtech|marketing\s+tech|martech)\b",
        "edtech":       r"\b(education|edtech|learning|lms|e-?learning)\b",
        "cybersecurity": r"\b(security|cybersecurity|infosec)\b",
        "gaming":       r"\b(gaming|game\s+dev|game\s+development|esports)\b",
        "ai_ml":        r"\b(artificial\s+intelligence|machine\s+learning|ai/ml|deep\s+learning)\b",
        "hr_tech":      r"\b(hr\s+tech|hrtech|recruitment\s+tech|hcm)\b",
        "logistics":    r"\b(logistics|supply\s+chain|shipping|delivery)\b",
        "automotive":   r"\b(automotive|auto|car|vehicle|ev|electric vehicle)\b",
        "media":        r"\b(media|entertainment|streaming|video|content)\b",
        "telecom":      r"\b(telecom|telecommunications|5g|networking)\b",
        "energy":       r"\b(energy|oil|gas|renewable|solar|wind)\b",
        "agritech":     r"\b(agriculture|agritech|farming)\b",
        "proptech":     r"\b(real\s+estate|proptech|property)\b",
        "travel":       r"\b(travel|tourism|hospitality|hotel|airline)\b",
        "manufacturing": r"\b(manufacturing|industrial|factory|iot|industry 4.0)\b",
        "government":   r"\b(government|public sector|govtech|civic)\b",
        "non_profit":   r"\b(non-?profit|ngo|social\s+impact|charity)\b",
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Build inverse lookup for fast typo correction
        self._typo_pattern = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in self.TYPO_CORRECTIONS) + r")\b",
            re.IGNORECASE,
        ) if self.TYPO_CORRECTIONS else None

        # All known terms for fuzzy correction
        self._all_terms = self._build_term_dictionary()

    def _build_term_dictionary(self) -> List[str]:
        """Build comprehensive dictionary of known terms for fuzzy correction."""
        terms = set()
        terms.update(self.ROLE_ONTOLOGY.keys())
        for v in self.ROLE_ONTOLOGY.values():
            terms.update(v)
        terms.update(self.SKILL_ABBREVIATIONS.keys())
        terms.update(self.SKILL_ABBREVIATIONS.values())
        for category in self.TECH_SKILLS_TAXONOMY.values():
            terms.update(category)
        terms.update(self.SOFT_SKILLS)
        for keywords in self.DOMAIN_KEYWORDS.values():
            terms.update(keywords)
        return list(terms)

    # ════════════════════════════════════════════════════════════════════
    # MAIN PARSING ORCHESTRATOR
    # ════════════════════════════════════════════════════════════════════

    def parse(self, jd_text: str) -> Dict[str, Any]:
        """
        Multi-layered intelligent query parsing.
        Works for formal JDs, casual queries, single-word searches, and anything in between.
        """
        # Layer 1: Normalize
        original = normalize_text(jd_text)
        text_lower = original.lower()

        # Layer 2: Typo correction
        corrected = self._correct_typos(text_lower)

        # Layer 3: Abbreviation expansion (creates enriched text)
        expanded = self._expand_all_abbreviations(corrected)

        # Layer 4: Extract structured entities
        role_keywords = self._extract_role_keywords(corrected)
        domain_concepts = self._extract_domains(corrected)
        hard_skills = self._extract_hard_skills(expanded)

        # Add domain concepts as implicit skills
        for d in domain_concepts:
            if d not in hard_skills:
                hard_skills.append(d)

        soft_skills = self._extract_soft_skills(corrected)

        # Layer 5: Semantic expansion
        expanded_concepts = self._expand_concepts(hard_skills + soft_skills)

        # Layer 6: Intent and qualifier extraction
        seniority = self._extract_seniority_smart(corrected, role_keywords)
        experience_range = self._extract_experience_smart(corrected, seniority)
        education = self._extract_education(corrected)
        industry = self._extract_industry(corrected)
        intensity = self._extract_intensity(corrected)

        # Layer 7: Implicit requirement inference
        implicit = self._infer_implicit_requirements(
            hard_skills, role_keywords, domain_concepts, expanded
        )
        hard_skills.extend([s for s in implicit if s not in hard_skills])

        # Layer 8: Build search-optimized text
        search_text = self._build_search_text(
            original, role_keywords, domain_concepts,
            hard_skills, soft_skills, expanded_concepts
        )

        requirements = {
            "raw_text": original,
            "corrected_text": corrected,
            "expanded_text": expanded,
            "search_text": search_text,
            "role_keywords": role_keywords,
            "domain_concepts": domain_concepts,
            "hard_skills": hard_skills,
            "soft_skills": soft_skills,
            "expanded_concepts": expanded_concepts,
            "implicit_skills": implicit,
            "experience_range": experience_range,
            "education": education,
            "seniority_level": seniority,
            "industry_domain": industry,
            "key_responsibilities": self._extract_responsibilities(original),
            "intensity_signals": intensity,
            "must_have_skills": [],
            "nice_to_have_skills": [],
        }


        # Score every extracted skill by importance using generic signals
        skill_importance = {}
        for skill in requirements["hard_skills"]:
            skill_importance[skill] = self._score_skill_importance(skill, original)

        # Rank skills by importance (highest first)
        ranked_skills = sorted(
            requirements["hard_skills"],
            key=lambda s: skill_importance.get(s, 0),
            reverse=True,
        )
        requirements["hard_skills"] = ranked_skills
        requirements["skill_importance"] = skill_importance

        # Categorize: top N% by importance = must_have, rest = nice_to_have
        # This adapts to JD length — short JDs have fewer must-haves
        total_skills = len(ranked_skills)
        if total_skills > 0:
            # Use importance score threshold instead of fixed top-N
            # Skills with score >= 3.0 are likely core requirements
            must_have_threshold = 3.0
            must_have_from_score = [s for s in ranked_skills if skill_importance[s] >= must_have_threshold]
            
            # If nothing meets the threshold, take top 30% as must-haves
            if not must_have_from_score:
                cutoff = max(3, total_skills // 3)
                must_have_from_score = ranked_skills[:cutoff]
            
            requirements["must_have_skills"] = must_have_from_score
            requirements["nice_to_have_skills"] = [
                s for s in ranked_skills if s not in must_have_from_score
            ]
        else:
            requirements["must_have_skills"] = []
            requirements["nice_to_have_skills"] = []
            

        # Extract negative requirements (what JD explicitly doesn't want)
        requirements["negative_requirements"] = self._extract_negative_requirements(original)

        return requirements


    # ════════════════════════════════════════════════════════════════════
    # LAYER METHODS
    # ════════════════════════════════════════════════════════════════════

    def _correct_typos(self, text: str) -> str:
        """Layer 2: Fix common typos using both explicit map and fuzzy matching."""
        # Step 1: Explicit typo corrections
        if self._typo_pattern:
            def replace(match):
                return self.TYPO_CORRECTIONS.get(match.group(1).lower(), match.group(1))
            text = self._typo_pattern.sub(replace, text)

        # Step 2: Fuzzy correction for unknown words (only if word has 5+ chars)
        words = text.split()
        corrected = []
        for word in words:
            clean_word = re.sub(r"[^\w]", "", word).lower()
            if len(clean_word) >= 5 and clean_word not in self._all_terms:
                # Try fuzzy match against known terms
                match = process.extractOne(
                    clean_word, self._all_terms,
                    scorer=fuzz.ratio, score_cutoff=88,
                )
                if match:
                    corrected.append(match[0])
                    continue
            corrected.append(word)

        return " ".join(corrected)

    def _expand_all_abbreviations(self, text: str) -> str:
        """Layer 3: Expand role + skill abbreviations to enrich text."""
        expanded = text
        added_terms = set()

        # Expand role abbreviations
        for abbr, expansions in self.ROLE_ONTOLOGY.items():
            pattern = r"\b" + re.escape(abbr) + r"\b"
            if re.search(pattern, expanded, re.IGNORECASE):
                for exp_term in expansions[:2]:  # Add top 2 expansions
                    if exp_term not in added_terms:
                        expanded += " " + exp_term
                        added_terms.add(exp_term)

        # Expand skill abbreviations
        for abbr, full in self.SKILL_ABBREVIATIONS.items():
            pattern = r"\b" + re.escape(abbr) + r"\b"
            if re.search(pattern, expanded, re.IGNORECASE):
                if full not in added_terms:
                    expanded += " " + full
                    added_terms.add(full)

        return expanded
    

    def _extract_negative_requirements(self, text: str) -> Dict[str, Any]:
        """
        Extract things the JD explicitly excludes.
        Works generically by looking for negation grammar, not hardcoded lists.
        """
        result = {
            "excluded_keywords": [],      # Specific terms JD says it doesn't want
            "excluded_in_parens": [],     # Lists in parentheses near negations
            "exclusion_strength": 0.0,    # 0.0 to 1.0 — how strongly JD uses negation
        }

        text_lower = text.lower()

        # Generic negation phrase patterns
        # These work for any JD that uses standard English negation
        negation_markers = [
            "not a fit", "not what we need", "won't move forward",
            "will not move forward", "explicitly do not want",
            "do not want", "don't want", "we don't",
            "we are not looking for", "not what we're looking for",
            "we will not consider", "filter out", "exclude",
            "we've had bad", "bad fit", "won't consider",
            "disqualif", "we won't", "no longer consider",
            "not interested in", "avoid", "rule out",
        ]

        # Count strength of negation usage
        negation_count = sum(text_lower.count(m) for m in negation_markers)
        # Cap at 1.0 — JDs with 5+ negations strongly signal exclusions matter
        result["exclusion_strength"] = min(1.0, negation_count / 5.0)

        # Split text into sentences and find ones containing negations
        sentences = re.split(r"[.!?\n]+", text)

        for sent in sentences:
            sent_lower = sent.lower().strip()
            if not sent_lower or len(sent_lower) < 10:
                continue

            if not any(marker in sent_lower for marker in negation_markers):
                continue

            # Pattern 1: Extract items in parentheses (often used for lists of excluded things)
            # Example: "consulting firms (TCS, Infosys, Wipro)"
            paren_matches = re.findall(r"\(([^)]+)\)", sent)
            for content in paren_matches:
                items = re.split(r"[,;]|\bor\b|\band\b|/", content)
                for item in items:
                    item = item.strip().lower()
                    if 2 < len(item) < 50:
                        result["excluded_in_parens"].append(item)

            # Pattern 2: Extract noun phrases after negation markers
            # Look for patterns like "we don't want X" or "not what we need: X"
            for marker in negation_markers:
                if marker in sent_lower:
                    # Get text after the marker
                    idx = sent_lower.find(marker)
                    after = sent_lower[idx + len(marker):].strip()
                    # Take up to next punctuation or 80 chars
                    phrase = re.split(r"[.,;:]", after)[0].strip()
                    if 5 < len(phrase) < 80:
                        # Extract meaningful keywords (filter stop words)
                        words = re.findall(r"\b[a-z]{3,}\b", phrase)
                        stop_words = {
                            "the", "and", "for", "are", "any", "you", "who",
                            "with", "have", "has", "had", "this", "that",
                            "from", "into", "your", "their", "them", "they",
                            "what", "where", "when", "which", "while",
                        }
                        meaningful = [w for w in words if w not in stop_words]
                        result["excluded_keywords"].extend(meaningful[:5])

        # Deduplicate
        result["excluded_keywords"] = list(set(result["excluded_keywords"]))[:30]
        result["excluded_in_parens"] = list(set(result["excluded_in_parens"]))[:20]

        return result






    def _extract_role_keywords(self, text: str) -> List[str]:
        """Extract all role-related terms."""
        roles = set()

        # Match abbreviations
        for abbr, expansions in self.ROLE_ONTOLOGY.items():
            pattern = r"\b" + re.escape(abbr) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                roles.update(expansions)

        # Match full role phrases
        role_patterns = [
            r"\b(software\s+engineer|software\s+developer)\b",
            r"\b(data\s+scientist|data\s+engineer|data\s+analyst)\b",
            r"\b(ml\s+engineer|ai\s+engineer|machine\s+learning\s+engineer)\b",
            r"\b(devops\s+engineer|site\s+reliability\s+engineer)\b",
            r"\b(product\s+manager|project\s+manager|program\s+manager)\b",
            r"\b(hr\s+manager|hr\s+executive|recruiter|talent\s+acquisition)\b",
            r"\b(ux\s+designer|ui\s+designer|product\s+designer)\b",
            r"\b(backend|frontend|fullstack|full\s+stack)\s*(?:engineer|developer)?\b",
            r"\b(qa\s+engineer|test\s+engineer|sdet)\b",
            r"\b(business\s+analyst|business\s+development|sales\s+executive)\b",
            r"\b(marketing\s+manager|content\s+writer|copywriter)\b",
        ]
        for pattern in role_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if isinstance(m, str):
                    roles.add(m)
                elif isinstance(m, tuple):
                    roles.add(m[0])

        return list(roles)

    def _extract_domains(self, text: str) -> List[str]:
        """Extract domain concepts (backend, hr, design, etc.)."""
        found = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    found.append(domain)
                    break
        return list(set(found))

    def _expand_concepts(self, concepts: List[str]) -> List[str]:
        """Expand concepts to include related terms."""
        expanded = []
        for concept in concepts:
            if concept.lower() in self.CONCEPT_EXPANSIONS:
                expanded.extend(self.CONCEPT_EXPANSIONS[concept.lower()])
        return list(set(expanded))

    def _extract_hard_skills(self, text: str) -> List[str]:
        """Extract technical skills from taxonomy."""
        found_skills = []
        for category, skills in self.TECH_SKILLS_TAXONOMY.items():
            for skill in skills:
                if len(skill) <= 3:
                    pattern = r"\b" + re.escape(skill) + r"\b"
                    if re.search(pattern, text, re.IGNORECASE):
                        found_skills.append(skill)
                else:
                    if skill in text:
                        found_skills.append(skill)
        return list(set(found_skills))

    def _extract_soft_skills(self, text: str) -> List[str]:
        """Extract soft skills."""
        found = []
        for skill in self.SOFT_SKILLS:
            normalized = skill.replace("-", " ")
            if normalized in text or skill in text:
                found.append(skill)
        return list(set(found))

    def _extract_intensity(self, text: str) -> Dict[str, List[str]]:
        """Detect intensity modifiers."""
        intensity = {}
        for level, modifiers in self.INTENSITY_MODIFIERS.items():
            for mod in modifiers:
                if mod in text:
                    intensity.setdefault(level, []).append(mod)
        return intensity

    def _extract_seniority_smart(self, text: str, roles: List[str]) -> str:
        """Smart seniority detection — considers role abbreviations like SDE1, SDE2."""
        # Check for level suffixes in role abbreviations
        if re.search(r"\b(sde|swe|se)\s*[12]\b", text):
            return "junior" if "1" in text else "mid"
        if re.search(r"\b(sde|swe|se)\s*3\b", text):
            return "senior"
        if re.search(r"\b(sde|swe|se)\s*4\b", text):
            return "lead"

        # Standard seniority patterns
        detected = []
        for level, pattern in self.SENIORITY_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(level)

        seniority_order = ["intern", "junior", "mid", "senior", "lead", "manager", "executive"]
        for level in reversed(seniority_order):
            if level in detected:
                return level
        return "mid"

    def _extract_experience_smart(self, text: str, seniority: str) -> Tuple[int, int]:
        """Smart experience extraction with qualitative + seniority fallback."""
        # Numeric patterns first
        patterns = [
            r"(\d+)\s*[\-–to]+\s*(\d+)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
            r"(?:at\s+least|minimum|min)\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:relevant|professional|hands[\s-]on|working)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return (int(groups[0]), int(groups[1]))
                elif len(groups) == 1:
                    years = int(groups[0])
                    return (years, years + 10)

        # Qualitative qualifier matching
        for qualifier, range_tuple in self.EXPERIENCE_QUALIFIERS.items():
            if qualifier in text:
                return range_tuple

        # Seniority-based fallback
        seniority_ranges = {
            "intern":    (0, 1),
            "junior":    (0, 3),
            "mid":       (2, 7),
            "senior":    (5, 15),
            "lead":      (7, 20),
            "manager":   (7, 20),
            "executive": (10, 30),
        }
        return seniority_ranges.get(seniority, (0, 99))

    def _extract_education(self, text: str) -> Dict[str, Any]:
        """Extract education requirements."""
        education = {"min_level": None, "preferred_fields": []}
        for level, pattern in self.EDUCATION_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                education["min_level"] = level
                break

        field_patterns = [
            r"(?:degree|major|background)\s+in\s+([\w\s,&/]+?)(?:\.|,|;|\n|or\s+equivalent)",
        ]
        fields = set()
        for pattern in field_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if isinstance(m, str):
                    fields.add(m.strip().lower())
        education["preferred_fields"] = list(fields)
        return education

    def _extract_industry(self, text: str) -> List[str]:
        """Extract industry/domain."""
        found = []
        for domain, pattern in self.INDUSTRY_DOMAINS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(domain)
        return found
    

    

    def _score_skill_importance(self, skill: str, text: str) -> float:
        """
        Generic skill importance scoring based on signals in the text itself.
        No hardcoding of specific roles or industries.
        
        Higher score = more important to the role.
        """
        score = 0.0
        text_lower = text.lower()
        skill_lower = skill.lower()
        
        if skill_lower not in text_lower:
            return 0.0
        
        # Signal 1: Mentioned in the first 300 chars (typically the role description)
        # This is where the core role is defined
        first_part = text_lower[:300]
        if skill_lower in first_part:
            score += 3.0
        
        # Signal 2: Mentioned in first 800 chars (role + key responsibilities)
        first_section = text_lower[:800]
        if skill_lower in first_section:
            score += 1.5
        
        # Signal 3: Frequency of mention (more mentions = more important)
        mention_count = text_lower.count(skill_lower)
        score += min(mention_count, 5) * 0.5  # Cap at 5 mentions
        
        # Signal 4: Proximity to "must have" / "required" / "essential" markers
        must_markers = ["must have", "required", "essential", "mandatory",
                        "minimum", "you have", "you must", "we need"]
        skill_positions = [m.start() for m in re.finditer(
            re.escape(skill_lower), text_lower
        )]
        
        for marker in must_markers:
            marker_positions = [m.start() for m in re.finditer(
                re.escape(marker), text_lower
            )]
            for skill_pos in skill_positions:
                for marker_pos in marker_positions:
                    distance = abs(skill_pos - marker_pos)
                    if distance < 150:  # Within ~150 chars = same context
                        score += 2.0
                        break
        
        # Signal 5: Penalty for proximity to "nice to have" / "plus" markers
        nice_markers = ["nice to have", "preferred", "bonus", "plus",
                        "good to have", "advantageous", "desirable"]
        for marker in nice_markers:
            marker_positions = [m.start() for m in re.finditer(
                re.escape(marker), text_lower
            )]
            for skill_pos in skill_positions:
                for marker_pos in marker_positions:
                    distance = abs(skill_pos - marker_pos)
                    if distance < 150:
                        score -= 1.5
                        break
        
        # Signal 6: Title-level mention (in the role title itself)
        # Extract probable title (first line, usually contains "Engineer", "Manager", etc.)
        first_line = text.split("\n")[0].lower() if text else ""
        if skill_lower in first_line:
            score += 4.0  # Title mentions are extremely important
        
        return max(0.0, score)
    





    def _infer_implicit_requirements(
        self, skills: List[str], roles: List[str],
        domains: List[str], text: str,
    ) -> List[str]:
        """
        Layer 7: Infer implicit requirements based on role + context.
        Example: "Frontend Engineer" implies html, css, javascript even if not stated.
        """
        implicit = set()

        # Role-based implicit skills
        role_implications = {
            "frontend":  ["javascript", "html", "css"],
            "backend":   ["api development", "database"],
            "fullstack": ["javascript", "html", "css", "api development", "database"],
            "data":      ["sql", "python"],
            "ml":        ["python", "machine learning"],
            "devops":    ["linux", "docker", "ci/cd"],
            "mobile":    ["mobile app", "ui development"],
            "hr":        ["communication", "interpersonal", "stakeholder management"],
            "sales":     ["communication", "negotiation", "interpersonal"],
            "marketing": ["communication", "creativity", "analytical"],
            "design":    ["creativity", "ui development", "communication"],
            "product":   ["stakeholder management", "communication", "analytical"],
        }

        for domain in domains:
            if domain in role_implications:
                implicit.update(role_implications[domain])

        # Skill-based implicit skills (frameworks imply languages)
        framework_to_lang = {
            "react": "javascript", "angular": "typescript", "vue": "javascript",
            "next.js": "javascript", "node.js": "javascript",
            "django": "python", "flask": "python", "fastapi": "python",
            "spring": "java", "spring boot": "java",
            "rails": "ruby", "ruby on rails": "ruby",
            "laravel": "php",
            "tensorflow": "python", "pytorch": "python", "scikit-learn": "python",
        }
        for skill in skills:
            if skill in framework_to_lang:
                implicit.add(framework_to_lang[skill])

        return list(implicit)

    def _build_search_text(
        self, original: str, roles: List[str], domains: List[str],
        hard: List[str], soft: List[str], expanded: List[str],
    ) -> str:
        """
        Layer 8: Build a search-optimized text representation.
        This text is used for embedding to maximize semantic match quality.
        """
        parts = [original]

        if roles:
            parts.append(f"Role: {', '.join(roles[:5])}")
        if domains:
            parts.append(f"Area: {', '.join(domains[:5])}")
        if hard:
            parts.append(f"Skills: {', '.join(hard[:15])}")
        if soft:
            parts.append(f"Qualities: {', '.join(soft[:8])}")
        if expanded:
            parts.append(f"Related: {', '.join(expanded[:8])}")

        return " . ".join(parts)

    def _extract_responsibilities(self, text: str) -> List[str]:
        """Extract responsibilities from formal JD sections."""
        responsibilities = []
        lines = text.split("\n")
        in_section = False

        for line in lines:
            line_stripped = line.strip()
            lower_line = line_stripped.lower()

            if any(kw in lower_line for kw in [
                "responsibilities", "what you'll do", "role overview",
                "key duties", "you will", "your role",
            ]):
                in_section = True
                continue

            if in_section:
                if any(kw in lower_line for kw in [
                    "requirements", "qualifications", "what we offer",
                    "benefits", "about us", "nice to have",
                ]):
                    in_section = False
                    continue
                cleaned = re.sub(r"^[\s•\-\*\d\.]+", "", line_stripped).strip()
                if len(cleaned) > 15:
                    responsibilities.append(cleaned)

        if not responsibilities:
            action_verbs = ["design", "develop", "build", "implement", "lead",
                            "manage", "create", "optimize", "analyze", "deploy",
                            "architect", "collaborate", "drive", "mentor"]
            sentences = re.split(r"[.!?]+", text)
            for sent in sentences:
                sent = sent.strip()
                if any(sent.lower().startswith(v) or f" {v} " in sent.lower()
                       for v in action_verbs):
                    if 15 < len(sent) < 300:
                        responsibilities.append(sent)
        return responsibilities[:15]

    def _categorize_skill_priority(self, text, all_skills):
        """Categorize skills as must-have or nice-to-have based on context."""
        must_have = []
        nice_to_have = []
        nice_patterns = r"(nice\s+to\s+have|preferred|bonus|advantageous|plus|desirable|optional)"
        must_patterns = r"(required|must\s+have|essential|mandatory|minimum|core)"

        nice_positions = [m.start() for m in re.finditer(nice_patterns, text, re.IGNORECASE)]
        must_positions = [m.start() for m in re.finditer(must_patterns, text, re.IGNORECASE)]

        for skill in all_skills:
            skill_pos = text.find(skill)
            if skill_pos == -1:
                must_have.append(skill)
                continue
            closest_nice = min([abs(skill_pos - p) for p in nice_positions], default=float("inf"))
            closest_must = min([abs(skill_pos - p) for p in must_positions], default=float("inf"))
            if closest_nice < closest_must and closest_nice < 200:
                nice_to_have.append(skill)
            else:
                must_have.append(skill)
        return must_have, nice_to_have


def json_safe_dumps(obj):
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        return str(obj)