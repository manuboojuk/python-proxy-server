# Simple python proxy server
This is a simple python web cache server that stores web pages for a given amount of time before expiry. It only works for get requests since get requests are what return the whole webpage thats needed. 

The server also injects a text box onto the returned webpage that indicates whether the page was retrieved from the cache or not. The injected text box also indicated the time the page was cached or the time when the fresh page was retrieved if it wasn't retrieved from the cache.

cached items are stored in the same directory as proxy.py

## To start the server
Usage: python3 proxy.py [CACHED_TIME]

## To use the server
localhost:8888/link/to/webpage
