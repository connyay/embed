"""Clustering evaluation - test if embeddings cluster coherently by topic."""

import numpy as np
from dataclasses import dataclass
from typing import List
from sklearn.metrics import silhouette_score

from ..client import EmbedClient


@dataclass
class Cluster:
    name: str
    texts: List[str]


@dataclass
class ClusteringResult:
    model: str
    silhouette: float
    cluster_sizes: List[int]


def evaluate_clustering(
    client: EmbedClient,
    clusters: List[Cluster],
    model: str,
) -> ClusteringResult:
    """Run clustering evaluation for a specific model.

    Args:
        client: Embed client
        clusters: List of clusters with their texts
        model: Model name to test

    Returns:
        ClusteringResult with silhouette score
    """
    all_texts = []
    labels = []
    cluster_sizes = []

    for i, cluster in enumerate(clusters):
        all_texts.extend(cluster.texts)
        labels.extend([i] * len(cluster.texts))
        cluster_sizes.append(len(cluster.texts))

    embeddings = client.embed(all_texts, model)

    # Silhouette ranges from -1 to 1, higher is better
    silhouette = silhouette_score(embeddings, labels)

    return ClusteringResult(
        model=model,
        silhouette=float(silhouette),
        cluster_sizes=cluster_sizes,
    )


def parse_clustering_suite(data: dict) -> List[Cluster]:
    """Parse a clustering test suite from YAML data."""
    return [
        Cluster(name=c["name"], texts=c["texts"])
        for c in data.get("clusters", [])
    ]
