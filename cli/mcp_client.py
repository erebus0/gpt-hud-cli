import json, os, subprocess, threading, queue, re, time
CONTENT_LEN_RE = re.compile(rb"Content-Length:\s*(\d+)\r\n\r\n", re.I)

class MCPClient:
    def __init__(self, cmd, cwd=None, env=None):
        self.cmd = cmd if isinstance(cmd, list) else cmd.split()
        self.cwd = cwd or os.getcwd()
        self.env = {**os.environ, **(env or {})}
        self.proc = None
        self.reader = None
        self.err_reader = None
        self.q = queue.Queue()
        self.stderr_buf = []
        self._id = 0
        self._lock = threading.Lock()

    def start(self):
        self.proc = subprocess.Popen(
            self.cmd, cwd=self.cwd, env=self.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
        )
        self.reader = threading.Thread(target=self._read_loop, daemon=True); self.reader.start()
        self.err_reader = threading.Thread(target=self._err_loop, daemon=True); self.err_reader.start()
        time.sleep(0.2)

    def close(self):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try: self.proc.wait(timeout=2)
                except Exception: self.proc.kill()
        except Exception: pass

    def _read_loop(self):
        buf = b""; out = self.proc.stdout
        while True:
            chunk = out.read(4096)
            if not chunk: break
            buf += chunk
            while True:
                m = CONTENT_LEN_RE.search(buf)
                if not m: break
                header_end = m.end(); length = int(m.group(1))
                if len(buf) - header_end < length: break
                body = buf[header_end:header_end+length]
                buf = buf[header_end+length:]
                try: self.q.put(json.loads(body.decode("utf-8","ignore")))
                except Exception: pass

    def _err_loop(self):
        err = self.proc.stderr
        while True:
            line = err.readline()
            if not line: break
            try: s = line.decode("utf-8","ignore").rstrip()
            except Exception: s = str(line)
            self.stderr_buf.append(s)

    def _next_id(self):
        with self._lock:
            self._id += 1
            return self._id

    def _ensure_running(self):
        if not self.proc or self.proc.poll() is not None:
            tail = " | ".join(self.stderr_buf[-5:]) if self.stderr_buf else "no stderr"
            raise RuntimeError(f"MCP process not running (stderr: {tail})")

    def request(self, method, params=None, timeout=15.0):
        self._ensure_running()
        rid = self._next_id()
        payload = {"jsonrpc":"2.0","id":rid,"method":method}
        if params is not None: payload["params"] = params
        data = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
        self.proc.stdin.write(header + data); self.proc.stdin.flush()

        end = time.time() + timeout
        while time.time() < end:
            try: msg = self.q.get(timeout=0.1)
            except queue.Empty:
                self._ensure_running(); continue
            if isinstance(msg, dict) and msg.get("id") == rid:
                if "error" in msg: raise RuntimeError(msg["error"].get("message","Unknown MCP error"))
                return msg.get("result")
        self._ensure_running()
        raise TimeoutError(f"MCP request timeout: {method}")

    def list_tools(self):
        try: return self.request("tools/list")["tools"]
        except Exception: return self.request("tools.list")["tools"]

    def call_tool(self, name, arguments=None):
        arguments = arguments or {}
        try: return self.request("tools/call", {"name":name,"arguments":arguments})
        except Exception: return self.request("tools/execute", {"name":name,"arguments":arguments})
