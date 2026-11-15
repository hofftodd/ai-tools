"""Tests for ai-search: python3 -m unittest -v (from this directory). Standard library only."""

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

HERE = Path(__file__).resolve().parent
_loader = SourceFileLoader("ai_search", str(HERE / "ai-search"))
_spec = spec_from_loader("ai_search", _loader)
assert _spec is not None
ais = module_from_spec(_spec)
_loader.exec_module(ais)

BRAVE_DOC = {
    "web": {
        "results": [
            {
                "title": "The <strong>Rust</strong> Book",
                "url": "https://doc.rust-lang.org/book/",
                "description": "Learn <strong>Rust</strong> &amp; more.",
                "extra_snippets": ["Chapter 1", ""],
                "page_age": "2026-10-01T00:00:00",
            },
            {"title": "Rust", "url": "https://www.rust-lang.org/"},
        ]
    }
}


class Fake:
    """A backend that records its calls and answers from a list of responses."""

    name = "fake"

    def __init__(self, *responses, min_interval=0.0):
        self.responses = list(responses) or [[ais.Result("T", "https://e.com", "c", "fake")]]
        self.min_interval = min_interval
        self.calls = []

    def search(self, q):
        self.calls.append((time.monotonic(), q))
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r


def make(backend, tmp, **kw):
    return ais.Search(backend, ais.Usage(Path(tmp) / "usage.json"), **kw)


class QueryTests(unittest.TestCase):
    def test_defaults_and_clamps(self):
        q = ais.parse_query({"q": ["  rust  "], "count": ["99"], "pageno": ["0"]})
        self.assertEqual((q.q, q.count, q.page, q.time_range), ("rust", 20, 1, ""))

    def test_rejects(self):
        for params, msg in [
            ({}, "missing q"),
            ({"q": ["x"], "format": ["html"]}, "only format=json"),
            ({"q": ["x"], "count": ["many"]}, "numbers"),
            ({"q": ["x"], "time_range": ["decade"]}, "time_range"),
        ]:
            with self.subTest(params=params), self.assertRaisesRegex(ais.BackendError, msg) as e:
                ais.parse_query(params)
            self.assertEqual(e.exception.status, 400)


class BraveTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.orig = ais._get_json

        def fake_get(url, headers, timeout):
            self.seen.append((url, headers))
            return BRAVE_DOC

        ais._get_json = fake_get

    def tearDown(self):
        ais._get_json = self.orig

    def test_maps_request_and_results(self):
        q = ais.Query("rust lang", count=5, page=2, language="en-US", time_range="week")
        results = ais.Brave("k").search(q)
        url, headers = self.seen[0]
        self.assertEqual(headers, {"X-Subscription-Token": "k"})
        for part in ("q=rust+lang", "count=5", "offset=1", "search_lang=en", "freshness=pw"):
            self.assertIn(part, url)
        self.assertEqual(results[0].title, "The Rust Book")
        self.assertEqual(results[0].content, "Learn Rust & more. … Chapter 1")
        self.assertEqual(results[0].published, "2026-10-01T00:00:00")
        self.assertEqual((results[1].content, results[1].engine), ("", "brave"))

    def test_needs_a_key(self):
        with self.assertRaises(SystemExit):
            ais.Brave("")


class SearchTests(unittest.TestCase):
    def test_cache_hits_skip_the_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Fake()
            s = make(fake, tmp)
            _, cached1 = s.search(ais.Query("a"))
            _, cached2 = s.search(ais.Query("a"))
            _, cached3 = s.search(ais.Query("a", count=3))  # a different query
            self.assertEqual((cached1, cached2, cached3), (False, True, False))
            self.assertEqual((len(fake.calls), s.hits, s.usage.calls), (2, 1, 2))

    def test_cache_expires(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Fake()
            s = make(fake, tmp, cache_ttl=0)
            s.search(ais.Query("a"))
            s.search(ais.Query("a"))
            self.assertEqual(len(fake.calls), 2)

    def test_calls_are_spaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Fake(min_interval=0.2)
            s = make(fake, tmp)
            threads = [
                threading.Thread(target=s.search, args=(ais.Query(f"q{i}"),)) for i in range(3)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            times = sorted(t for t, _ in fake.calls)
            gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
            self.assertEqual(len(times), 3)
            self.assertTrue(all(g >= 0.19 for g in gaps), gaps)

    def test_rate_limited_once_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok = [ais.Result("T", "https://e.com")]
            fake = Fake(ais.BackendError("slow down", 429), ok, min_interval=0.01)
            s = make(fake, tmp)
            orig_sleep = ais.time.sleep
            ais.time.sleep = lambda _s: None
            try:
                results, _ = s.search(ais.Query("a"))
            finally:
                ais.time.sleep = orig_sleep
            self.assertEqual((results, len(fake.calls)), (ok, 2))

    def test_other_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Fake(ais.BackendError("down"))
            with self.assertRaisesRegex(ais.BackendError, "down"):
                make(fake, tmp).search(ais.Query("a"))
            self.assertEqual(len(fake.calls), 1)

    def test_monthly_cap_survives_a_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(Fake(), tmp, monthly_cap=2)
            s.search(ais.Query("a"))
            s.search(ais.Query("b"))
            again = make(Fake(), tmp, monthly_cap=2)  # a restart: same usage file
            self.assertEqual(again.usage.calls, 2)
            with self.assertRaisesRegex(ais.BackendError, "monthly cap") as e:
                again.search(ais.Query("c"))
            self.assertEqual(e.exception.status, 429)
            s.search(ais.Query("a"))  # cached: no backend call, so not capped
            stale = json.dumps({"month": "2000-01", "calls": 99})
            (Path(tmp) / "usage.json").write_text(stale)
            self.assertEqual(make(Fake(), tmp).usage.calls, 0)  # a new month starts at 0


class HTTPTests(unittest.TestCase):
    def serve(self, token=""):
        self.tmp = tempfile.TemporaryDirectory()
        self.fake = Fake([ais.Result("Title", "https://e.com/x", "Snippet", "fake", "2026-01-01")])
        search = make(self.fake, self.tmp.name)
        self.server = ais.ThreadingHTTPServer(("127.0.0.1", 0), ais.make_handler(search, token))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def get(self, path, headers=None):
        req = urllib.request.Request(self.base + path, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_searxng_shape(self):
        """What ai-factory's research.search() reads: results[].title, url, content."""
        self.serve()
        status, doc = self.get("/search?q=hello+world&format=json")
        self.assertEqual(status, 200)
        self.assertEqual((doc["query"], doc["number_of_results"]), ("hello world", 1))
        r = doc["results"][0]
        self.assertEqual(
            (r["title"], r["url"], r["content"]), ("Title", "https://e.com/x", "Snippet")
        )
        self.assertEqual((r["engines"], r["publishedDate"]), (["fake"], "2026-01-01"))

    def test_errors_and_health(self):
        self.serve()
        self.assertEqual(self.get("/search?format=json")[0], 400)
        self.assertEqual(self.get("/nope")[0], 404)
        self.get("/search?q=a")
        status, health = self.get("/healthz")
        self.assertEqual((status, health["backend"], health["usage"]["calls"]), (200, "fake", 1))

    def test_token(self):
        self.serve(token="s3cret")
        self.assertEqual(self.get("/search?q=a")[0], 401)
        self.assertEqual(self.get("/search?q=a&token=s3cret")[0], 200)
        self.assertEqual(self.get("/search?q=a", {"Authorization": "Bearer s3cret"})[0], 200)
        self.assertEqual(self.get("/healthz")[0], 200)  # health needs no token


class BuildTests(unittest.TestCase):
    def test_backend_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"AI_SEARCH_STATE": tmp, "BRAVE_API_KEY": "k"}
            self.assertEqual(ais.build(env).backend.name, "brave")
            sx = ais.build({**env, "AI_SEARCH_BACKEND": "searxng",
                            "AI_SEARCH_SEARXNG_URL": "http://sx:8080/"})  # fmt: skip
            self.assertEqual((sx.backend.name, sx.backend.base), ("searxng", "http://sx:8080"))
            with self.assertRaises(SystemExit):
                ais.build({**env, "AI_SEARCH_BACKEND": "bing"})


if __name__ == "__main__":
    unittest.main()
