"""
Test retrieval quality using evaluation metrics.
Measures precision@k, recall, constraint satisfaction, and diversity.
"""
from app.catalog_loader import CatalogLoader
from app.hybrid_retrieval import HybridRetriever
from app.constraints import ConversationConstraints
from app.evaluation_metrics import RetrievalMetrics, EVALUATION_TEST_CASES


def test_retrieval_quality():
    """
    Test retrieval quality with evaluation metrics.
    
    IMPORTANT: This is an INTERNAL evaluation framework, not an academic benchmark.
    - Small test set (3 cases)
    - Handpicked relevance labels
    - No human evaluation
    
    Use for: internal quality tracking, regression testing, demo purposes.
    """
    print("=" * 70)
    print("INTERNAL RETRIEVAL QUALITY EVALUATION")
    print("=" * 70)
    print("\n⚠️  NOTE: Internal evaluation framework (not academic benchmark)")
    print("   - Small test set for engineering validation")
    print("   - Handpicked relevance labels")
    print("   - Use for quality tracking and regression testing\n")
    
    # Initialize components
    catalog_loader = CatalogLoader()
    retriever = HybridRetriever(catalog_loader.get_all_assessments())
    metrics = RetrievalMetrics()
    
    print(f"\nCatalog size: {catalog_loader.get_catalog_size()} assessments")
    print(f"Test cases: {len(EVALUATION_TEST_CASES)}\n")
    
    all_results = []
    
    for i, test_case in enumerate(EVALUATION_TEST_CASES, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST CASE {i}: {test_case['query']}")
        print(f"{'=' * 70}")
        
        # Build constraints
        constraints = ConversationConstraints()
        if "job_levels" in test_case["constraints"]:
            constraints.job_levels = test_case["constraints"]["job_levels"]
        if "max_duration" in test_case["constraints"]:
            constraints.max_duration = test_case["constraints"]["max_duration"]
        if "test_types" in test_case["constraints"]:
            constraints.test_types = test_case["constraints"]["test_types"]
        if "skills" in test_case["constraints"]:
            constraints.skills = test_case["constraints"]["skills"]
        
        # Retrieve
        retrieved = retriever.retrieve(
            query=test_case["query"],
            constraints=constraints,
            top_k=10
        )
        
        print(f"\nRetrieved: {len(retrieved)} assessments")
        print(f"Expected relevant: {len(test_case['relevant_ids'])} assessments")
        
        # Show top 3
        print("\nTop 3 Results:")
        for j, assessment in enumerate(retrieved[:3], 1):
            is_relevant = "✓" if assessment.id in test_case["relevant_ids"] else "✗"
            print(f"  {j}. {is_relevant} {assessment.name}")
            print(f"     Job Levels: {', '.join(assessment.job_levels)}")
            print(f"     Test Types: {', '.join(assessment.test_types)}")
            print(f"     Duration: {assessment.duration_minutes} mins")
        
        # Calculate metrics
        result = metrics.evaluate_retrieval(
            retrieved=retrieved,
            relevant_ids=test_case["relevant_ids"],
            constraints=constraints,
            k=3
        )
        
        print("\n📊 Metrics:")
        print(f"  Precision@3:            {result['precision@3']:.2%}")
        print(f"  Precision@5:            {result['precision@5']:.2%}")
        print(f"  Recall@10:              {result['recall@10']:.2%}")
        print(f"  MRR:                    {result['mrr']:.3f}")
        print(f"  Constraint Satisfaction: {result['constraint_satisfaction']:.2%}")
        print(f"  Diversity:              {result['diversity']:.2%}")
        
        all_results.append(result)
    
    # Aggregate results
    print(f"\n{'=' * 70}")
    print("AGGREGATE RESULTS")
    print(f"{'=' * 70}")
    
    avg_precision_3 = sum(r['precision@3'] for r in all_results) / len(all_results)
    avg_precision_5 = sum(r['precision@5'] for r in all_results) / len(all_results)
    avg_recall = sum(r['recall@10'] for r in all_results) / len(all_results)
    avg_mrr = sum(r['mrr'] for r in all_results) / len(all_results)
    avg_constraint = sum(r['constraint_satisfaction'] for r in all_results) / len(all_results)
    avg_diversity = sum(r['diversity'] for r in all_results) / len(all_results)
    
    print(f"\nAverage Precision@3:            {avg_precision_3:.2%}")
    print(f"Average Precision@5:            {avg_precision_5:.2%}")
    print(f"Average Recall@10:              {avg_recall:.2%}")
    print(f"Average MRR:                    {avg_mrr:.3f}")
    print(f"Average Constraint Satisfaction: {avg_constraint:.2%}")
    print(f"Average Diversity:              {avg_diversity:.2%}")
    
    # Quality assessment
    print(f"\n{'=' * 70}")
    print("QUALITY ASSESSMENT")
    print(f"{'=' * 70}")
    
    quality_score = (
        avg_precision_3 * 0.3 +
        avg_recall * 0.2 +
        avg_mrr * 0.2 +
        avg_constraint * 0.2 +
        avg_diversity * 0.1
    )
    
    print(f"\nOverall Quality Score: {quality_score:.2%} (Internal Metric)")
    
    if quality_score >= 0.80:
        grade = "EXCELLENT ✅ (for internal tracking)"
    elif quality_score >= 0.70:
        grade = "GOOD ✓ (for internal tracking)"
    elif quality_score >= 0.60:
        grade = "ACCEPTABLE ⚠ (for internal tracking)"
    else:
        grade = "NEEDS IMPROVEMENT ❌"
    
    print(f"Grade: {grade}")
    print(f"\n⚠️  Remember: This is an internal evaluation framework")
    print(f"   NOT a scientifically rigorous benchmark")
    
    # Recommendations
    print(f"\n{'=' * 70}")
    print("RECOMMENDATIONS")
    print(f"{'=' * 70}")
    
    if avg_precision_3 < 0.70:
        print("⚠ Precision@3 is low - consider tuning ranking weights")
    else:
        print("✓ Precision@3 is good")
    
    if avg_constraint < 0.80:
        print("⚠ Constraint satisfaction is low - check filtering logic")
    else:
        print("✓ Constraint satisfaction is good")
    
    if avg_diversity < 0.50:
        print("⚠ Diversity is low - results may be too similar")
    else:
        print("✓ Diversity is good")
    
    if avg_mrr < 0.70:
        print("⚠ MRR is low - most relevant items not ranking first")
    else:
        print("✓ MRR is good - relevant items ranking high")
    
    print(f"\n{'=' * 70}")
    print("✅ EVALUATION COMPLETE")
    print(f"{'=' * 70}\n")
    
    return quality_score >= 0.60


if __name__ == "__main__":
    success = test_retrieval_quality()
    exit(0 if success else 1)
