import asyncio
import json

from neo4j import GraphDatabase

from tools.export.export_followers import ExportHandler, export_followers


class GraphDb:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=("neo4j", "test")
        )

    def close(self):
        self.driver.close()

    def setup(self):
        with self.driver.session() as session:
            return session.write_transaction(self._create_actor_index)

    @staticmethod
    def _create_actor_index(tx):
        tx.run("CREATE INDEX actor_uri_index_1 IF NOT EXISTS FOR (a:Actor) ON (a.uri)")

    def insert_actor(self, uri, name):
        with self.driver.session() as session:
            return session.write_transaction(self._create_actor, uri, name)

    @staticmethod
    def _create_actor(tx, uri, name):
        result = tx.run(
            "MERGE (a:Actor {uri: $uri}) SET a.name = $name RETURN id(a)",
            uri=uri,
            name=name,
        )
        return result.single()[0]

    def insert_actor_uri(self, uri):
        with self.driver.session() as session:
            return session.write_transaction(self._merge_actor, uri)

    @staticmethod
    def _merge_actor(tx, uri):
        result = tx.run(
            "MERGE (a:Actor {uri: $uri}) RETURN id(a)",
            uri=uri,
        )
        return result.single()[0]

    def insert_follower(self, follower, follows):
        with self.driver.session() as session:
            return session.write_transaction(
                self._create_follower_rel, follower, follows
            )

    @staticmethod
    def _create_follower_rel(tx, follower, follows):
        result = tx.run(
            "MATCH (a:Actor), (b:Actor) WHERE a.uri = $follower AND b.uri = $follows "
            "CREATE (a)-[r:Follows]->(b) RETURN type(r)",
            follower=follower,
            follows=follows,
        )
        return result.single()


class GraphDbHandler(ExportHandler):
    def __init__(self):
        self.graph_db = GraphDb()
        self.graph_db.setup()

    async def new_actor(self, uri: str, data: dict, aux: str):
        actor_aux = json.loads(aux)
        name = (
            None
            if actor_aux.get("webfinger", None) is None
            else actor_aux["webfinger"].split("acct:")[-1]
        )
        self.graph_db.insert_actor(uri, name)

    async def follows(self, actor: str, follows: str):
        self.graph_db.insert_actor_uri(follows)
        self.graph_db.insert_follower(actor, follows)


async def main():
    handler = GraphDbHandler()
    await export_followers(handler)


if __name__ == "__main__":
    asyncio.run(main())
