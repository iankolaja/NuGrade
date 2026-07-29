from pathlib import Path
from anthropic import Anthropic
import json
import numpy as np
from .grading_functions import nuclide_symbol_format


class NuclearDataAgent:
    """Claude-powered conversational agent for querying NuGrade nuclear data.

    Exposes tools to the model for structured data access and semantic corpus
    search, and handles the tool-use loop automatically so that callers receive
    a plain text response from ``chat()``.
    """

    MODEL = "claude-opus-4-8"
    # Effort trades answer quality against latency and token spend. Chat is interactive
    # and most questions are lookups over a few tool calls, so 'medium' rather than the
    # 'high' default; raise it if answers come back shallow on multi-step questions.
    EFFORT = "medium"

    def __init__(self, api_key, sql_con=None):
        self.client = Anthropic(api_key=api_key)
        self.sql_con = sql_con
        self.scibert_available = self._load_scibert()
        self.tools = self._define_tools()
        self.skill = self._load_skill()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _load_scibert(self):
        """Load SciBERT tokenizer and model. Returns True on success."""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            model_name = 'allenai/scibert_scivocab_uncased'
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModel.from_pretrained(model_name)
            self._model.eval()
            self._torch = torch
            print("SciBERT loaded.")
            return True
        except Exception as e:
            print(f"SciBERT not available: {e}")
            return False

    def _load_skill(self):
        """Load the nuclear data analysis skill."""
        skill_path = Path(__file__).parent.parent / 'skills' / 'nuclear-data-quality-assessment.md'
        with open(skill_path, 'r') as f:
            return f.read()

    def _define_tools(self):
        """Return the list of tool schemas exposed to Claude."""
        tools = [
            {
                "name": "get_nuclear_data",
                "description": "Retrieve raw cross section data points for a specific nuclide and reaction. "
                               "Returns up to 10 points sorted by highest error. Use filters to target a specific "
                               "energy range, author, or experiment. For per-experiment summaries use get_nugrade_report.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "nuclide":       {"type": "string"},
                        "reaction_name": {"type": "string"},
                        "filters": {
                            "type": "object",
                            "description": "Optional filters applied to the data before returning.",
                            "properties": {
                                "energy_lower":   {"type": "number", "description": "Only return points at or above this energy (eV)."},
                                "energy_upper":   {"type": "number", "description": "Only return points at or below this energy (eV)."},
                                "Author":         {"type": "string", "description": "Filter to a specific author (partial match)."},
                                "EXFOR_Entry":    {"type": "string", "description": "Filter to a specific EXFOR entry."},
                                "EXFOR_Subentry": {"type": "string", "description": "Filter to a specific EXFOR subentry."},
                                "year_min":       {"type": "integer", "description": "Only return data from this year or later."},
                                "year_max":       {"type": "integer", "description": "Only return data from this year or earlier."},
                            }
                        }
                    },
                    "required": ["nuclide", "reaction_name"]
                }
            },
            {
                "name": "list_available_nuclides",
                "description": "Provides a nested dictionary showing all nuclides and all reactions with data available.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_experiment_list",
                "description": "List all experiments for a specific nuclide and reaction channel, "
                               "with their EXFOR entry/subentry IDs, authors, energy coverage, and quality metric. "
                               "Use this to find EXFOR IDs before calling get_entry_text or get_nuclear_data.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "nuclide":       {"type": "string"},
                        "reaction_name": {"type": "string"}
                    },
                    "required": ["nuclide", "reaction_name"]
                }
            },
            {
                "name": "get_nugrade_report",
                "description": "Provides a textual report using NuGrade's data tools to summarize the quality of data. "
                               "This corresponds to the plots users see. The settings listed in the beginning of the "
                               "output correspond to what the nuclide is being scored on at the moment.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "nuclide": {"type": "string"},
                        "reaction_name": {"type": "string"}
                    },
                    "required": ["nuclide", "reaction_name"]
                }
            },
        ]

        if self.sql_con is not None:
            tools.append({
                "name": "get_entry_text",
                "description": "Retrieve the full text record for a specific EXFOR entry from the corpus. "
                               "Use this after search_corpus has identified a relevant entry and you want "
                               "to read the complete experimental description. "
                               "Never reproduce the full text verbatim in your response. Some sources are "
                               "paywalled journal articles or private communications. Summarize and quote selectively instead.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "EXFOR_Entry": {"type": "string", "description": "The EXFOR entry number to retrieve."}
                    },
                    "required": ["EXFOR_Entry"]
                }
            })

        if self.scibert_available and self.sql_con is not None:
            tools.append({
                "name": "search_corpus",
                "description": (
                    "Semantic similarity search over EXFOR experimental text records. "
                    "Queries should be similar to EXFOR passage that answers the user's question. "
                    "Optionally pre-filter by structured fields before running similarity search. "
                    "Returns the top matching text passages with their EXFOR entry IDs."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural-language search query."
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional structured filters applied before similarity search.",
                            "properties": {
                                "Z":              {"type": "integer", "description": "Proton number (exact match)."},
                                "A":              {"type": "integer", "description": "Mass number (exact match)."},
                                "MT":             {"type": "integer", "description": "ENDF MT reaction code (exact match)."},
                                "Reaction":       {"type": "string",  "description": "Reaction string, e.g. 'N,G' (partial match)."},
                                "Element":        {"type": "string",  "description": "Element symbol, e.g. 'Li' (exact match)."},
                                "EXFOR_Entry":    {"type": "string",  "description": "Specific EXFOR entry number."},
                                "EXFOR_Subentry": {"type": "string",  "description": "Specific EXFOR subentry number."},
                                "Author":         {"type": "string",  "description": "Author name (partial match)."},
                                "Year":           {"type": "integer", "description": "Publication year (exact match)."},
                                "energy_lower":   {"type": "number",  "description": "Only include entries with data at or above this energy (eV)."},
                                "energy_upper":   {"type": "number",  "description": "Only include entries with data at or below this energy (eV)."},
                            }
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default 5, max 20)."
                        }
                    },
                    "required": ["query"]
                }
            })

        return tools

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _embed(self, text):
        """Return a unit-normalised mean-pooled embedding for ``text``.

        Must match the pooling used by get_embeddings_batch in the NuGrade-PreProcessing
        repo (2_report_embedding.ipynb), which generates the stored sentence_embeddings:
        attention-mask-weighted mean over tokens. A query vector built any other way
        (e.g. the CLS token) lives in a different space than the stored documents and
        silently degrades similarity ranking.
        """
        inputs = self._tokenizer(
            text, return_tensors='pt', truncation=True, max_length=512, padding=True
        )
        with self._torch.no_grad():
            outputs = self._model(**inputs)
        mask = inputs['attention_mask'].unsqueeze(-1).float()
        emb = ((outputs.last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9))
        emb = emb.squeeze().numpy().astype(np.float32)
        norm = np.linalg.norm(emb)
        return emb / (norm + 1e-8)

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def execute_tool(self, tool_name, tool_input, metrics=None, options=None):
        """Dispatch a tool call and return its string result."""
        if tool_name == "get_experiment_list":
            return self._get_experiment_list(**tool_input, metrics=metrics)
        elif tool_name == "get_nuclear_data":
            return self._get_nuclear_data(
                tool_input["nuclide"], tool_input["reaction_name"],
                filters=tool_input.get("filters"), metrics=metrics
            )
        elif tool_name == "list_available_nuclides":
            return self._list_available_nuclides(metrics=metrics, options=options)
        elif tool_name == "get_nugrade_report":
            return self._get_nugrade_report(**tool_input, metrics=metrics, options=options)
        elif tool_name == "get_entry_text":
            return self._get_entry_text(**tool_input)
        elif tool_name == "search_corpus":
            return self._search_corpus(**tool_input)
        return f"Unknown tool: {tool_name}"

    def _get_experiment_list(self, nuclide, reaction_name, metrics):
        """Returns the per-experiment summary for a nuclide/reaction channel."""
        nuclide_clean = nuclide_symbol_format(nuclide)
        try:
            return metrics[nuclide_clean].reactions[reaction_name].experiment_results.to_csv(index=False)
        except KeyError:
            return f"{nuclide_clean} / {reaction_name} not found."

    def _get_nuclear_data(self, nuclide, reaction_name, metrics, filters=None):
        """Returns up to 10 raw cross section data points, sorted by highest error. Use filters to narrow results."""
        nuclide_clean = nuclide_symbol_format(nuclide)
        if nuclide_clean not in metrics.keys() or reaction_name not in metrics[nuclide_clean].reactions:
            return f"{nuclide_clean} not found in data."

        full_data = metrics[nuclide_clean].reactions[reaction_name].data.copy()
        f = filters or {}
        if "energy_lower" in f:
            full_data = full_data[full_data["Energy"] >= f["energy_lower"]]
        if "energy_upper" in f:
            full_data = full_data[full_data["Energy"] <= f["energy_upper"]]
        if "Author" in f:
            full_data = full_data[full_data["Author"].str.contains(f["Author"], case=False, na=False)]
        if "EXFOR_Entry" in f:
            full_data = full_data[full_data["EXFOR_Entry"] == f["EXFOR_Entry"]]
        if "EXFOR_Subentry" in f:
            full_data = full_data[full_data["EXFOR_Subentry"] == f["EXFOR_Subentry"]]
        if "year_min" in f:
            full_data = full_data[full_data["Year"] >= f["year_min"]]
        if "year_max" in f:
            full_data = full_data[full_data["Year"] <= f["year_max"]]

        drop_columns = ['dEnergy', 'dData_assumed', 'EXFOR_Entry', 'endf7-1_chi_squared',
                        'endf7-1_relative_error', 'endf8_relative_error', 'endf8_chi_squared']
        result = (full_data.sort_values(by="endf8_relative_error", ascending=False)
                           .drop(columns=drop_columns)
                           .reset_index(drop=True)
                           .iloc[:10])
        message = f"Showing {len(result)} of {len(full_data)} filtered points (highest error first)."
        return result.to_csv() + f"\n{message}"

    def _get_nugrade_report(self, nuclide, reaction_name, metrics, options):
        """Accesses NuGrade computed summary for a given nuclide and reaction."""
        try:
            nuclide_clean = nuclide_symbol_format(nuclide)
            report_text = metrics[nuclide_clean].gen_report(options, for_web=False)
            return report_text + "\nNugrade report access successful."
        except Exception:
            return "Nugrade report access failed. Does the nuclide/reaction exist in NuGrade?"

    def _list_available_nuclides(self, metrics=None, options=None):
        """Lists all available nuclides and the configured reaction channels."""
        reaction_names = [r[1] for r in options.required_reaction_channels] if options else []
        return json.dumps({nuclide: reaction_names for nuclide in metrics.keys()})

    def _get_entry_text(self, EXFOR_Entry):
        """Return the full text of an EXFOR entry from the corpus, ordered by sentence."""
        rows = self.sql_con.execute(
            "SELECT Text FROM sentence_embeddings WHERE EXFOR_Entry = ? ORDER BY Sentence_Number",
            (EXFOR_Entry,)
        ).fetchall()
        if not rows:
            return f"No text records found for entry {EXFOR_Entry}."
        return f"[Entry {EXFOR_Entry}]\n" + " ".join(r[0] for r in rows)

    def _search_corpus(self, query, filters=None, top_k=5):
        """Semantic search over EXFOR sentence embeddings with optional pre-filtering.

        Parameters
        ----------
        query : str
            Natural-language search query.
        filters : dict, optional
            Structured field filters applied before similarity search. Supported keys:
            Z, A, MT, Reaction, Element, EXFOR_Entry, EXFOR_Subentry, Author, Year,
            energy_lower, energy_upper.
        top_k : int
            Number of top results to return (capped at 20).
        """
        filters = filters or {}
        top_k = min(int(top_k), 20)

        # --- Build SQL to get matching EXFOR_Entry values from subentries ---
        conditions, params = [], []
        needs_meas_join = 'Author' in filters or 'Year' in filters
        from_clause = "subentries s"
        if needs_meas_join:
            from_clause += " JOIN measurements m ON s.EXFOR_Subentry = m.EXFOR_Subentry"

        column_map = {
            'Z':              ('s.Z',              '='),
            'A':              ('s.A',              '='),
            'MT':             ('s.MT',             '='),
            'Reaction':       ('s.Reaction',       'LIKE'),
            'Element':        ('s.Element',        '='),
            'EXFOR_Entry':    ('s.EXFOR_Entry',    '='),
            'EXFOR_Subentry': ('s.EXFOR_Subentry', '='),
            'Author':         ('m.Author',         'LIKE'),
            'Year':           ('m.Year',           '='),
            # energy_lower/upper map to opposite columns to find overlapping entries
            'energy_lower':   ('s.E_max',          '>='),
            'energy_upper':   ('s.E_min',          '<='),
        }

        for key, value in filters.items():
            if key in column_map:
                col, op = column_map[key]
                if op == 'LIKE':
                    conditions.append(f"{col} LIKE ?")
                    params.append(f"%{value}%")
                else:
                    conditions.append(f"{col} {op} ?")
                    params.append(value)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        entry_sql = f"SELECT DISTINCT s.EXFOR_Entry FROM {from_clause} {where}"

        entries = [r[0] for r in self.sql_con.execute(entry_sql, params).fetchall()]
        if not entries:
            return "No entries found matching the specified filters."

        # --- Fetch sentence embeddings for matching entries ---
        placeholders = ",".join("?" * len(entries))
        rows = self.sql_con.execute(
            f"SELECT Text, EXFOR_Entry, Sentence_Number, Embedding FROM sentence_embeddings "
            f"WHERE EXFOR_Entry IN ({placeholders})",
            entries
        ).fetchall()

        entries_with_text = len({r[1] for r in rows})
        if not rows:
            return (f"No text records found for the {len(entries)} entries matching the filters. "
                    "The corpus does not cover these entries.")
        coverage_note = (f"Corpus coverage: {entries_with_text}/{len(entries)} filtered entries have text records.\n"
                         "Do not retry with different filters if coverage is low — the text simply is not in the corpus.")

        # --- Score by cosine similarity ---
        query_emb = self._embed(query)
        scored = []
        for text, entry, sent_num, emb_bytes in rows:
            stored = np.frombuffer(emb_bytes, dtype=np.float32)
            norm = np.linalg.norm(stored)
            if norm < 1e-8:
                continue
            sim = float(np.dot(query_emb, stored / norm))
            scored.append((sim, text, entry, sent_num))

        scored.sort(reverse=True)
        top = scored[:top_k]

        # --- Fetch a representative author for each top entry ---
        top_entries = [entry for _, _, entry, _ in top]
        author_placeholders = ",".join("?" * len(top_entries))
        entry_authors = {
            row[0]: row[1]
            for row in self.sql_con.execute(
                f"SELECT EXFOR_Entry, Author FROM measurements "
                f"WHERE EXFOR_Entry IN ({author_placeholders}) GROUP BY EXFOR_Entry",
                top_entries
            ).fetchall()
        }

        # --- Expand each result to a context window around the matched sentence ---
        context_window = 2
        lines = [f"Top {len(top)} results for '{query}' "
                 f"({len(rows)} sentences searched across {len(entries)} entries).\n"
                 f"{coverage_note}\n"]
        for sim, _, entry, sent_num in top:
            chunk_rows = self.sql_con.execute(
                "SELECT Text FROM sentence_embeddings "
                "WHERE EXFOR_Entry = ? AND Sentence_Number BETWEEN ? AND ? "
                "ORDER BY Sentence_Number",
                (entry, sent_num - context_window, sent_num + context_window)
            ).fetchall()
            chunk = " ".join(r[0] for r in chunk_rows)
            author = entry_authors.get(entry, "Unknown")
            lines.append(f"[Entry {entry} | {author} | score {sim:.3f}]\n{chunk}")
        return "\n\n".join(lines)

    # ------------------------------------------------------------------
    # Serialisation / chat loop
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_content(content):
        """Convert response blocks to plain dicts for storage in the session history.

        Thinking blocks must be preserved and replayed unchanged: the API rejects a
        continued conversation whose thinking blocks were dropped or edited.
        """
        result = []
        for block in content:
            if not hasattr(block, 'type'):
                result.append(block)
            elif block.type == "text":
                result.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                result.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
            elif block.type == "thinking":
                result.append({"type": "thinking", "thinking": block.thinking,
                               "signature": block.signature})
            elif block.type == "redacted_thinking":
                result.append({"type": "redacted_thinking", "data": block.data})
        return result

    @staticmethod
    def _apply_cache_breakpoint(conversation_history):
        """Move the prompt-cache breakpoint to the end of the conversation.

        The system prompt and tool schemas together fall short of the model's minimum
        cacheable prefix, so caching them achieves nothing. The history does cross that
        threshold once tool results (data tables, retrieved passages) accumulate, so the
        breakpoint goes on the newest turn and each request reuses the prior prefix.
        Stale breakpoints are cleared first — the API allows at most four per request.
        """
        for message in conversation_history:
            if isinstance(message["content"], list):
                for block in message["content"]:
                    if isinstance(block, dict):
                        block.pop("cache_control", None)

        for message in reversed(conversation_history):
            if isinstance(message["content"], list) and message["content"]:
                last_block = message["content"][-1]
                if isinstance(last_block, dict):
                    last_block["cache_control"] = {"type": "ephemeral"}
                return

    def chat(self, user_message, metrics, options, conversation_history=None):
        """Send a user message and run the tool-use loop until a final text response is ready.

        Parameters
        ----------
        user_message : str
            The user's input text.
        metrics : dict or LazyMetrics
            Per-nuclide grading results, used by tool implementations.
        options : MetricOptions
            Current grading options, passed to report-generating tools.
        conversation_history : list, optional
            Existing message history to continue. Mutated in place and returned.

        Returns
        -------
        final_response : str
            The model's text response after all tool calls are resolved.
        conversation_history : list
            Updated message history including this exchange.
        """
        if conversation_history is None:
            conversation_history = []

        conversation_history.append({
            "role": "user",
            "content": [{"type": "text", "text": user_message}]
        })

        # Truncate tool_result content in older turns to avoid accumulating
        # large search/data payloads in the context window. Keep the two most
        # recent user messages intact; compress tool_results in everything older.
        user_turns = [i for i, m in enumerate(conversation_history) if m["role"] == "user"]
        if len(user_turns) > 2:
            cutoff = user_turns[-2]
            for msg in conversation_history[:cutoff]:
                if msg["role"] == "user" and isinstance(msg["content"], list):
                    for block in msg["content"]:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            block["content"] = "[result omitted from history]"

        while True:
            self._apply_cache_breakpoint(conversation_history)

            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=8192,
                thinking={"type": "adaptive"},
                output_config={"effort": self.EFFORT},
                system=self.skill,
                tools=self.tools,
                messages=conversation_history
            )

            conversation_history.append({
                "role": "assistant",
                "content": self._serialize_content(response.content)
            })

            if response.stop_reason == "tool_use":
                # All results from one assistant turn go back in a single user message.
                # Splitting them across messages teaches the model to stop calling tools
                # in parallel.
                tool_results = []
                for tool_use in (b for b in response.content if b.type == "tool_use"):
                    print(f"[tool] {tool_use.name}({tool_use.input})")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": self.execute_tool(
                            tool_use.name, tool_use.input,
                            metrics=metrics, options=options
                        ),
                    })
                conversation_history.append({"role": "user", "content": tool_results})
            else:
                final_response = next(
                    (block.text for block in response.content if block.type == "text"),
                    "I wasn't able to produce a response to that."
                )
                return final_response, conversation_history
