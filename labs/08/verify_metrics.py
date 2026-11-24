import math
import sys
from pathlib import Path

# Подключаем модуль baseline из ЛР 7
LAB7_SRC = Path(__file__).resolve().parent.parent / "07" / "src"
sys.path.insert(0, str(LAB7_SRC))

from baseline_search import RAW_CATALOG, TfidfBaselineRetriever, evaluate_query  # noqa: E402


def manual_ndcg_at_3(actual_grades: list[int], ideal_grades: list[int] = [2, 1, 1]) -> float:
    """Эталонный ручной расчёт NDCG@3 с экспоненциальным gain (2^rel - 1)."""
    idcg = sum(((2 ** g) - 1) / math.log2(i + 2) for i, g in enumerate(ideal_grades[:3]))
    dcg = sum(((2 ** g) - 1) / math.log2(i + 2) for i, g in enumerate(actual_grades[:3]))
    return round(dcg / idcg, 4) if idcg > 0 else 0.0


def run_verification() -> None:
    print("=== 1. Проверка ручного расчёта NDCG@3 (manual_calculation.md) ===")
    print(f"Идеальный список [2, 1, 1] -> NDCG@3 = {manual_ndcg_at_3([2, 1, 1]):.4f} (ожидается 1.0000)")
    print(f"Неполный список  [2]       -> NDCG@3 = {manual_ndcg_at_3([2]):.4f} (ожидается 0.7262)")
    print(f"Инверсия ранга   [1, 2, 1] -> NDCG@3 = {manual_ndcg_at_3([1, 2, 1]):.4f} (ожидается 0.8213)")
    print(f"Пустая выдача    []        -> NDCG@3 = {manual_ndcg_at_3([]):.4f} (ожидается 0.0000)")

    # Инициализация модели из ЛР 7
    train_docs = [d for d in RAW_CATALOG if d["split"] == "train"]
    val_docs = [d for d in RAW_CATALOG if d["split"] == "validation"]

    retriever = TfidfBaselineRetriever()
    retriever.fit(train_docs)
    retriever.index_documents(val_docs)

    print("\n=== 2. Сверка с кодом ЛР 7 на запросе Q-03 ===")
    hits_q03 = retriever.search("тревожный оркестровый саундтрек", top_k=3)
    res_q03 = evaluate_query(hits_q03, val_docs, "cinematic", "dark", k=3)
    assert res_q03["ndcg_at_k"] == manual_ndcg_at_3([2]), "Расхождение в расчёте Q-03!"
    print(f"Q-03 выдача={hits_q03}, NDCG@3={res_q03['ndcg_at_k']} -> СОВПАДАЕТ")

    print("\n=== 3. Специальные тесты (из error_taxonomy.md) ===")
    hits_en = retriever.search("dark ambient synth", top_k=3)
    assert hits_en == []
    print(f"Тест 'Другой язык' ('dark ambient synth'): hits={hits_en} -> OK")

    assert retriever.search("", top_k=3) == []
    assert retriever.search("   ", top_k=3) == []
    print("Тест 'Неверный ввод' (пустая строка / пробелы): hits=[] -> OK")

    hits_meta = retriever.search("PR_GAMMA validation", top_k=3)
    assert hits_meta == []
    print(f"Тест 'Изоляция служебных полей' ('PR_GAMMA validation'): hits={hits_meta} -> OK")


if __name__ == "__main__":
    run_verification()