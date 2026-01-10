import threading
from enum import Enum
from typing import Any, Callable, Optional

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Middle
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar

from burf.storage.ds import CloudPath
from burf.storage.storage import Storage


class Deleter:
    def __init__(
        self,
        uri: CloudPath,
        storage: Storage,
        call_before_each_object: Callable[[CloudPath], Any],
        call_after_each_object: Callable[[CloudPath], Any],
    ) -> None:
        self.uri = uri
        self.stopped = False
        self._call_before = call_before_each_object
        self._call_after = call_after_each_object
        self._storage = storage
        self._blobs: Optional[list[CloudPath]] = None

    def list_blobs(self) -> list[CloudPath]:
        if self._blobs is None:
            if self.uri.is_blob:
                self._blobs = [self.uri]
            else:
                self._blobs = self._storage.list_all_blobs(self.uri)
        return self._blobs

    def number_of_blobs(self) -> int:
        return len(self.list_blobs())

    def delete(self) -> None:
        for blob in self.list_blobs():
            if self.stopped:
                break
            self._call_before(blob)
            self._storage.delete_blob(blob)
            self._call_after(blob)


class State(Enum):
    STOPPED = 0
    STARTED = 1
    FINISHED = 2


class DeleterScreen(Screen[None]):
    BINDINGS = [
        ("escape", "close", "close"),
        ("ctrl+x", "close", "close"),
    ]

    CSS = """
        #delete-info {
            margin-bottom: 1;
        }
        #deleter {
            display: none;
            padding-top: 2;
        }
        #question {
            padding-top: 2;
        }
        #horizontal {
            padding-top: 1;
        }
    """

    def __init__(
        self,
        delete_uri: CloudPath,
        storage: Storage,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._deleter = Deleter(
            delete_uri,
            storage,
            self.before_delete,
            self.after_delete,
        )
        self.state = State.STOPPED
        self._delete_thread: Optional[threading.Thread] = None

    def start_delete(self) -> None:
        total = self._deleter.number_of_blobs()

        def _set_total() -> None:
            self.progress.total = total

        self.app.call_from_thread(_set_total)

        self._deleter.delete()

        def _finish() -> None:
            if self._deleter.stopped:
                self.label.update("Delete stopped")
                self.state = State.STOPPED
            else:
                self.label.update("Delete finished")
                self.state = State.FINISHED
                # Refresh listing so the deleted object disappears.
                file_list = self.app.query_one("#file_list")
                if hasattr(file_list, "clear_cache"):
                    file_list.clear_cache()
                if hasattr(file_list, "refresh_contents"):
                    file_list.refresh_contents()

        self.app.call_from_thread(_finish)

    def before_delete(self, uri: CloudPath) -> None:
        self.app.call_from_thread(self.label.update, f"Deleting {uri}…")

    def after_delete(self, uri: CloudPath) -> None:
        def _update() -> None:
            self.progress.advance(1)
            self.label.update(f"Deleted {uri}")

        self.app.call_from_thread(_update)

    def compose(self) -> ComposeResult:
        self.label = Label("Ready to delete", id="delete-info")
        self.progress = ProgressBar(total=0)

        yield Header()

        with Container(id="question"):
            with Center():
                count_note = ""
                if not self._deleter.uri.is_blob:
                    count_note = " (this will delete all objects under the prefix)"
                # Use CloudPath's __str__ which includes scheme
                q = f"Proceed deleting {self._deleter.uri}{count_note}?"
                self.question_label = Label(q)
                yield self.question_label

            with Horizontal(id="horizontal"):
                with Center():
                    yield Button("Yes", id="yes")
                    yield Button("No", id="no")

        with Middle(id="deleter"):
            with Center():
                yield self.label
            with Center():
                yield self.progress

        yield Footer()

    def action_close(self) -> None:
        if self.state == State.STARTED:
            self.query_one("#question").styles.display = "block"
            self.question_label.update("Do you want to stop the delete?")
        else:
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.state == State.STOPPED:
            if event.button.id == "yes":
                self.query_one("#question").styles.display = "none"
                self.query_one("#deleter").styles.display = "block"
                self.state = State.STARTED
                self._deleter.stopped = False
                self._delete_thread = threading.Thread(
                    target=self.start_delete, daemon=True
                )
                self._delete_thread.start()
            else:
                self.dismiss()
        elif self.state == State.STARTED:
            if event.button.id == "yes":
                self._deleter.stopped = True
                self.dismiss()
            else:
                self.query_one("#question").styles.display = "none"
                self.query_one("#deleter").styles.display = "block"

    def on_unmount(self) -> None:
        self._deleter.stopped = True
