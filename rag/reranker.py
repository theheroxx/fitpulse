"""
FitStat RAG - Production Reranker

Pipeline:

    ChromaDB candidates
            ↓
    Semantic relevance
            ↓
    Query concept matching
            ↓
    Exact phrase matching
            ↓
    Keyword / lexical relevance
            ↓
    Title / metadata relevance
            ↓
    Intent compatibility
            ↓
    Collection prior
            ↓
    Risk / safety relevance
            ↓
    Diversity / deduplication
            ↓
    Final ranking

Designed for:
- ChromaDB
- SentenceTransformer embeddings
- Medical / exercise / nutrition RAG
- Existing FitStat retriever
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import math
import re

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_TOP_K = 5

DEFAULT_WEIGHTS = {
    "semantic": 0.34,
    "concept": 0.24,
    "keyword": 0.12,
    "phrase": 0.08,
    "metadata": 0.10,
    "intent": 0.07,
    "collection": 0.03,
    "risk": 0.02,
}


# ============================================================================
# INTENT / COLLECTION CONFIGURATION
# ============================================================================

INTENT_COLLECTION_PRIOR = {
    "medical": {
        "medical": 1.00,
        "exercises": 0.55,
        "nutrition": 0.20,
    },

    "exercises": {
        "exercises": 1.00,
        "medical": 0.45,
        "nutrition": 0.20,
    },

    "nutrition": {
        "nutrition": 1.00,
        "exercises": 0.35,
        "medical": 0.30,
    },
}


# ============================================================================
# QUERY CONCEPTS
# ============================================================================

CONCEPT_GROUPS = {

    # ------------------------------------------------------------------------
    # Exercise
    # ------------------------------------------------------------------------

    "exercise": {
        "exercise",
        "workout",
        "training",
        "activity",
        "fitness",
        "physical",
        "sport",
    },

    "cardio": {
        "cardio",
        "aerobic",
        "running",
        "jogging",
        "cycling",
        "walking",
        "endurance",
        "stamina",
        "vo2max",
        "vo2",
        "cardiovascular",
    },

    "strength": {
        "strength",
        "resistance",
        "weights",
        "lifting",
        "squats",
        "lunges",
        "pushups",
        "push",
    },

    "flexibility": {
        "flexibility",
        "stretching",
        "yoga",
        "mobility",
    },

    # ------------------------------------------------------------------------
    # Medical
    # ------------------------------------------------------------------------

    "asthma": {
        "asthma",
        "asthmatic",
        "bronchoconstriction",
        "inhaler",
        "wheezing",
        "airway",
    },

    "heart": {
        "heart",
        "cardiac",
        "cardiovascular",
        "blood",
        "pressure",
        "hypertension",
    },

    "diabetes": {
        "diabetes",
        "glucose",
        "insulin",
        "blood sugar",
        "hypoglycemia",
    },

    "respiratory": {
        "respiratory",
        "lung",
        "lungs",
        "breathing",
        "airway",
        "oxygen",
    },

    "environment": {
        "pollution",
        "polluted",
        "air quality",
        "aqi",
        "smog",
        "environment",
        "cold",
        "heat",
    },

    # ------------------------------------------------------------------------
    # Nutrition
    # ------------------------------------------------------------------------

    "nutrition": {
        "food",
        "eat",
        "meal",
        "diet",
        "nutrition",
        "protein",
        "calorie",
        "calories",
        "carbs",
        "carbohydrate",
        "fat",
        "vitamin",
        "mineral",
        "breakfast",
        "lunch",
        "dinner",
        "snack",
    },

    # ------------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------------

    "performance": {
        "improve",
        "increase",
        "maximize",
        "maximise",
        "boost",
        "improving",
        "better",
        "performance",
    },

    "endurance": {
        "endurance",
        "stamina",
        "aerobic",
        "cardio",
        "fitness",
        "vo2max",
        "vo2",
    },

    "safety": {
        "safe",
        "safety",
        "risk",
        "danger",
        "dangerous",
        "avoid",
        "precaution",
        "warning",
        "symptom",
        "symptoms",
    },
}


# ============================================================================
# INTENT KEYWORDS
# ============================================================================

INTENT_KEYWORDS = {

    "medical": {
        "medical",
        "health",
        "condition",
        "disease",
        "symptom",
        "asthma",
        "heart",
        "diabetes",
        "blood",
        "respiratory",
        "inhaler",
        "medication",
    },

    "exercises": {
        "exercise",
        "workout",
        "training",
        "fitness",
        "activity",
        "cardio",
        "running",
        "walking",
        "cycling",
        "strength",
        "aerobic",
        "endurance",
        "vo2max",
    },

    "nutrition": {
        "food",
        "eat",
        "meal",
        "protein",
        "calorie",
        "diet",
        "nutrition",
        "carbs",
        "fat",
        "vitamin",
        "mineral",
        "breakfast",
        "lunch",
        "dinner",
        "snack",
    },
}


# ============================================================================
# TEXT UTILITIES
# ============================================================================

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "to",
    "of",
    "for",
    "and",
    "or",
    "in",
    "on",
    "with",
    "about",
    "how",
    "what",
    "should",
    "can",
    "i",
    "my",
    "me",
    "someone",
    "does",
    "do",
    "be",
    "know",
}


def normalize_text(text: Any) -> str:

    if text is None:
        return ""

    text = str(text).lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = re.sub(r"[^\w\s]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text: Any) -> List[str]:

    normalized = normalize_text(text)

    if not normalized:
        return []

    return [
        token
        for token in normalized.split()
        if token not in STOPWORDS
    ]


def token_set(text: Any) -> set:

    return set(tokenize(text))


# ============================================================================
# STEM-LIKE NORMALIZATION
# ============================================================================

def simple_word_variants(word: str) -> set:

    word = normalize_text(word)

    if not word:
        return set()

    variants = {word}

    if len(word) > 4:

        if word.endswith("ing"):
            variants.add(word[:-3])

        if word.endswith("ed"):
            variants.add(word[:-2])

        if word.endswith("s"):
            variants.add(word[:-1])

    return variants


# ============================================================================
# QUERY CONCEPT DETECTION
# ============================================================================

def detect_query_concepts(query: str) -> List[str]:

    query_normalized = normalize_text(query)
    query_tokens = token_set(query)

    concepts = []

    for concept, keywords in CONCEPT_GROUPS.items():

        matched = False

        for keyword in keywords:

            keyword_normalized = normalize_text(keyword)

            # Multi-word phrase
            if " " in keyword_normalized:

                if keyword_normalized in query_normalized:
                    matched = True
                    break

            else:

                if keyword_normalized in query_tokens:
                    matched = True
                    break

                # variant matching
                for token in query_tokens:

                    if (
                        keyword_normalized in simple_word_variants(token)
                        or token in simple_word_variants(keyword_normalized)
                    ):
                        matched = True
                        break

                if matched:
                    break

        if matched:
            concepts.append(concept)

    return concepts


# ============================================================================
# SEMANTIC SCORE
# ============================================================================

def normalize_semantic_distances(
    distances: List[Optional[float]],
) -> List[float]:

    """
    Normalize Chroma distances relative to the current candidate set.

    IMPORTANT:

    Do NOT use:

        1 / (1 + distance)

    because Chroma distances in this system are approximately:

        100 - 400

    which compresses everything toward zero.

    Instead, use relative ranking inside the candidate batch.
    """

    valid = []

    for distance in distances:

        try:

            value = float(distance)

            if math.isnan(value) or math.isinf(value):
                continue

            valid.append(value)

        except (TypeError, ValueError):
            continue

    if not valid:
        return [0.0] * len(distances)

    min_distance = min(valid)
    max_distance = max(valid)

    if max_distance <= min_distance:
        return [
            1.0 if distance is not None else 0.0
            for distance in distances
        ]

    scores = []

    for distance in distances:

        try:

            value = float(distance)

            if math.isnan(value) or math.isinf(value):
                scores.append(0.0)
                continue

            normalized = (
                (value - min_distance)
                / (max_distance - min_distance)
            )

            score = 1.0 - normalized

            scores.append(
                max(0.0, min(1.0, score))
            )

        except (TypeError, ValueError):

            scores.append(0.0)

    return scores


# ============================================================================
# LEXICAL SCORE
# ============================================================================

def keyword_score(
    query: str,
    document: str,
) -> float:

    query_tokens = token_set(query)
    document_tokens = token_set(document)

    if not query_tokens or not document_tokens:
        return 0.0

    overlap = query_tokens.intersection(
        document_tokens
    )

    return min(
        len(overlap) / len(query_tokens),
        1.0,
    )


# ============================================================================
# PHRASE SCORE
# ============================================================================

def phrase_score(
    query: str,
    document: str,
) -> float:

    query_normalized = normalize_text(query)
    document_normalized = normalize_text(document)

    if not query_normalized or not document_normalized:
        return 0.0

    score = 0.0

    # Full query match
    if query_normalized in document_normalized:
        score = 1.0

    # Important query phrases
    query_tokens = tokenize(query)

    if len(query_tokens) >= 2:

        for size in [3, 2]:

            if len(query_tokens) < size:
                continue

            for i in range(
                len(query_tokens) - size + 1
            ):

                phrase = " ".join(
                    query_tokens[i:i + size]
                )

                if phrase in document_normalized:
                    score = max(
                        score,
                        min(
                            1.0,
                            0.45 + 0.15 * size,
                        ),
                    )

    return score


# ============================================================================
# CONCEPT SCORE
# ============================================================================

def concept_score(
    query: str,
    document: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> float:

    concepts = detect_query_concepts(query)

    if not concepts:
        return 0.0

    document_text = normalize_text(document)

    metadata_text = ""

    if metadata:

        metadata_text = normalize_text(
            " ".join(
                str(value)
                for value in metadata.values()
                if value is not None
            )
        )

    total_weight = 0.0
    matched_weight = 0.0

    # Specific concepts are more important
    concept_weights = {

        "asthma": 2.5,
        "heart": 2.5,
        "diabetes": 2.5,
        "respiratory": 2.2,

        "environment": 1.8,

        "vo2max": 2.5,
        "endurance": 2.0,
        "cardio": 1.6,

        "nutrition": 2.0,

        "exercise": 1.0,
        "strength": 1.0,
        "flexibility": 0.8,

        "performance": 1.0,
        "safety": 1.5,
    }

    for concept in concepts:

        weight = concept_weights.get(
            concept,
            1.0,
        )

        total_weight += weight

        keywords = CONCEPT_GROUPS.get(
            concept,
            set(),
        )

        matched = False

        for keyword in keywords:

            normalized_keyword = normalize_text(
                keyword
            )

            if (
                normalized_keyword in document_text
                or normalized_keyword in metadata_text
            ):
                matched = True
                break

        if matched:
            matched_weight += weight

    if total_weight == 0:
        return 0.0

    return min(
        matched_weight / total_weight,
        1.0,
    )


# ============================================================================
# METADATA SCORE
# ============================================================================

def metadata_score(
    query: str,
    metadata: Optional[Dict[str, Any]],
) -> float:

    if not metadata:
        return 0.0

    query_normalized = normalize_text(query)

    query_tokens = token_set(query)

    if not query_tokens:
        return 0.0

    title = normalize_text(
        metadata.get("title", "")
    )

    name = normalize_text(
        metadata.get("name", "")
    )

    category = normalize_text(
        metadata.get("category", "")
    )

    source = normalize_text(
        metadata.get("source", "")
    )

    # ------------------------------------------------------------
    # Title gets the highest importance.
    # ------------------------------------------------------------

    title_tokens = token_set(title)

    title_overlap = 0.0

    if title_tokens:

        title_overlap = (
            len(
                query_tokens.intersection(
                    title_tokens
                )
            )
            / len(query_tokens)
        )

    # Exact phrase in title
    if (
        title
        and title in query_normalized
    ):
        title_overlap = 1.0

    # ------------------------------------------------------------
    # Name
    # ------------------------------------------------------------

    name_tokens = token_set(name)

    name_overlap = 0.0

    if name_tokens:

        name_overlap = (
            len(
                query_tokens.intersection(
                    name_tokens
                )
            )
            / len(query_tokens)
        )

    # ------------------------------------------------------------
    # Category
    # ------------------------------------------------------------

    category_tokens = token_set(category)

    category_overlap = 0.0

    if category_tokens:

        category_overlap = (
            len(
                query_tokens.intersection(
                    category_tokens
                )
            )
            / len(query_tokens)
        )

    # ------------------------------------------------------------
    # Source
    # ------------------------------------------------------------

    source_tokens = token_set(source)

    source_overlap = 0.0

    if source_tokens:

        source_overlap = (
            len(
                query_tokens.intersection(
                    source_tokens
                )
            )
            / len(query_tokens)
        )

    score = (
        0.60 * title_overlap
        + 0.20 * name_overlap
        + 0.15 * category_overlap
        + 0.05 * source_overlap
    )

    return min(
        score,
        1.0,
    )


# ============================================================================
# INTENT SCORE
# ============================================================================

def intent_score(
    document: str,
    intent: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> float:

    intent = normalize_text(intent)

    if intent not in INTENT_KEYWORDS:
        return 0.0

    document_text = normalize_text(document)

    metadata_text = ""

    if metadata:

        metadata_text = normalize_text(
            " ".join(
                str(value)
                for value in metadata.values()
                if value is not None
            )
        )

    combined = (
        document_text
        + " "
        + metadata_text
    )

    keywords = INTENT_KEYWORDS[intent]

    if not keywords:
        return 0.0

    matches = 0

    for keyword in keywords:

        if normalize_text(keyword) in combined:
            matches += 1

    # Do not allow generic words to dominate.
    return min(
        matches / 4.0,
        1.0,
    )


# ============================================================================
# COLLECTION PRIOR
# ============================================================================

def collection_score(
    collection: str,
    intent: str,
) -> float:

    intent = normalize_text(intent)
    collection = normalize_text(collection)

    return (
        INTENT_COLLECTION_PRIOR
        .get(intent, {})
        .get(collection, 0.0)
    )


# ============================================================================
# RISK / SAFETY SCORE
# ============================================================================

SAFETY_TERMS = {
    "risk",
    "danger",
    "dangerous",
    "avoid",
    "warning",
    "symptom",
    "symptoms",
    "precaution",
    "precautions",
    "stop",
    "medical",
    "safety",
    "safe",
}


def risk_score(
    query: str,
    document: str,
) -> float:

    query_tokens = token_set(query)
    document_tokens = token_set(document)

    if not query_tokens:
        return 0.0

    query_safety = (
        query_tokens.intersection(
            SAFETY_TERMS
        )
    )

    if not query_safety:
        return 0.0

    document_safety = (
        document_tokens.intersection(
            SAFETY_TERMS
        )
    )

    if not document_safety:
        return 0.0

    return min(
        len(document_safety)
        / max(len(query_safety), 1),
        1.0,
    )


# ============================================================================
# QUERY-SPECIFIC BOOST
# ============================================================================

def specific_query_boost(
    query: str,
    document: str,
    metadata: Optional[Dict[str, Any]],
) -> float:

    """
    Gives strong boosts for highly specific concepts.

    Example:

        Query:
            What should someone with asthma know about exercise?

        Document:
            Asthma and Exercise

    This should receive a large boost.

    A generic:
            Heart Disease and Physical Activity

    should not.
    """

    concepts = detect_query_concepts(query)

    if not concepts:
        return 0.0

    title = ""

    if metadata:
        title = normalize_text(
            metadata.get("title", "")
        )

    document_text = normalize_text(document)

    score = 0.0

    specific_concepts = {
        "asthma": 0.40,
        "heart": 0.35,
        "diabetes": 0.35,
        "respiratory": 0.30,
        "vo2max": 0.40,
        "environment": 0.25,
    }

    for concept in concepts:

        keywords = CONCEPT_GROUPS.get(
            concept,
            set(),
        )

        weight = specific_concepts.get(
            concept,
            0.10,
        )

        concept_found = False

        for keyword in keywords:

            keyword_normalized = normalize_text(
                keyword
            )

            if (
                keyword_normalized in title
            ):
                score += weight
                concept_found = True
                break

            if (
                keyword_normalized in document_text
            ):
                score += weight * 0.65
                concept_found = True
                break

        if concept_found:
            continue

    return min(
        score,
        1.0,
    )


# ============================================================================
# SINGLE DOCUMENT SCORE
# ============================================================================

def calculate_document_score(
    query: str,
    document: str,
    distance: Optional[float] = None,
    intent: str = "exercises",
    metadata: Optional[Dict[str, Any]] = None,
    collection: str = "",
    semantic_score_override: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:

    if weights is None:
        weights = DEFAULT_WEIGHTS

    semantic = (
        semantic_score_override
        if semantic_score_override is not None
        else 0.0
    )

    keyword = keyword_score(
        query,
        document,
    )

    phrase = phrase_score(
        query,
        document,
    )

    concept = concept_score(
        query,
        document,
        metadata,
    )

    metadata_value = metadata_score(
        query,
        metadata,
    )

    intent_value = intent_score(
        document,
        intent,
        metadata,
    )

    collection_value = collection_score(
        collection,
        intent,
    )

    risk_value = risk_score(
        query,
        document,
    )

    specific_boost = specific_query_boost(
        query,
        document,
        metadata,
    )

    base_score = (
        weights["semantic"]
        * semantic

        + weights["concept"]
        * concept

        + weights["keyword"]
        * keyword

        + weights["phrase"]
        * phrase

        + weights["metadata"]
        * metadata_value

        + weights["intent"]
        * intent_value

        + weights["collection"]
        * collection_value

        + weights["risk"]
        * risk_value
    )

    # Specific concept boost is deliberately additive.
    final_score = (
        base_score
        + 0.20 * specific_boost
    )

    final_score = max(
        0.0,
        min(
            final_score,
            1.0,
        ),
    )

    return {

        "score": round(
            final_score,
            6,
        ),

        "semantic": round(
            semantic,
            6,
        ),

        "concept": round(
            concept,
            6,
        ),

        "keyword": round(
            keyword,
            6,
        ),

        "phrase": round(
            phrase,
            6,
        ),

        "metadata": round(
            metadata_value,
            6,
        ),

        "intent": round(
            intent_value,
            6,
        ),

        "collection": round(
            collection_value,
            6,
        ),

        "risk": round(
            risk_value,
            6,
        ),

        "specific_boost": round(
            specific_boost,
            6,
        ),
    }


# ============================================================================
# DIVERSITY / DUPLICATE HANDLING
# ============================================================================

def document_similarity(
    doc_a: str,
    doc_b: str,
) -> float:

    tokens_a = token_set(doc_a)
    tokens_b = token_set(doc_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(
        tokens_a.intersection(tokens_b)
    )

    union = len(
        tokens_a.union(tokens_b)
    )

    if union == 0:
        return 0.0

    return intersection / union


def remove_near_duplicates(
    candidates: List[Dict[str, Any]],
    threshold: float = 0.90,
) -> List[Dict[str, Any]]:

    selected = []

    for candidate in candidates:

        document = candidate.get(
            "document",
            "",
        )

        duplicate = False

        for existing in selected:

            similarity = document_similarity(
                document,
                existing.get(
                    "document",
                    "",
                ),
            )

            if similarity >= threshold:

                duplicate = True
                break

        if not duplicate:
            selected.append(candidate)

    return selected


# ============================================================================
# RAW CHROMADB RERANKING
# ============================================================================

def rerank_results(
    results: Dict[str, Any],
    query: str,
    intent: str = "exercises",
    top_k: int = DEFAULT_TOP_K,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:

    if not results:
        return []

    candidates = []

    # ========================================================================
    # First collect everything
    # ========================================================================

    for collection_name, collection_result in results.items():

        if not isinstance(
            collection_result,
            dict,
        ):
            continue

        documents = collection_result.get(
            "documents",
            [[]],
        )

        metadatas = collection_result.get(
            "metadatas",
            [[]],
        )

        distances = collection_result.get(
            "distances",
            [[]],
        )

        # ------------------------------------------------------------
        # Extract nested Chroma lists
        # ------------------------------------------------------------

        if (
            isinstance(documents, list)
            and documents
            and isinstance(documents[0], list)
        ):
            docs = documents[0]
        else:
            docs = []

        if (
            isinstance(metadatas, list)
            and metadatas
            and isinstance(metadatas[0], list)
        ):
            metadata_list = metadatas[0]
        else:
            metadata_list = []

        if (
            isinstance(distances, list)
            and distances
            and isinstance(distances[0], list)
        ):
            distance_list = distances[0]
        else:
            distance_list = []

        for index, document in enumerate(docs):

            if not isinstance(
                document,
                str,
            ):
                continue

            if not document.strip():
                continue

            metadata = {}

            if (
                index < len(metadata_list)
                and isinstance(
                    metadata_list[index],
                    dict,
                )
            ):
                metadata = metadata_list[index]

            distance = None

            if index < len(distance_list):
                distance = distance_list[index]

            candidates.append({
                "document": document,
                "collection": collection_name,
                "metadata": metadata,
                "distance": distance,
                "_index": index,
            })

    if not candidates:
        return []

    # ========================================================================
    # Normalize semantic distances ACROSS ALL collections
    # ========================================================================

    all_distances = [
        candidate.get("distance")
        for candidate in candidates
    ]

    semantic_scores = normalize_semantic_distances(
        all_distances
    )

    # ========================================================================
    # Calculate scores
    # ========================================================================

    for index, candidate in enumerate(
        candidates
    ):

        score_details = calculate_document_score(

            query=query,

            document=candidate["document"],

            distance=candidate.get(
                "distance"
            ),

            intent=intent,

            metadata=candidate.get(
                "metadata",
                {},
            ),

            collection=candidate.get(
                "collection",
                "",
            ),

            semantic_score_override=(
                semantic_scores[index]
            ),

            weights=weights,
        )

        candidate["score"] = score_details[
            "score"
        ]

        candidate["scores"] = score_details

    # ========================================================================
    # Sort
    # ========================================================================

    candidates.sort(
        key=lambda item: item.get(
            "score",
            0.0,
        ),
        reverse=True,
    )

    # ========================================================================
    # Remove exact duplicates
    # ========================================================================

    unique = []

    seen = set()

    for candidate in candidates:

        normalized = normalize_text(
            candidate["document"]
        )

        if normalized in seen:
            continue

        seen.add(normalized)

        unique.append(candidate)

    # ========================================================================
    # Remove near duplicates
    # ========================================================================

    unique = remove_near_duplicates(
        unique,
        threshold=0.93,
    )

    # ========================================================================
    # Return Top K
    # ========================================================================

    return unique[:top_k]


# ============================================================================
# DOCUMENT-ONLY FALLBACK
# ============================================================================

def rerank_documents(
    documents: List[str],
    query: str,
    intent: str = "exercises",
    top_k: int = DEFAULT_TOP_K,
) -> List[str]:

    if not documents:
        return []

    candidates = []

    for document in documents:

        if not isinstance(
            document,
            str,
        ):
            continue

        if not document.strip():
            continue

        scores = calculate_document_score(
            query=query,
            document=document,
            distance=None,
            intent=intent,
            metadata=None,
            collection=intent,
            semantic_score_override=0.0,
        )

        candidates.append({
            "document": document,
            "score": scores["score"],
            "scores": scores,
        })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        item["document"]
        for item in candidates[:top_k]
    ]


# ============================================================================
# CONTEXT RERANKING
# ============================================================================

def rerank_context(
    context: Dict[str, Any],
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:

    if not context:
        return context

    intent = context.get(
        "intent",
        "exercises",
    )

    raw_results = context.get(
        "raw_results",
        {},
    )

    # ========================================================================
    # Preferred path
    # ========================================================================

    if raw_results:

        ranked = rerank_results(
            results=raw_results,
            query=query,
            intent=intent,
            top_k=top_k,
        )

        documents = [
            item["document"]
            for item in ranked
        ]

        context["documents"] = [
            documents
        ]

        context[
            "reranked_results"
        ] = ranked

        context[
            "reranking_enabled"
        ] = True

        context[
            "final_count"
        ] = len(documents)

        context[
            "candidate_count"
        ] = sum(
            len(
                result.get(
                    "documents",
                    [[]],
                )[0]
            )
            if (
                isinstance(
                    result,
                    dict,
                )
                and isinstance(
                    result.get(
                        "documents",
                        [[]],
                    ),
                    list,
                )
                and result.get(
                    "documents",
                    [[]],
                )
                and isinstance(
                    result.get(
                        "documents",
                        [[]],
                    )[0],
                    list,
                )
            )
            else 0
            for result in raw_results.values()
            if isinstance(
                result,
                dict,
            )
        )

        return context

    # ========================================================================
    # Fallback
    # ========================================================================

    documents = context.get(
        "documents",
        [[]],
    )

    if (
        isinstance(documents, list)
        and documents
        and isinstance(documents[0], list)
    ):

        ranked_documents = rerank_documents(
            documents=documents[0],
            query=query,
            intent=intent,
            top_k=top_k,
        )

        context["documents"] = [
            ranked_documents
        ]

        context["final_count"] = len(
            ranked_documents
        )

    else:

        context["documents"] = [[]]
        context["final_count"] = 0

    context[
        "reranked_results"
    ] = []

    context[
        "reranking_enabled"
    ] = True

    return context


# ============================================================================
# DEBUG / EXPLANATION
# ============================================================================

def explain_ranking(
    context: Dict[str, Any],
) -> List[Dict[str, Any]]:

    ranked = context.get(
        "reranked_results",
        [],
    )

    explanations = []

    for rank, item in enumerate(
        ranked,
        1,
    ):

        scores = item.get(
            "scores",
            {},
        )

        explanations.append({

            "rank": rank,

            "collection": item.get(
                "collection"
            ),

            "score": item.get(
                "score"
            ),

            "distance": item.get(
                "distance"
            ),

            "semantic_score": scores.get(
                "semantic",
                0.0,
            ),

            "concept_score": scores.get(
                "concept",
                0.0,
            ),

            "keyword_score": scores.get(
                "keyword",
                0.0,
            ),

            "phrase_score": scores.get(
                "phrase",
                0.0,
            ),

            "metadata_score": scores.get(
                "metadata",
                0.0,
            ),

            "intent_score": scores.get(
                "intent",
                0.0,
            ),

            "collection_score": scores.get(
                "collection",
                0.0,
            ),

            "risk_score": scores.get(
                "risk",
                0.0,
            ),

            "specific_boost": scores.get(
                "specific_boost",
                0.0,
            ),

            "document": item.get(
                "document",
                "",
            ),
        })

    return explanations