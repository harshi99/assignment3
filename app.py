from flask import Flask, jsonify, request, render_template
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import os
import csv
import pyodbc
from datetime import datetime
from decimal import Decimal
import random
import time
import redis
import json


app = Flask(__name__)

# Blob Storage configuration
blob_connection_string = 'DefaultEndpointsProtocol=https;AccountName=assdata1;AccountKey=WMGVFc5Btn/cWP1ErRdsoFKp+VOWcfM9r5C6uOYSod9jeunIxoThQp+A6ecG6R48CFywsaCRl/AZ+ASttwd/CA==;EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
container_name = 'assignment3'

# SQL configuration
server = 'harshi1'
database = 'Asssignment3'
username = 'harshi'
password = 'Azure.123'
driver = '{ODBC Driver 18 for SQL Server};Server=tcp:harshi1.database.windows.net,1433;Database=Asssignment3;Uid=harshi;Pwd=Azure.123;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
# Establish the database connection
connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"
connection = pyodbc.connect(connection_string)

# Initialize Redis client
redis_host = 'Hassignment.redis.cache.windows.net'
redis_port = '6380'
redis_access_key = 'qurM4PQk6ewFHqlM7GBNzjkCPSiRky9BRAzCaA1v0ww='
redis_client = redis.Redis(host=redis_host, port=redis_port, password=redis_access_key, ssl=True)

@app.route('/')
def index():
    return render_template('index.html')

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

@app.route('/query', methods=['POST'])
def execute_query():
    query_type = request.form['query_type']
    num_queries = int(request.form['num_queries'])
    query_results = []
    execution_time = 0

    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor() 

    if query_type == 'random':
        queries = generate_random_query(num_queries)
        for query in queries:
            start_time = time.time()

            # Check if the result is cached
            result = redis_client.get(query)
            if result is not None:
                    # Deserialize the result from JSON
                    query_results.extend(json.loads(result))
            else:
                
                    cursor.execute(query)
                    execution_time += time.time() - start_time
                    rows = cursor.fetchall()
                    # Convert the rows to a list of dictionaries
                    result_dict = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
                    query_results.extend(result_dict)

            
                    # Serialize the result dictionary to JSON using the custom encoder
                    json_result = json.dumps(result_dict, cls=CustomJSONEncoder)

            
                    # Cache the result
                    redis_client.set(query, json_result)

        cursor.close()  # Close the cursor after fetching results
        connection.close()
    elif query_type == 'restricted':
        restriction_type = request.form['restriction_type']
        for _ in range(num_queries):
            if restriction_type == 'time':
                start_time = datetime.fromisoformat(request.form['start_time'])
                end_time = datetime.fromisoformat(request.form['end_time'])
                query = generate_restricted_time_query(start_time, end_time)
            elif restriction_type == 'magnitude':
                min_magnitude = float(request.form['min_magnitude'])
                max_magnitude = float(request.form['max_magnitude'])
                query = generate_restricted_magnitude_query(min_magnitude, max_magnitude)

            start_time = time.time()
            cursor.execute(query)
            execution_time += time.time() - start_time
            results = cursor.fetchall()
            # Convert each row to a dictionary
            result_dict = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
            query_results.append(result_dict)

        cursor.close()
        connection.close()

    return render_template('query_results.html', query_results=query_results, execution_time=execution_time)

def generate_random_query(num_queries):
    queries = []
    for _ in range(num_queries):
        query = "SELECT TOP 1 * FROM all_month ORDER BY NEWID()"
        queries.append(query)
    return queries
    
def generate_restricted_time_query(start_time, end_time):
    # Generate a restricted query based on the given time range
    return f"SELECT * FROM all_month WHERE time BETWEEN '{start_time}' AND '{end_time}'"

def generate_restricted_magnitude_query(min_magnitude, max_magnitude):
    # Generate a restricted query based on the given magnitude range
    return f"SELECT * FROM all_month WHERE mag BETWEEN {min_magnitude} AND {max_magnitude}"


if __name__ == '__main__':
    app.run(debug=True)
