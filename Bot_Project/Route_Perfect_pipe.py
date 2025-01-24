#!/usr/bin/env python
# coding: utf-8

# In[36]:


import json
import math
import numpy as np
from decimal import Decimal
import time
from datetime import datetime, timedelta
import requests
import psycopg2
import openrouteservice
import spacy
from spacy.matcher import PhraseMatcher
from word2number import w2n
import scipy
import sklearn
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from spacy.language import Language
from spacy.matcher import PhraseMatcher
from spacy.tokens import Span
from spacy.util import filter_spans
import nest_asyncio
import asyncio
from prefect import task, flow
from concurrent.futures import ThreadPoolExecutor
import os


# In[ ]:





# In[9]:


def filter_spans(spans):
    # Sort the spans by their start position
    spans = sorted(spans, key=lambda span: span.start)
    filtered_spans = []

    for span in spans:
        # Avoid overlapping spans
        if not filtered_spans or span.start >= filtered_spans[-1].end:
            filtered_spans.append(span)

    return filtered_spans


# In[10]:


@Language.factory("custom_city_matcher_1")
def create_custom_city_matcher(nlp, name, cities):
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp.make_doc(city) for city in cities]
    matcher.add("CITY", patterns)

    def custom_city_matcher(doc):
        # Apply the matcher to the document
        matches = matcher(doc)
        
        # Create spans for the matches and label them 'GPE'
        new_spans = [Span(doc, start, end, label="GPE") for _, start, end in matches]
        
        # Combine new spans with existing entities
        all_spans = list(doc.ents) + new_spans
        
        # Filter out overlapping or conflicting spans
        filtered_spans = filter_spans(all_spans)
        
        # Manually check for the cities in the list and ensure they're labeled as GPE
        for ent in filtered_spans:
            if ent.text in cities:
                ent.label_ = "GPE"  # Manually set the label to 'GPE'
        
        # Set the filtered spans as the document's entities
        doc.set_ents(filtered_spans, default="unmodified")
        
        return doc

    return custom_city_matcher


# In[11]:


# new_spacy_model = spacy.load("C:/Users/User/Desktop/Data_Science/Novo_Project/updated_spacy_model")


# In[ ]:


model_path = os.getenv("MODEL_PATH", "/app/model") 
new_spacy_model = spacy.load(model_path)


# In[58]:


# DB connector
@task
def db_connection():

    conn = psycopg2.connect("dbname=travel_bot user=postgres password=AxelData0110# host=localhost client_encoding=UTF8") #DB connection
    cursor = conn.cursor()

    return conn, cursor


# In[13]:


@task
def extract_city_days(text):
    
    # Process the text
    doc = new_spacy_model(text)
    
    # Extract custom-matched cities
    custom_cities = [ent.text for ent in doc.ents if ent.label_ == "GPE"][0]
    # other_cities = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    # other_cities_2 = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    
    #Extract numbers
    numbers = [token.text for token in doc if token.like_num]

    try:
        numbers = int(numbers[0])
    except:
        numbers = extract_number_and_convert(text) 
    
    # Merge both lists, removing duplicates
    # temp = [i for i in set(custom_cities + other_cities + other_cities_2)]
    
    return custom_cities, numbers


# In[15]:


@task
# Check for the city
def city_check(city):

    city = city
    
    cursor.execute('''
    SELECT DISTINCT city_id
    FROM cities
    WHERE city_name = %s
    ''', (city, ))

    # city = cursor.fetchone()

    # if city is None:
    #     cursor.execute('''
    #     INSERT INTO cities(city_name, county_id)
    #     VALUES (%s, %s)
    #     ''', (city, country))

    #     cursor.execute('''
    #     SELECT DISTINCT city_id
    #     FROM cities
    #     WHERE city_name = %s
    #     AND country_id = %s
    #     ''', (city, country_id))
    
    #     city_id = cursor.fetchone()[0]
    # else:
    city_id = cursor.fetchone()[0]
        # return 1, city_id

    return 0, city_id


# In[16]:


def find_distance(lat1: float, lng1: float, lat2: float, lng2: float):
    '''
    The function alculates distance between two points with coordinates

    lat1: float - The first point Lat
    lng1: float - The first point Lng
    lat2: float - The second point Lat
    lng2: float - The second point Lng
    return: integer - the distance in kilometers
    '''
    
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = 6371 * c
    
    return distance
    


# In[17]:


def unpack_places(places: list):
    '''
    The function helps transform data about places from tuple to a dict format

    places: list - With tuples that contains data about places
    return: ditionary - With data well formatted
    '''
    
    places_list = {}

    try:
        n = 0
        for place in places:
            place = {'id': place[0], 'name': place[1], 'address': place[2], 'site': place[3], 'lat': place[4], 'lng': place[5],
                     'description': place[6], 'rating': place[7], 'num_ratings': place[8]}
            places_list[n] = place
            n += 1
    except:
        place = {'id': places[0], 'name': places[1], 'address': places[2], 'site': places[3], 'lat': places[4], 'lng': places[5],
                 'description': places[6], 'rating': places[7], 'num_ratings': places[8]}
        places_list[0] = place

    return places_list


# In[18]:


@task
def find_poi(city: int, visited: list = [], activity_type: str = 'Culture', rating:float = 3.0, poi_per_day: int = 6, v_time: int = 90):

    '''
    The function that finds determined number of main tourist attractions like castles, museums, art galleries related to specific activity type, with determined rating
    in the specific city

    city: string - The city ID
    activity_type: string - one of ativies from the Places table. Default value is "Culture"
    rating: float - Filter for attractions with rating higher or equal to the value. Default value is 3.0
    poi_per_day: integer - number of main attractions to visit per day. Default value is 6
    v_time: integer - average time spent for one place visit in minutes. Default value is 90
    return: dictionary - with data for all found places
    '''
    
    city_id = city
    activity_type = activity_type
    rating = rating
    poi_per_day = poi_per_day
    v_time = v_time
    visited = visited

    visited_tuple = tuple(visited) if visited else tuple((-1, -1)) # костыль для первой итерации

    try:
        
        cursor.execute('''
        SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
        FROM places
        WHERE city_id = %s AND activity_type = %s
        AND ((place_name LIKE '%%castle%%' OR place_name LIKE '%%museum%%' OR place_name LIKE '%%gallery%%')
        OR (place_type LIKE '%%museum%%' OR place_type LIKE '%%art_gallery%%'))
        AND rating >= %s
        AND place_id NOT IN %s
        ORDER BY user_ratings_total DESC, rating DESC
        LIMIT %s
        ''', (city_id, activity_type, rating, visited_tuple, poi_per_day))
    
        places = cursor.fetchall()
        if not places:
            raise ValueError("No places found for the given criteria.")
    except:
        print('Find_poi DB Access Error')
        conn.rollback()

    places_list = unpack_places(places)

    for key in places_list.keys():
        places_list[key]['time'] = v_time # mins for visit
        if 'castle' in places_list[key]['name'].lower() or 'palácio' in places_list[key]['name'].lower():
            places_list[key]['temp_type'] = 'castle'
        else:
            places_list[key]['temp_type'] = 'collections'

    return places_list


# In[88]:


@task
def find_poi_order(places_list):
    '''
    The function that compare distances between main attractions and returns a list with order for the best route

    places_list: dictionary - with data for all places
    retunr: list - with intgeres indicating the key of each attraction in the dictionary
    '''

    ordered_places_idx = [-1, 0]

    while len(ordered_places_idx) != len(places_list) - 1:
        dist=False
        place_idx = 0
        lat1 = places_list[ordered_places_idx[-1]]['lat']
        lng1 = places_list[ordered_places_idx[-1]]['lng']
        # print(lat1)
        # print(lng1)

        for key2, value2 in places_list.items():
            if key2 in ordered_places_idx:
                continue
            else:
                lat2 = places_list[key2]['lat']
                lng2 = places_list[key2]['lng']
                if dist == False:
                    dist = find_distance(lat1, lng1, lat2, lng2)
                    place_idx = key2
                else:
                    if dist > find_distance(lat1, lng1, lat2, lng2):
                        dist = find_distance(lat1, lng1, lat2, lng2)
                        place_idx = key2
                    else:
                        continue
        ordered_places_idx.append(place_idx)
        

    return ordered_places_idx


# In[20]:


@task
def find_start_point(city_id, rating = 4.0, v_time = 60, visited = []):

    '''
    The function return breakfast place to start the day with

    city: string - the city ID
    visited: list - the list with IDs of visited places to exclude
    rating: float - Filter for places with rating higher or equal to the value. Default value is "4.0"
    v_time: integer - average time spent for one place visit in minutes. Default value is 60
    returns: dictionary - with data for the place
    '''

    city_id = city_id
    rating = rating
    v_time = v_time
    visited = visited
    
    visited_tuple = tuple(visited) if visited else tuple((-1, -1)) # костыль для первой итерации

    try:
        cursor.execute('''
            SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
            FROM places
            WHERE city_id = %s AND activity_type = 'Food'
            AND (place_type LIKE '%%cafe%%' OR place_type LIKE '%%bakery%%')
            AND rating >= %s
            AND place_id NOT IN %s
            ORDER BY user_ratings_total DESC, rating DESC
            LIMIT 1
            ''', (city_id, rating, visited_tuple))
    
    
        breakfast = cursor.fetchone()
        if not breakfast:
            # raise ValueError("No places found for the given criteria.")
            cursor.execute('''
            SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
            FROM places
            WHERE city_id = %s AND activity_type = 'Food'
            AND (place_type LIKE '%%restaurant%%')
            AND rating >= %s
            AND place_id NOT IN %s
            ORDER BY user_ratings_total DESC, rating DESC
            LIMIT 1
            ''', (city_id, rating, visited_tuple))
        
            breakfast = cursor.fetchone()
    except:
        print('Find_start_poi DB Access Error')
        conn.rollback()


    place = unpack_places(breakfast)
    place[0]['time'] = v_time # mins for visit
    place[0]['temp_type'] = 'breakfast'

    return place


# In[21]:


def find_route_box(lat1: float, lng1: float, lat2: float, lng2: float):
    '''
    The function that finds boundary box between two points with coordinates

    lat1: float - The first point Lat
    lng1: float - The first point Lng
    lat2: float - The second point Lat
    lng2: float - The second point Lng
    return: floats - 4 point coordinates max lat, max lng, min lat and min lng of hte box
    '''    

    if lat1 > lat2:
        lat_max = lat1
        lat_min = lat2
    else:
        lat_max = lat2
        lat_min = lat1

    if lng1 > lng2:
        lng_max = lng1
        lng_min = lng2
    else:
        lng_max = lng2
        lng_min = lng1

    return lat_max, lng_max, lat_min, lng_min


# In[31]:


def find_small_poi(lat_max: float, lng_max: float, lat_min: float, lng_min: float, from_coor: tuple, rating = 0.0, n_poi = 3, v_time = 3, visited = []):

    '''
    The function finds smaller tourist attractions for tipically for short visit like monuments, streets, squares etc. in a boundary box
    between two points

    lat_max: float - Minimum Lattitude of the box
    lng_max: float - Maximum Lattitude of the box
    lat_min: float - Minimum Longitude of the box
    lng_min: float - Maximum Longitude of the box
    from_coors: tuple - with coordinates (lat, lng) of the place where the user is going to start the route
    visited: list - with IDs of visited places to exclude
    n_poi: integer - number of places per box. Default values is 3
    rating: float - Filter for places with rating higher or equal to the value. Default value is 0
    v_time: integer - average time spent for one place visit in minutes. Default value is 30
    return: dictionary - with places for box
    '''

    rating = rating
    n_poi = n_poi
    v_time = v_time
    visited = visited
    

    lat, lng = from_coor
    visited_tuple = tuple(visited) if visited else tuple((-1, -1)) # костыль для первой итерации

    try:
        cursor.execute(
            '''
            SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
            FROM places
            WHERE (lat > %s AND lat < %s) AND (lng > %s AND lng < %s)
            AND activity_type = 'Culture'
            AND place_type NOT LIKE '%%museum%%'
            AND place_type NOT LIKE '%%art_gallery%%'
            AND rating >= %s
            AND place_id NOT IN %s
            ORDER BY user_ratings_total DESC, rating DESC, (ABS(lat - %s) + ABS(lng - %s))
            LIMIT %s
            ''', (lat_min, lat_max, lng_min, lng_max, rating, visited_tuple, lat, lng, n_poi)
        )
    
        places = cursor.fetchall()
        if not places:
            return False
            
        add_places_list = unpack_places(places)
    
        for key in add_places_list.keys():
            add_places_list[key]['time'] = v_time # mins for visit
            if 'monument' in add_places_list[key]['name'].lower():
                add_places_list[key]['temp_type'] = 'monument'
            else:
                add_places_list[key]['temp_type'] = 'small_poi'
                
    except:
            print('Find_small_poi DB Access Error')
            conn.rollback()


    return add_places_list


# In[30]:


@task
def daily_small_poi(places, order, visited = [], rating = 0.0, n_poi = 3, v_time = 30):
    '''
    The function that finds smaller attractions between all the main places and transfrom main places keys according to visit order

    places: dictionary - with data of all main attractions
    order: list - with keys of the attractions in order to visit
    visited: list -  visited: list - with IDs of visited places to exclude
    return: dictionary - with dictionary of small attractions between all the main points
            dictionary - with main attractions' keys trasfomed according to visit order
    '''
    
    places = places
    order = order
    visited = visited

    
    small_poi = {}
    for idx, val in enumerate(order):
        if val == order[-1]:
            break
            
        else:
            val2 = order[idx + 1]
            
            lat1 = places[val]['lat']
            lat2 = places[val2]['lat']
            lng1 = places[val]['lng']
            lng2 = places[val2]['lng']

            lat_max, lng_max, lat_min, lng_min = find_route_box(lat1, lng1, lat2, lng2)
            
            res = find_small_poi(lat_max, lng_max, lat_min, lng_min, from_coor = (lat1, lng1), rating = rating, n_poi = n_poi)

            if not res:
                small_poi[idx]= False
            else:
                small_poi[idx] = res
    print(small_poi)
    new_places = {}
    for idx, val in enumerate(order):
        new_places[idx - 1] = places[val]

    return small_poi, new_places


# In[24]:


@task
def join_poi(small_poi, new_places):
    '''
    The function that joins main attractions' dict and small attractions' dict in order to visit

    poi: dictionary - with data of the main attractions ordered by keys
    small_poi: dictionary - of dictionaries with smaller attractions data
    return: dictionary - with all places order by keys in a optimum route
    '''
    
    fin_dic = {}

    poi = new_places
    small_poi = small_poi

    n = 0
    for key, value in poi.items():
        if key == -1:
            fin_dic[key] = value
        else:
            if small_poi[key] != False:
                count = -1
                for key2, value2 in small_poi[key].items():
                    fin_dic[key2 + key + n] = value2
                    count += 1
                n += count
            else: 
                fin_dic[key + n] = value
        fin_dic[key + n] = value
    
    return fin_dic   


# In[25]:


def find_restaurant(place_1_coor: tuple, place_2_coor: tuple = False, rating = 4.0, v_time = 90, visited = []):

    '''
    The function that finds a lunch/ dinner restaurant near the place or inside the box between two places

    place_1_coor: tuple - lat, lng coordinates of the 1st place
    rating: float - Filter for places with rating higher or equal to the value. Default value is 4.5
    visited: list - with IDs of visited places to exclude
    place_2_coor: tuple - lat, lng coordinates of the second place for in-box search. Default value is False
    v_time: integer - average time spent for one place visit in minutes. Default value is 90
    return: dictionary - with data for the place
    '''

    rating = rating
    v_time = v_time
    visited = visited
    
    
    visited_tuple = tuple(visited) if visited else tuple((-1, -1)) # костыль для первой итерации
    
    lat1 = place_1_coor[0]
    lng1 = place_1_coor[1]

    if place_2_coor != False:
        lat2 = place_2_coor[0]
        lng2 = place_2_coor[1]

        lat_max, lng_max, lat_min, lng_min = find_route_box(lat1, lng1, lat2, lng2)
        
        try:
            cursor.execute(
            '''
            SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
            FROM places
            WHERE (lat > %s AND lat < %s) AND (lng > %s AND lng < %s)
            AND place_type LIKE '%%restaurant%%'
            AND rating >= %s
            AND place_id NOT IN %s
            AND LOWER(place_name) NOT LIKE '%%hotel%%'
            ORDER BY user_ratings_total DESC, rating DESC
            LIMIT 1
            ''', (lat_min, lat_max, lng_min, lng_max, rating, visited_tuple)
            )
    
            res = cursor.fetchone()
       
            if res == None:
            
                cursor.execute(
                    '''
                    WITH rests AS(
                        SELECT place_id, SUM(ABS(lat - %s) + ABS(lng - %s)) distance
                        FROM places
                        WHERE place_type LIKE '%%restaurant%%'
                        AND rating >= %s
                        AND place_id NOT IN %s
                        AND LOWER(place_name) NOT LIKE '%%hotel%%'
                        GROUP BY place_id
                        ORDER BY distance, user_ratings_total DESC, rating DESC
                        LIMIT 1)
            
                    SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
                    FROM places
                    WHERE place_id = (SELECT place_id FROM rests)
                    ''', (lat1, lng1, rating, visited_tuple))
            
                #if no results can search for 2nd coors or return to visited restaurants
                res = cursor.fetchone()
        except:
                print('Find_restaurant DB Access Error')
                conn.rollback()

    else:
        try:
            cursor.execute(
                    '''
                    WITH rests AS(
                        SELECT place_id, SUM(ABS(lat - %s) + ABS(lng - %s)) distance
                        FROM places
                        WHERE place_type LIKE '%%restaurant%%'
                        AND rating >= %s
                        AND place_id NOT IN %s
                        AND LOWER(place_name) NOT LIKE '%%hotel%%'
                        GROUP BY place_id
                        ORDER BY distance, user_ratings_total DESC, rating DESC
                        LIMIT 1)
    
                    SELECT place_id, place_name, formatted_address, website, lat, lng, place_description, rating, user_ratings_total
                    FROM places
                    WHERE place_id = (SELECT place_id FROM rests)
                    ''', (lat1, lng1, rating, visited_tuple))
    
                #if no results can search for 2nd coors or return to visited restaurants
            res = cursor.fetchone()
        except:
                print('Find_restaurant DB Access Error')
                conn.rollback()

    res = unpack_places(res)
    res[0]['time'] = v_time # mins for visit

    return res 


# In[26]:


def find_time_in_road(coors: tuple, mode = 'foot-walking'):

    '''
    The function returns time in minutes to get from one point to another depending on travel mode
    
    coors: tuple - lat, lng of the first and the second point
    mode: str - travel mode among 'driving-car', 'cycling-regular', 'foot-walking'. Default value is 'foot-walking'
    return: integer - minutes on a way
    '''
    mode = mode
    client = openrouteservice.Client(key='5b3ce3597851110001cf624848f0ee4e7aef4801805e3e162cd3ac09') 
    lat1, lng1, lat2, lng2 = coors
    lat1, lng1, lat2, lng2 = map(float, (lat1, lng1, lat2, lng2))

    matrix = client.distance_matrix(
        locations=[(lng1, lat1) , (lng2, lat2)],
        profile=mode,
        metrics=['duration'])
    
    time = matrix['durations'][0][1] // 60
    
    return time


# In[69]:


@task
def daily_route(fin_dic, visited: list = None, food_rating: float = 4.5, transport_mode:str = 'foot-walking', lunch_time: str = '14:00', dinner_time:str = '20:00'):

    '''
    The function returns optimum route for the daily city visit with places in order of visiting
    
    city: str - the city ID
    visited: list - with IDs of visited places to exclude
    food_rating: float - Filter for food places with rating higher or equal to the value. Default value is 4.5
    poi_rating: float - Filter for attraction places with rating higher or equal to the value. Default value is 4.5
    activity_type: str - filter fo activity type from DB. Default value is 'Culture'
    transport_mode: str - travel mode to count traveling time among 'driving-car', 'cycling-regular', 'foot-walking'. Default value is 'foot-walking'
    return: list - with ID of places to visit in optimum order
    '''
    all_places = fin_dic
    
    # print(all_places)
    day_visit = []
    
    if visited == None:
        visited= []
    else:
        visited = visited
        
    time = datetime.strptime("09:00", "%H:%M")
    break_1 = datetime.strptime(lunch_time, "%H:%M") # variables
    break_2 = datetime.strptime(dinner_time, "%H:%M") # variables
    
    stop = 0
    
    for key, value in all_places.items():
        if time >= break_1 or (time + timedelta(minutes = all_places[key]['time'])) > break_1:
            break
        visited.append(all_places[key]['id'])
        day_visit.append([all_places[key]['id'], all_places[key]['temp_type'], all_places[key]['name']])
        stop = key
        time += timedelta(minutes = all_places[key]['time'])
        # print(f'After place time: {time}')
        lat1 = all_places[key]['lat']
        lng1 = all_places[key]['lng']
        lat2 = all_places[key+1]['lat']
        lng2 = all_places[key+1]['lng']
    
        road_time = find_time_in_road(coors = (lat1, lng1, lat2, lng2), mode = 'foot-walking')
    
        if time >= break_1 or (time + timedelta(minutes = road_time)) >= break_1:
            food_lat = lat1
            food_lng = lng1
            break
        else:
            time += timedelta(minutes = road_time)
            # print(f'After next road time: {time}')
            food_lat = lat2
            food_lng = lng2
    
    # print(f'Lunch time is:{time}')
    # Lunch time
    lunch = find_restaurant(place_1_coor = (food_lat, food_lng), visited = visited)[0]
    visited.append(lunch['id'])
    day_visit.append([lunch['id'], 'lunch', lunch['name']])
    lunch_lat = lunch['lat']
    lunch_lng = lunch['lng']
    
    
    time -= timedelta(minutes = road_time)
    # print(f'mimus time: {time}')
    road_time = find_time_in_road(coors = (food_lat, food_lng, lunch_lat, lunch_lng), mode = transport_mode)
    time += timedelta(minutes = road_time)
    # print(f'Road to lunch: {time}')
    time += timedelta(minutes = lunch['time'])
    # print(f'Right after lunch time: {time}')
    
    next_lat = all_places[stop + 1]['lat']
    next_lng = all_places[stop + 1]['lng']
    # print(all_places[stop + 1]['id'], stop)
    
    road_time = find_time_in_road(coors = (lunch_lat, lunch_lng, next_lat, next_lng), mode = transport_mode)
    time += timedelta(minutes = road_time)
    
    # print(f'New adventure time is:{time}')
    # Till dinner
    for key, value in all_places.items():
        if time >= break_2:
            break
        try:
            new_key = stop + key + 2
            # print(new_key)
            visited.append(all_places[new_key]['id'])
            day_visit.append([all_places[new_key]['id'], all_places[new_key]['temp_type'], all_places[new_key]['name']])
            stop_2 = new_key
            time += timedelta(minutes = all_places[new_key]['time'])
    
            lat1 = all_places[new_key]['lat']
            lng1 = all_places[new_key]['lng']
            lat2 = all_places[new_key+1]['lat']
            lng2 = all_places[new_key+1]['lng']
    
            road_time = find_time_in_road(coors = (lat1, lng1, lat2, lng2), mode = transport_mode)
            next_time = lng2 = all_places[new_key+1]['time']
    
            if time >= break_2 or (time + timedelta(minutes = (road_time+next_time))) >= break_2:
                food_lat = lat1
                food_lng = lng1
                break
            else:
                time += timedelta(minutes = road_time)
        except:
            break
            
    # print(f'Dinner time is:{time}')
    # Dinner time
    dinner = find_restaurant(place_1_coor = (food_lat, food_lng), visited = visited)[0]
    visited.append(dinner['id'])
    day_visit.append([dinner['id'], 'dinner', dinner['name']])
    dinner_lat = dinner['lat']
    dinner_lng = lunch['lng']
    
    road_time = find_time_in_road(coors = (food_lat, food_lng, dinner_lat, dinner_lng), mode = transport_mode)
    time += timedelta(minutes = road_time)
    time += timedelta(minutes = dinner['time'])
    
    # print(f'Day finish time is:{time}')
    
    
    return day_visit, visited


# In[28]:


def simple_generator(place_type, name):

    sentences = {'breakfast' : [
                 f'Start your day right with a delicious breakfast at {name}.',
                 f'Kick off your morning with a cozy meal at {name}.',
                 f'Enjoy the most important meal of the day at {name}.',
                 f'Rise and shine with a tasty breakfast at {name}.',
                 f'Begin your day with flavors that inspire at {name}.'],
                 'lunch' : [
                 f'Relish the joy of great food and great vibes at {name}.',
                 f'Take a well-deserved break and enjoy {name} exceptional cuisine.',
                 f'Recharge your energy with a satisfying lunch at {name}.',
                 f'Explore bold flavors and a welcoming vibe at {name}.',
                 f'Reward yourself with {name} unbeatable quality and cozy vibe.'],
                 'dinner' : [
                 f'After a day of excitement, indulge in {name} culinary masterpieces and relax in its tranquil atmosphere.',
                 f'Enjoy a luxurious dinner at {name}, where the food is exceptional and the vibe is relaxing.',
                 f'After a long day of travel, relax with {name} flavorful dishes and unwind in its soothing environment.',
                 f'Celebrate the end of your journey with a flavorful dinner at {name}, where the atmosphere and dishes are second to none.',
                 f'After a day of discovery, enjoy a delectable dinner at {name}, where the ambiance and food offer ultimate relaxation.'],
                 'collections' : [
                 f'Let {name} enhance your journey with its captivating exhibitions, where each display offers something new to discover.',
                 f'{name} brings together the beauty of craftsmanship and culture, offering a perfect destination for any traveler.',
                 f'{name} presents a collection that will transport you to different times and places, offering a reflective stop on your travels.',
                 f'Reflect on the beauty and significance of culture as you explore the inspiring exhibits at {name}.',
                 f'Let the artistic offerings of {name} guide you through a journey of discovery and inspiration.'],
                 'monument' : [
                 f'Stop at {name} for a brief but enriching experience, allowing you to connect with its tranquil beauty.',
                 f'Take a moment at {name} to appreciate its unique beauty and find calm in its presence.',
                 f'Take a quick break at {name} to enjoy its beauty and soak in the peaceful vibes.',
                 f'Visit {name} to enjoy a quiet interlude and take in its graceful beauty.',
                 f'Stop for a moment at {name}, where you can take in the beauty and serenity of your surroundings.'],
                 'small_poi' : [
                 f'{name} is a peaceful escape, perfect for those who want to explore something off the usual tourist path.',
                 f'Spend a moment at {name} and explore the quiet beauty of a lesser-known corner of the city.',
                 f'A short visit to {name} allows you to connect with the charm of a lesser-known place.',
                 f'{name} is the perfect spot for a brief visit, offering a unique experience with plenty of character.',
                 f'Take a break at {name} and appreciate the peaceful vibe of this lesser-known but worthwhile place.'],
                 'castle' : [
                 f'{name} towering walls offer visitors a powerful glimpse into the past, filled with history and charm.',
                 f'Take a journey through time at {name}, a castle that has survived centuries of history and change.',
                 f'Visit {name} and feel the presence of history as you walk through its centuries-old castle walls.',
                 f'Walk through {name} and admire the magnificent structure of this historic fortress.',
                 f'Step into the past with a visit to {name}, where history, architecture, and nature blend seamlessly.']
                }

    if place_type in sentences:
        return random.choice(sentences[place_type]).format(name=name)


# In[29]:


@task
def result_message(day_seq):

    day_seq = day_seq

    messages = []
    
    for i in range(len(day_seq)):
        messages.append(f'Day {i+1}:')
        for place in day_seq[i]:
            place_type = place[1]
            name = place[2]
            sent = simple_generator(place_type = place_type, name = name)
            messages.append(sent)

    
    return messages


# In[89]:


@flow
def pipeline_flow(input_data, activity_type = 'Culture', poi_rating = 4.0, poi_per_day = 6, poi_v_time = 90, brkfst_rating = 4.0, brkfst_v_time = 60, 
                  s_poi_rating = 0.0, s_poi_per_day = 3, s_poi_v_time = 30, rest_rating = 4.0, rest_v_time = 90, move_mode = 'foot-walking', lunch_time = '14:00', dinner_time = '20:00'):

    conn, cursor = db_connection()
    city, days = extract_city_days(input_data)
    city_id = city_check(city)[1]
    visited = []
    full_seq = []

    for i in range(days):
        m_poi = find_poi(city = city_id, activity_type = activity_type, visited = visited, rating = poi_rating, poi_per_day = poi_per_day, v_time = poi_v_time)
        order = find_poi_order(m_poi)
        breakfast = find_start_point(city_id = city_id, rating = brkfst_rating, v_time = brkfst_v_time, visited = visited)[0]
        m_poi[-1] = breakfast
        small_poi, new_places = daily_small_poi(places = m_poi, order = order, visited = visited, rating = s_poi_rating, n_poi = s_poi_per_day, v_time = s_poi_v_time)
        print(new_places)
        fin_dic = join_poi(small_poi, new_places)
        day_visit, visited = daily_route(fin_dic = fin_dic, visited = visited, food_rating = rest_rating, transport_mode = move_mode, lunch_time = lunch_time, dinner_time = dinner_time)
        full_seq.append(day_visit)

    final_msg = result_message(full_seq)

    return final_msg         
        
    


# In[ ]:


# nest_asyncio.apply()
# executor = ThreadPoolExecutor()

# START = 0


# async def start(update: Update, context: CallbackContext) -> None:
#     await update.message.reply_text('What city would you like to visit and for how long?')
#     return START

# async def handle_input(update: Update, context: CallbackContext) -> int:
#     input_text = update.message.text
#     await update.message.reply_text("Route generation is in process...")
    
#     messages = pipeline_flow(input_text)
#     try:
#         for msg in messages:
#             print(f"Sending: {msg}")
#             await update.message.reply_text(msg)
#             await asyncio.sleep(1)
    
#         await update.message.reply_text("The route is done. You can start a new conversation with /start")

#     except Exception as e:
#         print(f"Error: {e}")
#         await update.message.reply_text("An error occurred. Please try again later with /start.")
#         conn.rollback()
#     # End the conversation
#     return ConversationHandler.END

# async def cancel(update: Update, context: CallbackContext) -> int:
#     """Handle cancel command."""
#     await update.message.reply_text("Conversation ended. You can start a new one anytime.")
#     return ConversationHandler.END

# # Main function to run the bot
# def main():
#     bot_token = '8066163217:AAHssbh4hc4TZBSkVyZgVRZjcWvm7Vfvlpw'  # Replace with your bot token
#     application = Application.builder().token(bot_token).build()

#     conversation_handler = ConversationHandler(
#             entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
#             states={
#                 START: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)],
#             },
#             fallbacks=[CommandHandler("cancel", cancel)],
#         )


#     application.add_handler(conversation_handler)

#     application.run_polling()

# if __name__ == '__main__':
#     main()


# In[ ]:




