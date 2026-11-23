"""Операции py-sc-client 0.4.0. Вызывается только в изолированном worker-процессе."""

import re
import time

from bs4 import BeautifulSoup
from sc_client import client
from sc_client.constants import sc_type as t
from sc_client.models import (
    ScAddr,
    ScConstruction,
    ScIdtfResolveParams,
    ScLinkContent,
    ScLinkContentType,
    ScTemplate,
)

from app.legal.search_baseline import normalize_search_term

LOCAL_PATH = re.compile(
    r"(?:file:/+[^\r\n]+|(?:/|[a-z]:[\\/]|\\\\|\.{1,2}[\\/])[^\r\n]+|"
    r"(?:[^\\/:\r\n]+[\\/])*[\w.-]+\.(?:html?|pdf|docx?|txt))",
    re.IGNORECASE,
)


def readable_definition(definitions):
    chunks = [text.strip() for _, text in definitions if text.strip()]
    text = "\n\n".join(chunk for chunk in chunks if not LOCAL_PATH.fullmatch(chunk))
    if text:
        return text, "available"
    return "", "unavailable_file_reference" if chunks else "unavailable"


def plain_text(value):
    if not isinstance(value, str):
        return ""
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup(["script", "style", "iframe"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())


class Memory:
    def __init__(self):
        self.keys = {}

    def key(self, identifier):
        if identifier not in self.keys:
            # type=None: отсутствие узла никогда не приводит к его созданию.
            self.keys[identifier] = client.resolve_keynodes(
                ScIdtfResolveParams(idtf=identifier, type=None)
            )[0]
        return self.keys[identifier]

    def search(self, template):
        return client.search_by_template(template)

    def members(self, node, target_type=t.VAR_NODE):
        template = ScTemplate()
        template.triple(node, t.VAR_PERM_POS_ARC, target_type >> "item")
        return [row.get("item") for row in self.search(template)]

    def contains(self, node, target):
        if not node or not target:
            return False
        template = ScTemplate()
        template.triple(node, t.VAR_PERM_POS_ARC, target)
        return bool(self.search(template))

    def relation(self, node, relation_name, target_type=t.VAR_NODE, reverse=False):
        relation = self.key(relation_name)
        if not relation:
            return []
        template = ScTemplate()
        if reverse:
            template.quintuple(
                target_type >> "item", t.VAR_COMMON_ARC, node, t.VAR_PERM_POS_ARC, relation
            )
        else:
            template.quintuple(
                node, t.VAR_COMMON_ARC, target_type >> "item", t.VAR_PERM_POS_ARC, relation
            )
        return [row.get("item") for row in self.search(template)]

    def content(self, link):
        result = client.get_link_content(link)
        return str(result[0].data) if result and result[0].data is not None else ""

    def texts(self, node, relation="nrel_main_idtf", russian=True):
        links = self.relation(node, relation, t.VAR_NODE_LINK)
        if russian:
            links = [link for link in links if self.contains(self.key("lang_ru"), link)]
        return [(link, plain_text(self.content(link))) for link in links]

    def system_identifier(self, node):
        identifiers = self.texts(node, "nrel_system_identifier", russian=False)
        return identifiers[0][1] if identifiers else None

    def definition(self, node):
        required = [
            self.key(k)
            for k in ("rrel_key_sc_element", "nrel_sc_text_translation", "rrel_example", "lang_ru")
        ]
        if not all(required):
            return []
        key, translation, example, language = required
        template = ScTemplate()
        template.quintuple(
            t.VAR_NODE >> "structure", t.VAR_PERM_POS_ARC, node, t.VAR_PERM_POS_ARC, key
        )
        template.quintuple(
            t.VAR_NODE >> "translation",
            t.VAR_COMMON_ARC,
            "structure",
            t.VAR_PERM_POS_ARC,
            translation,
        )
        template.quintuple(
            "translation",
            t.VAR_PERM_POS_ARC,
            t.VAR_NODE_LINK >> "text",
            t.VAR_PERM_POS_ARC,
            example,
        )
        template.triple(language, t.VAR_PERM_POS_ARC, "text")
        return [
            (row.get("text"), plain_text(self.content(row.get("text"))))
            for row in self.search(template)
        ]

    def legal(self, node):
        if any(
            self.contains(self.key(k), node)
            for k in ("belarus_legal_term", "belarus_legal_article", "belarus_legal_act")
        ):
            return True
        # Статьи/акты исходной KB не всегда имеют явное членство в классе.
        return bool(
            self.relation(node, "nrel_article", reverse=True) or self.relation(node, "nrel_article")
        )

    def source(self, node):
        if not node or not self.legal(node):
            return None
        titles = self.texts(node)
        definitions = self.definition(node)
        identifier = self.system_identifier(node)
        if not titles:
            return None
        text, text_status = readable_definition(definitions)
        related = []
        for relation in (
            "nrel_related_article",
            "nrel_related_articles",
            "nrel_article",
            "nrel_related_concept",
            "nrel_related_concepts",
        ):
            for target in self.relation(node, relation)[:12]:
                target_id = self.system_identifier(target)
                target_titles = self.texts(target)
                related.append(
                    {
                        "sc_identifier": target_id,
                        "sc_address": target.value,
                        "title": target_titles[0][1] if target_titles else target_id,
                        "relation": relation,
                    }
                )
        origins = []
        for target in self.relation(node, "nrel_article", reverse=True)[:4]:
            names = self.texts(target)
            origins.append(
                {
                    "sc_identifier": self.system_identifier(target),
                    "sc_address": target.value,
                    "title": names[0][1] if names else None,
                }
            )
        return {
            "source_system": "ostis",
            "sc_identifier": identifier,
            "sc_address": node.value,
            "id": identifier or f"addr:{node.value}",
            "title": titles[0][1],
            "excerpt": text[:1600],
            "text": text,
            "text_status": text_status,
            "source_exists": True,
            "source_relevant": None,
            "legal_applicability": None,
            "source_document": origins or None,
            "revision": None,
            "currency": "Редакция и актуальность правового текста не подтверждены.",
            "related": related,
            "provenance": {
                "title_links": [a.value for a, _ in titles],
                "text_links": [a.value for a, _ in definitions],
            },
        }

    def resolve_source(self, identifier):
        if re.fullmatch(r"addr:[1-9][0-9]{0,18}", identifier):
            node = ScAddr(int(identifier[5:]))
            if not client.get_elements_types(node)[0].is_node():
                return None
        elif re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,200}", identifier):
            node = self.key(identifier)
        else:
            return None
        return self.source(node)

    def concepts(self, term, *, exact_only=False):
        legal_class, main_id, language = (
            self.key(k) for k in ("belarus_legal_term", "nrel_main_idtf", "lang_ru")
        )
        if not all((legal_class, main_id, language)):
            raise RuntimeError("Отсутствует онтология юридических терминов.")
        links = client.search_links_by_contents(term)[0]
        if not links and not exact_only:
            links = client.search_links_by_contents_substrings(term)[0]
        nodes = {}
        for link in links[:24]:
            template = ScTemplate()
            template.quintuple(
                t.VAR_NODE >> "node", t.VAR_COMMON_ARC, link, t.VAR_PERM_POS_ARC, main_id
            )
            template.triple(legal_class, t.VAR_PERM_POS_ARC, "node")
            template.triple(language, t.VAR_PERM_POS_ARC, link)
            for row in self.search(template):
                node = row.get("node")
                nodes[node.value] = node
        return list(nodes.values())[:8]

    def vocabulary(self):
        """Названия понятий из текущей SC-памяти для привязки запроса LLM."""
        legal_class = self.key("belarus_legal_term")
        if not legal_class:
            raise RuntimeError("Отсутствует онтология юридических терминов.")
        terms = set()
        nodes = self.members(legal_class)
        for node in nodes:
            for _, title in self.texts(node):
                if normalized := normalize_search_term(title):
                    terms.add(normalized)
        return {"terms": sorted(terms), "concept_count": len(nodes)}

    def user_request(self, term, timeout=8):
        names = (
            "action_user_request",
            "action",
            "rrel_1",
            "action_initiated",
            "action_finished_successfully",
            "action_finished_unsuccessfully",
            "nrel_result",
        )
        keys = {name: self.key(name) for name in names}
        if not all(keys.values()):
            return [], {"status": "missing_keynodes", "method": "action_user_request"}
        construction = ScConstruction()
        construction.generate_node(t.CONST_NODE, "action")
        construction.generate_link(
            t.CONST_NODE_LINK, ScLinkContent(term, ScLinkContentType.STRING), "input"
        )
        construction.generate_connector(t.CONST_PERM_POS_ARC, keys["action"], "action")
        construction.generate_connector(t.CONST_PERM_POS_ARC, keys["action_user_request"], "action")
        construction.generate_connector(t.CONST_PERM_POS_ARC, "action", "input", "argument")
        construction.generate_connector(t.CONST_PERM_POS_ARC, keys["rrel_1"], "argument")
        addresses = client.generate_elements(construction)
        action = addresses[0]
        initiate = ScConstruction()
        initiate.generate_connector(t.CONST_PERM_POS_ARC, keys["action_initiated"], action)
        client.generate_elements(initiate)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.contains(keys["action_finished_unsuccessfully"], action):
                return [], {
                    "status": "unsuccessful",
                    "method": "action_user_request",
                    "action_address": action.value,
                }
            if self.contains(keys["action_finished_successfully"], action):
                nodes = []
                for structure in self.relation(action, "nrel_result"):
                    nodes.extend(self.members(structure))
                return nodes, {
                    "status": "finished",
                    "method": "action_user_request",
                    "action_address": action.value,
                }
            time.sleep(0.1)
        # Исход действия неизвестен; его нельзя автоматически инициировать повторно.
        raise TimeoutError("Истекло ожидание action_user_request")

    def lookup(self, terms, use_agent=True):
        matches, unmatched, trace, linked = {}, [], [], []
        # Первый вызов — существующий агент. Остальные кандидаты читаются шаблонами.
        for index, term in enumerate(terms):
            if not isinstance(term, str) or not 2 <= len(term) <= 200:
                continue
            agent_sources = []
            if use_agent and index == 0:
                nodes, event = self.user_request(term)
                agent_sources = [source for node in nodes if (source := self.source(node))]
                trace.append(
                    {
                        "term": term,
                        **event,
                        "result_nodes_count": len(nodes),
                        "source_count": len(agent_sources),
                    }
                )
            concept_nodes = self.concepts(term, exact_only=bool(agent_sources))
            direct_sources = [source for node in concept_nodes if (source := self.source(node))]
            if direct_sources or not agent_sources:
                reason = {}
                if use_agent and index == 0:
                    reason["reason"] = "exact_title" if agent_sources else "agent_no_sources"
                trace.append(
                    {
                        "term": term,
                        "method": "sc_template_search",
                        "status": "matched" if direct_sources else "unmatched",
                        **reason,
                    }
                )
            if not concept_nodes:
                unmatched.append(term)
            else:
                linked.append(term)
            for source in (*direct_sources, *agent_sources):
                previous = matches.get(source["id"], {})
                matched_terms = list(previous.get("matched_terms", []))
                if term not in matched_terms:
                    matched_terms.append(term)
                source["matched_term"] = matched_terms[0]
                source["matched_terms"] = matched_terms
                matches[source["id"]] = source
            if len(matches) >= 12:
                break
        return {
            "matches": list(matches.values())[:12],
            "unmatched_terms": unmatched,
            "linked_terms": linked,
            "trace": trace,
        }

    def question_data(self, node):
        if not any(
            self.contains(self.key(key), node) for key in ("concept_question", "concept_questions")
        ):
            return None
        texts = self.texts(node, "nrel_content")
        if not texts:
            return None
        answers, correct = {}, []
        for relation in ("nrel_answer", "nrel_answers"):
            for answer in self.relation(node, relation):
                content = self.texts(answer, "nrel_content")
                if not content:
                    continue
                identifier = self.system_identifier(answer) or f"addr:{answer.value}"
                answers[identifier] = {
                    "id": identifier,
                    "text": content[0][1],
                    "sc_address": answer.value,
                }
                if self.contains(self.key("concept_correct_answer"), answer):
                    correct.append(identifier)
        if len(set(correct)) != 1 or len(answers) < 2:
            return None
        identifier = self.system_identifier(node) or f"addr:{node.value}"
        return {
            "id": identifier,
            "text": texts[0][1],
            "answers": list(answers.values()),
            "correct_id": correct[0],
            "provenance": {
                "source_system": "ostis",
                "sc_identifier": self.system_identifier(node),
                "sc_address": node.value,
                "content_link": texts[0][0].value,
            },
            "currency": "Учебная разметка KB. Актуальность законодательства не подтверждена.",
        }

    def question(self, identifier=None, exclude=None):
        if identifier:
            if re.fullmatch(r"addr:[1-9][0-9]{0,18}", identifier):
                node = ScAddr(int(identifier[5:]))
            elif re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,200}", identifier):
                node = self.key(identifier)
            else:
                return None
            return self.question_data(node) if node else None
        seen = set(exclude or [])
        for class_name in ("concept_question", "concept_questions"):
            key = self.key(class_name)
            if not key:
                continue
            for node in self.members(key)[:100]:
                node_id = self.system_identifier(node) or f"addr:{node.value}"
                if node_id not in seen:
                    found = self.question_data(node)
                    if found:
                        return found
        return None

    def single_match_probe(self, terms):
        for term in terms:
            links = client.search_links_by_contents(term)[0]
            title_links = {
                link.value
                for node in self.concepts(term)
                for link, text in self.texts(node)
                if text == term
            }
            # Ссылки прошлых действий тоже содержат term; считаем title-ссылки отдельно.
            if len(title_links) == 1:
                nodes, trace = self.user_request(term)
                sources = [source for node in nodes if (source := self.source(node))]
                return {
                    "term": term,
                    "diagnostics": self.agent_diagnostics(term),
                    "title_link_count": len(title_links),
                    "links_before_action": len(links),
                    "links_after_action": len(client.search_links_by_contents(term)[0]),
                    "trace": trace,
                    "result_nodes_count": len(nodes),
                    "matches": sources,
                }
        return None

    def agent_diagnostics(self, term):
        """Наличие обязательных частей upstream-шаблона в реальной памяти."""
        return [
            {
                "sc_identifier": self.system_identifier(node),
                "definition_count": len(self.definition(node)),
                "singular_article_count": len(self.relation(node, "nrel_related_article")),
                "plural_article_count": len(self.relation(node, "nrel_related_articles")),
                "singular_concept_out": len(self.relation(node, "nrel_related_concept")),
                "singular_concept_in": len(
                    self.relation(node, "nrel_related_concept", reverse=True)
                ),
                "plural_concept_out": len(self.relation(node, "nrel_related_concepts")),
            }
            for node in self.concepts(term, exact_only=True)
        ]
