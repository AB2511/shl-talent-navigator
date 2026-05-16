# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
│                                                                   │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Health   │    │     Chat     │    │   API Docs       │   │
│  │  Endpoint  │    │   Endpoint   │    │  /docs /redoc    │   │
│  └────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Router Layer                             │
│                                                                   │
│  • Request validation (Pydantic)                                 │
│  • Constraint extraction                                         │
│  • State determination                                           │
│  • Response formatting                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Components                             │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Constraint      │  │  State Machine   │  │  Hybrid      │ │
│  │  Extractor       │  │                  │  │  Retriever   │ │
│  │                  │  │  • 6 states      │  │              │ │
│  │  • Accumulation  │  │  • Transitions   │  │  • Semantic  │ │
│  │  • Merging       │  │  • Loop-back     │  │  • Metadata  │ │
│  │  • Validation    │  │                  │  │  • Rules     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Catalog Loader  │  │  LLM Client      │  │  Prompts     │ │
│  │                  │  │                  │  │              │ │
│  │  • 50+ items     │  │  • Gemini        │  │  • System    │ │
│  │  • Full metadata │  │  • OpenRouter    │  │  • Templates │ │
│  │  • Validation    │  │  • Groq          │  │  • Formatting│ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Diagram

```
┌─────────────┐
│ User Query  │
│ "Need grad  │
│  assessment"│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 1. CONSTRAINT EXTRACTION                │
│                                         │
│  Extract from ALL messages:             │
│  • job_levels: ["Graduate"]             │
│  • skills: []                           │
│  • max_duration: None                   │
│  • remote_testing: None                 │
│  • test_types: []                       │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 2. STATE DETERMINATION                  │
│                                         │
│  Analyze conversation:                  │
│  • Off-topic? → REFUSAL                 │
│  • Comparison? → COMPARISON             │
│  • Refinement? → REFINEMENT             │
│  • Sufficient context? → RECOMMENDATION │
│  • Else → CLARIFICATION                 │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 3. HYBRID RETRIEVAL                     │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ STEP 1: Hard Filtering          │   │
│  │ • duration <= max_duration      │   │
│  │ • remote_testing == required    │   │
│  │ • job_level in target_levels    │   │
│  │ • test_type in preferred_types  │   │
│  │ Result: 30 assessments          │   │
│  └─────────────────────────────────┘   │
│           │                             │
│           ▼                             │
│  ┌─────────────────────────────────┐   │
│  │ STEP 2: Semantic Scoring        │   │
│  │ • Compute embeddings            │   │
│  │ • Cosine similarity             │   │
│  │ Result: Scores 0.0-1.0          │   │
│  └─────────────────────────────────┘   │
│           │                             │
│           ▼                             │
│  ┌─────────────────────────────────┐   │
│  │ STEP 3: Rule-Based Boosting     │   │
│  │ • Role match: +0.25             │   │
│  │ • Level match: +0.20            │   │
│  │ • Skill overlap: +0.15          │   │
│  │ • Duration match: +0.10         │   │
│  │ • Test type match: +0.10        │   │
│  └─────────────────────────────────┘   │
│           │                             │
│           ▼                             │
│  ┌─────────────────────────────────┐   │
│  │ STEP 4: Diversity Enforcement   │   │
│  │ • Mix test types (A, P, B, C)   │   │
│  │ • Mix categories                │   │
│  │ • Avoid repetition              │   │
│  │ Result: Top 10 diverse items    │   │
│  └─────────────────────────────────┘   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 4. LLM RESPONSE GENERATION              │
│                                         │
│  • Format assessments for prompt        │
│  • Add constraint context               │
│  • Generate explanation                 │
│  • Validate output                      │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 5. STRUCTURED RESPONSE                  │
│                                         │
│  {                                      │
│    "response": "Based on your needs...",│
│    "state": "recommendation",           │
│    "assessments": [                     │
│      {                                  │
│        "id": "shl-graduate-battery",    │
│        "name": "Graduate Battery",      │
│        "job_levels": ["Graduate"],      │
│        "duration_minutes": 60,          │
│        "test_types": ["A", "P"],        │
│        ...                              │
│      }                                  │
│    ]                                    │
│  }                                      │
└─────────────────────────────────────────┘
```

---

## Constraint Accumulation Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Conversation Turn 1                        │
│                                                               │
│  User: "Need graduate assessment"                            │
│                                                               │
│  Constraints: {                                              │
│    job_levels: ["Graduate"]                                  │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Conversation Turn 2                        │
│                                                               │
│  User: "Under 30 minutes"                                    │
│                                                               │
│  New Constraints: {                                          │
│    max_duration: 30                                          │
│  }                                                           │
│                                                               │
│  MERGE ↓                                                     │
│                                                               │
│  Accumulated Constraints: {                                  │
│    job_levels: ["Graduate"],                                 │
│    max_duration: 30                                          │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Conversation Turn 3                        │
│                                                               │
│  User: "Also needs to be remote"                             │
│                                                               │
│  New Constraints: {                                          │
│    remote_testing: True                                      │
│  }                                                           │
│                                                               │
│  MERGE ↓                                                     │
│                                                               │
│  Accumulated Constraints: {                                  │
│    job_levels: ["Graduate"],                                 │
│    max_duration: 30,                                         │
│    remote_testing: True                                      │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## State Machine Diagram

```
                    ┌─────────────────┐
                    │     START       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ INSUFFICIENT    │
                    │   CONTEXT       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
              ┌────▶│ CLARIFICATION   │◀────┐
              │     └────────┬────────┘     │
              │              │               │
              │              ▼               │
              │     ┌─────────────────┐     │
              │     │ RECOMMENDATION  │     │
              │     └────────┬────────┘     │
              │              │               │
              │              ▼               │
              │     ┌─────────────────┐     │
              └─────│  REFINEMENT     │─────┘
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   COMPARISON    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      END        │
                    └─────────────────┘

                    ┌─────────────────┐
         (anytime)  │    REFUSAL      │
                    │  (off-topic)    │
                    └─────────────────┘
```

---

## Hybrid Retrieval Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      HYBRID RETRIEVAL                            │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SEMANTIC BRANCH                             │   │
│  │                                                           │   │
│  │  Query → Embedding → Cosine Similarity → Scores         │   │
│  │                                                           │   │
│  │  "graduate software engineer"                            │   │
│  │         ↓                                                 │   │
│  │  [0.23, 0.45, 0.89, 0.12, ...]                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              METADATA BRANCH                             │   │
│  │                                                           │   │
│  │  Constraints → Hard Filters → Filtered Set              │   │
│  │                                                           │   │
│  │  {job_levels: ["Graduate"],                             │   │
│  │   max_duration: 30,                                      │   │
│  │   remote_testing: True}                                  │   │
│  │         ↓                                                 │   │
│  │  [Assessment1, Assessment5, Assessment12, ...]          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              RULE-BASED BRANCH                           │   │
│  │                                                           │   │
│  │  Assessment × Constraints → Boost Scores                │   │
│  │                                                           │   │
│  │  • Role keyword match: +0.25                             │   │
│  │  • Job level match: +0.20                                │   │
│  │  • Skill overlap: +0.15                                  │   │
│  │  • Duration match: +0.10                                 │   │
│  │  • Test type match: +0.10                                │   │
│  │         ↓                                                 │   │
│  │  [+0.45, +0.20, +0.35, +0.10, ...]                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              COMBINATION & RANKING                       │   │
│  │                                                           │   │
│  │  Final Score = Semantic Score + Boost Score             │   │
│  │                                                           │   │
│  │  [1.34, 0.65, 1.24, 0.22, ...]                          │   │
│  │         ↓                                                 │   │
│  │  Sort by score                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              DIVERSITY ENFORCEMENT                       │   │
│  │                                                           │   │
│  │  • Prefer diverse test types (A, P, B, C, S, K)         │   │
│  │  • Prefer diverse categories                             │   │
│  │  • Avoid repetition                                      │   │
│  │         ↓                                                 │   │
│  │  Top 10 diverse, relevant assessments                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        Assessment                                │
├─────────────────────────────────────────────────────────────────┤
│  id: str                                                         │
│  name: str                                                       │
│  description: str                                                │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Job Targeting                                            │   │
│  │ • job_levels: List[str]                                  │   │
│  │   ["Graduate", "Entry", "Mid-Professional", ...]        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Technical Specs                                          │   │
│  │ • duration_minutes: int                                  │   │
│  │ • remote_testing: bool                                   │   │
│  │ • adaptive_irt: bool                                     │   │
│  │ • languages: List[str]                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Classification                                           │   │
│  │ • test_types: List[str]  # A, P, B, C, S, K             │   │
│  │ • categories: List[str]                                  │   │
│  │ • skills: List[str]                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  url: str                                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  ConversationConstraints                         │
├─────────────────────────────────────────────────────────────────┤
│  role: Optional[str]                                             │
│  job_levels: List[str]                                           │
│  skills: List[str]                                               │
│  max_duration: Optional[int]                                     │
│  min_duration: Optional[int]                                     │
│  remote_testing: Optional[bool]                                  │
│  adaptive_required: Optional[bool]                               │
│  languages: List[str]                                            │
│  test_types: List[str]                                           │
│  categories: List[str]                                           │
│  exclude_ids: List[str]                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Router     │────▶│   State      │────▶│  Constraint  │
│              │     │   Machine    │     │  Extractor   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                           │
       │                                           │
       ▼                                           ▼
┌──────────────┐                          ┌──────────────┐
│   Hybrid     │◀─────────────────────────│  Catalog     │
│   Retriever  │                          │  Loader      │
└──────────────┘                          └──────────────┘
       │
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   Prompts    │────▶│   LLM        │
│              │     │   Client     │
└──────────────┘     └──────────────┘
       │
       │
       ▼
┌──────────────┐
│   Response   │
│   Formatter  │
└──────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  FastAPI    │  │  FastAPI    │  │  FastAPI    │
│  Instance 1 │  │  Instance 2 │  │  Instance 3 │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   Shared Components           │
         │                               │
         │  • Catalog (in-memory)        │
         │  • Embeddings (cached)        │
         │  • LLM Client (pooled)        │
         └───────────────────────────────┘
```

**Key Points**:
- Stateless design enables horizontal scaling
- Each instance has full catalog in memory
- Embeddings computed once at startup
- LLM calls are async and non-blocking

---

This architecture demonstrates:
- ✅ Separation of concerns
- ✅ Modular design
- ✅ Scalability
- ✅ Maintainability
- ✅ Testability
