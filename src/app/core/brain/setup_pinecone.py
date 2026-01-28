import logging
from pinecone import ServerlessSpec
from .config import get_pinecone_client, get_pinecone_index_name
import time

# Configure logging
logger = logging.getLogger(__name__)

def setup_index():
    pc = get_pinecone_client()
    index_name = get_pinecone_index_name()
    
    logger.info(f"Checking Pinecone index: {index_name}...")
    
    if index_name in [idx.name for idx in pc.list_indexes()]:
        # Check if metric and dimension are correct for hybrid search with E5-Large
        desc = pc.describe_index(index_name)
        if desc.metric != 'dotproduct' or desc.dimension != 1024:
            raise ValueError(
                f"Index '{index_name}' exists but has incompatible specs: "
                f"metric='{desc.metric}' (expected 'dotproduct'), "
                f"dimension={desc.dimension} (expected 1024)."
            )
        logger.info(f"Index '{index_name}' is correctly configured.")
    else:
        logger.info(f"Creating serverless index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=1024, # Typical for multilingual-e5-large
            metric='dotproduct', # MANDATORY for hybrid search on single index
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            ),
            deletion_protection='enabled'
        )
        logger.info("Waiting for index to be ready...")
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
            
        logger.info(f"Index '{index_name}' created and ready.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    setup_index()
