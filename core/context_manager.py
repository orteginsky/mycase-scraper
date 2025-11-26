# core/context_manager.py
"""
Context managers for safe resource management.
Ensures Playwright sessions are properly closed even on errors.
"""
from contextlib import contextmanager
from typing import Generator
from playwright.sync_api import sync_playwright, Page, BrowserContext, Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from core import config
from core.exceptions import AuthenticationError, SessionExpiredError
from utils.logger import get_logger

logger = get_logger(__name__)


def _create_playwright_context(persistent: bool = True):
    """
    Creates an optimized Playwright context for MyCase scraping.
    Maintains persistent session and blocks heavy resources.

    Args:
        persistent: If True, uses persistent browser profile (keeps cookies)

    Returns:
        tuple: (playwright_instance, context, page)
    """
    p = sync_playwright().start()

    try:
        if persistent:
            # 1. DEFINIR ARGUMENTOS (Igual que en seed_playwright_profile.py)
            browser_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                # --- CRÍTICO: Para leer las cookies del seed script ---
                "--password-store=basic", 
                "--use-mock-keychain",
            ]

            # 2. MANEJO DEL MODO HEADLESS (El arreglo para el crash)
            is_headless_requested = config.PW_HEADLESS
            
            if is_headless_requested:
                # Usamos el "Nuevo Headless" de Chrome que es más estable
                browser_args.append("--headless=new")
            
            launch_kwargs = {
                "user_data_dir": str(config.PW_USER_DATA_DIR),
                # TRUCO: Le decimos a Playwright que es "Headed" (False) para evitar que use
                # su driver antiguo, pero pasamos "--headless=new" en args para ocultarlo visualmente.
                "headless": False, 
                "args": browser_args,
                # Definir viewport es vital en headless para que no cargue versión móvil
                "viewport": {"width": 1920, "height": 1080} 
            }

            # 3. FORZAR USO DE CHROME (Igual que en el seed)
            # Si el config tiene algo, úsalo, si no, prefiere "chrome" sobre "chromium"
            launch_kwargs["channel"] = config.PW_BROWSER_CHANNEL or "chrome"

            logger.info(
                "Launching Playwright persistent context | logic_headless=%s | channel=%s",
                is_headless_requested,
                launch_kwargs["channel"]
            )

            context = p.chromium.launch_persistent_context(**launch_kwargs)
            logger.info("Persistent context created at %s", config.PW_USER_DATA_DIR)
        else:
            # Contexto Efímero (Para pruebas sin perfil)
            browser = p.chromium.launch(
                headless=config.PW_HEADLESS,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            logger.info("Ephemeral context started")

        # Obtener la página (launch_persistent_context ya crea una, new_context no)
        if persistent:
            page = context.pages[0]
        else:
            page = context.new_page()
            
        page.set_default_timeout(config.PW_TIMEOUT_MS)

        # Block unnecessary resources for speed
        if config.PW_BLOCK_RESOURCES:
            page.route(
                "**/*",
                lambda route, req: (
                    route.abort() if req.resource_type in config.PW_BLOCK_RESOURCES else route.continue_()
                ),
            )

        return p, context, page

    except Exception as e:
        logger.exception("Error creating Playwright context: %s", e)
        try:
            p.stop()
        except Exception:
            pass
        raise


def _ensure_logged_in(page: Page) -> None:
    """
    Ensures the user is logged into MyCase.
    Checks for active session, performs login if needed.
    """
    try:
        logger.info("Opening MyCase Dashboard...")
        # Aumentamos el timeout de navegación a 60s por si el internet es lento
        page.goto(config.DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)

        # --- FUNCIÓN DE VERIFICACIÓN ROBUSTA ---
        def check_is_logged_in():
            """Retorna True si ve elementos del Dashboard"""
            try:
                # Buscamos cualquiera de estos textos que aparecen en tu captura
                # "text=Home" es muy rápido y fiable en Playwright
                if page.is_visible("text=Home") and page.is_visible("text=Cases"):
                    return True
                # O busca un elemento específico si el texto falla
                if page.is_visible("text=My hours billed"): 
                    return True
                # El check original (nav) como respaldo
                if page.is_visible("nav"):
                    return True
                return False
            except:
                return False

        # 1. Verificar si ya estamos dentro (Cookies válidas)
        if check_is_logged_in():
             logger.info("Active session detected (Verified by text content)")
             return

        logger.info("No active session detected, attempting login...")

        # 2. Realizar Login
        if not config.MYCASE_EMAIL or not config.MYCASE_PASSWORD:
            raise AuthenticationError("MYCASE_EMAIL and MYCASE_PASSWORD must be configured")

        logger.info("Filling credentials...")
        page.fill("#login_session_email", config.MYCASE_EMAIL)
        page.fill("#login_session_password", config.MYCASE_PASSWORD)
        
        # Click y esperar navegación
        # Usamos wait_for_navigation para asegurar que la página cambió
        with page.expect_navigation(timeout=30000):
            page.click("#login-form-submit")

        # 3. Verificación Final (Post-Login)
        # Esperamos un poco a que renderice el texto
        try:
            # Esperar a que aparezca "Home" o "Billing" en la pantalla
            page.wait_for_selector("text=Home", timeout=20000)
            logger.info("Login successful (Dashboard text detected)")
        except PlaywrightTimeout:
            # Si falla, hacemos un último check manual
            if check_is_logged_in():
                logger.info("Login successful (Fallback check passed)")
            else:
                raise PlaywrightTimeout("Could not find Dashboard text")

    except PlaywrightTimeout:
        logger.error("Dashboard not detected after login attempt")
        try:
            page.screenshot(path="login_failure_debug.png")
            logger.info("Screenshot saved to login_failure_debug.png")
            # IMPRIMIR EL HTML PARA VER QUÉ ESTÁ PASANDO
            logger.info(f"Current URL: {page.url}")
        except:
            pass
            
        raise AuthenticationError(
            "Failed to reach dashboard after login. Check credentials or internet speed."
        )
    except AuthenticationError:
        raise
    except Exception as e:
        logger.exception("Error during login process: %s", e)
        raise AuthenticationError(f"Login failed: {str(e)}")

@contextmanager
def mycase_session(auto_login: bool = True) -> Generator[Page, None, None]:
    """
    Context manager for MyCase browser session.
    Automatically handles login and resource cleanup.

    Usage:
        with mycase_session() as page:
            page.goto("https://...")
            # do scraping work

    Args:
        auto_login: If True, ensures user is logged in before yielding

    Yields:
        Page: Playwright page object ready for scraping

    Raises:
        AuthenticationError: If login fails (when auto_login=True)
    """
    p = None
    context = None
    page = None

    try:
        p, context, page = _create_playwright_context(persistent=True)

        if auto_login:
            _ensure_logged_in(page)

        yield page

    finally:
        # Always clean up resources
        try:
            if context:
                context.close()
                logger.debug("Browser context closed")
        except Exception as e:
            logger.warning("Error closing context: %s", e)

        try:
            if p:
                p.stop()
                logger.debug("Playwright instance stopped")
        except Exception as e:
            logger.warning("Error stopping Playwright: %s", e)


@contextmanager
def mycase_session_full() -> Generator[tuple[Playwright, BrowserContext, Page], None, None]:
    """
    Context manager that yields full Playwright objects.
    Use this if you need access to context or playwright instance.

    Usage:
        with mycase_session_full() as (p, ctx, page):
            # access all objects

    Yields:
        tuple: (Playwright instance, BrowserContext, Page)
    """
    p = None
    context = None
    page = None

    try:
        p, context, page = _create_playwright_context(persistent=True)
        _ensure_logged_in(page)
        yield p, context, page

    finally:
        try:
            if context:
                context.close()
        except Exception as e:
            logger.warning("Error closing context: %s", e)

        try:
            if p:
                p.stop()
        except Exception as e:
            logger.warning("Error stopping Playwright: %s", e)