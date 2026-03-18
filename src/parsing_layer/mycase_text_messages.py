# parsing_layer/mycase_text_messages.py
from playwright.sync_api import Page
from config.settings import BASE_CASE_URL
from time import sleep


def select_text_message(page: Page, case_id: int, message: str = "hola"):
    """
    Abre la página de text_messages de un caso y escribe un mensaje en el chat.
    Si el ID no existe (404) se imprime un aviso y se salta al siguiente.
    """
    url = f"{BASE_CASE_URL}/{case_id}/text_messages"
    print(f"➡️  Abriendo: {url}")

    # 1️⃣ Ir a la página y capturar la respuesta
    response = page.goto(url, wait_until="domcontentloaded")

    # 2️⃣ Comprobar si el servidor devolvió 404
    if not response or response.status == 404:
        print(f"⚠️  ID {case_id} no existe (404). Se omite.")
        return

    # 3️⃣ Esperar a que el textarea del chat esté visible
    page.wait_for_selector('textarea[name="message-textarea"]', state="visible", timeout=3000)

    # 4️⃣ Escribir el mensaje en el chat
    page.fill('textarea[name="message-textarea"]', message)
    print(f"✍️  Escribí '{message}' en el chat.")

    # 5️⃣ Enviar el mensaje presionando Enter
    try:
        page.press('textarea[name="message-textarea"]', "Enter")
        print("✅ Mensaje enviado con Enter.")
    except Exception as e:
        print(f"⚠️ No se pudo enviar el mensaje con Enter: {e}")

    sleep(2)  # Pequeña pausa para estabilidad
