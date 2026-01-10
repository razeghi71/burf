from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Label

from burf.storage import HAS_GCS, HAS_S3


class StorageSelectionScreen(Screen[str]):
    CSS = """
    StorageSelectionScreen {
        align: center middle;
    }

    #content {
        width: auto;
        height: auto;
        border: heavy $accent;
        padding: 2;
        align: center middle;
    }

    #question {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }

    Horizontal {
        width: auto;
        height: auto;
    }

    Button {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="content"):
            yield Label("Select Storage Provider", id="question")
            with Horizontal():
                yield Button(
                    "Google Cloud Storage (GCS)", id="gs", disabled=not HAS_GCS
                )
                yield Button("AWS S3", id="s3", disabled=not HAS_S3)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id:
            self.dismiss(event.button.id)


class StorageSelectionApp(App[str]):
    def on_mount(self) -> None:
        self.push_screen(StorageSelectionScreen(), callback=self.exit)
