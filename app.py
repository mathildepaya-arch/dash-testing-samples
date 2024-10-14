import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from dash import dash_table
import utils
from requests.models import Response
from dash import callback_context


############################################# LAYOUT DEFINITION #############################################


def get_body():
    return html.Div(
        [
            html.H1("Test App", id="title"),
            html.P(
                "Please provide the reference of the part you are looking for:",
                id="text-provideReference",
            ),
            dbc.Input(
                id="input-reference",
                placeholder="Enter reference...",
                type="text",
                style={"marginBottom": "12px"},
            ),
            dbc.Button(
                "Search DB", id="button-searchDB", style={"marginBottom": "12px"}
            ),
            html.Div(id="placeholder-dbResults"),
            html.Hr(),
            html.P(
                "Fill out the information on your part to compute its dimensions:",
                id="text-information",
            ),
            dcc.Dropdown(
                id="dropdown-material",
                options=[
                    {"label": "Steel", "value": "steel"},
                    {"label": "Wood", "value": "wood"},
                    {"label": "Plastic", "value": "plastic"},
                ],
                placeholder="Select...",
                style={"marginBottom": "12px"},
            ),
            dbc.Input(
                id="input-weight",
                placeholder="Enter weight in kg...",
                type="number",
                style={"marginBottom": "12px"},
            ),
            dbc.Button("Compute estimated dimensions", id="button-compute"),
            html.Div(id="placeholder-algoResults"),
            html.Hr(),
            html.P("What do you think about testing ?"),
            html.Div(
                [
                    dbc.Button(
                        "Evil",
                        id="button-evil",
                        color="dark",
                        style={"margin": "10px"},
                    ),
                    dbc.Button(
                        "Good",
                        id="button-good",
                        color="light",
                        style={"margin": "10px"},
                    ),
                ],
            ),
            html.Div(id="placeholder-contextResults"),
        ],
        style={
            "marginTop": "8%",
            "marginBottom": "8%",
            "marginLeft": "20%",
            "marginRight": "20%",
            "textAlign": "center",
        },
    )


############################################# APP INITIALIZATION #############################################

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.layout = get_body()


############################################# HELPER FUNCTIONS #############################################


def handleDBresponse(response):
    """
    Processes the HTTP response from a database request and returns the data formatted in a Dash DataTable component if valid,
    or displays an appropriate error message if not.

    Args:
        response (object): The HTTP response object returned by a database request. This can be an instance of an Exception
                           or a response with attributes like status_code and a JSON body.

    Returns:
        dash.html.Div or str: If the response is valid, returns a Dash DataTable component with the formatted response data.
                              If the response is invalid or an error occurs, returns an error message as a string.
    """

    if isinstance(response, Exception):
        # Handle the exception
        return f"An error occurred: {str(response)}"
    # Check if the response has a status_code attribute
    if hasattr(response, "status_code"):
        status_code = response.status_code

        # Handle success responses (200-299)
        if 200 <= status_code < 300:
            try:
                # Assuming the data is in the JSON response
                data = response.json()  # Assuming the response has a .json() method

                # Format the data for the DataTable
                table_data = [
                    {"Property": "Material", "Value": data.get("material", "N/A")},
                    {"Property": "Weight (kg)", "Value": data.get("weight", "N/A")},
                ]

                # Return the DataTable component
                return html.Div(
                    [
                        dash_table.DataTable(
                            id="datatable-dbResults",
                            columns=[
                                {"name": "Property", "id": "Property"},
                                {"name": "Value", "id": "Value"},
                            ],
                            data=table_data,
                            style_cell={"textAlign": "center", "padding": "10px"},
                            style_header={
                                "backgroundColor": "#f2f2f2",
                                "fontWeight": "bold",
                                "border": "1px solid black",
                            },
                            style_data={
                                "border": "1px solid black",
                                "whiteSpace": "normal",
                                "height": "auto",
                                "fontFamily": "Arial, sans-serif",
                            },
                        )
                    ]
                )
            except Exception as e:
                # If the JSON parsing fails or data is invalid
                return f"Error processing data: {str(e)}"

        # Handle authentication problems (401)
        elif status_code == 401:
            return "[401] Authentication problem: Unauthorized access. Please check your credentials."

        # Handle authorization issues (403)
        elif status_code == 403:
            return "[403] Authorization problem: You do not have permission to access this resource."

        # Handle server issues (500-599)
        elif 500 <= status_code < 600:
            return f"Server error: A problem occurred on the server (Status Code: {status_code})."

        # Handle other non-successful responses
        else:
            return f"Error: Received response with status code {status_code}."

    # If there's no status_code (unusual case)
    return "Unexpected response format"


############################################# CALLBACK FUNCTIONS #############################################


def searchDB(clicks, ref):
    """
    Handles the search functionality when a button is clicked and sends a request to the database.
    
    Args:
        clicks (int): Number of times the search button is clicked.
        ref (str): The reference input provided by the user for the search.

    Returns:
        str or dash.html.Div: If `clicks` is `None` or zero, returns an empty string. 
                              If no reference is provided, returns a warning message.
                              Otherwise, it simulates a database request and returns the response handled by `handleDBresponse()`.
    """
    if clicks is None or clicks == 0:
        return ""
    else:
        if not ref:
            # display a warning if no reference
            return r"/!\ Please provide an input before launching the search"
        else:
            # send a request to a database
            try:
                # normally you would interact with an API endpoint here, but for ease of demonstration we fake a successful response
                # the results will therefore be the same regardless of the input
                """
                response = requests.post(
                    "http://website.com/api/DBsearch", json={"reference": ref}
                )
                """
                response = Response()
                response.status_code = 200
                response._content = b'{"material": "Steel", "weight": "4"}'
            except Exception as e:
                response = e
            # handle the response or error in the handleDBresponse function
            return handleDBresponse(response)


def compute(n_clicks, weight, material):
    """
    Computes the dimensions of a material based on user input when the button is clicked.
    
    Args:
        n_clicks (int): Number of times the compute button is clicked.
        weight (float): The weight of the material provided by the user.
        material (str): The type of material provided by the user.

    Returns:
        str or dash.html.Div: If `n_clicks` is `None` or zero, returns an empty string.
                              If weight or material is missing, returns a warning message.
                              Otherwise, computes the dimensions using `utils.compute_dimensions()` 
                              and returns the result in a Dash `html.Div` component.
    """
    if n_clicks is None or n_clicks == 0:
        return ""
    else:
        if weight is None or material is None:
            return r"/!\ Please provide an input before launching the search"
        try:
            return html.Div(
                str(utils.compute_dimensions(material, weight)), id="div-computeResults"
            )
        except Exception as e:
            return f"Error computing dimensions: {str(e)}"


def context(n_clicks_evil, n_clicks_good):
    """
    Determines which button was clicked (evil or good) and returns an appropriate message.

    Args:
        n_clicks_evil (int): Number of times the "evil" button is clicked.
        n_clicks_good (int): Number of times the "good" button is clicked.

    Returns:
        str: A message based on which button was clicked. 
             Returns "Wrong answer" if the evil button is clicked, 
             "Nice job" if the good button is clicked, 
             or an empty string if neither button is triggered.
    """
    # Check which button was clicked
    triggered = callback_context.triggered[0]["prop_id"].split(".")[0]

    if triggered == "button-evil":
        return "Wrong answer"

    elif triggered == "button-good":
        return "Nice job"

    return ""


############################################# REGISTER CALLBACK FUNCTIONS #############################################


def register_callbacks(app):
    @app.callback(
        Output("placeholder-dbResults", "children"),
        [Input("button-searchDB", "n_clicks")],
        [State("input-reference", "value")],
    )
    def call(n_clicks, input_value):
        return searchDB(n_clicks, input_value)

    @app.callback(
        Output("placeholder-algoResults", "children"),
        [Input("button-compute", "n_clicks")],
        [State("input-weight", "value"), State("dropdown-material", "value")],
    )
    def call(n_clicks, weight, material):
        return compute(n_clicks, weight, material)

    @app.callback(
        Output("placeholder-contextResults", "children"),
        [
            Input("button-evil", "n_clicks"),
            Input("button-good", "n_clicks"),
        ],
    )
    def call(n_clicks_evil, n_clicks_good):
        return context(n_clicks_evil, n_clicks_good)


register_callbacks(app)

############################################# RUN APP #############################################

if __name__ == "__main__":
    app.run_server(debug=True)
