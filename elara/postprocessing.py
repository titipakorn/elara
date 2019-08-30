import os
import geopandas
import pandas as pd

from elara.factory import WorkStation, Tool


class PostProcessor(Tool):
    options_enabled = True

    def check_prerequisites(self):
        return NotImplementedError

    def build(self, resource):
        return NotImplementedError


class AgentTripLogs(PostProcessor):
    """
    Process Leg Logs into Trip Logs.
    """

    requirements = [
        'agent_logs',
        'mode_hierarchy'
    ]
    valid_options = ['all']

    hierarchy = None

    def __str__(self):
        return f'AgentTripLogs modes'

    def build(self, resource: dict):
        super().build(resource)

        self.hierarchy = resource['mode_hierarchy']

        mode = self.option

        file_name = "{}_agents_leg_logs_{}".format(self.config.name, self.option)
        file_path = os.path.join(self.config.output_path, file_name)
        legs_df = pd.read_csv(file_path)

        # Group by trip and aggregate, applying hierarchy
        def combine_legs(gr):
            first_line = gr.iloc[0]
            last_line = gr.iloc[-1]

            duration = sum(gr.duration)
            duration_s = sum(gr.duration_s)
            distance = sum(gr.distance)

            modes = list(gr.modes)
            primary_mode = self.hierarchy.get(modes)

            return pd.Series(
                {'mode': primary_mode,
                 'ox': first_line.ox,
                 'oy': first_line.oy,
                 'dx': last_line.dx,
                 'dy': last_line.dy,
                 'start': first_line.start,
                 'end': last_line.end,
                 'duration': duration,
                 'start_s': first_line.start_s,
                 'end_s': last_line.end_s,
                 'duration_s': duration_s,
                 'distance': distance
                 }
            )

        trips_df = legs_df.groupby(['agent', 'trip']).apply(combine_legs)

        # reset index
        trips_df.reset_index(inplace=True)

        # Export results
        csv_path = os.path.join(
            self.config.output_path, "{}_agent_trip_logs_{}.csv".format(self.config.name, mode)
        )
        trips_df.to_csv(csv_path)


class VKT(PostProcessor):
    requirements = ['volume_counts']
    valid_options = ['car', 'bus', 'train', 'subway', 'ferry']

    # def __init__(self, config, option=None):
    #     super().__init__(config, option)

    def __str__(self):
        return f'VKT PostProcessor mode: {self.option}'

    def build(self, resource: dict):
        super().build(resource)

        mode = self.option

        file_name = "{}_volume_counts_{}_total.geojson".format(self.config.name, mode)
        file_path = os.path.join(self.config.output_path, file_name)
        volumes_gdf = geopandas.read_file(file_path)

        # Calculate VKT
        period_headers = generate_period_headers(self.config.time_periods)
        volumes = volumes_gdf[period_headers]
        link_lengths = volumes_gdf["length"].values / 1000  # Conversion to metres
        vkt = volumes.multiply(link_lengths, axis=0)
        vkt_gdf = pd.concat([volumes_gdf.drop(period_headers, axis=1), vkt], axis=1)

        # Export results
        csv_path = os.path.join(
            self.config.output_path, "{}_vkt_{}.csv".format(self.config.name, mode)
        )
        geojson_path = os.path.join(
            self.config.output_path,
            "{}_vkt_{}.geojson".format(self.config.name, mode),
        )
        vkt_gdf.drop("geometry", axis=1).to_csv(csv_path)
        export_geojson(vkt_gdf, geojson_path)


def generate_period_headers(time_periods):
    """
    Generate a list of strings corresponding to the time period headers in a typical
    data output.
    :param time_periods: Number of time periods across the day
    :return: List of time period numbers as strings
    """
    return list(map(str, range(time_periods)))


def export_geojson(gdf, path):
    """
    Given a geodataframe, export geojson representation to specified path.
    :param gdf: Input geodataframe
    :param path: Output path
    """
    with open(path, "w") as file:
        file.write(gdf.to_json())


# # Dictionary used to map configuration string to post-processor type
# POST_PROCESSOR_MAP = {"vkt": VKT}


class PostProcessWorkStation(WorkStation):

    tools = {
        'trip_logs': AgentTripLogs,
        'vkt': VKT,
    }

    def __str__(self):
        return f'PostProcessing WorkStation'

