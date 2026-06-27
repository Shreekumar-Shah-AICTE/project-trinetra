"""
jd.py — Job Description Constants for Project Trinetra (त्रिनेत्र)

Encodes the target JD (Senior AI Engineer — Founding Team at Redrob AI)
as structured constants used by all ranking dimensions.
"""

# ──────────────────────────────────────────────────────────────────────
#  CORE SKILL CONCEPTS — What the JD actually demands
#  Grouped by evidence strength: career proof > skill tag
# ──────────────────────────────────────────────────────────────────────

# Tier 1: "Things you absolutely need" — highest weight
CORE_CONCEPTS = [
    "embeddings", "embedding", "sentence-transformers", "sentence transformers",
    "bge", "e5", "openai embeddings",
    "vector database", "vector search", "vector db",
    "pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss",
    "hybrid search", "hybrid retrieval", "dense retrieval", "sparse retrieval",
    "bm25", "tf-idf", "tfidf",
    "ranking", "re-ranking", "reranking", "cross-encoder", "bi-encoder",
    "ndcg", "mrr", "map", "precision", "recall", "evaluation framework",
    "retrieval", "information retrieval",
]

# Tier 2: "Things we'd like you to have" — moderate weight
PREFERRED_CONCEPTS = [
    "lora", "qlora", "peft", "fine-tuning", "fine tuning", "finetuning",
    "learning to rank", "learning-to-rank", "xgboost", "lightgbm",
    "hr-tech", "hrtech", "recruiting", "talent", "marketplace",
    "distributed systems", "large-scale inference", "inference optimization",
    "open-source", "open source",
]

# Tier 3: General AI/ML competence — lower weight, supports but not sufficient
GENERAL_AI_CONCEPTS = [
    "machine learning", "deep learning", "nlp", "natural language processing",
    "transformer", "transformers", "bert", "gpt", "llm", "large language model",
    "neural network", "pytorch", "tensorflow", "keras",
    "recommendation", "recommendation system", "recommender",
    "search relevance", "search engine", "search system",
    "rag", "retrieval augmented generation",
    "langchain", "llamaindex",
    "data pipeline", "ml pipeline", "mlops",
    "a/b testing", "ab testing", "online experiment",
]

# Production system keywords — evidence of "shipper" not "researcher"
PRODUCTION_KEYWORDS = [
    "production", "deployed", "shipped", "scaled", "latency",
    "api", "microservices", "pipeline", "real users", "monitoring",
    "ci/cd", "docker", "kubernetes", "aws", "gcp", "azure",
    "end-to-end", "end to end",
]

# ──────────────────────────────────────────────────────────────────────
#  EXPERIENCE PARAMETERS
# ──────────────────────────────────────────────────────────────────────

IDEAL_YOE_MIN = 5
IDEAL_YOE_MAX = 9
SWEET_SPOT_YOE_MIN = 6
SWEET_SPOT_YOE_MAX = 8

# ──────────────────────────────────────────────────────────────────────
#  LOCATION PARAMETERS
# ──────────────────────────────────────────────────────────────────────

PREFERRED_LOCATIONS = {"pune", "noida", "delhi", "new delhi", "delhi ncr", "gurgaon", "gurugram"}
TIER1_INDIA_CITIES = {
    "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai", "kolkata",
    "pune", "noida", "delhi", "new delhi", "gurgaon", "gurugram",
    "delhi ncr", "ahmedabad",
}

# ──────────────────────────────────────────────────────────────────────
#  COMPANY CLASSIFIERS — Used by Guard Gate (Eye 1)
# ──────────────────────────────────────────────────────────────────────

# IT Consulting/Services firms — JD explicitly says "bad fit"
SERVICES_COMPANIES = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "tech mahindra", "mindtree", "mphasis",
    "hcl", "hcl technologies", "l&t infotech", "lti", "ltimindtree",
    "persistent systems", "hexaware", "zensar", "cyient", "birlasoft",
    "niit technologies", "coforge",
}

# Fictional companies planted as honeypot markers
FICTIONAL_COMPANIES = {
    "pied piper", "hooli", "raviga capital", "bachmanity",        # Silicon Valley
    "wayne enterprises", "wayne industries", "wayne tech",         # DC Comics
    "stark industries", "stark international",                     # Marvel
    "initech", "intertrode",                                       # Office Space
    "dunder mifflin", "dunder mifflin inc",                        # The Office
    "acme corp", "acme corporation", "acme inc",                   # Looney Tunes
    "globex", "globex inc", "globex corporation",                  # The Simpsons
    "umbrella corporation", "umbrella corp",                       # Resident Evil
    "soylent corp", "soylent green",                               # Soylent Green
    "cyberdyne systems", "cyberdyne",                              # Terminator
    "tyrell corporation", "tyrell corp",                           # Blade Runner
    "weyland-yutani", "weyland yutani",                            # Alien
    "oscorp", "oscorp industries",                                 # Spider-Man
    "lexcorp", "lex corp",                                         # DC Comics
    "massive dynamic",                                             # Fringe
    "prestige worldwide",                                          # Step Brothers
    "virtucon",                                                    # Austin Powers
}

# Known real product companies in India — strong positive signal
PRODUCT_COMPANIES = {
    # Indian unicorns / startups
    "flipkart", "swiggy", "zomato", "paytm", "phonepe", "cred", "razorpay",
    "meesho", "dream11", "policybazaar", "nykaa", "inmobi",
    "ola", "byju's", "byjus", "vedantu", "unacademy", "upgrad",
    "freshworks", "zoho", "glance", "pharmeasy",
    # AI/NLP focused Indian companies
    "haptik", "yellow.ai", "verloop.io", "saarthi.ai", "sarvam ai",
    "observe.ai", "niramai", "mad street den", "krutrim",
    "rephrase.ai", "genpact ai", "locobuzz", "aganitha",
    # Global tech giants
    "google", "amazon", "meta", "microsoft", "apple", "netflix",
    "uber", "linkedin", "salesforce", "adobe", "nvidia",
    "twitter", "x corp", "openai", "anthropic", "deepmind",
    "stripe", "airbnb", "spotify", "snap", "pinterest",
}

# ──────────────────────────────────────────────────────────────────────
#  SKILL ADJACENCY GRAPH — For Skill Corroboration (Guard Gate)
#  If a candidate claims skill A, they should plausibly have ≥1
#  skill from A's adjacency set. Isolated claims are suspicious.
# ──────────────────────────────────────────────────────────────────────

SKILL_ADJACENCY = {
    "faiss": {"vector search", "embeddings", "embedding", "pytorch", "numpy", "ann", "approximate nearest neighbor", "similarity search"},
    "pinecone": {"vector search", "embeddings", "embedding", "vector database", "semantic search", "retrieval"},
    "weaviate": {"vector search", "embeddings", "embedding", "vector database", "graphql", "semantic search"},
    "qdrant": {"vector search", "embeddings", "embedding", "vector database", "rust", "semantic search"},
    "milvus": {"vector search", "embeddings", "embedding", "vector database", "distributed systems"},
    "elasticsearch": {"search", "lucene", "kibana", "logstash", "full-text search", "bm25", "opensearch"},
    "opensearch": {"search", "elasticsearch", "aws", "kibana", "full-text search", "bm25"},
    "sentence-transformers": {"embeddings", "embedding", "pytorch", "transformers", "bert", "huggingface", "nlp"},
    "transformers": {"pytorch", "bert", "gpt", "huggingface", "nlp", "deep learning", "fine-tuning"},
    "bert": {"transformers", "nlp", "pytorch", "huggingface", "deep learning", "fine-tuning"},
    "rag": {"langchain", "llm", "embeddings", "vector search", "retrieval", "llamaindex"},
    "lora": {"fine-tuning", "llm", "peft", "qlora", "huggingface"},
    "qlora": {"fine-tuning", "llm", "peft", "lora", "huggingface"},
    "xgboost": {"machine learning", "gradient boosting", "feature engineering", "scikit-learn", "learning to rank"},
    "ndcg": {"ranking", "information retrieval", "search", "evaluation", "mrr", "map"},
    "mrr": {"ranking", "information retrieval", "search", "evaluation", "ndcg"},
}

# ──────────────────────────────────────────────────────────────────────
#  DISQUALIFIER HEADLINE PATTERNS
#  Candidates whose primary domain is NOT AI/ML engineering
# ──────────────────────────────────────────────────────────────────────

NON_AI_HEADLINE_PATTERNS = [
    "marketing", "sales", "accountant", "accounting", "finance manager",
    "hr manager", "human resources", "recruiter", "talent acquisition",
    "graphic designer", "ui designer", "ux designer",
    "content writer", "copywriter", "social media",
    "legal", "lawyer", "advocate", "attorney",
    "teacher", "professor", "lecturer",
    "nurse", "doctor", "physician",
    "civil engineer", "mechanical engineer", "electrical engineer",
    "architect", "interior designer",
    "chef", "hospitality", "hotel management",
    "real estate", "property", "insurance agent",
    # Extra non-AI domains identified during LLM audit
    "customer support", "support agent", "support executive", "customer success",
    "operations manager", "operations executive", "business analyst",
    "qa engineer", "test engineer", "software test", ".net developer", "dotnet developer",
]

# CV/Speech/Robotics — JD says "not what we need" unless they also have NLP/IR
CV_SPEECH_ROBOTICS_ONLY = [
    "computer vision", "image processing", "object detection", "yolo",
    "speech recognition", "speech synthesis", "text to speech", "tts",
    "robotics", "ros", "autonomous vehicle", "self-driving",
    "drone", "lidar", "slam",
]
