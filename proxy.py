#!/usr/bin/env/python3

import sys
import os
import time
import socket
import select


BUF_SIZE = 8192
USAGE = "Usage: proxy.py [expire_time: int]"
SERVER_ADDR = ("localhost", 8888)
TEXT_BOX_CODE = "<p style=\"z-index:9999; " \
				"position:fixed; top:20px; " \
				"left:20px; width:200px; " \
				"height:100px; " \
				"background-color:yellow; " \
				"padding:10px; " \
				"font-weight:bold;\">"


def main(argv: list) -> None:

	# check args
	if len(argv) != 2:
		print(USAGE)
		return None

	if not argv[1].isnumeric():
		print(USAGE)
		return None

	print("\nCACHED FILES WILL BE CREATED IN SAME DIRECTORY AS PROXY.PY")
	print("\nServer starting...\n")

	# make new socket for the server and bind localhost:8888
	server_socket = new_socket()
	server_socket.bind(SERVER_ADDR)
	server_socket.listen(5)
	inputs = [server_socket]

	# loop forever and wait for connections using select
	while True:

		readable = []
		print("Waiting for connection...")

		try:
			readable, [], [] = select.select(inputs, [], [])

		except KeyboardInterrupt:  # to close the server
			print("\n\nShutting down server...\n")
			sys.exit(0)

		except socket.error:
			inputs.pop()  # remove socket if we get some error

		for sock in readable:

			# if we get a new connection, add it to inputs
			if sock is server_socket:
				client_socket, client_address = server_socket.accept()
				inputs.append(client_socket)
				print("Connection from: ", client_address)

			# if we get a http request, handle it and remove from inputs
			else:
				handle_connection(sock, int(argv[1]))
				inputs.remove(sock)


def new_socket() -> socket:
	"""
	Make new TCP socket and return it.

	:return: The new socket
	"""

	new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	return new_sock


def handle_connection(client_socket: socket, cache_time_to_live: int) -> None:
	"""
	Handles a client's get request. This function will retrieve the requested
	object from the web server or from a cache and send it back to the client.

	:param client_socket: socket that the client is connecting from
	:param cache_time_to_live: time to live for a cached object
	:return: None
	"""

	# get clients get request
	get_req = client_socket.recv(BUF_SIZE).decode()

	# extract url and path to the request object from get request
	url_and_path = get_url_and_path(get_req)
	url = url_and_path[0]
	path = url_and_path[1]

	# modify get request so that we can forward it to the webserver to retrieve
	# the needed objects, check modify_get_request docstring for more info
	get_req = modify_get_request(get_req)

	# check if request is for an html object
	html_req = is_html_req(get_req)

	# calculate the name of the file that caches the object
	cache_filename = (url + '-' + path + ".txt").replace('/', '-')

	# calculate the time a cached object has been alive for
	time_alive = 0.0
	if os.path.exists(cache_filename):
		time_alive = time.time() - os.path.getmtime(cache_filename)

	# if we don't have the object in cache, or if the object has expired
	if not os.path.exists(cache_filename) or time_alive > cache_time_to_live:

		# connect to webserver and send modified get request
		webserver_socket = new_socket()
		try:
			webserver_socket.connect((url, 80))
		except socket.error:
			return None
		webserver_socket.sendall(get_req.encode())

		# make new cache file for object
		new_cache_file = open(cache_filename, "wb+")

		# if request is for html page
		if html_req:

			# get page from webserver
			response = ""
			while True:
				buf_response = webserver_socket.recv(BUF_SIZE).decode("cp1252")
				if len(buf_response) > 0:
					response += buf_response
				else:
					break

			# inject textbox to the html send it to client and cache it
			modified_responses = modify_response(response)
			client_socket.sendall(modified_responses[0].encode())
			new_cache_file.write(modified_responses[1].encode())

		# if request isn't for html page i.e no need to modify response
		else:

			# receive response, send to client, and cache response
			while True:
				rec_data = webserver_socket.recv(BUF_SIZE)
				if len(rec_data) > 0:
					try:
						client_socket.send(rec_data)
					except socket.error:
						break
					new_cache_file.write(rec_data)
				else:
					break

		new_cache_file.close()
		webserver_socket.close()

	# if we have the response to the request cached
	else:

		# open cached file
		cached_file = open(cache_filename, "rb")

		# read cached response and sent it to client
		response = cached_file.read(BUF_SIZE)
		while len(response) > 0:
			try:
				client_socket.send(response)
			except socket.error:
				break
			response = cached_file.read(BUF_SIZE)

	client_socket.close()
	return None


def modify_get_request(get_req: str) -> str:
	"""
	Change the get request so that the get request isn't to localhost but rather
	to the actual webserver we're trying to get the object from. Also if the get
	request is for an html object, we change the "Accept-Encoding" header to the
	value "identity" so that we can inject the textbox code.

	:param get_req: The original get request
	:return: The modified get request
	"""

	# split get request into their individual lines
	request_lines = get_req.split('\n')

	# get the url and path to the object from get request
	url_and_path = get_url_and_path(get_req)
	url = url_and_path[0]
	path = url_and_path[1]

	# prepare the lines to be injected into the get request
	req_method_line = "GET /" + path + " HTTP/1.1" + '\r'
	req_host_header_line = "Host: " + url + "\r"
	req_encoding_header_line = "Accept-Encoding: identity\r"

	# inject the method line
	request_lines[0] = req_method_line

	# find the "Host" header and inject the new host header line
	for i in range(len(request_lines)):
		if "Host: " in request_lines[i]:
			request_lines[i] = req_host_header_line
			break

	# find the "Accept-Encoding" header and inject new accept-encoding header
	# line if the get request is for an html object
	if is_html_req(get_req):
		for i in range(len(request_lines)):
			if "Accept-Encoding: " in request_lines[i]:
				request_lines[i] = req_encoding_header_line
				break

	# add back the '\n' to the end of the lines of the request
	for i in range(len(request_lines)):
		request_lines[i] += "\n"

	# join back the lines of the request into one string
	data = "".join(request_lines)
	return data


def get_url_and_path(get_req: str) -> tuple:
	"""
	Get the url of the webserver from which the object is being requested and
	get the path of the object on the webserver.

	:param get_req: The get request from which we want the url and path
	:return: tuple containing the url and path for the object being requested
	"""

	# get the url of webserver from the method line of the request
	url = ""
	index = 5
	while index < len(get_req) and get_req[index] != '/':
		url += str(get_req[index])
		index += 1

	# get path that gives the location of the requested object on the webserver
	path = ""
	index += 1
	while index < len(get_req) and get_req[index] != ' ':
		path += str(get_req[index])
		index += 1

	return url, path


def is_html_req(req: str) -> bool:
	"""
	Checks if the given request is requesting an html object.

	:param req: The request that we want to check
	:return: True if request is for an html object, False otherwise
	"""

	# walk through the lines of the request and check if "text/html" is in the
	# "Accept" header
	req_lines = req.split('\n')
	for line in req_lines:
		if "Accept: " and "text/html" in line:
			return True
	return False


def modify_response(response: str) -> tuple:
	"""
	Takes a response to an html object request and injects the textbox code into
	the response's html. Returns two versions of the modified response, one
	response for a fresh html page and one for a cached html page.

	:param response: Webserver response containing the html to be modified
	:return: tuple containing response for client and response to be cached
	"""

	# get the textbox code for a fresh page and a cached page
	notif_msg_code = modified_textbox_code()

	# find body tag and walk to the end of the body tag
	index = response.find("<body") + 1
	while response[index] != '\n':
		index += 1

	# make two new responses with the textbox code injected in the html body
	resp_fresh = response[:index + 1] + notif_msg_code[0] + response[index + 1:]
	resp_cache = response[:index + 1] + notif_msg_code[1] + response[index + 1:]

	return resp_fresh, resp_cache


def modified_textbox_code() -> tuple:
	"""
	Modify the given textbox code for a fresh version of an html page and a
	cached version of an html page, and add the current time to both.

	:return: tuple containing code for fresh page and cache page
	"""

	# create "Fresh version" code and add the current time
	msg_fresh = TEXT_BOX_CODE + "FRESH VERSION AT: "
	msg_fresh += time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
	msg_fresh += "</p>\n"

	# create "Cached version" code and add the current time
	msg_cache = TEXT_BOX_CODE + "CACHED VERSION AS OF: "
	msg_cache += time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
	msg_cache += "</p>\n"

	return msg_fresh, msg_cache


if __name__ == "__main__":
	main(sys.argv)
