#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Five collectors share one vCenter content object in a thread pool (adapter.py). This test runs the shared read
from five threads at once, with a fake vCenter, and checks that each call gets its own objects.

It proves the code does not share state between calls. It does not prove how a real vCenter behaves under load:
that is the live test that is still open (see the engineering review, CON-01).

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from pyVmomi import vim
from utils import vi_property_collector


class FakeView:
    def __init__(self):
        self.destroyed = False

    def Destroy(self):
        self.destroyed = True


class FakeVCenter:
    """One content object, used by every thread. It answers each read with the objects of the thread that asked."""

    def __init__(self):
        self.views = []
        self.lock = threading.Lock()
        self.propertyCollector = self
        self.viewManager = self
        self.rootFolder = None

    def CreateContainerView(self, root, types, recursive):
        view = FakeView()
        with self.lock:
            self.views.append(view)
        return view

    def RetrievePropertiesEx(self, specs, options):
        # Each read is answered with one object per thread name, so a mixed-up answer shows as a wrong name.
        name = threading.current_thread().name
        return SimpleNamespace(objects=[f"object of {name}"], token=None)


def test_five_threads_reading_one_shared_content_each_get_their_own_objects(monkeypatch):
    monkeypatch.setattr(vi_property_collector.vmodl.query.PropertyCollector, "ObjectSpec", lambda **kw: SimpleNamespace(**kw))
    monkeypatch.setattr(vi_property_collector.vmodl.query.PropertyCollector, "FilterSpec", lambda **kw: SimpleNamespace(**kw))
    content = FakeVCenter()

    with ThreadPoolExecutor(max_workers=5, thread_name_prefix="job") as pool:
        answers = list(pool.map(
            lambda _: vi_property_collector.retrieve_properties(content, vim.HostSystem, ["name"]), range(20)))

    for answer in answers:
        assert len(answer) == 1
        assert answer[0].startswith("object of job_")
    # Each read released its own container view.
    assert len(content.views) == 20
    assert all(view.destroyed for view in content.views)
