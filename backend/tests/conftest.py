"""I test non chiamano OpenAI né il database: l'app usa il motore finto di tests/stub_rag.py.

Il backend vero non ha più un motore finto: si sostituisce qui, prima che i test avviino l'app.
"""

import app.main
from tests.stub_rag import StubRag

app.main.create_engine = lambda settings, catalog: StubRag(catalog)
