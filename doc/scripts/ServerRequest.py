import requests


def ask_skyc_server(formation1, formation2):
    # api-endpoint
    URL = "https://studio.skybrush.io/api/v1/operations/plan-transition"

    # defining a params dict for the parameters to be sent to the API
    Data = {"version": 1, "source": formation1.tolist(), "target": formation2.tolist(), "max_velocity_xy": 5,
            "max_velocity_z": 5, "max_acceleration": 3, "transition_method": "const_jerk", "matching_method": "optimal"}

    # sending post request and saving response as response object
    r = requests.post(url=URL, json=Data)

    # extracting data in json format
    data = r.json()
    # print(data)
    return data['mapping'], data['durations']
