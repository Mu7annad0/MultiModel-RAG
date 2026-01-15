import logging
from typing import Any
from pydantic import BaseModel
from qdrant_client import QdrantClient, models


class QrantVectorDB:
    def __init__(self, db_dir: str):
        self.db_dir = db_dir
        self.client = None
        self.logger = logging.getLogger("uvicorn")
        
    def connect(self):
        try:
            self.client = QdrantClient(path=self.db_dir)
            self.logger.info(f"Connected to Qdrant at {self.db_dir}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise
    
    def disconnect(self):
        self.client = None
    
    def is_collection_exists(self, collection_name: str) -> bool:
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False
    
    def list_collections(self) -> list[str]:
        try:
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
        except Exception as e:
            self.logger.error(f"Error listing collections: {str(e)}")
            return []
    
    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        try:
            return self.client.get_collection(collection_name)
        except Exception as e:
            self.logger.error(f"Error getting collection info: {str(e)}")
            return None
    
    def delete_collection(self, collection_name: str) -> bool:
        try:
            if not self.is_collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} does not exist, nothing to delete")
                return True
            self.client.delete_collection(collection_name)
            self.logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting collection {collection_name}: {str(e)}")
            return False
    
    def create_collection(self, collection_name: str, vector_size: int, do_reset: bool = False) -> bool:
        try:
            self.logger.info(f"Creating collection: {collection_name} with vector size: {vector_size}")
            
            if do_reset:
                self.logger.info(f"Reset flag is True, deleting existing collection if exists")
                self.delete_collection(collection_name)
            
            if self.is_collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} already exists")
                return True
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            self.logger.info(f"Successfully created collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating collection {collection_name}: {str(e)}", exc_info=True)
            return False
    
    def insert(self, collection_name: str, texts: list, vectors: list, metadata: list = None, ids: list = None, batch_size: int = 50) -> bool:
        try:
            self.logger.info(f"Inserting {len(texts)} documents into collection: {collection_name}")
            
            if metadata is None:
                metadata = [{}] * len(texts)
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in range(len(texts))]

            for i in range(0, len(texts), batch_size):
                batch_end = min(i + batch_size, len(texts))
                batch_texts = texts[i:batch_end]
                batch_vectors = vectors[i:batch_end]
                batch_metadata = metadata[i:batch_end]
                batch_ids = ids[i:batch_end]

                batch_records = [
                    models.PointStruct(
                        id=batch_ids[x],
                        vector=batch_vectors[x],
                        payload={
                            "text": batch_texts[x],
                            "metadata": batch_metadata[x] if batch_metadata and x < len(batch_metadata) else {}
                        }
                    )
                    for x in range(len(batch_texts))
                ]

                try:
                    self.client.upsert(
                        collection_name=collection_name,
                        points=batch_records,
                    )
                    self.logger.info(f"Successfully inserted batch {i//batch_size + 1} ({len(batch_records)} documents)")
                except Exception as e:
                    self.logger.error(f"Error while inserting batch {i//batch_size + 1}: {str(e)}")
                    return False

            self.logger.info(f"Successfully inserted all {len(texts)} documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in insert: {str(e)}", exc_info=True)
            return False
    
    def search(self, collection_name: str, query_vector: list, limit: int = 5):
        if not self.is_collection_exists(collection_name):
            self.logger.error(f"Collection {collection_name} not found")
            return []
        try:
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
            )
            return [RetrievedDocument(text=r.payload.get("text", ""), score=float(r.score), metadata=r.payload.get("metadata", {})) for r in results.points]
        except Exception as e:
            self.logger.error(f"Error in search: {str(e)}", exc_info=True)
            return []


class RetrievedDocument(BaseModel):
    text: str
    score: float
    metadata: dict
