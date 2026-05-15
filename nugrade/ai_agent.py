from pathlib import Path
from anthropic import Anthropic
import json
from .grading_functions import nuclide_symbol_format

class NuclearDataAgent:
    """Claude-powered conversational agent for querying NuGrade nuclear data.

    Exposes three tools to the model — ``get_nuclear_data``, ``list_available_nuclides``,
    and ``get_nugrade_report`` — and handles the tool-use loop automatically so that
    callers receive a plain text response from ``chat()``.
    """

    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.tools = self._define_tools()
        self.skill = self._load_skill()
    
    def _define_tools(self):
        """Define available tools for Claude"""
        return [
            {
                "name": "get_nuclear_data",
                "description": "Retrieve experimental and evaluated cross section data for a specific nuclide and reaction.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "nuclide": {"type": "string"},
                        "reaction_name": {"type": "string"}
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
                "name": "get_nugrade_report",
                "description": "Provides a textual report using NuGrade's data tools to summarize the quality of data. This corresponds to the plots users see. The settings listed in the beginning of the output correspond to what the nuclide is being scored on at the moment.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "nuclide": {"type": "string"},
                        "reaction_name": {"type": "string"}
                    },
                    "required": ["nuclide", "reaction_name"]
                }
            }
        ]
    
    def _load_skill(self):
        """Load the nuclear data analysis skill"""
        skill_path = Path(__file__).parent.parent / 'skills' / 'nuclear-data-quality-assessment.md'
        with open(skill_path, 'r') as f:
            return f.read()
    
    def execute_tool(self, tool_name, tool_input, metrics=None, options=None):
        """Execute the requested tool"""
        if tool_name == "get_nuclear_data":
            return self._get_nuclear_data(**tool_input, metrics=metrics)
        elif tool_name == "list_available_nuclides":
            return self._list_available_nuclides(**tool_input, metrics=metrics)
        elif tool_name == "get_nugrade_report":
            return self._get_nugrade_report(**tool_input, metrics=metrics, options=options)
    
    def _get_nuclear_data(self, nuclide, reaction_name, metrics):
        """Accesses experiment-wide metrics and up to 100 points of nuclear cross section data for a given nuclide and reaction."""
        nuclide_clean = nuclide_symbol_format(nuclide)
        message = ""
        if nuclide_clean in metrics.keys() and reaction_name in metrics[nuclide_clean].reactions:
            full_data = metrics[nuclide_clean].reactions[reaction_name].data
            experiment_data = metrics[nuclide_clean].reactions[reaction_name].experiment_results
            filtered_data =  full_data.sort_values(by="endf8_relative_error")
            drop_columns = ['dEnergy', 'dData_assumed', 'MT', 'Dataset_Number', 'endf7-1_chi_squared', 
            'endf7-1_relative_error','endf8_relative_error', 'endf8_chi_squared']
            filtered_data = filtered_data.drop(columns=drop_columns).reset_index(drop=True)
            if len(filtered_data) > 100:
                message += f"Data long ({len(filtered_data)} points. Truncating to 100 points with highest error. "
                filtered_data = filtered_data.iloc[0:100]
            data_str = filtered_data.to_csv()
            data_str += "\n\nExperiments:\n"+experiment_data.to_csv()
        else:
            message += f"{nuclide_clean} not found in data. "
            data_str = ""
        print(data_str)
        return data_str + f"\n{message}"

    def _get_nugrade_report(self, nuclide, reaction_name, metrics, options):
        """Accesses NuGrade computed summary for a given nuclide and reaction including energy coverage,
        absolute relative error or chi squared, and number of experiments. Good starting point."""
        try:
            nuclide_clean = nuclide_symbol_format(nuclide)
            report_text = metrics[nuclide_clean].gen_report(options, for_web=False)
            return report_text + "\nNugrade report access successful."
        except Exception:
            return "Nugrade report access failed. Does the nuclide/reaction exist in NuGrade?"
    
    def _list_available_nuclides(self, metrics=None):
        """Lists all available nuclides and reactions. You can assume the data exists, but use this if a other tool call fails."""
        available_data_dict = {}
        nuclides = list(metrics.keys())
        for nuclide in nuclides:
            available_data_dict[nuclide] = list(metrics[nuclide].reactions.keys())
        return json.dumps(available_data_dict)
    
    @staticmethod
    def _serialize_content(content):
        result = []
        for block in content:
            if hasattr(block, 'type'):
                if block.type == "text":
                    result.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    result.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
            else:
                result.append(block)
        return result

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

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.skill,
                tools=self.tools,
                messages=conversation_history
            )

            if response.stop_reason == "tool_use":
                conversation_history.append({
                    "role": "assistant",
                    "content": self._serialize_content(response.content)
                })

                tool_uses = [b for b in response.content if b.type == "tool_use"]
                for tool_use in tool_uses:
                    print(f"[tool] {tool_use.name}({tool_use.input})")
                    tool_result = self.execute_tool(
                        tool_use.name,
                        tool_use.input,
                        metrics=metrics,
                        options=options
                    )
                    conversation_history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": tool_result
                        }]
                    })

            else:
                final_response = next(
                    block.text for block in response.content
                    if hasattr(block, "text")
                )
                conversation_history.append({
                    "role": "assistant",
                    "content": self._serialize_content(response.content)
                })
                return final_response, conversation_history

