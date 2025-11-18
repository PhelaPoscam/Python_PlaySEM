import sys
import os
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

sys.path.insert(
	0,
	os.path.abspath(
		os.path.join(os.path.dirname(__file__), '../src')
	)
)
