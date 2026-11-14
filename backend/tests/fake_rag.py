"""Motori RAG finti con forme diverse, per verificare che il backend li accetti tutti."""


def answer_plain(question):
    return "Solo testo, senza fonti."


def answer_langchain(question, lang=None):
    # forma tipica di una catena LangChain: {"result": …, "source_documents": [Document…]}
    return {
        "result": f"La capacità della batteria è 25.6 Ah [1]. (lang={lang})",
        "source_documents": [
            {"page_content": "| Battery capacity | 25.6 Ah |\n| Charging time | 4.5 h |",
             "metadata": {"source": "data/manuals/BellaBot_User_Manual-multilanguage/en.md"}},
        ],
    }


async def answer_async(question, **kwargs):
    return ("Risposta asincrona [1]", ["Testo qualsiasi che non viene dai manuali, ma è comunque una fonte."])


def search(query, k=5):
    return [{"text": "| Battery capacity | 25.6 Ah |", "file": "BellaBot_User_Manual-multilanguage.pdf", "score": 0.91}]
