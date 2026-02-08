from anthropic import Anthropic
import os
import json
from .grading_functions import nuclide_symbol_format

class NuclearDataAgent:
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
        with open('skills/nuclear-data-quality-assessment.md', 'r') as f:
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
        """Accesses nuclear data for a given nuclide and reaction."""
        nuclide_clean = nuclide_symbol_format(nuclide)
        return metrics[nuclide_clean].reactions[reaction_name].data.to_csv()

    def _get_nugrade_report(self, nuclide, reaction_name, metrics, options):
        """Accesses nuclear data for a given nuclide and reaction."""
        nuclide_clean = nuclide_symbol_format(nuclide)
        metric =  metrics[nuclide_clean]
        report_text = metric.gen_report(options, for_web=False)
        return report_text
    
    def _list_available_nuclides(self, metrics=None):
        """Lists all available nuclides and reactions."""
        available_data_dict = {}
        nuclides = list(metrics.keys())
        for nuclide in nuclides:
            available_data_dict[nuclide] = list(metrics[nuclide].reactions.keys())
        return json.dumps(available_data_dict)
    
    def chat(self, user_message, metrics, options, conversation_history=None):
        if conversation_history is None:
            conversation_history = []
        
        conversation_history.append({
            "role": "user",
            "content": [{
                "type": "text",
                "text": user_message
            }]
        })
        
        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=self.skill,
                tools=self.tools,
                messages=conversation_history
            )
            
            # Check if Claude wants to use a tool
            if response.stop_reason == "tool_use":
                # Add Claude's request to history
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Find the tool use block
                #tool_use = next(
                #    block for block in response.content 
                #    if block.type == "tool_use"
                #)
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                for tool_use in tool_uses:
                    
                    # Execute the tool
                    tool_result = self.execute_tool(
                        tool_use.name, 
                        tool_use.input,
                        metrics=metrics,
                        options=options
                    )
                    
                    # Send result back to Claude
                    conversation_history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": tool_result
                        }]
                    })
                
                # Loop continues - Claude processes the tool result
                
            else:
                # Claude gave final answer
                final_response = next(
                    block.text for block in response.content 
                    if hasattr(block, "text")
                )
                
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                return final_response, conversation_history

