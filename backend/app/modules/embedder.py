import logging
import torch
from sentence_transformers import SentenceTransformer
from app.core.settings import settings

logger = logging.getLogger(__name__)


class Embedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        logger.info("Loading %s on %s...", settings.embedding_model, self.device)
        self.model = SentenceTransformer(settings.embedding_model, device=self.device)
        logger.info("%s loaded.", settings.embedding_model)

    def embed(self, text: str):
        """Embeds a single string and returns a flat list of 1024 floats."""
        output = self.model.encode(text, normalize_embeddings=False)
        return output.tolist()

    def embed_batch(self, texts: list[str]):
        """Embeds a batch of strings."""
        outputs = self.model.encode(texts, normalize_embeddings=False)
        return outputs.tolist()


embedder = Embedder()
