from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


MODEL_NAME = "all-MiniLM-L6-v2"

_model = SentenceTransformer(MODEL_NAME)


def calculate_semantic_similarity(
    resume_text: str,
    job_description: str,
) -> dict:
    """
    Calculate semantic similarity between a resume
    and a job description using sentence embeddings.
    """

    if not resume_text or not job_description:
        return {
            "semantic_score": 0.0,
            "similarity": 0.0,
        }

    embeddings = _model.encode(
        [
            resume_text,
            job_description,
        ],
        normalize_embeddings=True,
    )

    similarity = cosine_similarity(
        [embeddings[0]],
        [embeddings[1]],
    )[0][0]

    similarity = float(similarity)

    return {
        "semantic_score": round(similarity * 100, 2),
        "similarity": round(similarity, 4),
    }

def calculate_batch_semantic_similarity(
    resume_texts: list[str],
    job_description: str,
) -> list[dict]:
    """
    Calculate semantic similarity between multiple resumes
    and one job description using a single batch embedding call.
    """

    if not resume_texts or not job_description:
        return [
            {
                "semantic_score": 0.0,
                "similarity": 0.0,
            }
            for _ in resume_texts
        ]

    texts = resume_texts + [job_description]

    embeddings = _model.encode(
        texts,
        normalize_embeddings=True,
    )

    job_embedding = embeddings[-1]

    resume_embeddings = embeddings[:-1]

    similarities = resume_embeddings @ job_embedding

    return [
        {
            "semantic_score": round(
                float(similarity) * 100,
                2,
            ),
            "similarity": round(
                float(similarity),
                4,
            ),
        }
        for similarity in similarities
    ]