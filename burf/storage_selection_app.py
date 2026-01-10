from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.widgets import Button, Footer, Label

from burf.storage import HAS_GCS, HAS_S3


class StorageSelectionApp(App[str]):
    CSS = """
    Screen {
        align: center middle;
    }
    #question {
        margin-bottom: 2;
        text-align: center;
    }
    Button {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Center():
            with Middle():
                yield Label("Select Storage Provider", id="question")
                with Center():
                    yield Button(
                        "Google Cloud Storage (GCS)", id="gs", disabled=not HAS_GCS
                    )
                    yield Button("AWS S3", id="s3", disabled=not HAS_S3)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id:
            self.exit(event.button.id)
