from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from urllib.parse import parse_qs, urlparse
import time

DATABASE_FILE = 'database.json'
HOST_NAME = '127.0.0.1'
PORT_NUMBER = 8000


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
        except ValueError:
            self.send_error(400, 'Invalid query string')
            return
        path_name = str(path.split('/')[1])
        if path == '/' + path_name:
            resource = None
            try:
                with open('database.json') as f:
                    resource = json.load(f)[path_name]
            except KeyError:
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write("Resource not found".encode())
            if resource:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resource).encode())

        elif self.path.startswith('/' + path_name + '/'):
            resource_id = None
            query_components = dict(parse_qs(urlparse(self.path).query))
            if not query_components:
                resource_id = parsed_path.path.strip("/")
                if '/' in resource_id:
                    resource_id = resource_id.split('/')[1]
            if resource_id == path_name:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write("Bad request".encode())
            else:
                if query_components:
                    results = self.get_by_query(query_components, path_name)
                    if len(results) == 0:
                        self.send_response(404)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write("Resource not found".encode())
                    else:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(results).encode())
                    # self.get_customer_by_id(customer_id[0])
                elif resource_id:
                    self.get_by_id(resource_id, path_name)
                else:
                    self.send_response(400)
                    self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # Get the request body
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length).decode()
        print(request_body)
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
        except ValueError:
            self.send_error(400, 'Invalid query string')
            return
        path_name = str(path.split('/')[1])
        # Parse the request body as a JSON object
        try:
            new_resource = json.loads(request_body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return
        # Load the database from the JSON file
        with open(DATABASE_FILE, 'r') as f:
            database = json.load(f)
        # Verificam daca exista un id in request_body
        id_value = json.loads(request_body).get('id')
        # Assign a new ID to the resource
        if id_value is None:
            if database[path_name]:
                new_id = max(int(resource['id'])
                             for resource in database[path_name]) + 1
            else:
                new_id = 1
            new_resource['id'] = str(new_id)
        else:
            try:
                for resource in database[path_name]:
                    if str(id_value) == str(resource['id']):
                        self.send_response(409)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write("Resource already exists".encode())
                        return
                new_resource['id'] = str(id_value)
            except KeyError:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write("Resource not found".encode())
                return
        # Add the new resource to the database
        database[path_name].append(new_resource)
        # Save the updated database to the JSON file
        with open(DATABASE_FILE, 'w') as f:
            json.dump(database, f)
        # Return the new resource with its assigned ID
        self.send_response(201)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(new_resource).encode())

    def do_PUT(self):
        # Get the request body
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length).decode()
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
        except ValueError:
            self.send_error(400, 'Invalid query string')
            return
        path_name = str(path.split('/')[1])
        # Parse the request body as a JSON object
        try:
            updated_resource = json.loads(request_body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return
        parsed_url = urlparse(self.path)
        resource_id = parsed_url.path.strip("/")
        if '/' in resource_id:
            resource_id = resource_id.split('/')[1]
        if resource_id == path_name:
            self.send_response(405)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write("Method not allowed".encode())
        elif resource_id:
            resource = None
            try:
                with open('database.json') as f:
                    resources = json.load(f)[path_name]
                    for r in resources:
                        if str(r['id']) == str(resource_id):
                            resource = r
                            resource.update(updated_resource)
            except KeyError:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write("Resource not found".encode())
                return

            if resource:
                resource.update(updated_resource)
                with open(DATABASE_FILE, 'r') as f:
                    database = json.load(f)
                for i in range(len(database)):
                    if database[path_name][i]['id'] == resource['id']:
                        database[path_name][i] = resource
                with open(DATABASE_FILE, 'w') as f:
                    json.dump(database, f)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(updated_resource).encode())
            else:
                # daca nu exista resursa, ar trebui teoretic sa o creez
                self.send_response(404)
                self.end_headers()

    def do_DELETE(self):
        # Get the resource ID from the URL path
        finalCharater = False
        try:
            params = dict(parse_qs(urlparse(self.path).query))
        except ValueError:
            self.send_error(400, 'Invalid query string')
            return
        print("params", params)
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            if path[-1] == '/':
                finalCharater = True
        except ValueError:
            self.send_error(400, 'Invalid query string')
            return
        path_name = str(path.split('/')[1])
        # Load the database from the JSON file
        with open(DATABASE_FILE, 'r') as f:
            database = json.load(f)
        # If the resource ID is not found, return a 404 error
        resource_id = None
        for resource_id in params.items():
            resource_id = str(params['id'][0])
        query_components = dict(parse_qs(urlparse(self.path).query))
        # daca nu este folosit qs, iau id-ul din path
        if not query_components:
            resource_id = parsed_path.path.strip("/")
            if '/' in resource_id:
                resource_id = resource_id.split('/')[1]
        if resource_id == path_name and finalCharater:
            self.send_response(400)
            self.end_headers()
            return
        elif resource_id == path_name and not finalCharater:
            database[path_name] = []
            with open(DATABASE_FILE, 'w') as f:
                json.dump(database, f)
            self.send_response(204)
            self.end_headers()
            return
        try:
            if not any(resource['id'] == resource_id for resource in database[path_name]):
                self.send_response(404)
                self.end_headers()
                return
        except KeyError:
            self.send_response(404)
            self.end_headers()
            return
        # Remove the resource with the specified ID from the database
        for resource in database[path_name]:
            if resource['id'] == resource_id:
                database[path_name].remove(resource)

        # Save the updated database to the JSON file
        with open(DATABASE_FILE, 'w') as f:
            json.dump(database, f)

        # Return a 200 OK
        self.send_response(200)
        self.end_headers()

    def get_by_id(self, customer_id, path_name):
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)[path_name]
        for customer in data:
            if customer['id'] == customer_id:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps(customer)
                self.wfile.write(response.encode('utf-8'))
                return
        self.send_response(404)
        self.end_headers()

    def get_by_query(self, query, path_name):
        with open(DATABASE_FILE, 'r') as f:
            database = json.load(f)[path_name]
        results = []
        for record in database:
            match = True
            for param_key, param_value in query.items():
                if param_key not in record or str(record[param_key]) != param_value[0]:
                    match = False
                    break
            if match:
                results.append(record)
        return results


def run():
    print('Starting server...')
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), RequestHandler)
    print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER))


# Run the server
if __name__ == '__main__':
    # If the database file does not exist, create an empty JSON list
    if not os.path.isfile(DATABASE_FILE):
        with open(DATABASE_FILE, 'w') as f:
            json.dump([], f)
    # If the database file is empty, create an empty JSON list
    elif os.stat(DATABASE_FILE).st_size == 0:
        with open(DATABASE_FILE, 'w') as f:
            json.dump({"customers": [], "books": [], "orders": []}, f)
    run()
