require("http").createServer((q, r) => r.end(q.url === "/health" ? "ok" : "shop")).listen(3000);
