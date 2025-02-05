import sys
import os
from numpy.matrixlib import defmatrix
import pytest
import pandas as pd
import numpy as np
import lxml.etree as etree
from datetime import datetime, timedelta


sys.path.append(os.path.abspath('../elara'))
from elara.config import Config, PathFinderWorkStation
from elara.inputs import InputsWorkStation
from elara import plan_handlers
from elara.plan_handlers import PlanHandlerWorkStation

test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
test_inputs = os.path.join(test_dir, "test_intermediate_data")
test_outputs = os.path.join(test_dir, "test_outputs")
if not os.path.exists(test_outputs):
    os.mkdir(test_outputs)
benchmarks_path = os.path.join(test_outputs, "benchmarks")
if not os.path.exists(benchmarks_path):
    os.mkdir(benchmarks_path)


test_matsim_time_data = [
    ('00:00:00', 0),
    ('01:01:01', 3661),
    (None, None),
]


@pytest.mark.parametrize("time,seconds", test_matsim_time_data)
def test_convert_time(time, seconds):
    assert plan_handlers.convert_time_to_seconds(time) == seconds


# Config
@pytest.fixture
def test_config():
    config_path = os.path.join(test_dir, 'test_xml_scenario.toml')
    config = Config(config_path)
    assert config
    return config


@pytest.fixture
def test_config_v12():
    config_path = os.path.join(test_dir, 'test_xml_scenario_v12.toml')
    config = Config(config_path)
    assert config
    return config

@pytest.fixture
def test_config_v13():
    config_path = os.path.join(test_dir, 'test_xml_scenario_v13.toml')
    config = Config(config_path)
    assert config
    return config


def test_v12_config(test_config_v12):
    assert test_config_v12.version == 12


# Paths
@pytest.fixture
def test_paths(test_config):
    paths = PathFinderWorkStation(test_config)
    paths.connect(managers=None, suppliers=None)
    paths.load_all_tools()
    paths.build()
    assert set(paths.resources) == set(paths.tools)
    return paths


@pytest.fixture
def test_paths_v12(test_config_v12):
    paths = PathFinderWorkStation(test_config_v12)
    paths.connect(managers=None, suppliers=None)
    paths.load_all_tools()
    paths.build()
    assert set(paths.resources) == set(paths.tools)
    return paths


# Input Manager
@pytest.fixture
def input_manager(test_config, test_paths):
    input_workstation = InputsWorkStation(test_config)
    input_workstation.connect(managers=None, suppliers=[test_paths])
    input_workstation.load_all_tools()
    input_workstation.build()
    return input_workstation


@pytest.fixture
def input_manager_v12(test_config_v12, test_paths_v12):
    input_workstation = InputsWorkStation(test_config_v12)
    input_workstation.connect(managers=None, suppliers=[test_paths_v12])
    input_workstation.load_all_tools()
    input_workstation.build()
    return input_workstation


# Base
@pytest.fixture
def base_handler(test_config, input_manager):
    base_handler = plan_handlers.PlanHandlerTool(test_config, 'all')
    assert base_handler.mode == 'all'
    base_handler.build(input_manager.resources, write_path=test_outputs)
    return base_handler


@pytest.fixture
def base_handler_v12(test_config_v12, input_manager):
    base_handler = plan_handlers.PlanHandlerTool(test_config_v12, 'all')
    assert base_handler.mode == 'all'
    base_handler.build(input_manager.resources, write_path=test_outputs)
    return base_handler


mode_distances = [
    ({'a':2, 'b':0.5}, 'a'),
    ({'a':2, 'b':2}, 'a'),
    ({'a':2}, 'a'),
    ({'a':2, 'b':-1}, 'a'),
    ({'transit_walk':2, 'b':1}, 'b'),
    ({None: 1}, None),
]


@pytest.mark.parametrize("modes,mode", mode_distances)
def get_furthest_mode(modes, mode):
    assert plan_handlers.PlanHandlerTool.get_furthest_mode(modes) == mode


def test_extract_mode_from_v11_route_elem(base_handler):
    class Resource:
        route_to_mode_map = {"a":"bus"}
    base_handler.resources['transit_schedule'] = Resource()
    string = """
    <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42"
    distance="10100.0">PT1===home_stop_out===city_line===a===work_stop_in</route>
    """
    elem = etree.fromstring(string)
    assert base_handler.extract_mode_from_v11_route_elem(elem) == "bus"


def test_extract_routeid_from_v12_route_elem(base_handler):
    class Resource:
        route_to_mode_map = {"a":"bus"}
    base_handler.resources['transit_schedule'] = Resource()
    string = """
    <route type="default_pt" start_link="1"
    end_link="2" trav_time="00:33:03" distance="2772.854305426653">
    {"transitRouteId":"a","boardingTime":"09:15:00","transitLineId":"b",
    "accessFacilityId":"1","egressFacilityId":"2"}</route>
    """
    elem = etree.fromstring(string)
    assert base_handler.extract_routeid_from_v12_route_elem(elem) == "a"


def test_extract_mode_from_route_elem_v11(base_handler):
    class Resource:
        route_to_mode_map = {"a":"bus"}
    base_handler.resources['transit_schedule'] = Resource()
    string = """
    <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42"
    distance="10100.0">PT1===home_stop_out===city_line===a===work_stop_in</route>
    """
    elem = etree.fromstring(string)
    assert base_handler.extract_mode_from_route_elem("pt", elem) == "bus"


def test_extract_mode_from_route_elem_v12(base_handler_v12):
    class Resource:
        route_to_mode_map = {"a":"bus"}
    base_handler_v12.resources['transit_schedule'] = Resource()
    string = """
    <route type="default_pt" start_link="1"
    end_link="2" trav_time="00:33:03" distance="2772.854305426653">
    {"transitRouteId":"a","boardingTime":"09:15:00","transitLineId":"b",
    "accessFacilityId":"1","egressFacilityId":"2"}</route>
    """
    elem = etree.fromstring(string)
    assert base_handler_v12.extract_mode_from_route_elem("bus", elem) == "bus"


### Utility Handler ###

@pytest.fixture
def person_single_plan_elem():
    string = """
        <person id="test1">
        <plan score="10" selected="yes">
        </plan>
    </person>
        """
    return etree.fromstring(string)


@pytest.fixture
def person_plans_elem():
    string = """
        <person id="test2">
        <plan score="10" selected="yes">
        </plan>
        <plan score="8" selected="no">
        </plan>
    </person>
        """
    return etree.fromstring(string)


@pytest.fixture
def utility_handler(test_config, input_manager):
    handler = plan_handlers.UtilityLogs(test_config, 'all')
    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)
    assert len(handler.utility_log.chunk) == 0
    return handler


def test_utility_handler_process_single_plan(utility_handler, person_single_plan_elem):
    assert len(utility_handler.utility_log) == 0
    utility_handler.process_plans(person_single_plan_elem)
    assert len(utility_handler.utility_log) == 1
    assert utility_handler.utility_log.chunk == [{'agent': 'test1','score': '10'}]


def test_utility_handler_process_multi_plan(utility_handler, person_plans_elem):
    assert len(utility_handler.utility_log) == 0
    utility_handler.process_plans(person_plans_elem)
    assert len(utility_handler.utility_log) == 1
    assert utility_handler.utility_log.chunk == [{'agent': 'test2','score': '10'}]


def test_utility_handler_process_plans(utility_handler, person_single_plan_elem, person_plans_elem):
    assert len(utility_handler.utility_log) == 0
    utility_handler.process_plans(person_single_plan_elem)
    utility_handler.process_plans(person_plans_elem)
    assert len(utility_handler.utility_log) == 2
    assert utility_handler.utility_log.chunk == [{'agent': 'test1','score': '10'}, {'agent': 'test2','score': '10'}]


### Leg Log Handler ###
# Wrapping
test_matsim_time_data = [
    (['06:00:00', '12:45:00', '18:30:00'], '1-18:30:00'),
    (['06:00:00', '12:45:00', '24:00:00'], '2-00:00:00'),
    (['06:00:00', '24:00:00', '08:30:00'], '2-08:30:00'),
    (['06:00:00', '18:45:00', '12:30:00'], '2-12:30:00'),
    (['06:00:00', '18:45:00', '18:45:00'], '1-18:45:00'),
    (['00:00:00', '12:45:00', '18:45:00'], '1-18:45:00'),
    (['06:00:00', '04:45:00', '02:45:00'], '3-02:45:00'),
    (['00:00:00'], '1-00:00:00'),
    (['24:00:00'], '2-00:00:00'),
]

non_wrapping_test_matsim_time_data = [
    (['06:00:00', '12:45:00', '18:30:00'], '1-18:30:00'),
    (['06:00:00', '12:45:00', '24:00:00'], '2-00:00:00'),
    (['06:00:00', '24:00:00', '08:30:00'], '1-08:30:00'),
    (['06:00:00', '18:45:00', '12:30:00'], '1-12:30:00'),
    (['00:00:00'], '1-00:00:00'),
    (['24:00:00'], '2-00:00:00'),
]

@pytest.mark.parametrize("times,final_string", non_wrapping_test_matsim_time_data)
def test_matsim_time_to_datetime(times, final_string):
    current_dt = None
    for new_time_str in times:
        current_dt = plan_handlers.matsim_time_to_datetime(
            current_dt,
            new_time_str,
            base_year=1900,
            base_month=1,
            )
    assert isinstance(current_dt, datetime)
    assert current_dt == datetime.strptime(f"{final_string}", '%d-%H:%M:%S')


test_durations_data = [
    (
        None, datetime(year=2020, month=4, day=1, hour=0),
        timedelta(hours=0), datetime(year=2020, month=4, day=1, hour=0)
    ),
    (
        None, datetime(year=2020, month=4, day=1, hour=1),
        timedelta(hours=1), datetime(year=2020, month=4, day=1, hour=0)
    ),
    (
        datetime(year=2020, month=4, day=1, hour=1), datetime(year=2020, month=4, day=1, hour=1),
        timedelta(hours=0), datetime(year=2020, month=4, day=1, hour=1)
    ),
    (
        datetime(year=2020, month=4, day=1, hour=1), datetime(year=2020, month=4, day=1, hour=2),
        timedelta(hours=1), datetime(year=2020, month=4, day=1, hour=1)
    ),
    (
        datetime(year=2020, month=4, day=1, hour=2), datetime(year=2020, month=4, day=1, hour=1),
        timedelta(hours=-1), datetime(year=2020, month=4, day=1, hour=2)
    ),
]
@pytest.mark.parametrize("start,end,duration,start_time", test_durations_data)
def test_safe_duration(start, end, duration, start_time):
    d, st = plan_handlers.safe_duration(start, end)
    assert d == duration
    assert st == start_time


test_distance_data = [
    (0,0,0,0,0),
    (1,1,1,1,0),
    (0,0,3,4,5),
    (3,4,0,0,5),
    (3,0,0,-4,5)
]
@pytest.mark.parametrize("x1,y1,x2,y2,dist", test_distance_data)
def test_distance(x1,y1,x2,y2,dist):
    assert plan_handlers.distance(x1,y1,x2,y2) == dist


# Normal Case
@pytest.fixture
def agent_leg_log_handler(test_config, input_manager):
    handler = plan_handlers.LegLogs(test_config, 'all')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.activities_log.chunk) == 0
    assert len(handler.legs_log.chunk) == 0

    return handler


def test_agent_log_handler(agent_leg_log_handler):
    handler = agent_leg_log_handler

    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert len(handler.activities_log.chunk) == 23
    assert len(handler.legs_log.chunk) == 18


@pytest.fixture
def agent_leg_log_handler_finalised(agent_leg_log_handler):
    handler = agent_leg_log_handler
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    handler.finalise()
    return handler


def test_finalised_logs(agent_leg_log_handler_finalised):
    handler = agent_leg_log_handler_finalised

    assert len(handler.results) == 0


# Plans Wrapping case

# Bad Config (plans wrap past 24hrs)
@pytest.fixture
def test_bad_plans_config():
    config_path = os.path.join(test_dir, 'test_xml_scenario_bad_plans.toml')
    config = Config(config_path)
    assert config
    return config


# Paths
@pytest.fixture
def test_bad_plans_paths(test_bad_plans_config):
    paths = PathFinderWorkStation(test_bad_plans_config)
    paths.connect(managers=None, suppliers=None)
    paths.load_all_tools()
    paths.build()
    assert set(paths.resources) == set(paths.tools)
    return paths


# Input Manager
@pytest.fixture
def input_bad_plans_manager(test_bad_plans_config, test_bad_plans_paths):
    input_workstation = InputsWorkStation(test_bad_plans_config)
    input_workstation.connect(managers=None, suppliers=[test_bad_plans_paths])
    input_workstation.load_all_tools()
    input_workstation.build()
    return input_workstation


@pytest.fixture
def agent_leg_log_handler_bad_plans(test_bad_plans_config, input_bad_plans_manager):
    handler = plan_handlers.LegLogs(test_bad_plans_config, 'all')

    resources = input_bad_plans_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.activities_log.chunk) == 0
    assert len(handler.legs_log.chunk) == 0

    return handler


@pytest.fixture
def agent_leg_log_handler_finalised_bad_plans(agent_leg_log_handler_bad_plans):
    handler = agent_leg_log_handler_bad_plans
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    assert handler.activities_log.chunk[-1].get('end_day') == 1
    assert handler.legs_log.chunk[-1].get('end_day') == 1
    handler.finalise()
    return handler


def test_finalised_logs_bad_plans(agent_leg_log_handler_finalised_bad_plans):
    handler = agent_leg_log_handler_finalised_bad_plans
    assert len(handler.results) == 0

### Toll Log Handler ###

@pytest.fixture
def toll_log_handler(test_config, input_manager):
    handler = plan_handlers.AgentTollsPaidFromRPConfig(test_config, 'car')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    return handler

#paying single toll
def test_toll_onelink(toll_log_handler):
    handler = toll_log_handler

    person = """
    <person id="chris">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)
    assert len(handler.toll_log) == 1
    assert handler.toll_log.iloc[0]['toll']=='10.0'

#using two adjacent toll links consecutively should only incur one charge
def test_toll_consecutivelinks(toll_log_handler):
    handler = toll_log_handler

    person = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-3 3-4</route>
            </leg>
            <activity type="work" link="3-4" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)
    assert len(handler.toll_log) == 1
    assert handler.toll_log.iloc[0]['toll']=='10.0'

#using two adjacent toll links non-consecutively should incur charge twice
def test_toll_nonconsecutivelinks(toll_log_handler):
    handler = toll_log_handler

    person = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-3 3-2 2-1</route>
            </leg>
            <activity type="work" link="2-1" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)
    assert len(handler.toll_log) == 2
    assert float(handler.toll_log.iloc[0]['toll'])+ float(handler.toll_log.iloc[1]['toll'])== 20

def test_toll_finalise(toll_log_handler):
    handler = toll_log_handler

    person = """
    <person id="fatema">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-3 3-2 2-1</route>
            </leg>
            <activity type="work" link="2-1" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)
    handler.finalise()
    assert handler.results['tolls_paid_total_by_agent'].sum() == 20

def test_toll_tagged(toll_log_handler):
    handler = toll_log_handler
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    handler.finalise()
    assert handler.results['tolls_paid_log'].iloc[1]['tollname'] == "Toll Road 3"
    assert handler.results['tolls_paid_log'].iloc[3]['tollname'] == "missing"
    return handler


### Trip Log Handler ###

# Normal Case
@pytest.fixture
def agent_trip_handler(test_config, input_manager):
    handler = plan_handlers.TripLogs(test_config, 'all')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.activities_log.chunk) == 0
    assert len(handler.trips_log.chunk) == 0

    return handler


def test_agent_trip_log_process_person(agent_trip_handler):
    handler = agent_trip_handler

    person = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route
             type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)

    assert handler.activities_log.chunk[0]["start_s"] == 0
    assert handler.activities_log.chunk[0]["duration_s"] == 8*60*60
    assert handler.activities_log.chunk[0]["end_s"] == 8*60*60
    assert handler.activities_log.chunk[0]["act"] == "home"

    assert handler.trips_log.chunk[0]["start_s"] == 8*60*60
    assert handler.trips_log.chunk[0]["duration_s"] == 4
    assert handler.trips_log.chunk[0]["end_s"] == 8*60*60 + 4
    assert handler.trips_log.chunk[0]["mode"] == "car"

    assert handler.activities_log.chunk[1]["start_s"] == 8*60*60 + 4
    assert handler.activities_log.chunk[1]["duration_s"] == 17.5*60*60 - (8*60*60 + 4)
    assert handler.activities_log.chunk[1]["end_s"] == 17.5*60*60
    assert handler.activities_log.chunk[1]["act"] == "work"

def test_agent_trip_log_process_pt_bus_person(agent_trip_handler):
    handler = agent_trip_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"

    person = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="1010.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)

    assert handler.activities_log.chunk[0]["start_s"] == 0
    assert handler.activities_log.chunk[0]["duration_s"] == 8*60*60
    assert handler.activities_log.chunk[0]["end_s"] == 8*60*60
    assert handler.activities_log.chunk[0]["act"] == "home"

    assert handler.trips_log.chunk[0]["start_s"] == 8*60*60
    assert handler.trips_log.chunk[0]["duration_s"] == 1.5*60*60
    assert handler.trips_log.chunk[0]["end_s"] == 8*60*60 + 1.5*60*60
    assert handler.trips_log.chunk[0]["mode"] == "bus"

    assert handler.activities_log.chunk[1]["start_s"] == 8*60*60 + 1.5*60*60
    assert handler.activities_log.chunk[1]["duration_s"] == 17.5*60*60 - (8*60*60 + 1.5*60*60)
    assert handler.activities_log.chunk[1]["end_s"] == 17.5*60*60
    assert handler.activities_log.chunk[1]["act"] == "work"


def test_agent_trip_log_process_pt_rail_person(agent_trip_handler):
    handler = agent_trip_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"

    person = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(person)
    handler.process_plans(person)

    assert handler.activities_log.chunk[0]["start_s"] == 0
    assert handler.activities_log.chunk[0]["duration_s"] == 8*60*60
    assert handler.activities_log.chunk[0]["end_s"] == 8*60*60
    assert handler.activities_log.chunk[0]["act"] == "home"

    assert handler.trips_log.chunk[0]["start_s"] == 8*60*60
    assert handler.trips_log.chunk[0]["duration_s"] == 1.5*60*60
    assert handler.trips_log.chunk[0]["end_s"] == 8*60*60 + 1.5*60*60
    assert handler.trips_log.chunk[0]["mode"] == "rail"

    assert handler.activities_log.chunk[1]["start_s"] == 8*60*60 + 1.5*60*60
    assert handler.activities_log.chunk[1]["duration_s"] == 17.5*60*60 - (8*60*60 + 1.5*60*60)
    assert handler.activities_log.chunk[1]["end_s"] == 17.5*60*60
    assert handler.activities_log.chunk[1]["act"] == "work"


def test_agent_trip_log_handler(agent_trip_handler):
    handler = agent_trip_handler

    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert len(handler.activities_log.chunk) == 15
    assert len(handler.trips_log.chunk) == 10


@pytest.fixture
def agent_trip_log_handler_finalised(agent_trip_handler):
    handler = agent_trip_handler
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    handler.finalise()
    return handler


def test_finalised_logs(agent_trip_log_handler_finalised):
    handler = agent_trip_log_handler_finalised

    assert len(handler.results) == 0


# Plans Wrapping case

@pytest.fixture
def agent_trip_log_handler_bad_plans(test_bad_plans_config, input_bad_plans_manager):
    handler = plan_handlers.TripLogs(test_bad_plans_config, 'all')

    resources = input_bad_plans_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.activities_log.chunk) == 0
    assert len(handler.trips_log.chunk) == 0

    return handler


@pytest.fixture
def agent_trips_log_handler_finalised_bad_plans(agent_trip_log_handler_bad_plans):
    handler = agent_trip_log_handler_bad_plans
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    assert handler.activities_log.chunk[-1].get('end_day') == 1
    assert handler.trips_log.chunk[-1].get('end_day') == 1
    handler.finalise()
    return handler


def test_finalised_trips_logs_bad_plans(agent_trips_log_handler_finalised_bad_plans):
    handler = agent_trips_log_handler_finalised_bad_plans
    assert len(handler.results) == 0


# Plan Handler ###
@pytest.fixture
def agent_plan_handler(test_bad_plans_config, input_manager):
    handler = plan_handlers.PlanLogs(test_bad_plans_config, 'poor')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)
    assert len(handler.plans_log.chunk) == 0
    return handler


def test_agent_plans_handler(agent_plan_handler):
    handler = agent_plan_handler

    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert len(handler.plans_log.chunk) == 8


@pytest.fixture
def agent_plans_handler_finalised(agent_plan_handler):
    handler = agent_plan_handler
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    handler.finalise()
    return handler


def test_finalised_plans(agent_plans_handler_finalised):
    handler = agent_plans_handler_finalised

    assert len(handler.results) == 0


# Plans Wrapping case

# Bad Config (plans wrap past 24hrs)
@pytest.fixture
def agent_plans_handler_bad_plans(test_bad_plans_config, input_bad_plans_manager):
    handler = plan_handlers.PlanLogs(test_bad_plans_config, 'poor')

    resources = input_bad_plans_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.plans_log.chunk) == 0
    return handler


# @pytest.fixture
# def agent_plans_handler_finalised_bad_plans(agent_plans_handler_bad_plans):
#     handler = agent_plans_handler_bad_plans
#     plans = handler.resources['plans']
#     for plan in plans.persons:
#         handler.process_plans(plan)
#     assert handler.plans_log.chunk[-1].get('end_day') == 1
#     handler.finalise()
#     return handler


# def test_finalised_plans_bad_plans(agent_plans_handler_finalised_bad_plans):
#     handler = agent_plans_handler_finalised_bad_plans
#     assert len(handler.results) == 0


### Agent Highway Distance Handler ###
@pytest.fixture
def agent_distances_handler_car_mode(test_config, input_manager):
    handler = plan_handlers.AgentHighwayDistanceLogs(test_config, 'car')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.agent_ids) == len(handler.resources['subpopulations'].map)
    assert list(handler.agent_indices.keys()) == handler.agent_ids

    assert len(handler.ways) == len(handler.resources['osm_ways'].classes)
    assert list(handler.ways_indices.keys()) == handler.ways

    assert handler.distances.shape == (
        len(handler.resources['subpopulations'].map),
        len(handler.resources['osm_ways'].classes)
    )

    return handler


def test_agent_distances_handler_car_mode(agent_distances_handler_car_mode):
    handler = agent_distances_handler_car_mode

    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert np.sum(handler.distances) == 40600.0

    # agent
    assert np.sum(handler.distances[handler.agent_indices['chris']]) == 20400.0

    # class
    assert np.sum(handler.distances[:, handler.ways_indices['trunk']]) == 30600.0


@pytest.fixture
def agent_distances_handler_finalised_car(agent_distances_handler_car_mode):
    handler = agent_distances_handler_car_mode
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    handler.finalise()
    return handler


def test_finalised_agent_distances_car(agent_distances_handler_finalised_car):
    handler = agent_distances_handler_finalised_car

    for name, result in handler.results.items():
        cols = handler.ways
        if 'total' in name:
            for c in cols:
                assert c in result.index
            assert 'total' in result.index
            assert np.sum(result[cols].values) == 40600.0

        else:
            for c in cols:
                assert c in result.columns
            assert 'total' in result.columns
            df = result.loc[:, cols]
            assert np.sum(df.values) == 40600.0


### Trips Highway Distance Handler ###
@pytest.fixture
def trip_distances_handler_car_mode(test_config, input_manager):
    handler = plan_handlers.TripHighwayDistanceLogs(test_config, 'car')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    assert len(handler.ways) == len(handler.resources['osm_ways'].classes)

    return handler


def test_trip_distances_handler_car_mode(trip_distances_handler_car_mode):
    handler = trip_distances_handler_car_mode

    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert len(handler.distances_log.chunk) == 10
    assert sum([d['None'] for d in handler.distances_log.chunk]) == 10000
    assert sum([d['trunk'] for d in handler.distances_log.chunk]) == 30600

    # agent
    assert sum([d['trunk'] for d in handler.distances_log.chunk if d['agent'] == 'chris']) == 20400.0


def test_trip_distances_handler_finalised_car(trip_distances_handler_car_mode):
    handler = trip_distances_handler_car_mode
    plans = handler.resources['plans']
    for plan in plans.persons:
        handler.process_plans(plan)
    handler.finalise()

    path = handler.distances_log.path
    results = pd.read_csv(path)
    assert len(results) == 10
    assert sum(results.trunk) == 30600
    assert sum(results.loc[results.agent == 'chris'].trunk) == 20400


### Trip Modeshare Handlers ###
@pytest.fixture
def test_trip_modeshare_handler(test_config, input_manager):
    handler = plan_handlers.TripModes(test_config, mode='all', groupby_person_attribute="subpopulation")

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    # assert len(handler.modes) == len(handler.resources['output_config'].modes)
    assert list(handler.mode_indices.keys()) == handler.modes

    assert len(handler.classes) == 3
    assert set(handler.class_indices.keys()) == {"rich", "poor", None}

    assert handler.mode_counts.shape == (6, 3, 24)

    return handler


def test_trip_mode_share_simple(test_trip_modeshare_handler):
    handler = test_trip_modeshare_handler
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 1


def test_trip_mode_share_pt(test_trip_modeshare_handler):
    handler = test_trip_modeshare_handler
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 1


def test_trip_distance_mode_share_complex_pt_1(test_trip_modeshare_handler):
    handler = test_trip_modeshare_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"
    modes = handler.modes + ['rail']
    handler.modes, handler.mode_indices = handler.generate_id_map(modes)
    handler.mode_counts = np.zeros((len(handler.modes),
                                    len(handler.classes),
                                    handler.config.time_periods))
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['rail']]) == 1


def test_trip_distance_mode_share_complex_pt_2(test_trip_modeshare_handler):
    handler = test_trip_modeshare_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"
    modes = handler.modes + ['rail']
    handler.modes, handler.mode_indices = handler.generate_id_map(modes)
    handler.mode_counts = np.zeros((len(handler.modes),
                                    len(handler.classes),
                                    handler.config.time_periods))
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 1


### Modeshare Handler No Attribute Slices###
@pytest.fixture
def test_trip_modeshare_handler_no_attribute_slice(test_config_v12, input_manager):
    handler = plan_handlers.TripModes(test_config_v12, mode='all')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    # assert len(handler.modes) == len(handler.resources['output_config'].modes)
    assert list(handler.mode_indices.keys()) == handler.modes

    assert len(handler.classes) == 1
    assert list(handler.class_indices.keys()) == [None]

    assert handler.mode_counts.shape == (6, 1, 24)

    return handler


def test_trip_mode_share_without_attribute_slice(test_trip_modeshare_handler_no_attribute_slice):
    handler = test_trip_modeshare_handler_no_attribute_slice
    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 1


### Modeshare Handler With Attribute Slices###
@pytest.fixture
def test_trip_modeshare_handler_age_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.TripModes(test_config_v12, mode='all', groupby_person_attribute="age")

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    # assert len(handler.modes) == len(handler.resources['output_config'].modes)
    assert list(handler.mode_indices.keys()) == handler.modes

    assert len(handler.classes) == 3
    assert set(handler.classes) == {"yes", "no", None}

    assert handler.mode_counts.shape == (6, 3, 24)

    return handler


def test_trip_mode_share_without_attribute_slice(test_trip_modeshare_handler_age_attribute_slice):
    handler = test_trip_modeshare_handler_age_attribute_slice
    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">young</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    string = """
    <person id="chris">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">old</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['car'], handler.class_indices['yes']]) == 1

def test_trip_handler_test_data(test_trip_modeshare_handler):
    handler = test_trip_modeshare_handler

    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert np.sum(handler.mode_counts) == 10

    # mode
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 4
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 4
    assert np.sum(handler.mode_counts[handler.mode_indices['bike']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['walk']]) == 0

    # class
    assert np.sum(handler.mode_counts[:, handler.class_indices['rich'], :]) == 2
    assert np.sum(handler.mode_counts[:, handler.class_indices['poor'], :]) == 8
    # assert np.sum(handler.mode_counts[:, handler.class_indices['not_applicable'], :, :]) == 0

    # time
    assert np.sum(handler.mode_counts[:, :, :12]) == 5
    assert np.sum(handler.mode_counts[:, :, 12:]) == 5


@pytest.fixture
def test_trip_modeshares_handler_finalised(test_trip_modeshare_handler):
    handler = test_trip_modeshare_handler
    plans = handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)
    handler.finalise()
    return handler


def test_finalised_trip_mode_counts(test_trip_modeshares_handler_finalised):
    handler = test_trip_modeshares_handler_finalised

    for name, result in handler.results.items():
        if 'counts' in name:
            if isinstance(result, pd.DataFrame):
                assert result["count"].sum() == 10 / handler.config.scale_factor
            else:
                assert result.sum() == 10 / handler.config.scale_factor

        else:
            if isinstance(result, pd.DataFrame):
                assert result.share.sum() == 1
            else:
                assert result.sum() == 1


### TripDestinationModeShare Modeshare Handler No Attribute Slices###
@pytest.fixture
def test_trip_activity_modeshare_handler_without_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.TripActivityModes(test_config_v12, mode='all', destination_activity_filters = ["work_a","work_b"])

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 1
    assert list(handler.class_indices.keys()) == [None]

    assert handler.mode_counts.shape == (6, 1, 24)

    return handler


@pytest.fixture
def test_trip_pt_interaction_modeshare_handler_without_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.TripActivityModes(test_config_v12, mode='all', destination_activity_filters = ["pt interaction"])

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 1
    assert list(handler.class_indices.keys()) == [None]

    assert handler.mode_counts.shape == (6, 1, 24)

    return handler


def test_trip_activity_mode_share_without_attribute_slice_with_activities_simple(test_trip_activity_modeshare_handler_without_attribute_slice):
    handler = test_trip_activity_modeshare_handler_without_attribute_slice
    string = """
    <person id="alex">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 1


def test_trip_activity_mode_share_without_attribute_slice_with_activities_complex(test_trip_activity_modeshare_handler_without_attribute_slice):
    handler = test_trip_activity_modeshare_handler_without_attribute_slice
    string = """
    <person id="varun">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10200.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="18:00:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    string = """
    <person id="alex">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10200.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="shop" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:40:00" >
            </activity>

        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    string = """
    <person id="george">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="12:30:00" >
            </activity>
            <leg mode="walk" trav_time="00:01:18">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="generic" start_link="1-5" end_link="1-3" trav_time="00:01:18" distance="10100.0"></route>
            </leg>
            <activity type="pt interaction" link="1-3" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="bus" trav_time="00:43:42">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="default_pt" start_link="1-3" end_link="3-4" trav_time="00:43:42" distance="10200.0">
                {"transitRouteId":"work_bound","boardingTime":"08:30:00","transitLineId":"city_line","accessFacilityId":"home_stop_out","egressFacilityId":"work_stop_in"}
                </route>
            </leg>
            <activity type="pt interaction" link="3-4" x="130.0" y="0.0" max_dur="00:00:00" >
            </activity>
           <leg mode="walk" trav_time="00:01:18">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="generic" start_link="3-4" end_link="4-3" trav_time="00:01:18" distance="10100.0"></route>
            </leg>
            <activity type="work_b" link="4-3" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['walk']]) == 3

def test_trip_activity_mode_share_without_attribute_slice_with_activities_pt_interaction(test_trip_pt_interaction_modeshare_handler_without_attribute_slice):
    handler = test_trip_pt_interaction_modeshare_handler_without_attribute_slice

    string = """
    <person id="george">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="12:30:00" >
            </activity>
            <leg mode="walk" trav_time="00:01:18">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="generic" start_link="1-5" end_link="1-3" trav_time="00:01:18" distance="10100.0"></route>
            </leg>
            <activity type="pt interaction" link="1-3" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="bus" trav_time="00:43:42">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="default_pt" start_link="1-3" end_link="3-4" trav_time="00:43:42" distance="10200.0">
                {"transitRouteId":"work_bound","boardingTime":"08:30:00","transitLineId":"city_line","accessFacilityId":"home_stop_out","egressFacilityId":"work_stop_in"}
                </route>
            </leg>
            <activity type="pt interaction" link="3-4" x="130.0" y="0.0" max_dur="00:00:00" >
            </activity>
           <leg mode="walk" trav_time="00:01:18">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="generic" start_link="3-4" end_link="4-3" trav_time="00:01:18" distance="10100.0"></route>
            </leg>
            <activity type="work_b" link="4-3" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 0
    assert np.sum(handler.mode_counts[handler.mode_indices['walk']]) == 1
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 1


@pytest.fixture
def test_trip_work_and_education_activity_modeshare_handler(test_config, input_manager):
    handler = plan_handlers.TripActivityModes(test_config, mode='all', groupby_person_attribute="subpopulation", destination_activity_filters=["work", "education"])

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)
    periods = 24
    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 3
    assert set(handler.class_indices.keys()) == {"rich", "poor", None}
    assert handler.mode_counts.shape == (6, 3, 24)
    return handler


def test_trip_work_mode_share_with_destination_activities_filter(test_trip_work_and_education_activity_modeshare_handler):
    handler = test_trip_work_and_education_activity_modeshare_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"
    modes = handler.modes + ['rail']
    handler.modes, handler.mode_indices = handler.generate_id_map(modes)
    handler.mode_counts = np.zeros((len(handler.modes),
                                    len(handler.classes),
                                    handler.config.time_periods))
    stringA = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    stringB = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="education" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    personA = etree.fromstring(stringA)
    personB = etree.fromstring(stringB)
    handler.process_plans(personA)
    handler.process_plans(personB)
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 2


### TripDestinationModeShare Handler With Attribute Slices###
@pytest.fixture
def test_trip_activity_modeshare_handler_age_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.TripActivityModes(
        test_config_v12,
        mode='all',
        destination_activity_filters = ["work_a","work_b"],
        groupby_person_attribute="age"
        )

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    # assert len(handler.modes) == len(handler.resources['output_config'].modes)
    assert list(handler.mode_indices.keys()) == handler.modes

    assert len(handler.classes) == 3
    assert set(handler.classes) == {"yes", "no", None}

    assert handler.mode_counts.shape == (6, 3, 24)

    return handler

def test_trip_activity_mode_share_with_attribute_slice(test_trip_activity_modeshare_handler_age_attribute_slice):
    handler = test_trip_activity_modeshare_handler_age_attribute_slice
    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">yes</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    string = """
    <person id="chris">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    # mode
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['car'], handler.class_indices['yes']]) == 1

    # class
    assert np.sum(handler.mode_counts[:, handler.class_indices['yes'], :]) == 1
    assert np.sum(handler.mode_counts[:, handler.class_indices['no'], :]) == 1


@pytest.fixture
def test_trip_activity_modeshare_plan_handler_finalised(test_trip_activity_modeshare_handler_age_attribute_slice):
    handler = test_trip_activity_modeshare_handler_age_attribute_slice
    # plans = test_plan_activity_modeshare_handler_age_attribute_slice.resources['plans']

    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">yes</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    string = """
    <person id="chris">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="bike" dep_time="17:30:00" trav_time="00:52:31">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bike</attribute>
                </attributes>
                <route type="generic" start_link="3-4" end_link="1-2" trav_time="00:52:31" distance="13130.0"></route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    handler.finalise()
    return handler

def test_trip_activity_finalised_mode_counts(test_trip_activity_modeshare_plan_handler_finalised):
    handler = test_trip_activity_modeshare_plan_handler_finalised
    for name, result in handler.results.items():
        if 'counts' in name:
            if isinstance(result, pd.DataFrame):
                assert result["count"].sum() == 2 / handler.config.scale_factor
            else:
                assert result.sum() == 2 / handler.config.scale_factor

        else:
            if isinstance(result, pd.DataFrame):
                assert result.share.sum() == 1
            else:
                assert result.sum() == 1


### Plan Modeshare Handlers ###
@pytest.fixture
def test_plan_modeshare_handler(test_config, input_manager):
    handler = plan_handlers.PlanModes(test_config, mode='all', groupby_person_attribute="subpopulation")

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)
    periods = 24
    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 3
    assert set(handler.class_indices.keys()) == {"rich", "poor", None}
    assert handler.mode_counts.shape == (6, 3, 24)
    return handler


def test_plan_mode_share_simple(test_plan_modeshare_handler):
    handler = test_plan_modeshare_handler
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 1


def test_plan_mode_share_pt(test_plan_modeshare_handler):
    handler = test_plan_modeshare_handler
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 1


def test_plan_mode_share_complex_pt_1(test_plan_modeshare_handler):
    handler = test_plan_modeshare_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"
    modes = handler.modes + ['rail']
    handler.modes, handler.mode_indices = handler.generate_id_map(modes)
    handler.mode_counts = np.zeros((len(handler.modes),
                                    len(handler.classes),
                                    handler.config.time_periods))
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['rail']]) == 1


def test_distance_mode_share_complex_pt_2(test_plan_modeshare_handler):
    handler = test_plan_modeshare_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"
    modes = handler.modes + ['rail']
    handler.modes, handler.mode_indices = handler.generate_id_map(modes)
    handler.mode_counts = np.zeros((len(handler.modes),
                                    len(handler.classes),
                                    handler.config.time_periods))
    string = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 1


### Modeshare Handler No Attribute Slices###
@pytest.fixture
def test_plan_modeshare_handler_no_attribute_slice(test_config_v12, input_manager):
    handler = plan_handlers.PlanModes(test_config_v12, mode='all')

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)
    periods = 24
    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 1
    assert list(handler.class_indices.keys()) == [None]
    assert handler.mode_counts.shape == (6, 1, 24)
    return handler


def test_plan_mode_share_without_attribute_slice(test_plan_modeshare_handler_no_attribute_slice):
    handler = test_plan_modeshare_handler_no_attribute_slice
    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
            <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 1


### Modeshare Handler With Attribute Slices###
@pytest.fixture
def test_plan_modeshare_handler_age_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.TripModes(test_config_v12, mode='all', groupby_person_attribute="age")

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)
    periods = 24
    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 3
    assert set(handler.classes) == {"yes", "no", None}
    assert handler.mode_counts.shape == (6, 3, 24)
    return handler


def test_plan_mode_share_without_attribute_slice(test_plan_modeshare_handler_age_attribute_slice):
    handler = test_plan_modeshare_handler_age_attribute_slice
    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">young</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    string = """
    <person id="chris">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">old</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['car'], handler.class_indices['yes']]) == 1

def test_plan_handler_test_data(test_plan_modeshare_handler):
    handler = test_plan_modeshare_handler

    plans = test_plan_modeshare_handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)

    assert np.sum(handler.mode_counts) == 5

    # mode
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['bike']]) == 1
    assert np.sum(handler.mode_counts[handler.mode_indices['walk']]) == 0

    # class
    assert np.sum(handler.mode_counts[:, handler.class_indices['rich'], :]) == 1
    assert np.sum(handler.mode_counts[:, handler.class_indices['poor'], :]) == 4


@pytest.fixture
def test_plan_handler_finalised(test_plan_modeshare_handler):
    handler = test_plan_modeshare_handler
    plans = test_plan_modeshare_handler.resources['plans']
    for person in plans.persons:
        handler.process_plans(person)
    handler.finalise()
    return handler


def test_finalised_plan_mode_counts(test_plan_handler_finalised):
    handler = test_plan_handler_finalised

    for name, result in handler.results.items():
        if 'counts' in name:
            if isinstance(result, pd.DataFrame):
                assert result["count"].sum() == 5 / handler.config.scale_factor
            else:
                assert result.sum() == 5 / handler.config.scale_factor

        else:
            if isinstance(result, pd.DataFrame):
                assert result.share.sum() == 1
            else:
                assert result.sum() == 1


### TripDestinationModeShare Modeshare Handler No Attribute Slices###
@pytest.fixture
def test_plan_activity_modeshare_handler_without_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.TripActivityModes(test_config_v12, mode='all', destination_activity_filters = ["work_a","work_b"])

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 1
    assert list(handler.class_indices.keys()) == [None]

    assert handler.mode_counts.shape == (6, 1, 24)

    return handler

def test_activity_plan_mode_share_without_attribute_slice_with_activities_simple(test_plan_activity_modeshare_handler_without_attribute_slice):
    handler = test_plan_activity_modeshare_handler_without_attribute_slice
    string = """
    <person id="alex">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 1

def test_activity_plan_mode_share_without_attribute_slice_with_activities_complex(test_plan_activity_modeshare_handler_without_attribute_slice):
    handler = test_plan_activity_modeshare_handler_without_attribute_slice
    string = """
    <person id="varun">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10200.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="18:00:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    string = """
    <person id="alex">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10200.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="shop" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:40:00" >
            </activity>

        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    string = """
    <person id="george">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="12:30:00" >
            </activity>
            <leg mode="walk" trav_time="00:01:18">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="generic" start_link="1-5" end_link="1-3" trav_time="00:01:18" distance="10100.0"></route>
            </leg>
            <activity type="pt interaction" link="1-3" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="bus" trav_time="00:43:42">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="default_pt" start_link="1-3" end_link="3-4" trav_time="00:43:42" distance="10200.0">
                {"transitRouteId":"work_bound","boardingTime":"08:30:00","transitLineId":"city_line","accessFacilityId":"home_stop_out","egressFacilityId":"work_stop_in"}
                </route>
            </leg>
            <activity type="pt interaction" link="3-4" x="130.0" y="0.0" max_dur="00:00:00" >
            </activity>
           <leg mode="walk" trav_time="00:01:18">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bus</attribute>
                </attributes>
                <route type="generic" start_link="3-4" end_link="4-3" trav_time="00:01:18" distance="10100.0"></route>
            </leg>
            <activity type="work_b" link="4-3" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['walk']]) == 3


@pytest.fixture
def test_work_and_education_plan_activity_modeshare_handler(test_config, input_manager):
    handler = plan_handlers.TripActivityModes(test_config, mode='all', groupby_person_attribute="subpopulation", destination_activity_filters=["work", "education"])

    resources = input_manager.resources
    handler.build(resources, write_path=test_outputs)
    periods = 24
    assert list(handler.mode_indices.keys()) == handler.modes
    assert len(handler.classes) == 3
    assert set(handler.class_indices.keys()) == {"rich", "poor", None}
    assert handler.mode_counts.shape == (6, 3, 24)
    return handler


def test_work_plan_mode_share_with_destination_activities_filter(test_work_and_education_plan_activity_modeshare_handler):
    handler = test_work_and_education_plan_activity_modeshare_handler
    handler.resources['transit_schedule'].route_to_mode_map["rail_dummy"] = "rail"
    modes = handler.modes + ['rail']
    handler.modes, handler.mode_indices = handler.generate_id_map(modes)
    handler.mode_counts = np.zeros((len(handler.modes),
                                    len(handler.classes),
                                    handler.config.time_periods))
    stringA = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="work" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    stringB = """
    <person id="nick">
        <plan score="1" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="1-2" end_link="1-2" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="pt interaction" link="1-2" x="50.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10101.0">PT1===home_stop_out===city_line===work_bound===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="pt" trav_time="00:43:42">
                <route type="experimentalPt1" start_link="1-2" end_link="3-4" trav_time="00:43:42" distance="10100.0">PT1===home_stop_out===rail_dummy===rail_dummy===work_stop_in</route>
            </leg>
            <activity type="pt interaction" link="3-4" x="10050.0" y="0.0" max_dur="00:00:00" >
            </activity>
            <leg mode="transit_walk" trav_time="00:01:18">
                <route type="generic" start_link="3-4" end_link="3-4" trav_time="00:01:18" distance="65.0"></route>
            </leg>
            <activity type="education" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    personA = etree.fromstring(stringA)
    personB = etree.fromstring(stringB)
    handler.process_plans(personA)
    handler.process_plans(personB)
    assert np.sum(handler.mode_counts[handler.mode_indices['bus']]) == 2


### PlanActivityModeShare Handler With Attribute Slices###
@pytest.fixture
def test_plan_activity_modeshare_handler_age_attribute_slice(test_config_v12, input_manager_v12):
    handler = plan_handlers.PlanActivityModes(
        test_config_v12,
        mode='all',
        destination_activity_filters = ["work_a","work_b"],
        groupby_person_attribute="age"
        )

    resources = input_manager_v12.resources
    handler.build(resources, write_path=test_outputs)

    periods = 24

    # assert len(handler.modes) == len(handler.resources['output_config'].modes)
    assert list(handler.mode_indices.keys()) == handler.modes

    assert len(handler.classes) == 3
    assert set(handler.classes) == {"yes", "no", None}

    assert handler.mode_counts.shape == (6, 3, 24)

    return handler

def test_plan_activity_mode_share_with_attribute_slice(test_plan_activity_modeshare_handler_age_attribute_slice):
    handler = test_plan_activity_modeshare_handler_age_attribute_slice
    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">yes</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    string = """
    <person id="chris">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)
    # mode
    assert np.sum(handler.mode_counts[handler.mode_indices['car']]) == 2
    assert np.sum(handler.mode_counts[handler.mode_indices['car'], handler.class_indices['yes']]) == 1

    # class
    assert np.sum(handler.mode_counts[:, handler.class_indices['yes'], :]) == 1
    assert np.sum(handler.mode_counts[:, handler.class_indices['no'], :]) == 1


@pytest.fixture
def test_plan_activity_modeshare_plan_handler_finalised(test_plan_activity_modeshare_handler_age_attribute_slice):
    handler = test_plan_activity_modeshare_handler_age_attribute_slice
    # plans = test_plan_activity_modeshare_handler_age_attribute_slice.resources['plans']

    string = """
    <person id="nick">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">yes</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="car" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">car</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_a" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
            <leg mode="bike" dep_time="08:00:00" trav_time="00:00:04">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bike</attribute>
                </attributes>
                <route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="100.0">1-2 2-1 1-5</route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    string = """
    <person id="chris">
        <attributes>
            <attribute name="subpopulation" class="java.lang.String">poor</attribute>
            <attribute name="age" class="java.lang.String">no</attribute>
        </attributes>
        <plan score="129.592238766919" selected="yes">
            <activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
            </activity>
            <leg mode="bike" dep_time="17:30:00" trav_time="00:52:31">
                <attributes>
                    <attribute name="routingMode" class="java.lang.String">bike</attribute>
                </attributes>
                <route type="generic" start_link="3-4" end_link="1-2" trav_time="00:52:31" distance="13130.0"></route>
            </leg>
            <activity type="work_b" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
            </activity>
        </plan>
    </person>
    """
    person = etree.fromstring(string)
    handler.process_plans(person)

    handler.finalise()
    return handler

def test_plan_activity_finalised_mode_counts(test_plan_activity_modeshare_plan_handler_finalised):
    handler = test_plan_activity_modeshare_plan_handler_finalised
    for name, result in handler.results.items():
        if 'counts' in name:
            if isinstance(result, pd.DataFrame):
                assert result["count"].sum() == 2 / handler.config.scale_factor
            else:
                assert result.sum() == 2 / handler.config.scale_factor

        else:
            if isinstance(result, pd.DataFrame):
                assert result.share.sum() == 1
            else:
                assert result.sum() == 1

# Plan Handler Manager
def test_load_workstation_with_trip_modes(test_config, test_paths):
    input_workstation = InputsWorkStation(test_config)
    input_workstation.connect(managers=None, suppliers=[test_paths])
    input_workstation.load_all_tools()
    input_workstation.build()

    plan_workstation = PlanHandlerWorkStation(test_config)
    plan_workstation.connect(managers=None, suppliers=[input_workstation])

    # mode_share
    tool = plan_workstation.tools['trip_modes']
    plan_workstation.resources['trip_modes'] = tool(
        test_config,
        mode='all',
        groupby_person_attribute="subpopulation"
        )

    # detination based mode_share
    tool = plan_workstation.tools['trip_activity_modes']
    plan_workstation.resources['trip_activity_modes'] = tool(
        test_config,
        'all',
        destination_activity_filters=["work"]
    )

     # detination and attribute based mode_share
    tool = plan_workstation.tools['trip_activity_modes']
    plan_workstation.resources['trip_activity_modes'] = tool(
        test_config,
        'all',
        destination_activity_filters=["work"],
        groupby_person_attribute = "subpopulation"
    )

    plan_workstation.build(write_path=test_outputs)

    assert os.path.exists(os.path.join(test_outputs, "trip_modes_all_detailed_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_modes_all_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_modes_all_detailed_shares.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_modes_all_shares.csv"))

    assert os.path.exists(os.path.join(test_outputs, "trip_activity_modes_all_work_detailed_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_activity_modes_all_work_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_activity_modes_all_work_shares.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_activity_modes_all_work_detailed_shares.csv"))

    assert os.path.exists(os.path.join(test_outputs, "trip_activity_modes_all_work_subpopulation_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_activity_modes_all_work_subpopulation_shares.csv"))


def test_load_workstation_with_plan_modes(test_config, test_paths):
    input_workstation = InputsWorkStation(test_config)
    input_workstation.connect(managers=None, suppliers=[test_paths])
    input_workstation.load_all_tools()
    input_workstation.build()

    plan_workstation = PlanHandlerWorkStation(test_config)
    plan_workstation.connect(managers=None, suppliers=[input_workstation])

    # mode_share
    tool = plan_workstation.tools['plan_modes']
    plan_workstation.resources['plan_modes'] = tool(
        test_config,
        mode='all',
        groupby_person_attribute="subpopulation"
        )

    # detination based mode_share
    tool = plan_workstation.tools['plan_activity_modes']
    plan_workstation.resources['plan_activity_modes'] = tool(
        test_config,
        'all',
        destination_activity_filters=["work"]
    )

     # detination and attribute based mode_share
    tool = plan_workstation.tools['plan_activity_modes']
    plan_workstation.resources['plan_activity_modes'] = tool(
        test_config,
        'all',
        destination_activity_filters=["work"],
        groupby_person_attribute = "subpopulation"
    )

    plan_workstation.build(write_path=test_outputs)

    assert os.path.exists(os.path.join(test_outputs, "plan_modes_all_detailed_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_modes_all_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_modes_all_detailed_shares.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_modes_all_shares.csv"))

    assert os.path.exists(os.path.join(test_outputs, "plan_activity_modes_all_work_detailed_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_activity_modes_all_work_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_activity_modes_all_work_shares.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_activity_modes_all_work_detailed_shares.csv"))

    assert os.path.exists(os.path.join(test_outputs, "plan_activity_modes_all_work_subpopulation_counts.csv"))
    assert os.path.exists(os.path.join(test_outputs, "plan_activity_modes_all_work_subpopulation_shares.csv"))


def test_load_workstation_with_logs(test_config, test_paths):
    input_workstation = InputsWorkStation(test_config)
    input_workstation.connect(managers=None, suppliers=[test_paths])
    input_workstation.load_all_tools()
    input_workstation.build()

    plan_workstation = PlanHandlerWorkStation(test_config)
    plan_workstation.connect(managers=None, suppliers=[input_workstation])

    # leg_logs
    plan_workstation.resources['leg_logs'] = plan_workstation.tools['leg_logs'](
        test_config,
        mode='all',
        )

    # trip_logs
    plan_workstation.resources['trip_logs'] = plan_workstation.tools['trip_logs'](
        test_config,
        mode='all',
        )

    plan_workstation.build(write_path=test_outputs)

    assert os.path.exists(os.path.join(test_outputs, "leg_logs_all_legs.csv"))
    assert os.path.exists(os.path.join(test_outputs, "leg_logs_all_activities.csv"))

    assert os.path.exists(os.path.join(test_outputs, "trip_logs_all_trips.csv"))
    assert os.path.exists(os.path.join(test_outputs, "trip_logs_all_activities.csv"))

def test_non_zero_pt_interaction_legs(agent_leg_log_handler):
    """ PT interaction activity has non-zero duration """

    handler = agent_leg_log_handler

    person = """
	<person id="interaction_duration">
		<attributes>
			<attribute name="subpopulation" class="java.lang.String">poor</attribute>
			<attribute name="age" class="java.lang.String">no</attribute>
		</attributes>
		<plan score="129.592238766919" selected="yes">
			<activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
			</activity>
			<leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
			</leg>
			<activity type="pt interaction" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
			</activity>
			<leg mode="walk" dep_time="17:30:00" trav_time="00:07:34">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-5" end_link="1-2" trav_time="00:07:34" distance="10100.0">1-5 5-1 1-2</route>
			</leg>
			<activity type="home" link="1-2" x="0.0" y="0.0" >
			</activity>
		</plan>
	</person>
    """

    person = etree.fromstring(person)
    handler.process_plans(person)
    assert handler.legs_log.chunk[-1]['start_s'] == 63000

def test_zero_pt_interaction_legs(agent_leg_log_handler):
    """ PT interaction activity has zero duration (not 'end_time' attribute in the 'pt interaction' activity ) """

    handler = agent_leg_log_handler

    person = """
	<person id="zero_interaction_duration">
		<attributes>
			<attribute name="subpopulation" class="java.lang.String">poor</attribute>
			<attribute name="age" class="java.lang.String">no</attribute>
		</attributes>
		<plan score="129.592238766919" selected="yes">
			<activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
			</activity>
			<leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
			</leg>
			<activity type="pt interaction" link="1-5" x="0.0" y="10000.0">
			</activity>
			<leg mode="walk" dep_time="08:00:04" trav_time="00:07:34">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-5" end_link="1-2" trav_time="00:07:34" distance="10100.0">1-5 5-1 1-2</route>
			</leg>
			<activity type="home" link="1-2" x="0.0" y="0.0" >
			</activity>
		</plan>
	</person>
    """

    person = etree.fromstring(person)
    handler.process_plans(person)
    assert handler.legs_log.chunk[-1]['start_s'] == 28804


def test_non_zero_pt_interaction_trips(agent_trip_handler):
    """ PT interaction activity has non-zero duration """

    handler = agent_trip_handler

    person = """
	<person id="interaction_duration">
		<attributes>
			<attribute name="subpopulation" class="java.lang.String">poor</attribute>
			<attribute name="age" class="java.lang.String">no</attribute>
		</attributes>
		<plan score="129.592238766919" selected="yes">
			<activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
			</activity>
			<leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
			</leg>
			<activity type="pt interaction" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
			</activity>
			<leg mode="walk" dep_time="17:30:00" trav_time="00:07:34">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-5" end_link="1-2" trav_time="00:07:34" distance="10100.0">1-5 5-1 1-2</route>
			</leg>
			<activity type="home" link="1-2" x="0.0" y="0.0" >
			</activity>
		</plan>
	</person>
    """

    person = etree.fromstring(person)
    handler.process_plans(person)
    assert handler.trips_log.chunk[-1]['end_s'] == 63454

def test_zero_pt_interaction_trips(agent_trip_handler):
    """ PT interaction activity has zero duration """

    handler = agent_trip_handler

    person = """
	<person id="interaction_duration">
		<attributes>
			<attribute name="subpopulation" class="java.lang.String">poor</attribute>
			<attribute name="age" class="java.lang.String">no</attribute>
		</attributes>
		<plan score="129.592238766919" selected="yes">
			<activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
			</activity>
			<leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
			</leg>
			<activity type="pt interaction" link="1-5" x="0.0" y="10000.0">
			</activity>
			<leg mode="walk" dep_time="08:00:04" trav_time="00:07:34">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-5" end_link="1-2" trav_time="00:07:34" distance="10100.0">1-5 5-1 1-2</route>
			</leg>
			<activity type="home" link="1-2" x="0.0" y="0.0" >
			</activity>
		</plan>
	</person>
    """

    person = etree.fromstring(person)
    handler.process_plans(person)
    assert handler.trips_log.chunk[-1]['end_s'] == 29258


def test_non_zero_pt_interaction_plan(agent_plan_handler):
    """ PT interaction activity has non-zero duration, plan logs """

    handler = agent_plan_handler

    person = """
	<person id="nick">
		<attributes>
			<attribute name="subpopulation" class="java.lang.String">poor</attribute>
			<attribute name="age" class="java.lang.String">no</attribute>
		</attributes>
		<plan score="129.592238766919" selected="yes">
			<activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
			</activity>
			<leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
			</leg>
			<activity type="pt interaction" link="1-5" x="0.0" y="10000.0" end_time="17:30:00" >
			</activity>
			<leg mode="walk" dep_time="17:30:00" trav_time="00:07:34">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-5" end_link="1-2" trav_time="00:07:34" distance="10100.0">1-5 5-1 1-2</route>
			</leg>
			<activity type="home" link="1-2" x="0.0" y="0.0" >
			</activity>
		</plan>
	</person>
    """
    
    person = etree.fromstring(person)
    handler.process_plans(person)
    assert len(handler.plans_log.chunk) == 1
    assert handler.plans_log.chunk[0]['act_duration'] == 22945
    assert handler.plans_log.chunk[0]['start'] == 28800

def test_zero_pt_interaction_plan(agent_plan_handler):
    """ PT interaction activity has zero duration, plan logs """

    handler = agent_plan_handler

    person = """
	<person id="nick">
		<attributes>
			<attribute name="subpopulation" class="java.lang.String">poor</attribute>
			<attribute name="age" class="java.lang.String">no</attribute>
		</attributes>
		<plan score="129.592238766919" selected="yes">
			<activity type="home" link="1-2" x="0.0" y="0.0" end_time="08:00:00" >
			</activity>
			<leg mode="walk" dep_time="08:00:00" trav_time="00:00:04">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-2" end_link="1-5" trav_time="00:00:04" distance="10100.0">1-2 2-1 1-5</route>
			</leg>
			<activity type="pt interaction" link="1-5" x="0.0" y="10000.0">
			</activity>
			<leg mode="walk" dep_time="08:00:04" trav_time="00:07:34">
				<attributes>
					<attribute name="routingMode" class="java.lang.String">car</attribute>
				</attributes>
				<route type="links" start_link="1-5" end_link="1-2" trav_time="00:07:34" distance="10100.0">1-5 5-1 1-2</route>
			</leg>
			<activity type="home" link="1-2" x="0.0" y="0.0" >
			</activity>
		</plan>
	</person>
    """
    
    person = etree.fromstring(person)
    handler.process_plans(person)
    assert len(handler.plans_log.chunk) == 1
    assert handler.plans_log.chunk[0]['act_duration'] == 57141
    assert handler.plans_log.chunk[0]['start'] == 28800