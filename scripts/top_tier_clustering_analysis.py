import json
import math
from pathlib import Path

INPUT = Path("data/forecasts_ranked.json")
OUTPUT = Path("data/top_tier_clusters.json")
GAP_THRESHOLD = 2.0


def cluster_rows(rows):
    clusters = []
    current = [rows[0]]
    for row in rows[1:]:
        gap = current[-1]["priority_score"] - row["priority_score"]
        if gap < GAP_THRESHOLD:
            current.append(row)
        else:
            clusters.append(current)
            current = [row]
    clusters.append(current)
    return clusters


def main():
    rows = json.loads(INPUT.read_text(encoding="utf-8"))
    top_n = max(1, math.ceil(len(rows) * 0.10))
    top_rows = rows[:top_n]
    clusters = cluster_rows(top_rows) if top_rows else []
    summaries = []
    for index, cluster in enumerate(clusters, start=1):
        scores = [float(row["priority_score"]) for row in cluster]
        confidences = [float(row.get("decision_confidence", 0.0)) for row in cluster]
        recs = {}
        for row in cluster:
            recs[row["recommendation"]] = recs.get(row["recommendation"], 0) + 1
        summaries.append(
            {
                "cluster_id": index,
                "cluster_size": len(cluster),
                "score_range": [min(scores), max(scores)],
                "average_confidence": round(sum(confidences) / len(confidences), 4),
                "recommendation_distribution": recs,
                "item_ids": [row["item_id"] for row in cluster],
            }
        )
    largest = max((cluster["cluster_size"] for cluster in summaries), default=0)
    result = {
        "top_item_count": top_n,
        "gap_threshold": GAP_THRESHOLD,
        "number_of_clusters": len(summaries),
        "largest_cluster_size": largest,
        "cluster_fragility_score": round(largest / top_n, 4) if top_n else 0.0,
        "clusters": summaries,
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote top-tier clustering analysis to {OUTPUT}")
    print(f"Top items analyzed: {top_n}")
    print(f"Clusters: {result['number_of_clusters']}")
    print(f"Largest cluster size: {result['largest_cluster_size']}")
    print(f"Cluster fragility score: {result['cluster_fragility_score']:.2%}")


if __name__ == "__main__":
    main()
