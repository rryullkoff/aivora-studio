"""AudioTools behaviors for Aivora Studio."""

from .dependencies import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageTk,
    get_ffmpeg_exe,
    messagebox,
    subprocess,
    tk,
)
from . import config
from .config import (
    ACCENT,
    ACCENT_HOVER,
    BORDER,
    CARD_2,
    MUTED,
    TEXT,
)
from .helpers import (
    get_extension,
)


class AudioToolsMixin:

    def create_audio_analysis_panel(self, parent):

        panel = tk.Frame(parent, bg=CARD_2)
        self.audio_analysis_panel = panel
        panel.pack(fill="x", padx=20, pady=(14, 4))

        header = tk.Frame(panel, bg=CARD_2)
        header.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(
            header,
            text="Bande son",
            bg=CARD_2,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        self.waveform_label = tk.Label(
            header,
            text="CHARGE UN FICHIER POUR L'APERÇU",
            bg=CARD_2,
            fg=MUTED,
            font=("Segoe UI", 8),
        )
        self.waveform_label.pack(side="right")

        tk.Button(
            header,
            text="Calculer le BPM",
            command=self.calculate_bpm,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 8, "bold"),
            padx=11,
            pady=5,
        ).pack(side="right", padx=(0, 8))

        self.waveform_canvas = tk.Canvas(
            panel,
            bg=CARD_2,
            height=88,
            highlightthickness=0,
        )
        self.waveform_canvas.pack(fill="x", padx=10, pady=(6, 10))
        self.waveform_canvas.bind(
            "<Configure>",
            lambda event: self.draw_waveform(),
        )

        self.waveform_peaks = []

    def decode_audio_pcm(self, sample_rate, duration=None):

        if not self.current_file or get_ffmpeg_exe is None:
            return None

        command = [
            get_ffmpeg_exe(),
            "-v",
            "error",
            "-i",
            self.current_file,
        ]

        if duration is not None:
            command.extend(["-t", str(duration)])

        command.extend(
            [
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-f",
                "s16le",
                "pipe:1",
            ]
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        return result.stdout or None

    def get_pcm_peaks(self, data, bucket_count):

        samples = memoryview(data).cast("h")

        if not samples:
            return []

        bucket_count = min(bucket_count, len(samples))
        peaks = []

        for index in range(bucket_count):
            start = index * len(samples) // bucket_count
            end = (index + 1) * len(samples) // bucket_count
            peak = max(abs(sample) for sample in samples[start:end])
            peaks.append(peak / 32768.0)

        return peaks

    def estimate_audio_bpm(self):

        sample_rate = 44100
        hop_size = 512
        data = self.decode_audio_pcm(sample_rate, duration=45)

        if not data:
            return None

        envelope = self.get_pcm_peaks(
            data,
            max(1, len(data) // 2 // hop_size),
        )

        if len(envelope) < 32:
            return None

        onsets = [
            max(0.0, envelope[index] - envelope[index - 1])
            for index in range(1, len(envelope))
        ]
        average = sum(onsets) / len(onsets)

        if max(onsets, default=0.0) <= average * 1.5:
            return None

        centered_onsets = [value - average for value in onsets]
        hops_per_second = sample_rate / hop_size
        min_lag = max(1, int(hops_per_second * 60 / 200))
        max_lag = min(
            len(centered_onsets) // 2,
            int(hops_per_second * 60 / 60),
        )

        if min_lag >= max_lag:
            return None

        best_lag = max(
            range(min_lag, max_lag + 1),
            key=lambda lag: sum(
                centered_onsets[index] * centered_onsets[index - lag]
                for index in range(lag, len(centered_onsets))
            ),
        )
        bpm = 60 * hops_per_second / best_lag

        while bpm < 80:
            bpm *= 2
        while bpm > 180:
            bpm /= 2

        return str(round(bpm))

    def calculate_bpm(self, show_error=True):

        if not config.ENABLE_AUDIO_ANALYSIS:
            return None

        bpm = self.estimate_audio_bpm()

        if not bpm:
            if show_error:
                messagebox.showwarning(
                    "BPM INDISPONIBLE",
                    "LE BPM N'A PAS PU ÊTRE ESTIMÉ POUR CE FICHIER AUDIO.",
                )
            return None

        entry = self.entries["bpm"]
        entry.delete(0, tk.END)
        entry.insert(0, bpm)
        self.waveform_label.config(text=f"BPM ESTIMÉ : {bpm}")

        return bpm

    def load_waveform(self):

        if not config.ENABLE_AUDIO_ANALYSIS:
            self.waveform_peaks = []
            self.draw_waveform()
            return

        self.waveform_peaks = []

        data = self.decode_audio_pcm(sample_rate=1000)

        if not data:
            self.waveform_peaks = []
            self.waveform_label.config(
                text="APERÇU AUDIO INDISPONIBLE",
            )

        else:
            self.waveform_peaks = self.get_pcm_peaks(data, bucket_count=180)
            extension = get_extension(self.current_file).lstrip(".").upper()
            existing_bpm = self.entries["bpm"].get().strip()
            label = f"{extension} • FORME D'ONDE"
            if existing_bpm:
                label = f"{extension} • BPM : {existing_bpm}"
            self.waveform_label.config(text=label)

        self.draw_waveform()

    def draw_waveform(self):

        canvas = self.waveform_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)

        if not self.waveform_peaks:
            middle = height / 2
            canvas.create_line(14, middle, width - 14, middle, fill=BORDER)
            canvas.create_text(
                width / 2,
                middle,
                text="LA FORME D'ONDE APPARAÎTRA ICI",
                fill=MUTED,
                font=("Segoe UI", 8),
            )
            return

        scale = 3
        image_width = max(1, width * scale)
        image_height = max(1, height * scale)
        middle = image_height / 2
        peaks = self.waveform_peaks

        for _ in range(2):
            peaks = [
                (
                    peaks[max(0, index - 2)]
                    + 2 * peaks[max(0, index - 1)]
                    + 3 * peaks[index]
                    + 2 * peaks[min(len(peaks) - 1, index + 1)]
                    + peaks[min(len(peaks) - 1, index + 2)]
                ) / 9
                for index in range(len(peaks))
            ]

        envelope = []
        for index, peak in enumerate(peaks):
            amplitude = max(1.5, min(0.43, peak ** 0.72) * (height / 2 - 8))
            x = (index / max(len(peaks) - 1, 1)) * (image_width - 2 * scale) + scale
            envelope.append((x, middle - amplitude * scale))

        upper_curve = self.interpolate_waveform(envelope, 5)
        lower_curve = [(x, 2 * middle - y) for x, y in reversed(upper_curve)]
        outline = upper_curve + lower_curve

        mask = Image.new("L", (image_width, image_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(outline, fill=210)
        glow_mask = mask.filter(ImageFilter.GaussianBlur(radius=height * scale / 12))

        accent_color = tuple(
            int(ACCENT[index:index + 2], 16)
            for index in (1, 3, 5)
        )
        accent_hover_color = tuple(
            int(ACCENT_HOVER[index:index + 2], 16)
            for index in (1, 3, 5)
        )
        background = tuple(
            int(CARD_2[index:index + 2], 16)
            for index in (1, 3, 5)
        )
        image = Image.new("RGBA", (image_width, image_height), (*background, 255))
        glow = Image.new("RGBA", (image_width, image_height), (*accent_color, 0))
        glow.putalpha(glow_mask.point(lambda value: int(value * 0.34)))
        image = Image.alpha_composite(image, glow)

        gradient = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        color_stops = (
            (0.0, accent_color),
            (0.52, accent_hover_color),
            (1.0, accent_color),
        )
        for x in range(image_width):
            progress = x / max(image_width - 1, 1)
            for stop_index in range(len(color_stops) - 1):
                start, start_color = color_stops[stop_index]
                end, end_color = color_stops[stop_index + 1]
                if start <= progress <= end:
                    blend = (progress - start) / (end - start)
                    color = tuple(
                        round(first + (second - first) * blend)
                        for first, second in zip(start_color, end_color)
                    )
                    break
            else:
                color = color_stops[-1][1]

            gradient_draw.line(
                (x, 0, x, image_height),
                fill=(*color, 255),
            )

        gradient.putalpha(mask)
        image = Image.alpha_composite(image, gradient)

        draw = ImageDraw.Draw(image)
        middle_line = round(middle)
        draw.line(
            (scale * 2, middle_line, image_width - scale * 2, middle_line),
            fill=(255, 255, 255, 24),
            width=scale,
        )
        draw.line(upper_curve, fill=(255, 255, 255, 220), width=scale + 1)
        draw.line(
            [(x, 2 * middle - y) for x, y in upper_curve],
            fill=(*accent_color, 190),
            width=scale,
        )

        self.waveform_photo = ImageTk.PhotoImage(
            image.resize((width, height), Image.Resampling.LANCZOS)
        )
        canvas.create_image(0, 0, image=self.waveform_photo, anchor="nw")

    def interpolate_waveform(self, points, steps_per_segment):

        if len(points) < 3:
            return points

        smooth_points = []
        for index in range(len(points) - 1):
            previous = points[max(0, index - 1)]
            current = points[index]
            following = points[index + 1]
            after = points[min(len(points) - 1, index + 2)]

            for step in range(steps_per_segment):
                t = step / steps_per_segment
                t_squared = t * t
                t_cubed = t_squared * t
                x = current[0] + (following[0] - current[0]) * t
                y = 0.5 * (
                    2 * current[1]
                    + (-previous[1] + following[1]) * t
                    + (2 * previous[1] - 5 * current[1] + 4 * following[1] - after[1]) * t_squared
                    + (-previous[1] + 3 * current[1] - 3 * following[1] + after[1]) * t_cubed
                )
                smooth_points.append((round(x), round(y)))

        smooth_points.append(points[-1])
        return smooth_points
