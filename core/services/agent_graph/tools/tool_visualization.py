
# c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\tool_visualization.py
import json
import pandas as pd
import plotly.express as px
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional


@tool
def create_visualization(data_json: str, chart_type: str, x_column: str, y_column: Optional[str] = None, title: Optional[str] = None, color_column: Optional[str] = None) -> str:
    """
    Creates a visualization based on the provided data and chart specifications.
    Use this tool when the user explicitly asks for a chart or graph, or when
    the collected data is suitable for visualization and the user might benefit from it.
    You should first use other tools like 'query_asset_database' to get the data,
    then pass the data to this tool. The data should be a summary or aggregated data, not raw large datasets.

    Args:
        data_json (str): A JSON string representing a list of dictionaries (like pandas DataFrame records).
                         Example: '[{"category": "A", "value": 10}, {"category": "B", "value": 20}]'
        chart_type (str): The type of chart to create. Supported types: "bar", "line", "pie", "scatter".
        x_column (str): The name of the column to be used for the x-axis (or labels for pie chart).
        y_column (Optional[str]): The name of the column to be used for the y-axis (or values for pie chart).
                                  Required for bar, line, scatter. For pie, if using 'names' and 'values' convention, this is 'values'.
        title (Optional[str]): The title of the chart.
        color_column (Optional[str]): The name of the column to use for coloring the chart marks (optional).

    Returns:
        str: A JSON string containing the Plotly chart specification if successful,
             or an error message string if visualization cannot be created.
    """
    try:
        data = json.loads(data_json)
        if not isinstance(data, list) or not data:
            return json.dumps({"error": "Invalid data_json format. Expected a non-empty list of dictionaries."})
        if not all(isinstance(item, dict) for item in data):
            return json.dumps({"error": "Invalid data_json format. All items in list must be dictionaries."})

        df = pd.DataFrame(data)
        if df.empty:
            return json.dumps({"error": "Provided data is empty after converting to DataFrame."})

        if x_column not in df.columns:
            return json.dumps({"error": f"x_column '{x_column}' not found in the provided data columns: {df.columns.tolist()}"})

        # y_column is required for bar, line, scatter
        if chart_type in ["bar", "line", "scatter"] and not y_column:
            return json.dumps({"error": f"y_column is required for chart_type '{chart_type}'."})
        if y_column and y_column not in df.columns:
            return json.dumps({"error": f"y_column '{y_column}' not found in the provided data columns: {df.columns.tolist()}"})

        # color_column is optional, but if provided, must exist
        if color_column and color_column not in df.columns:
            return json.dumps({"error": f"color_column '{color_column}' not found in the provided data columns: {df.columns.tolist()}"})

        fig = None

        # Common arguments for Plotly Express functions
        plot_args = {
            "data_frame": df,
            "x": x_column,
            # Default title
            "title": title if title else f"{chart_type.capitalize()} chart of {y_column if y_column else x_column}",
        }
        if color_column:
            plot_args["color"] = color_column

        if chart_type == "bar":
            if not y_column:
                return json.dumps({"error": "y_column is required for bar chart."})
            plot_args["y"] = y_column
            fig = px.bar(**plot_args)
        elif chart_type == "line":
            if not y_column:
                return json.dumps({"error": "y_column is required for line chart."})
            plot_args["y"] = y_column
            plot_args["markers"] = True
            fig = px.line(**plot_args)
        elif chart_type == "pie":
            if not y_column:
                return json.dumps({"error": "For pie chart, please provide 'x_column' for names and 'y_column' for values."})
            pie_args = {"data_frame": df, "names": x_column,
                        "values": y_column, "title": plot_args["title"]}
            if color_column:
                pie_args["color"] = x_column
            fig = px.pie(**pie_args)
        elif chart_type == "scatter":
            if not y_column:
                return json.dumps({"error": "y_column is required for scatter chart."})
            plot_args["y"] = y_column
            fig = px.scatter(**plot_args)
        else:
            return json.dumps({"error": f"Unsupported chart_type: '{chart_type}'. Supported types are 'bar', 'line', 'pie', 'scatter'."})

        if fig:
            fig.update_layout(
                title_x=0.5,
                legend_title_text=color_column if color_column else ''
            )
            return fig.to_json()
        else:
            return json.dumps({"error": "Failed to generate chart figure."})

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid data_json: Not a valid JSON string."})
    except KeyError as e:
        return json.dumps({"error": f"Data parsing error or missing key: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred in visualization tool: {str(e)}"})
