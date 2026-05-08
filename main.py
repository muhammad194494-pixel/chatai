from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
import threading
import requests
import json
import os
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────
API_URL = "http://149.13.58.193:8000/v1/chat/completions"
API_KEY = "mael-rop"
MODEL   = "0727-360B-API"

SYSTEM_PROMPT = """Kamu adalah Mael, asisten AI yang cerdas, ramah, dan helpful.
Nama kamu adalah Mael. Selalu jawab dengan sopan, jelas, dan natural dalam bahasa yang sama dengan user.
Kamu memiliki memori percakapan — ingat semua yang sudah dibicarakan sebelumnya.
Jika user bertanya siapa kamu, jawab bahwa kamu adalah Mael, asisten AI yang selalu siap membantu."""

# ─── WARNA ────────────────────────────────────────────────
BG_DARK     = (0.07, 0.07, 0.12, 1)
BG_CARD     = (0.11, 0.11, 0.18, 1)
BG_INPUT    = (0.14, 0.14, 0.22, 1)
ACCENT      = (0.29, 0.56, 1.0,  1)
ACCENT2     = (0.50, 0.27, 0.90, 1)
TEXT_WHITE  = (1,    1,    1,    1)
TEXT_GRAY   = (0.6,  0.6,  0.7,  1)
BUBBLE_AI   = (0.14, 0.16, 0.26, 1)
BUBBLE_USER = (0.20, 0.40, 0.80, 1)
RED_SOFT    = (0.85, 0.25, 0.35, 1)

Window.clearcolor = BG_DARK


# ──────────────────────────────────────────────────────────
def get_history_path():
    """Path file JSON untuk simpan history."""
    try:
        from android.storage import app_storage_path  # type: ignore
        storage = app_storage_path()
    except Exception:
        storage = os.path.expanduser("~")
    return os.path.join(storage, "mael_history.json")


def load_history():
    """Muat history dari file JSON. Return list of dict."""
    path = get_history_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history_display):
    """Simpan history ke file JSON."""
    path = get_history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history_display, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Save Error] {e}")


def build_api_messages(history_display):
    """
    Konversi display history → format API messages.
    System prompt selalu ada di posisi pertama.
    """
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history_display:
        msgs.append({"role": item["role"], "content": item["content"]})
    return msgs


# ──────────────────────────────────────────────────────────
class RoundedBox(Widget):
    def __init__(self, bg_color=(0.1, 0.1, 0.2, 1), radius=14, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius   = radius
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[radius]
            )
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self.rect.pos  = self.pos
        self.rect.size = self.size


# ──────────────────────────────────────────────────────────
class DateSeparator(BoxLayout):
    """Label tanggal pemisah antar hari."""
    def __init__(self, date_str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height      = dp(32)
        self.padding     = [dp(10), dp(4)]
        self.spacing     = dp(6)
        self.add_widget(Widget())
        lbl = Label(
            text=f"[color=666688]─── {date_str} ───[/color]",
            markup=True,
            font_size=dp(11),
            size_hint=(None, 1),
            color=TEXT_GRAY,
            italic=True,
        )
        lbl.bind(texture_size=lbl.setter('size'))
        self.add_widget(lbl)
        self.add_widget(Widget())


# ──────────────────────────────────────────────────────────
class ChatBubble(BoxLayout):
    def __init__(self, text, is_user=False, time_str="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding     = [dp(10), dp(4)]
        self.spacing     = dp(2)

        color      = BUBBLE_USER if is_user else BUBBLE_AI
        align      = 'right'     if is_user else 'left'
        sender     = "Kamu"      if is_user else "✦ Mael"
        sender_hex = "5b9aff"    if is_user else "a07fff"

        # Header: nama + waktu
        header_row = BoxLayout(size_hint_y=None, height=dp(18))
        name_lbl = Label(
            text=f"[b][color={sender_hex}]{sender}[/color][/b]",
            markup=True, size_hint_y=None,
            halign=align, font_size=dp(11), color=TEXT_GRAY,
        )
        name_lbl.bind(texture_size=name_lbl.setter('size'))

        time_lbl = Label(
            text=f"[color=555577]{time_str}[/color]",
            markup=True, size_hint_y=None,
            halign='right', font_size=dp(10), color=TEXT_GRAY,
        )
        time_lbl.bind(texture_size=time_lbl.setter('size'))

        if is_user:
            header_row.add_widget(Widget())
            header_row.add_widget(time_lbl)
            header_row.add_widget(name_lbl)
        else:
            header_row.add_widget(name_lbl)
            header_row.add_widget(time_lbl)
            header_row.add_widget(Widget())

        # Bubble konten
        bubble_row = BoxLayout(size_hint_y=None, spacing=0)

        if is_user:
            bubble_row.add_widget(Widget())

        card = RoundedBox(bg_color=color, radius=dp(14))
        msg_label = Label(
            text=text, markup=True,
            size_hint=(None, None),
            halign='left', valign='top',
            font_size=dp(14.5), color=TEXT_WHITE,
            padding=(dp(14), dp(10)),
        )
        msg_label.bind(
            width=lambda *_: setattr(
                msg_label, 'text_size', (msg_label.width, None)
            ),
            texture_size=lambda *_: setattr(
                msg_label, 'height', msg_label.texture_size[1] + dp(20)
            )
        )
        card.add_widget(msg_label)
        card.bind(
            size=lambda *_: setattr(msg_label, 'width', card.width),
            pos=lambda *_: setattr(msg_label, 'pos', card.pos),
        )
        card.size_hint_x = 0.78 if is_user else 0.85

        bubble_row.add_widget(card)
        if not is_user:
            bubble_row.add_widget(Widget())

        bubble_row.height = dp(50)
        msg_label.bind(
            height=lambda *_: setattr(bubble_row, 'height', msg_label.height)
        )

        self.add_widget(header_row)
        self.add_widget(bubble_row)

        def _recalc(*_):
            self.height = header_row.height + bubble_row.height + dp(12)
        bubble_row.bind(height=_recalc)
        self.height = dp(80)


# ──────────────────────────────────────────────────────────
class HeaderBar(BoxLayout):
    def __init__(self, on_clear=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height      = dp(60)
        self.padding     = [dp(14), dp(8)]
        self.spacing     = dp(10)

        with self.canvas.before:
            Color(*BG_CARD)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *_: setattr(self._bg, 'pos', self.pos),
            size=lambda *_: setattr(self._bg, 'size', self.size),
        )

        # Avatar
        avatar = Label(
            text="M", font_size=dp(22), bold=True,
            size_hint=(None, 1), width=dp(44), color=TEXT_WHITE,
        )
        with avatar.canvas.before:
            Color(*ACCENT2)
            avatar._circ = Ellipse(pos=avatar.pos, size=(dp(44), dp(44)))
        avatar.bind(pos=lambda *_: setattr(avatar._circ, 'pos', avatar.pos))

        # Info teks
        info = BoxLayout(orientation='vertical', spacing=0)
        name_lbl = Label(
            text="[b]Mael[/b]", markup=True,
            font_size=dp(16), color=TEXT_WHITE, halign='left',
        )
        name_lbl.bind(size=lambda *_: setattr(name_lbl, 'text_size', name_lbl.size))
        status_lbl = Label(
            text="[color=33dd88]● Online[/color]", markup=True,
            font_size=dp(11), color=TEXT_GRAY, halign='left',
        )
        status_lbl.bind(
            size=lambda *_: setattr(status_lbl, 'text_size', status_lbl.size)
        )
        info.add_widget(name_lbl)
        info.add_widget(status_lbl)

        # Tombol hapus 🗑
        clear_btn = Button(
            text="🗑", font_size=dp(20),
            size_hint=(None, 1), width=dp(44),
            background_color=(0, 0, 0, 0),
            color=(0.85, 0.3, 0.3, 1),
        )
        if on_clear:
            clear_btn.bind(on_press=lambda *_: on_clear())

        self.add_widget(avatar)
        self.add_widget(info)
        self.add_widget(Widget())
        self.add_widget(clear_btn)


# ──────────────────────────────────────────────────────────
class TypingIndicator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height      = dp(44)
        self.padding     = [dp(14), dp(6)]

        self._lbl = Label(
            text="[color=9999cc]Mael sedang mengetik...[/color]",
            markup=True, font_size=dp(13), italic=True, color=TEXT_GRAY,
        )
        self.add_widget(self._lbl)
        self._n   = 0
        self._evt = Clock.schedule_interval(self._tick, 0.45)

    def _tick(self, *_):
        dots = [".", "..", "..."][self._n % 3]
        self._lbl.text = f"[color=9999cc]Mael sedang mengetik{dots}[/color]"
        self._n += 1

    def stop(self):
        self._evt.cancel()


# ──────────────────────────────────────────────────────────
class ChatApp(App):

    def build(self):
        self.title          = "Mael AI"
        self._typing_widget = None
        self._last_date     = None

        # ── Muat history dari JSON ──
        self.history_display = load_history()

        root = BoxLayout(orientation='vertical')

        # Header
        root.add_widget(HeaderBar(on_clear=self._confirm_clear))

        # Chat scroll area
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.chat_box = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=dp(6), padding=[dp(10), dp(10)],
        )
        self.chat_box.bind(minimum_height=self.chat_box.setter('height'))
        self.scroll.add_widget(self.chat_box)
        root.add_widget(self.scroll)

        # Input bar
        input_bar = BoxLayout(
            size_hint_y=None, height=dp(64),
            padding=[dp(10), dp(8)], spacing=dp(8),
        )
        with input_bar.canvas.before:
            Color(*BG_CARD)
            input_bar._bg = Rectangle(pos=input_bar.pos, size=input_bar.size)
        input_bar.bind(
            pos=lambda *_: setattr(input_bar._bg, 'pos', input_bar.pos),
            size=lambda *_: setattr(input_bar._bg, 'size', input_bar.size),
        )

        self.user_input = TextInput(
            hint_text="  Tulis pesan ke Mael...",
            multiline=False,
            background_color=(0, 0, 0, 0),
            foreground_color=TEXT_WHITE,
            cursor_color=ACCENT,
            font_size=dp(14),
            padding=[dp(14), dp(12)],
            size_hint=(1, 1),
        )
        with self.user_input.canvas.before:
            Color(*BG_INPUT)
            self.user_input._bg = RoundedRectangle(
                pos=self.user_input.pos,
                size=self.user_input.size,
                radius=[dp(22)]
            )
        self.user_input.bind(
            pos=lambda *_: setattr(
                self.user_input._bg, 'pos', self.user_input.pos
            ),
            size=lambda *_: setattr(
                self.user_input._bg, 'size', self.user_input.size
            ),
            on_text_validate=self.send_message,
        )

        send_btn = Button(
            text="➤", font_size=dp(20),
            size_hint=(None, 1), width=dp(46),
            background_color=(0, 0, 0, 0),
            color=TEXT_WHITE, bold=True,
        )
        with send_btn.canvas.before:
            Color(*ACCENT)
            send_btn._bg = RoundedRectangle(
                pos=send_btn.pos, size=send_btn.size, radius=[dp(23)]
            )
        send_btn.bind(
            pos=lambda *_: setattr(send_btn._bg, 'pos', send_btn.pos),
            size=lambda *_: setattr(send_btn._bg, 'size', send_btn.size),
            on_press=self.send_message,
        )

        input_bar.add_widget(self.user_input)
        input_bar.add_widget(send_btn)
        root.add_widget(input_bar)

        # Render history atau sambutan
        if self.history_display:
            Clock.schedule_once(self._render_saved_history, 0.2)
        else:
            Clock.schedule_once(lambda dt: self._add_bubble(
                "Halo! Aku [b]Mael[/b] \U0001f44b\nAda yang bisa aku bantu hari ini?",
                is_user=False, save=False
            ), 0.3)

        return root

    # ── Render ulang history tersimpan ────────────────────
    def _render_saved_history(self, *_):
        for item in self.history_display:
            date_str = item.get("date", "")
            if date_str and date_str != self._last_date:
                self.chat_box.add_widget(DateSeparator(date_str))
                self._last_date = date_str
            self.chat_box.add_widget(ChatBubble(
                text=item["content"],
                is_user=(item["role"] == "user"),
                time_str=item.get("time", ""),
            ))
        Clock.schedule_once(
            lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.2
        )

    # ── Tambah bubble baru + simpan ───────────────────────
    def _add_bubble(self, text, is_user=False, save=True):
        now      = datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d %b %Y")

        if date_str != self._last_date:
            self.chat_box.add_widget(DateSeparator(date_str))
            self._last_date = date_str

        self.chat_box.add_widget(
            ChatBubble(text=text, is_user=is_user, time_str=time_str)
        )
        Clock.schedule_once(
            lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.15
        )

        if save:
            self.history_display.append({
                "role":    "user" if is_user else "assistant",
                "content": text,
                "time":    time_str,
                "date":    date_str,
            })
            save_history(self.history_display)

    # ── Typing indicator ───────────────────────────────────
    def _show_typing(self):
        self._typing_widget = TypingIndicator()
        self.chat_box.add_widget(self._typing_widget)
        Clock.schedule_once(
            lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1
        )

    def _hide_typing(self):
        if self._typing_widget:
            self._typing_widget.stop()
            self.chat_box.remove_widget(self._typing_widget)
            self._typing_widget = None

    # ── Kirim pesan ───────────────────────────────────────
    def send_message(self, *_):
        msg = self.user_input.text.strip()
        if not msg:
            return
        self._add_bubble(msg, is_user=True)
        self.user_input.text = ""
        self._show_typing()
        threading.Thread(target=self._call_api, daemon=True).start()

    # ── Panggil API (thread) ───────────────────────────────
    def _call_api(self):
        try:
            headers = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {API_KEY}",
            }
            payload = {
                "model":       MODEL,
                "messages":    build_api_messages(self.history_display),
                "max_tokens":  1024,
                "temperature": 0.8,
            }
            resp = requests.post(
                API_URL, headers=headers, json=payload, timeout=45
            )
            data = resp.json()

            if "choices" in data and data["choices"]:
                reply = data["choices"][0]["message"]["content"].strip()
            else:
                reply = f"\u26a0\ufe0f Respons tidak valid dari server."

        except requests.exceptions.Timeout:
            reply = "\u26a0\ufe0f Timeout. Coba lagi ya!"
        except requests.exceptions.ConnectionError:
            reply = "\u26a0\ufe0f Gagal terhubung ke server."
        except Exception as e:
            reply = f"\u26a0\ufe0f Error: {str(e)}"

        Clock.schedule_once(lambda dt: self._on_reply(reply))

    def _on_reply(self, reply):
        self._hide_typing()
        self._add_bubble(reply, is_user=False)

    # ── Konfirmasi hapus history ───────────────────────────
    def _confirm_clear(self):
        box = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(14))
        box.add_widget(Label(
            text="Hapus semua history chat?\nTidak bisa dikembalikan!",
            halign='center', color=TEXT_WHITE, font_size=dp(14),
        ))
        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        cancel_btn = Button(
            text="Batal", background_color=BG_INPUT, color=TEXT_WHITE
        )
        clear_btn = Button(
            text="Hapus Semua", background_color=RED_SOFT, color=TEXT_WHITE
        )

        def do_clear(*_):
            popup.dismiss()
            self._clear_history()

        cancel_btn.bind(on_press=lambda *_: popup.dismiss())
        clear_btn.bind(on_press=do_clear)
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(clear_btn)
        box.add_widget(btn_row)

        popup = Popup(
            title="Konfirmasi Hapus",
            title_color=TEXT_WHITE,
            content=box,
            size_hint=(0.85, None), height=dp(200),
            background_color=BG_CARD,
            separator_color=ACCENT,
        )
        popup.open()

    def _clear_history(self):
        self.history_display = []
        self._last_date      = None
        save_history([])
        self.chat_box.clear_widgets()
        Clock.schedule_once(lambda dt: self._add_bubble(
            "History dihapus \U0001f5d1\ufe0f\nHalo lagi! Aku [b]Mael[/b], ada yang bisa aku bantu?",
            is_user=False, save=False
        ), 0.2)


# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    ChatApp().run()

