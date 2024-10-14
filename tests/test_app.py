import requests_mock
import requests
import app as app_file
import dash_bootstrap_components as dbc
import dash
from dash import html
from dash import dash_table
from requests.exceptions import HTTPError
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from contextvars import copy_context
from dash._callback_context import context_value
from dash._utils import AttributeDict


#################################################### -- helper functions -- ####################################################


def serialize_dash_component(component):
    # Check if the component is a list or tuple
    if isinstance(component, (list, tuple)):
        return [serialize_dash_component(item) for item in component]

    # Check if the component has the to_plotly_json method
    if hasattr(component, "to_plotly_json"):
        # Serialize the component using to_plotly_json
        serialized = component.to_plotly_json()

        # Focus on relevant properties for surface-level comparison
        serialized_filtered = {
            "type": serialized.get(
                "type"
            ),  # Component type (e.g., Div, Row, DataTable)
            "props": {},  # Only relevant props
            "children": [],  # Only relevant children
        }

        # Check if the component is a DataTable for detailed serialization
        if serialized_filtered["type"] == "DataTable":
            # Include additional properties specific to DataTable
            for key, value in serialized.get("props", {}).items():
                # Add relevant DataTable properties
                if key in {"data", "columns", "style_table", "style_data_conditional"}:
                    serialized_filtered["props"][key] = value

            # Include children if present
            if "children" in serialized:
                serialized_filtered["children"] = serialize_dash_component(
                    serialized["children"]
                )

            return serialized_filtered

        # Include properties that are likely to be visually relevant for other components
        for key, value in serialized.get("props", {}).items():
            if key in {"children", "style", "className"}:  # Add more keys as needed
                if key == "children":
                    # Recursively serialize children
                    serialized_filtered["children"] = serialize_dash_component(value)
                else:
                    serialized_filtered["props"][key] = value

        return serialized_filtered

    # If it's a plain object (e.g., string, number), return it directly
    return component


def launch_app(app_file):
    # recreate the Dash app with its body and callbacks
    app = dash.Dash(__name__)
    app.layout = app_file.get_body()
    app_file.register_callbacks(app)
    return app


def extract_data_from_datatable(datatable):
    # Extract column headers
    headers = datatable.find_elements(By.CSS_SELECTOR, "th")
    column_names = [header.text for header in headers]

    # Extract data rows
    rows = datatable.find_elements(By.CSS_SELECTOR, "tbody tr")
    table_data = []
    for row in rows:
        cells = row.find_elements(By.CSS_SELECTOR, "td")
        # Check if any cells are empty
        if all(cell.text.strip() == "" for cell in cells):
            continue  # Skip empty rows
        row_data = {column_names[i]: cells[i].text for i in range(len(cells))}
        table_data.append(row_data)

    return column_names, table_data


def compare_datatables(actual_columns, actual_data, expected_columns, expected_data):
    assert actual_columns == [
        col["name"] for col in expected_columns
    ], "Column names do not match."

    assert len(actual_data) == len(expected_data), "Number of rows do not match."

    for actual_row, expected_row in zip(actual_data, expected_data):
        assert (
            actual_row == expected_row
        ), f"Row data does not match: {actual_row} != {expected_row}"

    print("DataTables match as expected.")


#################################################### -- tests -- ####################################################

# DISPLAY TEST : ensures that the elements that are supposed to appear on first render are effectively displayed


def test_display(dash_duo):
    app = launch_app(app_file)
    dash_duo.start_server(app)

    assert (
        dash_duo.find_element("#title").text == "Test App"
    ), "The title is not the right one"
    assert dash_duo.get_logs() == [], "browser console should contain no error"


# UNIT TEST : ensures that a specific function works as expected with different inputs

# Create an expected result
data = {"material": "Steel", "weight": "4"}
# Format the data for the DataTable
table_data = [
    {"Property": "Material", "Value": data.get("material", "N/A")},
    {"Property": "Weight (kg)", "Value": data.get("weight", "N/A")},
]
table_columns = [
    {"name": "Property", "id": "Property"},
    {"name": "Value", "id": "Value"},
]

expected = html.Div(
    [
        dash_table.DataTable(
            id="datatable-dbResults",
            columns=table_columns,
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


@requests_mock.Mocker(kw="mock")
def test_function_handleDBresponse(**kwargs):

    # MOCKING DIFFERENT RESPONSES

    mock_link_address = "https://mock-server.com"

    ### SUCCESSFUL REQUEST
    # define a get() method for the mock URL
    kwargs["mock"].get(mock_link_address, status_code=200, json=data)
    # call the method to get the http response object
    successResponse = requests.get(mock_link_address)

    try:
        # get the result of the tested function for this success input
        resultSuccess = app_file.handleDBresponse(successResponse)
        # compare the result to the expected value
        assert serialize_dash_component(expected) == serialize_dash_component(
            resultSuccess
        ), "Success response not handled properly"
    except Exception as e:
        # if there was any unexpected Exceptions during the process, fail the test and return the exception
        assert False, f"An error occured: {e}"

    ### AUTHORIZATION ISSUE
    kwargs["mock"].get(mock_link_address, status_code=403)
    response403 = requests.get(mock_link_address)

    try:
        result403 = app_file.handleDBresponse(response403)
        assert (
            result403
            == "[403] Authorization problem: You do not have permission to access this resource."
        ), "403 error not handled properly"
    except Exception as e:
        assert False, f"An error occured: {e}"

    ### HTTP EXCEPTION (e.g., requests.exceptions.HTTPError)
    kwargs["mock"].get(mock_link_address, exc=HTTPError("HTTP Error occurred"))

    try:
        responseException = requests.get(mock_link_address)
    except HTTPError as e:
        # Pass the exception to the handleDBresponse function
        resultException = app_file.handleDBresponse(e)

        # Test
        assert (
            resultException == f"An error occurred: HTTP Error occurred"
        ), "HTTPException not handled properly"


def test_callback_compute():
    # MOCK DIFFERENT INPUTS

    # button not clicked yet
    input1 = (None, 0, 0)
    input2 = (0, 0, 0)

    # basic input
    input3 = (1, 4, "Steel")

    # missing weight or material or both
    input4 = (1, None, "Steel")
    input5 = (1, 4, None)
    input6 = (1, None, None)

    # negative weight
    input7 = (1, -4, "Steel")

    # unknown material
    input8 = (1, 4, "Paper")

    # TESTS
    assert app_file.compute(*input1) == "", "Issue concerning: button not clicked yet"
    assert app_file.compute(*input2) == "", "Issue concerning: button not clicked yet"

    assert serialize_dash_component(
        app_file.compute(*input3)
    ) == serialize_dash_component(
        html.Div("{'volume_m3': 0.00051, 'dimension_m': 0.079872}")
    ), "Issue concerning: basic input"

    assert (
        app_file.compute(*input4)
        == r"/!\ Please provide an input before launching the search"
    ), "Issue concerning: missing weight or material or both"
    assert (
        app_file.compute(*input5)
        == r"/!\ Please provide an input before launching the search"
    ), "Issue concerning: missing weight or material or both"
    assert (
        app_file.compute(*input6)
        == r"/!\ Please provide an input before launching the search"
    ), "Issue concerning: missing weight or material or both"

    assert (
        app_file.compute(*input7)
        == "Error computing dimensions: Weight must be a positive number."
    ), "Issue concerning: negative weight"
    assert (
        app_file.compute(*input8)
        == "Error computing dimensions: Material must be 'steel', 'wood', or 'plastic'."
    ), "Issue concerning: unknown material"


def test_callback_context():
    def run_callback():
        context_value.set(
            AttributeDict(**{"triggered_inputs": [{"prop_id": "button-good.n_clicks"}]})
        )
        return app_file.context(0, 0)

    ctx = copy_context()
    output = ctx.run(run_callback)
    assert output == "Nice job"


# INTEGRATION TEST : ensures multiple elements work as expected together


def test_callback_searchDB():
    # MOCK DIFFERENT INPUTS

    # button not clicked yet
    input1 = (None, 0)
    input2 = (0, 0)

    # basic input
    input3 = (1, 100877275)

    # missing ref
    input4 = (1, None)
    input5 = (1, "")

    # TESTS
    assert (
        app_file.searchDB(*input1) == ""
    ), "searchDB(): button not clicked yet scenario not handled properly"
    assert (
        app_file.searchDB(*input2) == ""
    ), "searchDB(): button not clicked yet scenario not handled properly"

    assert serialize_dash_component(
        app_file.searchDB(*input3)
    ) == serialize_dash_component(
        expected
    ), "searchDB(): basic input scenario not handled properly"

    assert (
        app_file.searchDB(*input4)
        == r"/!\ Please provide an input before launching the search"
    ), "searchDB(): missing weight or material or both scenario not handled properly"
    assert (
        app_file.searchDB(*input5)
        == r"/!\ Please provide an input before launching the search"
    ), "searchDB(): missing weight or material or both scenario not handled properly"


# END-TO-END TEST : simulates a user's interactions (clicks, keys, ...) through the application


def test_ete_searchDB(dash_duo):
    # Launch a simulation of the app
    app = launch_app(app_file)
    dash_duo.start_server(app)

    # Type the reference "100877275" into the input field
    input_field = dash_duo.find_element("#input-reference")
    input_field.send_keys("100877275")

    # Click the search button
    button = dash_duo.find_element("#button-searchDB")
    button.click()

    # Wait until the DataTable is present and has data
    WebDriverWait(dash_duo.driver, 10).until(
        EC.presence_of_element_located((By.ID, "datatable-dbResults"))
    )

    # Retrieve the data from the Dash component
    datatable = dash_duo.find_element("#datatable-dbResults")

    # Extract actual data from the DataTable
    actual_columns, actual_data = extract_data_from_datatable(datatable)

    # Compare actual and expected DataTables
    compare_datatables(actual_columns, actual_data, table_columns, table_data)


def test_ete_compute(dash_duo):
    app = launch_app(app_file)
    dash_duo.start_server(app)

    # Open the dropdown to select "Steel"
    dropdown = dash_duo.find_element("#dropdown-material")
    dropdown.click()  # Click to open the dropdown

    # Wait until the dropdown options are visible
    WebDriverWait(dash_duo.driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(@class, 'Select-menu')]")
        )
    )

    # Select "Steel" from the dropdown options
    options = dash_duo.find_elements("#dropdown-material .VirtualizedSelectOption")
    steel_option = options[0]
    steel_option.click()  # Click on the "Steel" option

    input_field = dash_duo.find_element("#input-weight")
    input_field.send_keys(4)

    # Click the search button
    button = dash_duo.find_element("#button-compute")
    button.click()
    # Wait until the DataTable is present and has data
    WebDriverWait(dash_duo.driver, 10).until(
        EC.presence_of_element_located((By.ID, "div-computeResults"))
    )

    results = dash_duo.find_element("#div-computeResults").text

    assert (
        results == "{'volume_m3': 0.00051, 'dimension_m': 0.079872}"
    ), "compute results do not match"
