# Simple python proxy server
Simple school project to learn more about http

This is a simple python web cache server that stores web pages for a given amount of time before expiry. It only works for get requests since get requests are what return the whole webpage thats needed. The server only works for http requests, not https.

The server also injects a text box onto the returned webpage that indicates whether the page was retrieved from the cache or not. The injected text box also indicates the time the page was cached or the time when the fresh page was retrieved if it wasn't retrieved from the cache.

Cached items are stored in the same directory as proxy.py

The server works best with simple static web pages, and might not work as well with more complicated web pages

## To start the server
Usage: python3 proxy.py [CACHED_TIME]

## To use the server
localhost:8888/link/to/webpage
