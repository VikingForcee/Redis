# Minimal Binary Protocol Key-Value Store

This project implements a minimal in-memory key-value store using a custom binary protocol in C++. It mimics the core structure of real-world systems like Redis, focusing on manual parsing, request handling, and response serialization.

## Features

- Custom binary protocol parser
- Support for `set`, `get`, and `del` commands
- Simple in-memory storage using `std::map`
- Manual byte-level serialization and deserialization
- Designed for educational purposes to understand how low-level servers work

## Protocol Format

### Request Format

Each request is a length-prefixed binary message with the following structure:

┌────┬────┬─────┬────┬─────┬────┬─────┐
│nstr│len1│str1 │len2│str2 │... │strn│
└────┴────┴─────┴────┴─────┴────┴─────┘


- `nstr` (4 bytes): number of strings
- Each string is encoded as:
  - `len` (4 bytes): length of the string
  - followed by the actual bytes of the string

Example:
- `["set", "foo", "bar"]` is sent as:  
  - 3 (number of strings)  
  - 3 ("set"), 3 ("foo"), 3 ("bar")

### Response Format

┌────────┬────────────┬────────────┐
│len (4B)│status (4B) │data (n B) │
└────────┴────────────┴────────────┘

- `len`: total response length (including `status` and `data`)
- `status`: 0 for OK, 1 for Not Found, 2 for Error
- `data`: result value if applicable (e.g., from `get`)



# Project Structure

1. Conn struct: mimics a TCP connection with input/output buffers
2. parse_req(): parses incoming binary commands
3. do_request(): performs logic using a global std::map
4. make_response(): serializes the response into a binary format
5. main(): runs a test scenario to demonstrate functionality

### Future Possibility : Replace std::map with a custom hashtable