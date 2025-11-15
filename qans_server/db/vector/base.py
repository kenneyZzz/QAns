
from pymilvus import MilvusClient
from qans_server.setting_config import settings

db_client = MilvusClient(settings.vector_url)
db_client.use_database(settings.vector_db)
