"""End-to-end tests for the Arabic CS study helper.

Every test drives the real app in a real browser. The Claude API is mocked, so the
suite is deterministic, needs no API key and costs nothing to run.
"""

from conftest import CHATS_STORAGE, fake_claude

FIRST_EXAMPLE = "ما هو الـ pointer في لغة C؟"


def ask_first_example(page):
    page.click(f"button.chip:has-text('{FIRST_EXAMPLE}')")
    page.wait_for_selector(".msg.bot")


# ---------- the first screen ----------

def test_welcome_screen_offers_example_questions(app):
    assert app.locator("#welcome").is_visible()
    assert app.locator("button.chip").count() == 4


def test_asking_without_a_key_opens_the_key_dialog(app_without_key):
    app_without_key.click("button.chip >> nth=0")
    assert app_without_key.locator("#keyDialog").is_visible()
    assert app_without_key.locator(".msg").count() == 0   # nothing is sent


# ---------- asking a question ----------

def test_question_and_streamed_answer_are_shown(app):
    fake_claude(app)
    ask_first_example(app)

    assert app.locator(".msg.user").inner_text().strip() == FIRST_EXAMPLE
    answer = app.locator(".msg.bot")
    assert "المؤشر" in answer.inner_text()
    assert app.locator("#welcome").count() == 0          # welcome screen is replaced


def test_markdown_is_rendered_not_shown_as_symbols(app):
    fake_claude(app)
    ask_first_example(app)

    answer = app.locator(".msg.bot")
    assert answer.locator("h4").count() == 1             # "## ..." became a heading
    assert answer.locator("pre").count() == 1            # ``` became a code block
    assert answer.locator("b").count() == 1              # ** ** became bold
    assert "##" not in answer.inner_text()
    assert "```" not in answer.inner_text()


def test_code_inside_the_answer_keeps_its_line_breaks(app):
    fake_claude(app)
    ask_first_example(app)

    code = app.locator(".msg.bot pre").inner_text()
    assert "int x = 5;" in code and "int *p = &x;" in code


# ---------- errors ----------

def test_invalid_key_shows_an_arabic_error_and_saves_nothing(app):
    fake_claude(app, status=401)
    app.click("button.chip >> nth=0")
    app.wait_for_selector(".msg.error")

    assert "المفتاح غير صحيح" in app.locator(".msg.error").inner_text()
    assert app.evaluate(f"localStorage.getItem('{CHATS_STORAGE}')") in (None, "[]")


def test_rate_limit_shows_its_own_message(app):
    fake_claude(app, status=429, error={"type": "error", "error": {"type": "rate_limit_error",
                                                                   "message": "slow down"}})
    app.click("button.chip >> nth=0")
    app.wait_for_selector(".msg.error")
    assert "طلبات كثيرة" in app.locator(".msg.error").inner_text()


# ---------- saved conversations ----------

def test_conversation_survives_a_page_reload(app):
    fake_claude(app)
    ask_first_example(app)

    app.reload()
    app.click("#chatsBtn")
    assert app.locator("#chatList li").count() == 1
    app.click("#chatList button.pick")

    assert app.locator(".msg.user").inner_text().strip() == FIRST_EXAMPLE
    assert "المؤشر" in app.locator(".msg.bot").inner_text()
    assert app.locator(".msg.bot pre").count() == 1      # code survives the round trip


def test_chat_is_named_after_the_first_question(app):
    fake_claude(app)
    ask_first_example(app)
    app.click("#chatsBtn")
    assert FIRST_EXAMPLE in app.locator("#chatList li").inner_text()


def test_new_chat_starts_from_the_welcome_screen(app):
    fake_claude(app)
    ask_first_example(app)

    app.click("#chatsBtn")
    app.click("#newChatBtn")

    assert app.locator("#welcome").is_visible()
    assert app.locator(".msg").count() == 0
    app.click("#chatsBtn")
    assert app.locator("#chatList li").count() == 1      # the old chat is still saved


def test_deleting_a_chat_removes_it_from_storage(app):
    fake_claude(app)
    ask_first_example(app)

    app.click("#chatsBtn")
    app.click("#chatList button.del")

    assert app.evaluate(f"localStorage.getItem('{CHATS_STORAGE}')") == "[]"
    assert "لا توجد محادثات" in app.locator("#chatList").inner_text()


# ---------- answer modes ----------

def test_selecting_a_mode_updates_the_buttons(app):
    app.click("button.mode[data-mode='quiz']")
    assert app.locator("button.mode[data-mode='quiz']").get_attribute("aria-pressed") == "true"
    assert app.locator("button.mode[data-mode='explain']").get_attribute("aria-pressed") == "false"


def test_quiz_mode_is_sent_to_the_model(app):
    sent = {}
    app.route("**/v1/messages*", lambda route, request: (
        sent.update(request.post_data_json or {}),
        route.fulfill(status=200,
                      headers={"access-control-allow-origin": "*", "content-type": "text/event-stream"},
                      body=""),
    )[-1])

    app.click("button.mode[data-mode='quiz']")
    app.fill("#input", "اختبرني عن المؤشرات")
    app.press("#input", "Enter")
    app.wait_for_timeout(1000)

    assert "ONE question at a time" in sent.get("system", "")
