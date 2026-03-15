import os
import torch
from sentence_transformers import SentenceTransformer

class Embedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        # Determine device
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        print(f"Loading BGE-M3 on {self.device}...")
        self.model = SentenceTransformer("BAAI/bge-m3", device=self.device)
        print("BGE-M3 Loaded.")

    def embed(self, text: str):
        """Embeds a single string and returns a flat list of 1024 floats."""
        # BGE-M3 produces 1024D vectors
        output = self.model.encode(text, normalize_embeddings=False)
        return output.tolist()

    def embed_batch(self, texts: list[str]):
        """Embeds a batch of strings."""
        outputs = self.model.encode(texts, normalize_embeddings=False)
        return outputs.tolist()

embedder = Embedder()
