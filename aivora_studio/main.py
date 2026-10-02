"""Desktop application entry point."""

import sys


def main():

    if "--qt-preview" in sys.argv[1:]:
        from .qt_preview import main as run_preview

        run_preview()
        return

    from .app import AivoraStudio

    app = AivoraStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
