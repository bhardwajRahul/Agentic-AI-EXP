import kuzu
from pathlib import Path
import json
from sentence_transformers import SentenceTransformer
import asyncio
import sys

root = Path(__file__).parent.parent
sys.path.append(str(root))

from config.settings import KNOWLEDGE_GRAPH_DB
from utils.helper import setup_logger

logger = setup_logger(__name__)


class KnowledgeGraph:
    def __init__(self, db_path: str = KNOWLEDGE_GRAPH_DB):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = kuzu.Database(str(self.path))
        self.conn = kuzu.Connection(self.db)
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        asyncio.run(self._create_generic_schema())

    async def _create_generic_schema(self):
        try:
            # Check if the Entity table exists
            try:
                self.conn.execute("MATCH (n:Entity) RETURN n LIMIT 1")
                logger.info("Entity table already exists.")
            except Exception:
                # If the table does not exist, create it
                self.conn.execute("""
                    CREATE NODE TABLE Entity(
                        id STRING, 
                        type STRING, 
                        description STRING, 
                        embedding FLOAT[384], 
                        PRIMARY KEY(id)
                    )
                """)
                logger.info("Entity table created successfully.")

            # Ensure the embedding index exists
            try:
                self.conn.execute(
                    "CALL db.create_vector_index('Entity', 'embedding', 'cosine')"
                )
                logger.info("Vector index on 'embedding' created successfully.")
            except Exception as e:
                logger.info(f"Error creating vector index: {e}")

            # Check if the RELATED_TO table exists
            try:
                self.conn.execute("MATCH ()-[r:RELATED_TO]->() RETURN r LIMIT 1")
                logger.info("RELATED_TO table already exists.")
            except Exception:
                # If the table does not exist, create it
                self.conn.execute("""
                    CREATE REL TABLE RELATED_TO(
                        FROM Entity TO Entity, 
                        rel_type STRING, 
                        confidence DOUBLE
                    )
                """)
                logger.info("RELATED_TO table created successfully.")
        except Exception as e:
            logger.info(f"Error creating schema: {e}")

    def execute_query(self, query: str):
        try:
            return self.conn.execute(query)
        except Exception as e:
            logger.info(f"Error executing query: {e}")
            return None

    def clear_database(self):
        try:
            self.conn.execute("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared successfully.")
        except Exception as e:
            logger.info(f"Error clearing database: {e}")

    async def _compute_embedding(self, text: str):
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.info(f"Error computing embedding: {e}")
            return None

    def close(self):
        self.conn.close()

    async def add_node(self, node_id: str, node_type: str, description: str):
        try:
            existing_node_query = f"MATCH (n:Entity) WHERE n.id = '{node_id}' RETURN n"
            result = self.execute_query(existing_node_query)
            if result and result.has_next():
                logger.info(
                    f"Node with id '{node_id}' already exists. Skipping insertion."
                )
                return

            embedding = self.model.encode(description).tolist()
            query = f"""
            CREATE (:Entity {{
                id: '{node_id}', 
                type: '{node_type}', 
                description: '{description}', 
                embedding: {embedding}
            }})
            """
            self.execute_query(query)
            logger.info(f"Node '{node_id}' added successfully.")
        except Exception as e:
            logger.info(f"Error adding node: {e}")

    async def add_relationship(
        self, source: str, target: str, rel_type: str, confidence: float = 1.0
    ):
        try:
            query = f"""
            MATCH (a:Entity), (b:Entity)
            WHERE a.id = '{source}' AND b.id = '{target}'
            CREATE (a)-[:RELATED_TO {{ rel_type: '{rel_type}', confidence: {confidence} }}]->(b)
            """
            self.execute_query(query)
        except Exception as e:
            logger.info(f"Error adding relationship: {e}")
            return

    async def find_similar_nodes(self, description: str, top_k: int = 5):
        try:
            query_embedding = await self._compute_embedding(description)

            query = f"CALL query_vector_index('Entity', 'embedding', {query_embedding}, {top_k}) YIELD node, score RETURN node.id, node.type, score"

            result = self.conn.execute(query)
            matched = []
            while result.has_next():
                row = result.get_next()
                matched.append({"id": row[0], "type": row[1], "score": row[2]})
            return matched
        except Exception as e:
            logger.info(f"Error finding similar nodes: {e}")
            return []

    async def traverse_graph(
        self, start_node: str, depth_down: int = 4, depth_up: int = 2
    ):
        try:
            query = f"""
            MATCH path=(n)-[r*..{depth_down}]->(m)
            WHERE n.id = '{start_node}'
            RETURN path
            UNION
            MATCH path=(n)<-[r*..{depth_up}]-(m)
            WHERE n.id = '{start_node}'
            RETURN path
            """
            result = self.execute_query(query)

            paths = []
            while result.has_next():
                row = result.get_next()
                path = row[0]
                processed_path = []
                for segment in path:
                    start_node = {
                        k: v for k, v in segment.start_node.items() if k != "embedding"
                    }
                    relationship = {
                        "type": segment.type,
                        "properties": segment.get("properties", {}),
                    }
                    end_node = {
                        k: v for k, v in segment.end_node.items() if k != "embedding"
                    }
                    processed_path.append(
                        {
                            "start_node": start_node,
                            "relationship": relationship,
                            "end_node": end_node,
                        }
                    )
                paths.append(processed_path)

            return paths
        except Exception as e:
            logger.info(f"Error traversing graph: {e}")
            return None

    async def find_similar_nodes_with_context(
        self, description: str, top_k: int = 5, depth_down: int = 4, depth_up: int = 2
    ):
        try:
            query_embedding = await self._compute_embedding(description)

            query = f"CALL query_vector_index('Entity', 'embedding', {query_embedding}, {top_k}) YIELD node, score RETURN node.id, node.type, score"
            result = self.conn.execute(query)

            matched_nodes = []
            while result.has_next():
                row = result.get_next()
                matched_nodes.append({"id": row[0], "type": row[1], "score": row[2]})

            context = []
            for node in matched_nodes:
                node_id = node["id"]
                subgraph = await self.traverse_graph(node_id, depth_down, depth_up)
                context.append({"node": node, "subgraph": subgraph})

            return context

        except Exception as e:
            logger.info(f"Error in semantic search with context expansion: {e}")
            return []

    async def preprocess_graph(self):
        try:
            query = (
                "MATCH (n:Entity) WHERE n.embedding IS NULL RETURN n.id, n.description"
            )
            result = self.conn.execute(query)

            while result.has_next():
                row = result.get_next()
                node_id, description = row[0], row[1]
                embedding = await self._compute_embedding(description)
                update_query = f"MATCH (n:Entity) WHERE n.id = '{node_id}' SET n.embedding = {embedding}"
                self.execute_query(update_query)

            logger.info("Graph preprocessing complete: All nodes have embeddings.")
        except Exception as e:
            logger.info(f"Error during graph preprocessing: {e}")

    def generate_prompt(self, question: str, context: list):
        context_str = "\n".join(
            [
                f"Node: {c['node']}, Subgraph: {json.dumps(c['subgraph'], indent=2)}"
                for c in context
            ]
        )
        prompt = f"""
        You are an AI assistant. Answer the following question based on the provided graph data.

        Question: {question}

        Graph Data:
        {context_str}

        Answer:
        """
        return prompt
