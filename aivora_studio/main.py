"""Desktop application entry point."""

from .app import AivoraStudio


def main():
    app = AivoraStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
