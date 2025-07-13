#include <iostream>
#include <vector>
#include <map>
#include <string>
#include <cstring>

using namespace std;

const uint32_t k_max_args = 16;
const uint32_t RES_OK = 0;
const uint32_t RES_NX = 1;
const uint32_t RES_ERR = 2;

struct Conn {
    vector<uint8_t> incoming;
    vector<uint8_t> outgoing;
    bool want_close = false;
};

struct Response {
    uint32_t status = RES_OK;
    vector<uint8_t> data;
};

map<string, string> g_data;

// --- Helper functions ---
bool read_u32(const uint8_t *&cur, const uint8_t *end, uint32_t &out) {
    if (cur + 4 > end) return false;
    memcpy(&out, cur, 4);
    cur += 4;
    return true;
}

bool read_str(const uint8_t *&cur, const uint8_t *end, size_t n, string &out) {
    if (cur + n > end) return false;
    out.assign((const char*)cur, (const char*)cur + n);
    cur += n;
    return true;
}

void buf_append(vector<uint8_t> &buf, const uint8_t *data, size_t len) {
    buf.insert(buf.end(), data, data + len);
}

int32_t parse_req(const uint8_t *data, size_t size, vector<string> &out) {
    const uint8_t *end = data + size;
    uint32_t nstr = 0;
    if (!read_u32(data, end, nstr)) return -1;
    if (nstr > k_max_args) return -1;

    while (out.size() < nstr) {
        uint32_t len = 0;
        if (!read_u32(data, end, len)) return -1;
        out.push_back("");
        if (!read_str(data, end, len, out.back())) return -1;
    }
    if (data != end) return -1;
    return 0;
}

void do_request(vector<string> &cmd, Response &out) {
    if (cmd.size() == 2 && cmd[0] == "get") {
        auto it = g_data.find(cmd[1]);
        if (it == g_data.end()) {
            out.status = RES_NX;
            return;
        }
        const string &val = it->second;
        out.data.assign(val.begin(), val.end());
    } else if (cmd.size() == 3 && cmd[0] == "set") {
        g_data[cmd[1]] = cmd[2];
    } else if (cmd.size() == 2 && cmd[0] == "del") {
        g_data.erase(cmd[1]);
    } else {
        out.status = RES_ERR;
    }
}

void make_response(const Response &resp, vector<uint8_t> &out) {
    uint32_t resp_len = 4 + (uint32_t)resp.data.size();
    buf_append(out, (const uint8_t *)&resp_len, 4);
    buf_append(out, (const uint8_t *)&resp.status, 4);
    buf_append(out, resp.data.data(), resp.data.size());
}

bool try_one_request(Conn *conn) {
    if (conn->incoming.empty()) return false;

    vector<string> cmd;
    if (parse_req(conn->incoming.data(), conn->incoming.size(), cmd) < 0) {
        conn->want_close = true;
        return false;
    }

    Response resp;
    do_request(cmd, resp);
    make_response(resp, conn->outgoing);
    return true;
}

// --- Test Runner ---
void encode_command(const vector<string>& cmd, vector<uint8_t>& out) {
    uint32_t n = cmd.size();
    buf_append(out, (const uint8_t*)&n, 4);
    for (const auto& s : cmd) {
        uint32_t len = s.size();
        buf_append(out, (const uint8_t*)&len, 4);
        buf_append(out, (const uint8_t*)s.data(), len);
    }
}

void print_response(const vector<uint8_t>& buf) {
    const uint8_t* ptr = buf.data();
    const uint8_t* end = buf.data() + buf.size();
    uint32_t len, status;
    read_u32(ptr, end, len);
    read_u32(ptr, end, status);
    string value;
    read_str(ptr, end, len - 4, value);
    cout << "Status: " << status << ", Value: '" << value << "'\n";
}

int main() {
    Conn conn;

    // Test SET command
    encode_command({"set", "foo", "bar"}, conn.incoming);
    try_one_request(&conn);
    conn.incoming.clear();
    conn.outgoing.clear();

    // Test GET command
    encode_command({"get", "foo"}, conn.incoming);
    try_one_request(&conn);
    print_response(conn.outgoing);

    conn.incoming.clear();
    conn.outgoing.clear();

    // Test DEL command
    encode_command({"del", "foo"}, conn.incoming);
    try_one_request(&conn);
    conn.incoming.clear();
    conn.outgoing.clear();

    // Test GET after DEL
    encode_command({"get", "foo"}, conn.incoming);
    try_one_request(&conn);
    print_response(conn.outgoing);

    return 0;
}
