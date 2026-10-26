import re
from dataclasses import dataclass
from pathlib import Path

from app.models import Citation

TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    content: str


class LocalRetriever:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []
        for file in sorted(self.path.glob("*.md")):
            content = file.read_text(encoding="utf-8")
            first_line = content.splitlines()[0].lstrip("# ").strip()
            documents.append(
                KnowledgeDocument(
                    document_id=file.stem,
                    title=first_line or file.stem.replace("-", " ").title(),
                    content=content,
                )
            )
        return documents

    def search(self, query: str, limit: int = 3) -> list[Citation]:
        query_tokens = set(TOKEN_PATTERN.findall(query.lower()))
        ranked: list[tuple[int, KnowledgeDocument]] = []
        for document in self.load():
            document_tokens = set(TOKEN_PATTERN.findall(document.content.lower()))
            ranked.append((len(query_tokens & document_tokens), document))
        ranked.sort(key=lambda item: (-item[0], item[1].document_id))

        citations: list[Citation] = []
        for score, document in ranked[:limit]:
            if score == 0:
                continue
            sentences = [
                line.strip("- ").strip()
                for line in document.content.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            quote = max(
                sentences,
                key=lambda sentence: len(
                    query_tokens & set(TOKEN_PATTERN.findall(sentence.lower()))
                ),
                default=document.content[:240],
            )
            citations.append(
                Citation(
                    document_id=document.document_id,
                    title=document.title,
                    quote=quote[:400],
                )
            )
        return citations

