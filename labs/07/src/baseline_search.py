import argparse
import csv
import hashlib
import json
import math
import platform
import re
import sys
from collections import Counter
from pathlib import Path

# Конфигурация эксперимента
CONFIG = {
    "dataset_version": "1.0-audio-assets",
    "random_seed": 42,  # Сохранен для будущих стохастических моделей; baseline детерминирован
    "top_k": 3,
    "feature_field": "description",
    "idf_formula": "log((1 + N) / (1 + df)) + 1",
    "tie_breaker": "track_id_asc",
}

# Собственный предметный датасет: 45 аудио-ассетов (5 категорий x 3 настроения x 3 продюсера)
# Train: продюсеры PR_ALPHA, PR_BETA (15 треков)
# Validation: продюсеры PR_GAMMA, PR_DELTA (15 треков)
# Test: продюсеры PR_EPSILON, PR_ZETA (15 треков)
RAW_CATALOG = [
    # --- TRAIN (15 треков) ---
    {"track_id": "TRK-001", "split": "train", "producer": "PR_ALPHA", "category": "ambient", "mood": "dark",
     "description": "глубокий аналоговый синтезатор гулкий бас мрачный космический фон без ударных"},
    {"track_id": "TRK-002", "split": "train", "producer": "PR_ALPHA", "category": "ambient", "mood": "calm",
     "description": "мягкое электропиано теплый пэд спокойный воздушный эмбиент для медитации"},
    {"track_id": "TRK-003", "split": "train", "producer": "PR_BETA", "category": "ambient", "mood": "bright",
     "description": "кристальные колокольчики светлый синтезатор легкий утренний текстурный фон"},
    {"track_id": "TRK-004", "split": "train", "producer": "PR_ALPHA", "category": "hiphop", "mood": "dark",
     "description": "тяжелый прямой бит виниловый треск мрачный семпл пианино медленный темп"},
    {"track_id": "TRK-005", "split": "train", "producer": "PR_BETA", "category": "hiphop", "mood": "calm",
     "description": "расслабленный лоуфай ритм теплый бас мягкие ударные уютный инструментал"},
    {"track_id": "TRK-006", "split": "train", "producer": "PR_BETA", "category": "hiphop", "mood": "bright",
     "description": "энергичный грув фанковая гитара звонкий малый барабан позитивный ритм"},
    {"track_id": "TRK-007", "split": "train", "producer": "PR_ALPHA", "category": "cinematic", "mood": "dark",
     "description": "напряженные виолончели низкие духовые тревожный оркестровый саундтрек"},
    {"track_id": "TRK-008", "split": "train", "producer": "PR_BETA", "category": "cinematic", "mood": "calm",
     "description": "нежная акустическая гитара камерные струнные лирическая кинотема"},
    {"track_id": "TRK-009", "split": "train", "producer": "PR_ALPHA", "category": "cinematic", "mood": "bright",
     "description": "эпический оркестр валторны торжественные струнные вдохновляющий финал"},
    {"track_id": "TRK-010", "split": "train", "producer": "PR_BETA", "category": "techno", "mood": "dark",
     "description": "индустриальный прямой ритм кислотный синтезатор жесткий клубный бас"},
    {"track_id": "TRK-011", "split": "train", "producer": "PR_ALPHA", "category": "techno", "mood": "calm",
     "description": "гипнотический пульс минималистичный синтезатор ровный глубокий грув"},
    {"track_id": "TRK-012", "split": "train", "producer": "PR_BETA", "category": "techno", "mood": "bright",
     "description": "мелодичный арпеджиатор быстрый темп светлые клавишные танцевальный трек"},
    {"track_id": "TRK-013", "split": "train", "producer": "PR_ALPHA", "category": "folk", "mood": "dark",
     "description": "низкий резонанс акустической гитары минорный перебор суровая баллада"},
    {"track_id": "TRK-014", "split": "train", "producer": "PR_BETA", "category": "folk", "mood": "calm",
     "description": "теплая классическая гитара тихая перкуссия спокойная лесная мелодия"},
    {"track_id": "TRK-015", "split": "train", "producer": "PR_ALPHA", "category": "folk", "mood": "bright",
     "description": "звонкое банджо быстрый акустический ритм радостная дорожная тема"},

    # --- VALIDATION (15 треков) ---
    {"track_id": "TRK-016", "split": "validation", "producer": "PR_GAMMA", "category": "ambient", "mood": "dark",
     "description": "мрачный синтезатор гулкий космический бас темный атмосферный дрон"},
    {"track_id": "TRK-017", "split": "validation", "producer": "PR_DELTA", "category": "ambient", "mood": "calm",
     "description": "спокойный эмбиент мягкое электропиано воздушный пэд для фонового видео"},
    {"track_id": "TRK-018", "split": "validation", "producer": "PR_GAMMA", "category": "ambient", "mood": "bright",
     "description": "светлый синтезатор звонкие колокольчики прозрачный утренний фон"},
    {"track_id": "TRK-019", "split": "validation", "producer": "PR_DELTA", "category": "hiphop", "mood": "dark",
     "description": "мрачный бит тяжелый виниловый бас медленный андеграунд ритм"},
    {"track_id": "TRK-020", "split": "validation", "producer": "PR_GAMMA", "category": "hiphop", "mood": "calm",
     "description": "расслабленный лоуфай бит мягкие ударные теплый виниловый треск"},
    {"track_id": "TRK-021", "split": "validation", "producer": "PR_DELTA", "category": "hiphop", "mood": "bright",
     "description": "позитивный грув фанковая гитара энергичный бит для влога"},
    {"track_id": "TRK-022", "split": "validation", "producer": "PR_GAMMA", "category": "cinematic", "mood": "dark",
     "description": "тревожный оркестровый саундтрек низкие виолончели мрачный саспенс"},
    {"track_id": "TRK-023", "split": "validation", "producer": "PR_DELTA", "category": "cinematic", "mood": "calm",
     "description": "лирическая кинотема нежная акустическая гитара спокойные струнные"},
    {"track_id": "TRK-024", "split": "validation", "producer": "PR_GAMMA", "category": "cinematic", "mood": "bright",
     "description": "вдохновляющий эпический оркестр торжественные духовые и струнные"},
    {"track_id": "TRK-025", "split": "validation", "producer": "PR_DELTA", "category": "techno", "mood": "dark",
     "description": "жесткий индустриальный ритм мрачный кислотный бас клубный техно"},
    {"track_id": "TRK-026", "split": "validation", "producer": "PR_GAMMA", "category": "techno", "mood": "calm",
     "description": "минималистичный синтезатор гипнотический ровный пульс глубокий ритм"},
    {"track_id": "TRK-027", "split": "validation", "producer": "PR_DELTA", "category": "techno", "mood": "bright",
     "description": "быстрый мелодичный арпеджиатор светлые клавишные энергичный техно"},
    {"track_id": "TRK-028", "split": "validation", "producer": "PR_GAMMA", "category": "folk", "mood": "dark",
     "description": "минорный перебор акустической гитары мрачная северная баллада"},
    {"track_id": "TRK-029", "split": "validation", "producer": "PR_DELTA", "category": "folk", "mood": "calm",
     "description": "спокойная классическая гитара мягкая перкуссия теплая мелодия"},
    {"track_id": "TRK-030", "split": "validation", "producer": "PR_GAMMA", "category": "folk", "mood": "bright",
     "description": "радостная акустическая тема звонкое банджо быстрый позитивный ритм"},

    # --- TEST (15 треков, не используются при настройке) ---
    {"track_id": "TRK-031", "split": "test", "producer": "PR_EPSILON", "category": "ambient", "mood": "dark",
     "description": "темный аналоговый гул мрачный космический синтезатор"},
    {"track_id": "TRK-032", "split": "test", "producer": "PR_ZETA", "category": "ambient", "mood": "calm",
     "description": "спокойный воздушный пэд мягкое электропиано для сна"},
    {"track_id": "TRK-033", "split": "test", "producer": "PR_EPSILON", "category": "ambient", "mood": "bright",
     "description": "светлый утренний синтезатор кристальные колокольчики"},
    {"track_id": "TRK-034", "split": "test", "producer": "PR_ZETA", "category": "hiphop", "mood": "dark",
     "description": "мрачный медленный бит тяжелый бас виниловый семпл"},
    {"track_id": "TRK-035", "split": "test", "producer": "PR_EPSILON", "category": "hiphop", "mood": "calm",
     "description": "уютный лоуфай инструментал мягкие ударные теплый бас"},
    {"track_id": "TRK-036", "split": "test", "producer": "PR_ZETA", "category": "hiphop", "mood": "bright",
     "description": "энергичный позитивный грув фанковая гитара и ритм"},
    {"track_id": "TRK-037", "split": "test", "producer": "PR_EPSILON", "category": "cinematic", "mood": "dark",
     "description": "мрачный оркестровый саспенс тревожные виолончели"},
    {"track_id": "TRK-038", "split": "test", "producer": "PR_ZETA", "category": "cinematic", "mood": "calm",
     "description": "нежная кинотема акустическая гитара и камерные струнные"},
    {"track_id": "TRK-039", "split": "test", "producer": "PR_EPSILON", "category": "cinematic", "mood": "bright",
     "description": "торжественный эпический оркестр вдохновляющий финал"},
    {"track_id": "TRK-040", "split": "test", "producer": "PR_ZETA", "category": "techno", "mood": "dark",
     "description": "мрачный клубный техно жесткий индустриальный бас"},
    {"track_id": "TRK-041", "split": "test", "producer": "PR_EPSILON", "category": "techno", "mood": "calm",
     "description": "глубокий ровный пульс минималистичный синтезатор"},
    {"track_id": "TRK-042", "split": "test", "producer": "PR_ZETA", "category": "techno", "mood": "bright",
     "description": "быстрый танцевальный техно светлый арпеджиатор"},
    {"track_id": "TRK-043", "split": "test", "producer": "PR_EPSILON", "category": "folk", "mood": "dark",
     "description": "мрачная баллада низкий резонанс акустической гитары"},
    {"track_id": "TRK-044", "split": "test", "producer": "PR_ZETA", "category": "folk", "mood": "calm",
     "description": "теплая спокойная мелодия классическая гитара"},
    {"track_id": "TRK-045", "split": "test", "producer": "PR_EPSILON", "category": "folk", "mood": "bright",
     "description": "радостный быстрый ритм звонкое банджо"},
]

# Набор запросов для validation (14 запросов: 7 буквальных + 7 сленговых/синонимических)
VALIDATION_QUERIES = [
    # Буквальные запросы (используют лексику из train-словаря)
    {"query_id": "Q-01", "segment": "literal", "text": "мрачный синтезатор бас", "target_category": "ambient", "target_mood": "dark"},
    {"query_id": "Q-02", "segment": "literal", "text": "расслабленный лоуфай бит", "target_category": "hiphop", "target_mood": "calm"},
    {"query_id": "Q-03", "segment": "literal", "text": "тревожный оркестровый саундтрек", "target_category": "cinematic", "target_mood": "dark"},
    {"query_id": "Q-04", "segment": "literal", "text": "быстрый мелодичный арпеджиатор", "target_category": "techno", "target_mood": "bright"},
    {"query_id": "Q-05", "segment": "literal", "text": "звонкое банджо радостная", "target_category": "folk", "target_mood": "bright"},
    {"query_id": "Q-06", "segment": "literal", "text": "спокойный эмбиент электропиано", "target_category": "ambient", "target_mood": "calm"},
    {"query_id": "Q-07", "segment": "literal", "text": "нежная акустическая гитара кинотема", "target_category": "cinematic", "target_mood": "calm"},

    # Синонимические / сленговые запросы монтажёров (лексика отсутствует в train)
    {"query_id": "Q-08", "segment": "synonym", "text": "тягучий подклад хоррор", "target_category": "ambient", "target_mood": "dark"},
    {"query_id": "Q-09", "segment": "synonym", "text": "чилл кач релакс", "target_category": "hiphop", "target_mood": "calm"},
    {"query_id": "Q-10", "segment": "synonym", "text": "напряжение триллер симфония", "target_category": "cinematic", "target_mood": "dark"},
    {"query_id": "Q-11", "segment": "synonym", "text": "драйв танцпол синт", "target_category": "techno", "target_mood": "bright"},
    {"query_id": "Q-12", "segment": "synonym", "text": "кантри веселый перебор", "target_category": "folk", "target_mood": "bright"},
    {"query_id": "Q-13", "segment": "synonym", "text": "медитативный родес тишина", "target_category": "ambient", "target_mood": "calm"},
    {"query_id": "Q-14", "segment": "synonym", "text": "драма мелодрама пиццикато", "target_category": "cinematic", "target_mood": "calm"},
]


def tokenize(text: str) -> list[str]:
    """Приводит текст к нижнему регистру и извлекает словарные токены."""
    return re.findall(r"[а-яёa-z0-9]+", text.lower())


class TfidfBaselineRetriever:
    """Детерминированный TF-IDF + Cosine Similarity поисковик."""

    def __init__(self):
        self.idf: dict[str, float] = {}
        self.doc_vectors: dict[str, dict[str, float]] = {}
        self.catalog_index: dict[str, dict] = {}

    def fit(self, train_docs: list[dict]) -> None:
        """Вычисляет IDF исключительно на обучающей выборке (без утечки validation/test)."""
        n_docs = len(train_docs)
        df_counts: Counter[str] = Counter()
        for doc in train_docs:
            unique_tokens = set(tokenize(doc[CONFIG["feature_field"]]))
            for token in unique_tokens:
                df_counts[token] += 1

        self.idf = {
            token: math.log((1.0 + n_docs) / (1.0 + df)) + 1.0
            for token, df in df_counts.items()
        }

    def _vectorize(self, text: str) -> dict[str, float]:
        """Строит L2-нормированный TF-IDF вектор по словарю train."""
        tokens = tokenize(text)
        if not tokens:
            return {}
        tf_counts = Counter(tokens)
        raw_vec = {}
        for token, count in tf_counts.items():
            if token in self.idf:
                raw_vec[token] = float(count) * self.idf[token]

        norm = math.sqrt(sum(val * val for val in raw_vec.values()))
        if norm == 0.0:
            return {}
        return {token: val / norm for token, val in raw_vec.items()}

    def index_documents(self, docs: list[dict]) -> None:
        """Индексирует целевой набор карточек для поиска."""
        self.doc_vectors.clear()
        self.catalog_index.clear()
        for doc in docs:
            tid = doc["track_id"]
            self.catalog_index[tid] = doc
            self.doc_vectors[tid] = self._vectorize(doc[CONFIG["feature_field"]])

    def search(self, query_text: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Возвращает top_k документов с ненулевым косинусным сходством."""
        q_vec = self._vectorize(query_text)
        if not q_vec:
            return []

        scored: list[tuple[str, float]] = []
        for tid, d_vec in self.doc_vectors.items():
            if not d_vec:
                continue
            score = sum(q_val * d_vec.get(tok, 0.0) for tok, q_val in q_vec.items())
            if score > 0.0:
                scored.append((tid, round(score, 6)))

        # Стабильная сортировка: по убыванию сходства, при равенстве — по возрастанию track_id
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]


def compute_relevance_grade(doc: dict, target_cat: str, target_mood: str) -> int:
    """
    Правило экспертной оценки релевантности:
    2 — совпадают и категория (жанр), и настроение;
    1 — совпадает только категория или только настроение;
    0 — не совпадает ни категория, ни настроение.
    """
    cat_match = doc["category"] == target_cat
    mood_match = doc["mood"] == target_mood
    if cat_match and mood_match:
        return 2
    if cat_match or mood_match:
        return 1
    return 0


def evaluate_query(
    retrieved: list[tuple[str, float]],
    val_docs: list[dict],
    target_cat: str,
    target_mood: str,
    k: int = 3,
) -> dict:
    """Рассчитывает NDCG@k (экспоненциальный gain) и Recall@k (для grade == 2)."""
    doc_map = {d["track_id"]: d for d in val_docs}

    # Идеальное ранжирование в validation
    ideal_grades = sorted(
        [compute_relevance_grade(d, target_cat, target_mood) for d in val_docs],
        reverse=True,
    )[:k]
    idcg = sum(((2 ** g) - 1) / math.log2(idx + 2) for idx, g in enumerate(ideal_grades))

    # Фактическое ранжирование
    actual_grades = [
        compute_relevance_grade(doc_map[tid], target_cat, target_mood)
        for tid, _ in retrieved[:k]
    ]
    dcg = sum(((2 ** g) - 1) / math.log2(idx + 2) for idx, g in enumerate(actual_grades))
    ndcg = (dcg / idcg) if idcg > 0 else 0.0

    # Recall@k: доля найденных строго релевантных документов (grade == 2) среди всех таких в validation
    total_exact_relevant = sum(
        1 for d in val_docs if compute_relevance_grade(d, target_cat, target_mood) == 2
    )
    found_exact_relevant = sum(1 for g in actual_grades if g == 2)
    recall = (found_exact_relevant / total_exact_relevant) if total_exact_relevant > 0 else 0.0

    return {
        "ndcg_at_k": round(ndcg, 4),
        "recall_at_k": round(recall, 4),
        "grades": actual_grades,
    }


def get_config_hash() -> str:
    """Вычисляет детерминированный SHA-256 хеш конфигурации и данных."""
    payload = json.dumps({"config": CONFIG, "catalog": RAW_CATALOG}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def run_experiment(base_dir: Path) -> None:
    """Полный цикл воспроизведения: сохранение данных, обучение на train, оценка на validation."""
    data_dir = base_dir / "data"
    results_dir = base_dir / "results"
    data_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Сохранение датасета и метаданных окружения
    catalog_path = data_dir / "audio_catalog_v1.json"
    catalog_path.write_text(json.dumps(RAW_CATALOG, ensure_ascii=False, indent=2), encoding="utf-8")

    env_info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "config_hash": get_config_hash(),
        "config": CONFIG,
    }
    (results_dir / "environment.json").write_text(
        json.dumps(env_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2. Разделение выборок
    train_docs = [d for d in RAW_CATALOG if d["split"] == "train"]
    val_docs = [d for d in RAW_CATALOG if d["split"] == "validation"]

    # 3. Обучение baseline только на train и индексация validation
    retriever = TfidfBaselineRetriever()
    retriever.fit(train_docs)
    retriever.index_documents(val_docs)

    # 4. Оценка всех запросов validation
    detailed_results = []
    for q in VALIDATION_QUERIES:
        hits = retriever.search(q["text"], top_k=CONFIG["top_k"])
        metrics = evaluate_query(
            hits, val_docs, q["target_category"], q["target_mood"], k=CONFIG["top_k"]
        )
        detailed_results.append({
            "query_id": q["query_id"],
            "segment": q["segment"],
            "query": q["text"],
            "target": f"{q['target_category']} / {q['target_mood']}",
            "retrieved_ids": [tid for tid, _ in hits],
            "scores": [score for _, score in hits],
            "grades": metrics["grades"],
            "ndcg_at_3": metrics["ndcg_at_k"],
            "recall_at_3": metrics["recall_at_k"],
        })

    # 5. Агрегация метрик по сегментам
    def aggregate(rows: list[dict], name: str) -> dict:
        n = len(rows)
        mean_ndcg = round(sum(r["ndcg_at_3"] for r in rows) / n, 4) if n else 0.0
        mean_recall = round(sum(r["recall_at_3"] for r in rows) / n, 4) if n else 0.0
        return {"segment": name, "queries_count": n, "mean_ndcg_at_3": mean_ndcg, "mean_recall_at_3": mean_recall}

    summary_rows = [
        aggregate([r for r in detailed_results if r["segment"] == "literal"], "literal"),
        aggregate([r for r in detailed_results if r["segment"] == "synonym"], "synonym"),
        aggregate(detailed_results, "all"),
    ]

    # Сохранение CSV и JSON
    csv_path = results_dir / "validation_baseline.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["segment", "queries_count", "mean_ndcg_at_3", "mean_recall_at_3"])
        writer.writeheader()
        writer.writerows(summary_rows)

    (results_dir / "validation_detail.json").write_text(
        json.dumps(detailed_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Experiment completed. Config hash: {env_info['config_hash']}")
    for row in summary_rows:
        print(f"Segment={row['segment']:8s} | N={row['queries_count']:2d} | NDCG@3={row['mean_ndcg_at_3']:.4f} | Recall@3={row['mean_recall_at_3']:.4f}")


def interactive_search(query_text: str) -> None:
    """Интерактивный поиск по всему каталогу (без пересчёта метрик)."""
    train_docs = [d for d in RAW_CATALOG if d["split"] == "train"]
    retriever = TfidfBaselineRetriever()
    retriever.fit(train_docs)
    retriever.index_documents(RAW_CATALOG)

    hits = retriever.search(query_text, top_k=CONFIG["top_k"])
    print(f"Query: '{query_text}' -> Hits: {hits}")
    for tid, score in hits:
        doc = retriever.catalog_index[tid]
        print(f"  [{tid}] (split={doc['split']}, score={score}): {doc['description']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseline TF-IDF Search for Audio Assets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Reproduce dataset, run validation evaluation, save artifacts")

    search_parser = subparsers.add_parser("search", help="Run single query against full catalog")
    search_parser.add_argument("--query", type=str, required=True, help="Search query text")

    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent

    if args.command == "run":
        run_experiment(project_root)
    elif args.command == "search":
        interactive_search(args.query)